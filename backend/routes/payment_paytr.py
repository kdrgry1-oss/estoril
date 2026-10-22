"""
=============================================================================
payment_paytr.py — PayTR iFrame API ödeme akışı
=============================================================================

iyzico (payment.py) ile aynı sipariş/ödeme akışının PayTR karşılığı:

  POST /api/payment/paytr/initialize → siparişten PayTR token'ı üretir,
                                        iframe URL'i döndürür.
  POST /api/payment/paytr/callback   → PayTR bildirim (notification) POST'u;
                                        hash doğrulanır, sipariş "ödendi"
                                        işaretlenir, düz metin "OK" döner
                                        (PayTR şartı; aksi halde tekrar dener).

Kimlik: merchant_id + merchant_key + merchant_salt (HMAC-SHA256, base64).
Ayarlar: db.settings (id="paytr") → merchant_id, api_key(=merchant_key),
         api_secret(=merchant_salt), mode(live/sandbox).
Not: Ödeme onaylanınca onay maili + CAPI purchase payment.py'deki ortak
     yardımcılar üzerinden tetiklenir (tek event, idempotent).
=============================================================================
"""
import base64
import hashlib
import hmac
import json
import re
import secrets as _secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .deps import db, logger

router = APIRouter(prefix="/payment/paytr", tags=["Payment PayTR"])

TOKEN_URL = "https://www.paytr.com/odeme/api/get-token"
IFRAME_URL = "https://www.paytr.com/odeme/guest/{token}"


async def _get_paytr_settings() -> dict:
    s = await db.settings.find_one({"id": "paytr"}, {"_id": 0})
    # merchant_key = api_key, merchant_salt = api_secret (generic marketplace-settings şeması)
    mid = (s or {}).get("merchant_id")
    key = (s or {}).get("api_key")
    salt = (s or {}).get("api_secret")
    if not (mid and key and salt):
        raise HTTPException(status_code=400, detail="PayTR ödeme bilgileri eksik. Lütfen admin panelinden ayarlayın.")
    mode = (s or {}).get("mode", "sandbox")
    test_mode = 0 if mode in ("live", "production", "prod", "canli", "canlı") else 1
    return {"merchant_id": str(mid), "merchant_key": str(key), "merchant_salt": str(salt), "test_mode": test_mode}


def _b64_hmac(message: str, key: str) -> str:
    return base64.b64encode(hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()).decode("utf-8")


def _build_basket(order: dict) -> list:
    """PayTR user_basket: [[ürün adı, birim fiyat (str), adet], ...]."""
    basket = []
    for it in (order.get("items") or []):
        name = str(it.get("name") or it.get("title") or "Ürün")[:120]
        qty = int(it.get("quantity") or 1)
        unit = round(float(it.get("price") or 0), 2)
        basket.append([name, f"{unit:.2f}", qty])
    shipping = round(float(order.get("shipping_cost") or 0), 2)
    if shipping > 0.009:
        basket.append(["Kargo", f"{shipping:.2f}", 1])
    if not basket:
        basket.append(["Sipariş", f"{round(float(order.get('total') or 0), 2):.2f}", 1])
    return basket


def _client_ip(request: Request, order: dict) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return order.get("customer_ip") or (request.client.host if request.client else "0.0.0.0")


