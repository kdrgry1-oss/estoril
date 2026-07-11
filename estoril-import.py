#!/usr/bin/env python3
"""
Estoril ürün + kategorilerini kendi products.json'undan panelin ürün/kategori
sayfalarina aktarir. Panelin KENDI API'sini kullanir (sema-guvenli), yerelden
(127.0.0.1) konusur. Harici veri/sistem YOK — kaynak yalnizca Estoril'in
kendi products.json'u.

Calistir (sunucuda):
  ADMIN_PASSWORD='Estoril.2026!' python3 estoril-import.py
Tekrar calistirip ustune eklemek icin: FORCE=1 ekle.
"""
import json, os, sys, urllib.request, urllib.error

BASE     = os.environ.get("BASE", "http://127.0.0.1:8001/api")
EMAIL    = os.environ.get("ADMIN_EMAIL", "admin@facette.com")   # giris hesabi (dahili)
PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
PJSON    = os.environ.get("PRODUCTS_JSON", "/var/www/estoril/products.json")

def api(method, path, token=None, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.stderr.write("HTTP %s %s -> %s\n" % (method, path, e.read().decode("utf-8")[:300]))
        raise

def main():
    if not PASSWORD:
        sys.exit("ADMIN_PASSWORD gerekli: ADMIN_PASSWORD='...' python3 estoril-import.py")
    if not os.path.exists(PJSON):
        sys.exit("Bulunamadi: " + PJSON)
    products = json.load(open(PJSON, encoding="utf-8"))
    print("Kaynak: %s (%d urun)" % (PJSON, len(products)))

    tok = api("POST", "/auth/login", body={"email": EMAIL, "password": PASSWORD}).get("token")
    if not tok:
        sys.exit("Giris basarisiz (sifre?)")
    print("Giris OK")

    # Tekrar-guvenligi: zaten urun varsa dur (FORCE=1 ile gecilebilir)
    total = api("GET", "/products?limit=1", token=tok).get("total", 0)
    if total > 0 and os.environ.get("FORCE") != "1":
        sys.exit("Sistemde zaten %d urun var. Tekrar eklememek icin cikildi. Yine de: FORCE=1" % total)

    # Mevcut kategorileri yukle -> (isim, parent_id) -> id
    cat_index = {}
    for c in api("GET", "/categories", token=tok):
        cat_index[(c.get("name", "").strip().lower(), c.get("parent_id") or "")] = c["id"]

    def ensure_cat(name, parent_id):
        key = (name.strip().lower(), parent_id or "")
        if key in cat_index:
            return cat_index[key]
        cid = api("POST", "/categories", token=tok,
                  body={"name": name, "parent_id": parent_id, "is_active": True})["id"]
        cat_index[key] = cid
        return cid

    def ensure_path(path):          # "Ana > Alt > ..."
        parent, leaf = None, None
        for seg in [s.strip() for s in path.split(">") if s.strip()]:
            leaf = ensure_cat(seg, parent)
            parent = leaf
        return leaf, (path.split(">")[-1].strip() if path else "")

    made = 0
    for i, p in enumerate(products, 1):
        cat_ids, cat_name = [], ""
        for cp in (p.get("cats") or []):
            cid, leaf_name = ensure_path(cp)
            if cid:
                cat_ids.append(cid)
                cat_name = leaf_name
        imgs = p.get("imgs") or ([p["img"]] if p.get("img") else [])
        body = {
            "name": p.get("name", ""),
            "price": float(p.get("price") or 0),
            "sale_price": (float(p["sale"]) if p.get("sale") else None),
            "description": p.get("desc", ""),
            "images": imgs,
            "categories": cat_ids,
            "category_name": cat_name,
            "stock": 100 if p.get("stock") else 0,
            "is_active": True,
            "brand": "Estoril",
            "manufacturer": "Estoril",
        }
        api("POST", "/products", token=tok, body=body)
        made += 1
        if made % 20 == 0 or made == len(products):
            print("  %d/%d urun" % (made, len(products)))

    print("TAMAM: %d urun, %d kategori olusturuldu." % (made, len(cat_index)))

if __name__ == "__main__":
    main()
