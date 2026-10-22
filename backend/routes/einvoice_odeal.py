"""
=============================================================================
einvoice_odeal.py — ÖdeAl e-Fatura / e-Arşiv callback alıcısı
=============================================================================

ÖdeAl modeli (Doğan'dan FARKLI):
  ÖdeAl'da sunucudan "faturayı şimdi kes" diye çağrılan bir REST ucu YOKTUR.
  Ödeme ÖdeAl üzerinden tamamlandığında e-Fatura / e-Arşiv faturası ÖdeAl
  tarafından OTOMATİK oluşturulur ve partner'a "E-Invoice Created" callback'i
  ile bildirilir (ÖdeAl D2D dökümanı). Bu yüzden entegrasyonun doğru şekli:
  o callback'i karşılayıp ilgili siparişe fatura bilgisini (no / PDF / tip)
  yazmaktır.

Kurulum (ÖdeAl configuration servisi → E-Invoice Created callback URL):
  https://panel.estoril.com.tr/api/einvoice/odeal/callback

Not: ÖdeAl'ın gönderdiği alan adları hesaba/sürüme göre değişebildiğinden,
gelen gövde esnek okunur ve HAM gövde db.einvoice_callbacks'e loglanır —
ilk gerçek callback geldiğinde alan eşlemesi kesinleştirilebilir.
=============================================================================
"""
import hmac
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import PlainTextResponse

from .deps import db, logger, require_admin

router = APIRouter(prefix="/einvoice/odeal", tags=["E-Invoice ÖdeAl"])


def _first(d: dict, *keys):
    """Verilen anahtarlardan ilk dolu olanı döndürür (büyük/küçük/alt tire toleranslı)."""
    if not isinstance(d, dict):
        return None
    lower = {str(k).lower().replace("_", ""): v for k, v in d.items()}
    for k in keys:
        norm = k.lower().replace("_", "")
        if norm in lower and lower[norm] not in (None, ""):
            return lower[norm]
    return None


async def _odeal_secret() -> str:
    s = await db.settings.find_one({"id": "odeal"}, {"_id": 0}) or {}
    return str(s.get("callback_secret") or "").strip()


@router.post("/callback")
async def odeal_einvoice_callback(request: Request):
    """ÖdeAl 'E-Invoice Created' bildirimi. Faturayı eşleşen siparişe yazar."""
    # Gövdeyi hem JSON hem form olarak dene
    raw_text = ""
    payload = {}
    try:
        raw_text = (await request.body()).decode("utf-8", "replace")
    except Exception:
        raw_text = ""
    try:
        payload = await request.json()
    except Exception:
        try:
            payload = dict(await request.form())
        except Exception:
            payload = {}

    # HAM kaydı — alan eşlemesini doğrulamak için (idempotent değil, append).
    try:
        await db.einvoice_callbacks.insert_one({
            "provider": "odeal",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "headers": {k: v for k, v in request.headers.items() if k.lower() in
                        ("content-type", "x-odeal-signature", "x-signature", "user-agent")},
            "raw": raw_text[:8000],
            "parsed": payload if isinstance(payload, dict) else {},
        })
    except Exception as e:
        logger.warning(f"ÖdeAl callback log hatası: {e}")

    # Opsiyonel imza doğrulaması (ÖdeAl secret tanımlıysa).
    secret = await _odeal_secret()
    if secret:
        sig = request.headers.get("x-odeal-signature") or request.headers.get("x-signature") or ""
        expected = hmac.new(secret.encode(), raw_text.encode(), hashlib.sha256).hexdigest()
        exp_b64 = __import__("base64").b64encode(
            hmac.new(secret.encode(), raw_text.encode(), hashlib.sha256).digest()).decode()
        if sig and sig not in (expected, exp_b64):
            logger.warning("ÖdeAl callback imza uyuşmuyor — yine de loglandı, işlenmedi.")
            return PlainTextResponse("OK")  # PayTR gibi: tekrar denemesin diye OK

    data = payload if isinstance(payload, dict) else {}
    # ÖdeAl bazen veriyi iç içe bir anahtarda gönderebilir
    for nest in ("data", "invoice", "eInvoice", "einvoice", "result", "payload"):
        if isinstance(data.get(nest), dict):
            inner = data[nest]
            merged = dict(data)
            merged.update(inner)
            data = merged
            break

    order_ref = _first(data, "orderId", "order_id", "merchant_oid", "merchantOid",
                        "referenceCode", "referenceId", "orderNumber", "order_number",
                        "basketId", "conversationId")
    invoice_number = _first(data, "invoiceNumber", "invoice_no", "documentNumber",
                             "documentId", "invoiceId", "ettn", "uuid")
    invoice_url = _first(data, "invoiceUrl", "pdfUrl", "documentUrl", "url", "pdf")
    invoice_type = (_first(data, "invoiceType", "documentType", "type") or "").lower()
    if "arsiv" in invoice_type or "archive" in invoice_type:
        invoice_type = "e-arsiv"
    elif "fatura" in invoice_type or "invoice" in invoice_type:
        invoice_type = "e-fatura"
    else:
        invoice_type = invoice_type or "e-arsiv"

    if not order_ref:
        logger.warning("ÖdeAl callback: sipariş referansı bulunamadı (HAM loglandı).")
        return PlainTextResponse("OK")

    # Siparişi birkaç olası alanda eşleştir
    order = await db.orders.find_one(
        {"$or": [
            {"id": order_ref},
            {"order_number": order_ref},
            {"paytr_merchant_oid": order_ref},
            {"odeal_order_ref": order_ref},
        ]}, {"_id": 0})
    if not order:
        logger.warning(f"ÖdeAl callback: sipariş eşleşmedi ref={order_ref} (HAM loglandı).")
        return PlainTextResponse("OK")

    now = datetime.now(timezone.utc).isoformat()
    update = {
        "invoice_issued": True,
        "invoice_provider": "odeal",
        "invoice_type": invoice_type,
        "invoice_issued_at": now,
        "updated_at": now,
    }
    if invoice_number:
        update["invoice_number"] = str(invoice_number)
    if invoice_url:
        update["invoice_url"] = str(invoice_url)

    await db.orders.update_one({"id": order.get("id")}, {"$set": update})
    logger.info(f"ÖdeAl e-fatura kaydedildi order={order.get('order_number')} "
                f"no={invoice_number} tip={invoice_type}")
    return PlainTextResponse("OK")


@router.get("/callbacks")
async def list_odeal_callbacks(limit: int = 20, user=Depends(require_admin)):
    """Son ÖdeAl callback'lerini (HAM dahil) döndürür — alan eşlemesini doğrulamak için."""
    rows = await db.einvoice_callbacks.find(
        {"provider": "odeal"}, {"_id": 0}).sort("received_at", -1).to_list(min(limit, 100))
    return {"count": len(rows), "callbacks": rows}
