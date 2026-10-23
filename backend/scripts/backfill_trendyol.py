"""
=============================================================================
backfill_trendyol.py — TEK SEFERLİK Trendyol geçmiş sipariş + ürün backfill
=============================================================================
Ne yapar:
  1) SİPARİŞLER: Trendyol sipariş ucu ~14 günlük pencereye izin verdiği için,
     --days gün öncesine kadar 14'er günlük pencerelerle GERİYE doğru tüm
     siparişleri çeker ve db.orders'a upsert eder (map_trendyol_order ile).
     NOT: Geçmiş siparişler için STOK DÜŞÜMÜ YAPILMAZ (bunlar eski siparişler).
  2) ÜRÜNLER: Trendyol'daki tüm ürünleri (get_filtered_products) sayfalı çeker.
     - Barkodu DB'de zaten varsa: dokunmaz (matched).
     - Ürün adı panelde EŞLEŞİYORSA: o ürüne barcode + stock_code atar (boşsa).
     - Hiç eşleşmezse ve --create ise: panele TASLAK ürün olarak ekler
       (is_active=False — incelenip yayınlanmak üzere).

Çalıştırma (sunucuda):
  cd /opt/estoril/backend
  venv/bin/python -m scripts.backfill_trendyol --days 180
  # sadece siparişler:   --orders-only
  # sadece ürünler:      --products-only
  # eşleşmeyeni ekleme:  --no-create
=============================================================================
"""
import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# backend/ kökünü yola ekle (trendyol_client, routes.* için)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.deps import db, generate_id  # noqa: E402
from routes.integrations_trendyol import (  # noqa: E402
    get_trendyol_config, map_trendyol_order, _ms_to_iso,
)
from trendyol_client import TrendyolClient  # noqa: E402

_TR = str.maketrans("çğıöşü", "cgiosu")


def _norm(s: str) -> str:
    """İsim karşılaştırması için normalize: küçük harf + TR katlama + boşluk sadeleştir."""
    return re.sub(r"\s+", " ", (s or "").strip().lower().translate(_TR))


async def _build_client():
    cfg = await get_trendyol_config()
    if not cfg.get("is_active"):
        raise SystemExit("Trendyol entegrasyonu yapılandırılmamış (settings.id=trendyol).")
    return TrendyolClient(
        supplier_id=cfg["supplier_id"], api_key=cfg["api_key"],
        api_secret=cfg["api_secret"], mode=cfg["mode"],
    )


async def backfill_orders(client, days: int):
    now = datetime.now()
    earliest = now - timedelta(days=days)
    win = timedelta(days=14)
    imported = updated = scanned = 0
    cur_end = now
    while cur_end > earliest:
        cur_start = max(cur_end - win, earliest)
        s_ms = int(cur_start.timestamp() * 1000)
        e_ms = int(cur_end.timestamp() * 1000)
        page = 0
        while page < 50:
            resp = await client.get_orders(start_date_ms=s_ms, end_date_ms=e_ms, size=200, page=page)
            content = resp.get("content") or []
            for t in content:
                scanned += 1
                onum = t.get("orderNumber")
                try:
                    existing = await db.orders.find_one({"order_number": str(onum), "platform": "trendyol"})
                    od = map_trendyol_order(t)
                    if existing:
                        await db.orders.update_one(
                            {"_id": existing["_id"]},
                            {"$set": {k: v for k, v in od.items() if k != "status"}})
                        updated += 1
                    else:
                        od["id"] = generate_id()
                        od["created_at"] = _ms_to_iso(t.get("orderDate")) or datetime.now(timezone.utc).isoformat()
                        await db.orders.insert_one(od)
                        imported += 1
                except Exception as e:
                    print(f"  [sipariş hata] {onum}: {e}")
            total_pages = resp.get("totalPages") or 0
            page += 1
            if not content or page >= total_pages:
                break
        print(f"  pencere {cur_start:%Y-%m-%d} → {cur_end:%Y-%m-%d}: tarandı={scanned} yeni={imported} güncel={updated}")
        cur_end = cur_start
    return {"scanned": scanned, "imported": imported, "updated": updated}


async def backfill_products(client, create_missing: bool):
    # Mevcut panel ürünlerini isim + barkod indexle
    name_index = {}
    barcode_set = set()
    async for p in db.products.find({}, {"_id": 1, "name": 1, "barcode": 1, "stock_code": 1}):
        nm = _norm(p.get("name"))
        if nm and nm not in name_index:
            name_index[nm] = p
        if p.get("barcode"):
            barcode_set.add(str(p["barcode"]))
    created = matched = assigned = skipped = 0
    page = 0
    while page < 60:
        res = await client.get_filtered_products(page=page, size=200, archived=False)
        content = res.get("content") or []
        for row in content:
            bc = str(row.get("barcode") or "").strip()
            sc = str(row.get("stockCode") or "").strip()
            title = row.get("title") or ""
            if not bc:
                skipped += 1
                continue
            if bc in barcode_set:
                matched += 1
                continue
            m = name_index.get(_norm(title))
            if m:
                upd = {}
                if not m.get("barcode"):
                    upd["barcode"] = bc
                if not m.get("stock_code"):
                    upd["stock_code"] = sc or bc
                if upd:
                    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
                    await db.products.update_one({"_id": m["_id"]}, {"$set": upd})
                    assigned += 1
                    barcode_set.add(bc)
                else:
                    matched += 1
            elif create_missing:
                imgs = [i.get("url") for i in (row.get("images") or []) if isinstance(i, dict) and i.get("url")]
                if not imgs and row.get("imageUrl"):
                    imgs = [row["imageUrl"]]
                doc = {
                    "id": generate_id(),
                    "name": title,
                    "barcode": bc,
                    "stock_code": sc or bc,
                    "price": row.get("listPrice") or row.get("salePrice") or 0,
                    "sale_price": row.get("salePrice"),
                    "stock": row.get("quantity") or 0,
                    "brand": row.get("brand") or "",
                    "images": [{"url": u} for u in imgs],
                    "is_active": False,          # taslak — incelenip yayınlanacak
                    "source": "trendyol_backfill",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.products.insert_one(doc)
                created += 1
                barcode_set.add(bc)
        total_pages = res.get("totalPages") or 0
        page += 1
        if not content or page >= total_pages:
            break
    return {"created": created, "assigned_barcode": assigned, "already_matched": matched, "skipped_no_barcode": skipped}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180, help="Kaç gün geriye sipariş (varsayılan 180)")
    ap.add_argument("--orders-only", action="store_true")
    ap.add_argument("--products-only", action="store_true")
    ap.add_argument("--no-create", action="store_true", help="Eşleşmeyen Trendyol ürünlerini panele EKLEME")
    args = ap.parse_args()

    client = await _build_client()

    if not args.products_only:
        print(f"== SİPARİŞ BACKFILL ({args.days} gün) ==")
        r = await backfill_orders(client, args.days)
        print(f">> SİPARİŞ: {r['imported']} yeni, {r['updated']} güncellendi (tarandı {r['scanned']}).")

    if not args.orders_only:
        print("== ÜRÜN BACKFILL ==")
        r = await backfill_products(client, create_missing=not args.no_create)
        print(f">> ÜRÜN: {r['assigned_barcode']} ürüne barkod atandı, {r['created']} taslak eklendi, "
              f"{r['already_matched']} zaten eşleşik, {r['skipped_no_barcode']} barkodsuz atlandı.")

    print("TAMAMLANDI.")


if __name__ == "__main__":
    asyncio.run(main())
