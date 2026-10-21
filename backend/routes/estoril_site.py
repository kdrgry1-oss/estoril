"""
Estoril site içerik yönetimi — JSON dosya tabanlı.

Vitrin (statik Estoril sitesi) ile Facette panelini bağlar:
- Site içeriği (site-content.json) ve ürünler (products.json), vitrinin servis
  edildiği klasördeki JSON dosyalarında tutulur. Vitrin sayfaları bu dosyaları
  fetch ile okur; panelden kaydedince site anında güncellenir.
- Görseller mevcut /api/upload/image endpoint'i ile yüklenir (R2 + WebP optimize);
  dönen URL bu JSON'lara yazılır. Masaüstü/mobil ayrımı JSON şemasında
  img: { desktop, mobile } olarak tutulur.

Kurulum: ESTORIL_SITE_DIR env değişkeni vitrin klasörünü göstermeli
(örn. /var/www/estoril). Yazma izni gerekir.
"""
import json
import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from .deps import logger, require_admin, db

router = APIRouter(prefix="/estoril", tags=["Estoril Site"])

SITE_DIR = os.environ.get("ESTORIL_SITE_DIR", "/var/www/estoril")
CONTENT_FILE = "site-content.json"
PRODUCTS_FILE = "products.json"

MAX_JSON_BYTES = 5 * 1024 * 1024  # 5 MB güvenlik sınırı


def _path(name: str) -> str:
    return os.path.join(SITE_DIR, name)


def _read(name: str):
    p = _path(name)
    if not os.path.exists(p):
        raise HTTPException(status_code=404, detail=f"{name} bulunamadı ({SITE_DIR})")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        logger.error(f"estoril read {name}: {e}")
        raise HTTPException(status_code=500, detail=f"{name} okunamadı: {e}")


def _write_atomic(name: str, data) -> None:
    """Aynı dizine tmp yazıp os.replace ile atomik değiştirir — yarım dosya kalmaz."""
    raw = json.dumps(data, ensure_ascii=False, indent=1)
    if len(raw.encode("utf-8")) > MAX_JSON_BYTES:
        raise HTTPException(status_code=400, detail="İçerik çok büyük (maks 5MB)")
    os.makedirs(SITE_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=SITE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(raw)
        # kaydetmeden önce mevcut dosyanın yedeğini al (tek seviye)
        target = _path(name)
        if os.path.exists(target):
            try:
                os.replace(target, target + ".bak")
            except OSError as e:
                logger.warning(f"estoril backup {name}: {e}")
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# ── Site içeriği (ana sayfa slider'ı, banner, kategori slide'ları, tanıtım sayfaları) ──

@router.get("/site-content")
async def get_site_content():
    """Public — vitrin de bu endpoint'ten okuyabilir (CDN arkasında değilse)."""
    return _read(CONTENT_FILE)


@router.put("/site-content")
async def save_site_content(payload: dict, current_user: dict = Depends(require_admin)):
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="Geçersiz içerik")
    payload["_updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["_updated_by"] = current_user.get("email") or current_user.get("id")
    _write_atomic(CONTENT_FILE, payload)
    return {"success": True}


# ── Ürünler ─────────────────────────────────────────────────────────────────

@router.get("/products")
async def get_products():
    return _read(PRODUCTS_FILE)


@router.put("/products")
async def save_products(payload: list, current_user: dict = Depends(require_admin)):
    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=400, detail="Ürün listesi boş olamaz")
    for p in payload:
        if not isinstance(p, dict) or not str(p.get("name", "")).strip():
            raise HTTPException(status_code=400, detail="Her ürünün adı olmalı")
    _write_atomic(PRODUCTS_FILE, payload)
    return {"success": True, "count": len(payload)}


@router.put("/products/{index}")
async def save_product(index: int, payload: dict, current_user: dict = Depends(require_admin)):
    """Tek ürünü index ile günceller (vitrin ürünleri index'le linkler: ?i=78)."""
    products = _read(PRODUCTS_FILE)
    if not (0 <= index < len(products)):
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    allowed = {"name", "img", "imgs", "price", "sale", "cats", "stock", "desc"}
    for key, val in payload.items():
        if key in allowed:
            products[index][key] = val
    _write_atomic(PRODUCTS_FILE, products)
    return {"success": True, "index": index}


