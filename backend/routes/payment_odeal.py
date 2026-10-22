"""
=============================================================================
payment_odeal.py — ÖdeAl ödeme (sanal POS) akışı
=============================================================================

ÖdeAl ödeme modeli (D2D/App2App + payment-result callback):
  - Ayarlar: db.settings (id="odeal") → merchant_id, api_key, api_secret,
    callback_secret, mode(live/sandbox). Base: api(.stg).odeal.com/api/v1
  - Ödeme sonucu ÖdeAl'dan 'payment-result' callback'i ile gelir; siparişi
    "ödendi" işaretleriz. Ödeme ÖdeAl'dan geçtiği için e-Fatura'yı da ÖdeAl
    otomatik oluşturup einvoice_odeal callback'i ile bildirir.

DURUM / GÜVENLİK NOTU:
  Kart çekimini BAŞLATAN uç (get-token / create-payment) ÖdeAl'ın hesaba
  özel API dökümanını (endpoint + auth + imza şeması) gerektirir. Gerçek para
  işleyen bir akışı TAHMİNLE yazmak güvenli olmadığından `initialize` dökümanı
  gelene kadar bilinçli olarak hata döndürür (sahte "başarılı" ÜRETMEZ).
  payment-result callback'i ise dökümante olduğu için şimdiden hazırdır.
=============================================================================
"""
import base64
import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .deps import db, logger

router = APIRouter(prefix="/payment/odeal", tags=["Payment ÖdeAl"])

BASE_STG = "https://api.stg.odeal.com/api/v1"
BASE_PROD = "https://api.odeal.com/api/v1"


async def _settings() -> dict:
    s = await db.settings.find_one({"id": "odeal"}, {"_id": 0}) or {}
    mid = s.get("merchant_id"); key = s.get("api_key"); sec = s.get("api_secret")
    if not (mid and key):
        raise HTTPException(status_code=400, detail="ÖdeAl ödeme bilgileri eksik. Panel > Entegrasyonlar > ÖdeAl.")
    mode = s.get("mode", "sandbox")
    live = mode in ("live", "production", "prod", "canli", "canlı")
    return {"merchant_id": str(mid), "api_key": str(key), "api_secret": str(sec or ""),
            "callback_secret": str(s.get("callback_secret") or ""),
            "base": BASE_PROD if live else BASE_STG, "live": live}


def _first(d: dict, *keys):
    if not isinstance(d, dict):
        return None
    low = {str(k).lower().replace("_", ""): v for k, v in d.items()}
    for k in keys:
        n = k.lower().replace("_", "")
        if n in low and low[n] not in (None, ""):
            return low[n]
    return None


@router.post("/initialize")
async def initialize_payment(order_id: str, request: Request):
    """ÖdeAl sanal POS ödeme başlatma. Kart çekim ucu için ÖdeAl API dökümanı gerekli."""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
    await _settings()  # creds var mı kontrol (yoksa 400)
    # Dökümanı olmayan kart-çekim ucunu TAHMİNLE üretmiyoruz (para güvenliği).
    return {
        "success": False,
        "needs_spec": True,
        "message": ("ÖdeAl sanal POS ödeme başlatma ucu için ÖdeAl'ın hesaba özel API "
                    "dökümanı gerekli (create-payment/get-token endpoint'i, auth başlığı, "
                    "imza şeması). Döküman gelince bu uç tamamlanacak. payment-result "
                    "callback'i hazır: /api/payment/odeal/callback"),
    }


@router.post("/callback")
async def payment_callback(request: Request):
    """ÖdeAl payment-result bildirimi. Siparişi 'ödendi' işaretler, onay akışını tetikler."""
    raw = ""
    try:
        raw = (await request.body()).decode("utf-8", "replace")
    except Exception:
        raw = ""
    try:
        data = await request.json()
    except Exception:
        try:
            data = dict(await request.form())
        except Exception:
            data = {}

    try:
        await db.payment_callbacks.insert_one({
            "provider": "odeal", "received_at": datetime.now(timezone.utc).isoformat(),
            "raw": raw[:8000], "parsed": data if isinstance(data, dict) else {},
        })
    except Exception:
        pass

    s = await db.settings.find_one({"id": "odeal"}, {"_id": 0}) or {}
    secret = str(s.get("callback_secret") or "").strip()
    if secret:
        sig = request.headers.get("x-odeal-signature") or request.headers.get("x-signature") or ""
        hx = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
        b64 = base64.b64encode(hmac.new(secret.encode(), raw.encode(), hashlib.sha256).digest()).decode()
        if sig and sig not in (hx, b64):
            logger.warning("ÖdeAl payment callback imza uyuşmuyor — işlenmedi.")
            return PlainTextResponse("OK")

    data = data if isinstance(data, dict) else {}
    for nest in ("data", "payment", "result", "payload"):
        if isinstance(data.get(nest), dict):
            m = dict(data); m.update(data[nest]); data = m; break

    ref = _first(data, "orderId", "order_id", "referenceCode", "referenceId",
                 "orderNumber", "order_number", "merchant_oid", "basketId")
    status = str(_first(data, "status", "paymentStatus", "result") or "").lower()
    success = bool(_first(data, "success", "isSuccess")) or status in ("success", "paid", "completed", "approved", "basarili")

    if not ref:
        logger.warning("ÖdeAl payment callback: referans yok (HAM loglandı).")
        return PlainTextResponse("OK")
    order = await db.orders.find_one(
        {"$or": [{"id": ref}, {"order_number": ref}, {"odeal_order_ref": ref}]}, {"_id": 0})
    if not order:
        logger.warning(f"ÖdeAl payment callback: sipariş eşleşmedi ref={ref}")
        return PlainTextResponse("OK")
    if order.get("payment_status") == "paid":
        return PlainTextResponse("OK")

    now = datetime.now(timezone.utc).isoformat()
    if success:
        await db.orders.update_one(
            {"id": order.get("id"), "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": "paid", "paid_at": now, "status": "confirmed",
                      "payment_provider": "odeal", "payment_id": str(ref), "updated_at": now}})
        logger.info(f"ÖdeAl payment PAID order={order.get('order_number')} ref={ref}")
        try:
            from .payment import _notify_paid_order_confirmed
            await _notify_paid_order_confirmed(order.get("id"))
        except Exception as e:
            logger.warning(f"ÖdeAl onay bildirimi hata: {e}")
        try:
            from .orders import dispatch_purchase_capi
            await dispatch_purchase_capi(order.get("id"), source="odeal_callback")
        except Exception as e:
            logger.warning(f"ÖdeAl CAPI purchase hata: {e}")
    else:
        await db.orders.update_one(
            {"id": order.get("id"), "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": "failed", "updated_at": now}})
        logger.info(f"ÖdeAl payment FAILED order={order.get('order_number')} ref={ref}")
    return PlainTextResponse("OK")
