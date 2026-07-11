#!/usr/bin/env bash
# SON DEPLOY: SEO slug URL + üye girişi + iyzico footer + (önceki) sepet/header/arama/panel-bağlama
set -euo pipefail
SD="$(cd "$(dirname "$0")" && pwd)"
SITE=/var/www/estoril; APP=/opt/facette; CERT=/etc/letsencrypt/live/estoril.com.tr
[ "$(id -u)" -eq 0 ] || { echo "root: sudo ./deploy-son.sh"; exit 1; }
[ -d "$SITE" ] || { echo "vitrin klasörü yok: $SITE (önce temel kurulum)"; exit 1; }

echo "> 1/5 vitrin dosyaları (SEO + login + iyzico + sepet)"
cp -f "$SD/Estoril Premium Ana Sayfa.dc.html" "$SITE/"
cp -f "$SD/Estoril Premium Kategori.dc.html" "$SITE/"
cp -f "$SD/Estoril Premium Urun.dc.html" "$SITE/"
cp -f "$SD/Alpha Platinium Ice.dc.html" "$SITE/"
cp -f "$SD/support.js" "$SITE/"; cp -f "$SD/cart.js" "$SITE/"; cp -f "$SD/login.js" "$SITE/"
# boşluksuz kopyalar (temiz/SEO URL için)
cp -f "$SITE/Estoril Premium Kategori.dc.html" "$SITE/kategori.dc.html"
cp -f "$SITE/Estoril Premium Urun.dc.html"     "$SITE/urun.dc.html"
cp -f "$SITE/Alpha Platinium Ice.dc.html"      "$SITE/alpha.dc.html"
cp -f "$SITE/Estoril Premium Ana Sayfa.dc.html" "$SITE/index.html"
chown -R www-data:www-data "$SITE"

echo "> 2/5 panel: storefront-products endpoint (DB tek kaynak)"
python3 - <<'PY'
import io, re
P="/opt/facette/backend/routes/estoril_site.py"
s=io.open(P,encoding="utf-8").read()
if re.search(r'from \.deps import [^\n]*\bdb\b', s) is None:
    s=re.sub(r'(from \.deps import [^\n]*)', r'\1, db', s, count=1)
EP='''

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
'''
if "storefront-products" not in s:
    s=s.rstrip()+"\n"+EP
io.open(P,"w",encoding="utf-8").write(s)
PY
python3 -c "import ast; ast.parse(open('/opt/facette/backend/routes/estoril_site.py').read()); print('   backend OK')"
systemctl restart facette-backend; sleep 3
systemctl is-active --quiet facette-backend || { journalctl -u facette-backend -n 30 --no-pager; exit 1; }

echo "> 3/5 endpoint testi"
echo "   ürün: $(curl -s http://127.0.0.1:8001/api/estoril/storefront-products | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))' 2>/dev/null || echo '?')"

echo "> 4/5 nginx (SEO path + /products.json + /api proxy)"
cat > /etc/nginx/sites-available/estoril <<NGINX
server { listen 80; listen [::]:80; server_name estoril.com.tr www.estoril.com.tr panel.estoril.com.tr; return 301 https://\$host\$request_uri; }
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name estoril.com.tr www.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem; ssl_certificate_key ${CERT}/privkey.pem; ssl_protocols TLSv1.2 TLSv1.3;
    root ${SITE}; index index.html;
    location = /urun { try_files /urun.dc.html =404; }
    location /urun/ { try_files /urun.dc.html =404; }
    location = /kategori { try_files /kategori.dc.html =404; }
    location /kategori/ { try_files /kategori.dc.html =404; }
    location = /alpha { try_files /alpha.dc.html =404; }
    location = /products.json { proxy_pass http://127.0.0.1:8001/api/estoril/storefront-products; add_header Cache-Control "no-store"; }
    location /api/ {
        proxy_pass http://127.0.0.1:8001; proxy_http_version 1.1;
        proxy_set_header Host \$host; proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location ~* \.json\$ { add_header Cache-Control "no-store, must-revalidate"; try_files \$uri =404; }
    location / { try_files \$uri \$uri/ /index.html; }
}
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name panel.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem; ssl_certificate_key ${CERT}/privkey.pem; ssl_protocols TLSv1.2 TLSv1.3;
    root ${APP}/frontend/build; index index.html; client_max_body_size 25M;
    location = / { return 301 /admin; }
    location /api/ {
        proxy_pass http://127.0.0.1:8001; proxy_http_version 1.1;
        proxy_set_header Host \$host; proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
    location / { try_files \$uri \$uri/ /index.html; }
}
NGINX

echo "> 5/5 nginx test + reload"
nginx -t && systemctl reload nginx
echo "TAMAM: SEO linkler + üye girişi + iyzico footer + tek-kaynak. https://estoril.com.tr"
