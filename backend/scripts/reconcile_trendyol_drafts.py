"""
=============================================================================
reconcile_trendyol_drafts.py — Trendyol taslak ürünlerini mevcut ürünlerle
çok-sinyalli eşleştir, barkodu GERÇEK ürüne taşı, duplike taslağı temizle.
=============================================================================
Eşleştirme sinyalleri (güçlüden zayıfa):
  1) Stok kodu / stockCode eşleşmesi (kesin)            → skor 1.00
  2) Bulanık ad benzerliği (token örtüşmesi + difflib)  → 0..1
  3) (opsiyonel --images) görsel algısal hash (aHash)   → 0..1

Varsayılan: RAPOR modu (hiçbir şey değişmez) → /tmp/reconcile_trendyol.csv
  --apply            : yüksek güvenli eşleşmeleri UYGULA (barkodu gerçek ürüne
                       ata + duplike taslağı sil)
  --name-threshold X : ad benzerliği eşiği (varsayılan 0.86)
  --review-threshold X: incele listesi alt eşiği (varsayılan 0.70)
  --images           : görsel aHash sinyalini de kullan (yavaş; ağ indirir)

Çalıştırma:
  cd /opt/estoril/backend
  MONGO_URL="mongodb://127.0.0.1:27017" DB_NAME="estoril" \
    venv/bin/python -m scripts.reconcile_trendyol_drafts            # rapor
  ... --apply                                                       # uygula
=============================================================================
"""
import argparse
import csv
import difflib
import io
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

import pymongo

_TR = str.maketrans("çğıöşü", "cgiosu")
_STOP = {"estoril", "cihazi", "cihazı", "cihaz", "profesyonel", "yeni", "model", "adet",
         "ve", "ile", "for", "the", "set", "li", "lu"}


def _norm(s):
    s = (s or "").strip().lower().translate(_TR)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s):
    return {t for t in _norm(s).split() if len(t) > 1 and t not in _STOP}


def _name_score(a, b):
    """0..1 — token örtüşmesi (Dice) ile difflib oranının maksimumu."""
    ta, tb = _tokens(a), _tokens(b)
    dice = (2 * len(ta & tb) / (len(ta) + len(tb))) if (ta and tb) else 0.0
    seq = difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()
    return max(dice, seq)


def _codes(p):
    """Bir ürünün olası kod kümesi (stok kodu/sku/id/barkod + varyantlar)."""
    out = set()
    for k in ("stock_code", "sku", "id", "barcode", "productMainId"):
        v = p.get(k)
        if v:
            out.add(str(v).strip())
    for v in (p.get("variants") or []):
        for k in ("stock_code", "sku", "barcode"):
            if v.get(k):
                out.add(str(v[k]).strip())
    return {c for c in out if c}


# ── Opsiyonel görsel aHash ────────────────────────────────────────────────
_IMG_CACHE = {}


def _ahash(url):
    if not url:
        return None
    if url in _IMG_CACHE:
        return _IMG_CACHE[url]
    try:
        from PIL import Image
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=15).read()
        im = Image.open(io.BytesIO(data)).convert("L").resize((8, 8))
        px = list(im.getdata())
        avg = sum(px) / len(px)
        bits = 0
        for i, v in enumerate(px):
            if v >= avg:
                bits |= (1 << i)
        _IMG_CACHE[url] = bits
        return bits
    except Exception:
        _IMG_CACHE[url] = None
        return None


def _img_score(a_url, b_url):
    ha, hb = _ahash(a_url), _ahash(b_url)
    if ha is None or hb is None:
        return 0.0
    dist = bin(ha ^ hb).count("1")      # 0..64 hamming
    return max(0.0, 1 - dist / 16.0)    # ≤16 bit fark → benzer kabul