@router.post("/initialize")
async def initialize_payment(order_id: str, ok_url: str, fail_url: str, request: Request):
    """Sipariş için PayTR iFrame token'ı üretir; iframe URL döndürür."""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı")

    s = await _get_paytr_settings()
    ship = order.get("shipping_address") or {}
    email = (ship.get("email") or order.get("email") or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        email = "siparis@estoril.com.tr"

    total = round(float(order.get("total") or 0), 2)
    if total <= 0:
        raise HTTPException(status_code=400, detail="Sipariş tutarı geçersiz")
    payment_amount = int(round(total * 100))  # kuruş

    # PayTR merchant_oid: yalnızca harf+rakam, benzersiz. Tekrar denemelerde yeni üretilir.
    merchant_oid = (re.sub(r"[^A-Za-z0-9]", "", str(order_id))[:50] or "SIP") + _secrets.token_hex(4)
    user_ip = _client_ip(request, order)
    basket = _build_basket(order)
    user_basket = base64.b64encode(json.dumps(basket, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    no_installment = 0
    max_installment = 0
    currency = "TL"

    name = ((ship.get("first_name") or "") + " " + (ship.get("last_name") or "")).strip() or "Müşteri"
    phone = str(ship.get("phone") or order.get("phone") or "")
    address = str(ship.get("address") or "Adres")

    hash_str = (f"{s['merchant_id']}{user_ip}{merchant_oid}{email}{payment_amount}"
                f"{user_basket}{no_installment}{max_installment}{currency}{s['test_mode']}")
    paytr_token = _b64_hmac(hash_str + s["merchant_salt"], s["merchant_key"])

    form = {
        "merchant_id": s["merchant_id"],
        "user_ip": user_ip,
        "merchant_oid": merchant_oid,
        "email": email,
        "payment_amount": payment_amount,
        "paytr_token": paytr_token,
        "user_basket": user_basket,
        "debug_on": 1 if s["test_mode"] else 0,
        "no_installment": no_installment,
        "max_installment": max_installment,
        "user_name": name,
        "user_address": address,
        "user_phone": phone,
        "merchant_ok_url": ok_url,
        "merchant_fail_url": fail_url,
        "timeout_limit": 30,
        "currency": currency,
        "test_mode": s["test_mode"],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(TOKEN_URL, data=form)
        data = resp.json()
    except Exception as e:
        logger.error(f"PayTR get-token error: {e}")
        raise HTTPException(status_code=502, detail=f"PayTR bağlantı hatası: {e}")

    if data.get("status") != "success":
        logger.warning(f"PayTR token failed order={order_id}: {data.get('reason')}")
        return {"success": False, "error": data.get("reason") or "Ödeme başlatılamadı"}

    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "paytr_merchant_oid": merchant_oid,
            "paytr_amount": payment_amount,
            "payment_provider": "paytr",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    return {
        "success": True,
        "token": data.get("token"),
        "iframe_url": IFRAME_URL.format(token=data.get("token")),
    }


@router.post("/callback")
async def payment_callback(request: Request):
    """PayTR bildirim POST'u. Hash doğrular, siparişi günceller, 'OK' döner."""
    form = await request.form()
    merchant_oid = form.get("merchant_oid") or ""
    status = form.get("status") or ""
    total_amount = form.get("total_amount") or ""
    received_hash = form.get("hash") or ""

    s = await _get_paytr_settings()
    expected = _b64_hmac(f"{merchant_oid}{s['merchant_salt']}{status}{total_amount}", s["merchant_key"])
    if not hmac.compare_digest(expected, received_hash):
        logger.warning(f"PayTR callback hash uyuşmuyor oid={merchant_oid}")
        # Hatalı hash'te PayTR'ye 'OK' DÖNMÜYORUZ (sahte bildirim).
        raise HTTPException(status_code=400, detail="PAYTR notification failed: bad hash")

    order = await db.orders.find_one({"paytr_merchant_oid": merchant_oid}, {"_id": 0})
    if not order:
        logger.warning(f"PayTR callback: sipariş bulunamadı oid={merchant_oid}")
        # Sipariş yoksa da PayTR tekrar denemesin diye OK döneriz.
        return PlainTextResponse("OK")

    # Zaten ödenmişse tekrar işleme (idempotent).
    if order.get("payment_status") == "paid":
        return PlainTextResponse("OK")

    paid = status == "success"
    # Tutar doğrulaması: PayTR total_amount (kuruş) = initialize'da gönderilen tutar.
    if paid:
        try:
            if int(total_amount) != int(order.get("paytr_amount") or -1):
                logger.warning(f"PayTR tutar uyuşmuyor oid={merchant_oid} gelen={total_amount} beklenen={order.get('paytr_amount')}")
                paid = False
        except (TypeError, ValueError):
            paid = False

    now = datetime.now(timezone.utc).isoformat()
    if paid:
        await db.orders.update_one(
            {"id": order.get("id"), "payment_status": {"$ne": "paid"}},
            {"$set": {
                "payment_status": "paid",
                "payment_id": merchant_oid,
                "paytr_payment_id": merchant_oid,
                "paid_at": now,
                "status": "confirmed",
                "updated_at": now,
            }},
        )
        logger.info(f"PayTR payment PAID order={order.get('order_number')} oid={merchant_oid}")
        try:
            from .payment import _notify_paid_order_confirmed
            await _notify_paid_order_confirmed(order.get("id"))
        except Exception as e:
            logger.warning(f"PayTR onay bildirimi hata: {e}")
        try:
            from .orders import dispatch_purchase_capi
            await dispatch_purchase_capi(order.get("id"), source="paytr_callback")
        except Exception as e:
            logger.warning(f"PayTR CAPI purchase hata: {e}")
    else:
        reason = form.get("failed_reason_msg") or form.get("failed_reason_code") or ""
        await db.orders.update_one(
            {"id": order.get("id"), "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": "failed", "paytr_fail_reason": str(reason)[:300], "updated_at": now}},
        )
        logger.info(f"PayTR payment FAILED order={order.get('order_number')} oid={merchant_oid} reason={reason}")

    return PlainTextResponse("OK")