@router.get("/storefront-products")
async def storefront_products():
    cats = {}
    async for c in db.categories.find({}, {"_id": 0, "id": 1, "name": 1, "parent_id": 1}):
        cats[c["id"]] = c
    def path_of(cid):
        parts, seen = [], set()
        while cid and cid in cats and cid not in seen:
            seen.add(cid); parts.append(cats[cid]["name"]); cid = cats[cid].get("parent_id")
        return " > ".join(reversed(parts))
    out = []
    async for p in db.products.find({}, {"_id": 0}).sort("created_at", 1):
        imgs = [(i.get("url") if isinstance(i, dict) else i) for i in (p.get("images") or [])]
        cids = p.get("category_ids") or ([p.get("category_id")] if p.get("category_id") else [])
        out.append({
            "name": p.get("name", ""), "price": p.get("price"), "sale": p.get("sale_price"),
            "stock": (p.get("stock", 0) or 0) > 0,
            "cats": [x for x in (path_of(c) for c in cids if c) if x],
            "img": imgs[0] if imgs else "", "imgs": imgs,
            "desc": p.get("description", ""), "type": "simple",
        })
    return out


# ===== ESTORIL MAIL ACCOUNTS =====
import subprocess as _subprocess
import re as _re
from typing import Optional as _Optional
from pydantic import BaseModel as _BaseModel

_MAIL_BIN = "/usr/local/bin/estoril-mail"

class _MailAcct(_BaseModel):
    email: str
    password: _Optional[str] = None

def _run_mail(args):
    try:
        return _subprocess.run(["sudo", "-n", _MAIL_BIN, *args],
                               capture_output=True, text=True, timeout=30)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"mail komutu calismadi: {e}")

@router.get("/mail/accounts")
async def mail_accounts_list(current_user: dict = Depends(require_admin)):
    p = _run_mail(["list"])
    accs = [ln.strip() for ln in p.stdout.splitlines() if "@" in ln]
    return {"accounts": accs}

@router.post("/mail/accounts")
async def mail_accounts_add(payload: _MailAcct, current_user: dict = Depends(require_admin)):
    email = (payload.email or "").strip().lower()
    pw = payload.password or ""
    local = email.split("@")[0] if "@" in email else email
    if not local or not _re.match(r"^[a-z0-9._-]+$", local):
        raise HTTPException(status_code=400, detail="Gecersiz kullanici adi (a-z 0-9 . _ -)")
    if len(pw) < 6:
        raise HTTPException(status_code=400, detail="Sifre en az 6 karakter olmali")
    p = _run_mail(["add", email, pw])
    if p.returncode != 0:
        raise HTTPException(status_code=400, detail=(p.stdout + p.stderr).strip() or "Eklenemedi")
    return {"ok": True, "message": p.stdout.strip()}

@router.post("/mail/accounts/password")
async def mail_accounts_pw(payload: _MailAcct, current_user: dict = Depends(require_admin)):
    email = (payload.email or "").strip().lower()
    pw = payload.password or ""
    if len(pw) < 6:
        raise HTTPException(status_code=400, detail="Sifre en az 6 karakter olmali")
    p = _run_mail(["passwd", email, pw])
    if p.returncode != 0:
        raise HTTPException(status_code=400, detail=(p.stdout + p.stderr).strip() or "Degistirilemedi")
    return {"ok": True, "message": p.stdout.strip()}

@router.delete("/mail/accounts")
async def mail_accounts_del(payload: _MailAcct, current_user: dict = Depends(require_admin)):
    email = (payload.email or "").strip().lower()
    p = _run_mail(["del", email])
    if p.returncode != 0:
        raise HTTPException(status_code=400, detail=(p.stdout + p.stderr).strip() or "Silinemedi")
    return {"ok": True, "message": p.stdout.strip()}