def _img_url(p):
    imgs = p.get("images") or []
    if imgs:
        first = imgs[0]
        return first.get("url") if isinstance(first, dict) else first
    return p.get("img") or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--name-threshold", type=float, default=0.86)
    ap.add_argument("--review-threshold", type=float, default=0.70)
    ap.add_argument("--images", action="store_true")
    ap.add_argument("--out", default="/tmp/reconcile_trendyol.csv")
    args = ap.parse_args()

    db = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017"))[
        os.environ.get("DB_NAME", "estoril")]

    drafts = list(db.products.find({"source": "trendyol_backfill"}))
    originals = list(db.products.find({"source": {"$ne": "trendyol_backfill"}}))
    # Kod → orijinal index
    code_index = {}
    for o in originals:
        for c in _codes(o):
            code_index.setdefault(c, o)
    print(f"Taslak: {len(drafts)} | Orijinal: {len(originals)} | eşik(ad)={args.name_threshold} "
          f"görsel={'açık' if args.images else 'kapalı'} mod={'UYGULA' if args.apply else 'RAPOR'}")

    rows = []
    merged = assigned = reviewed = nomatch = 0
    for d in drafts:
        best, best_score, method = None, 0.0, ""
        # 1) kesin kod eşleşmesi
        for c in _codes(d):
            if c in code_index:
                best, best_score, method = code_index[c], 1.0, "stok_kodu"
                break
        # 2) bulanık ad
        if best_score < 1.0:
            for o in originals:
                s = _name_score(d.get("name"), o.get("name"))
                if s > best_score:
                    best, best_score, method = o, s, "ad"
        # 3) görsel (yalnız ad orta bölgedeyse ve --images)
        if args.images and best and args.review_threshold <= best_score < args.name_threshold:
            isc = _img_score(_img_url(d), _img_url(best))
            if isc > best_score:
                best_score, method = isc, f"görsel(ad={method})"

        d_bc = str(d.get("barcode") or "")
        d_sc = str(d.get("stock_code") or "")
        if best and best_score >= args.name_threshold:
            action = "BİRLEŞTİR"
            if args.apply:
                upd = {}
                if not best.get("barcode") and d_bc:
                    upd["barcode"] = d_bc
                if not best.get("stock_code") and d_sc:
                    upd["stock_code"] = d_sc
                if upd:
                    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
                    db.products.update_one({"_id": best["_id"]}, {"$set": upd})
                    assigned += 1
                db.products.delete_one({"_id": d["_id"]})   # duplike taslağı sil
                merged += 1
        elif best and best_score >= args.review_threshold:
            action = "İNCELE"
            reviewed += 1
        else:
            action = "EŞLEŞME_YOK"
            nomatch += 1
        rows.append({
            "taslak_urun": d.get("name", ""), "taslak_barkod": d_bc, "taslak_stok": d_sc,
            "eslesen_urun": (best or {}).get("name", "") if best else "",
            "skor": round(best_score, 3), "yontem": method, "aksiyon": action,
        })

    rows.sort(key=lambda r: -r["skor"])
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["aksiyon", "skor", "yontem", "taslak_urun",
                                          "eslesen_urun", "taslak_barkod", "taslak_stok"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})

    print(f"\n>> BİRLEŞTİR (yüksek güven): {sum(1 for r in rows if r['aksiyon']=='BİRLEŞTİR')}")
    print(f">> İNCELE (orta güven): {reviewed}")
    print(f">> EŞLEŞME YOK (gerçek yeni ürün): {nomatch}")
    if args.apply:
        print(f">> UYGULANDI: {merged} taslak birleştirildi, {assigned} ürüne barkod atandı, duplike taslaklar silindi.")
    else:
        print(f">> RAPOR modu — hiçbir şey değişmedi. Detay: {args.out}")
        print("   İlk 15 öneri:")
        for r in rows[:15]:
            print(f"   [{r['aksiyon']}] {r['skor']:.2f} ({r['yontem']}) "
                  f"'{r['taslak_urun'][:40]}' → '{r['eslesen_urun'][:40]}'")
        print("   Uygulamak için: aynı komuta --apply ekle.")


if __name__ == "__main__":
    main()
