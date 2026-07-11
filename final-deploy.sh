#!/usr/bin/env bash
# TAM vitrin deploy: temiz URL + mobil header + sepet(cart.js) + login->WA + vitrin<->panel (DB tek kaynak)
set -euo pipefail
SD="$(cd "$(dirname "$0")" && pwd)"
SITE=/var/www/estoril; APP=/opt/facette; CERT=/etc/letsencrypt/live/estoril.com.tr
[ "$(id -u)" -eq 0 ] || { echo "root: sudo ./final-deploy.sh"; exit 1; }

echo "> 1/5 cart.js + .dc.html (temiz URL + header + sepet)"
cp "$SD/cart.js" "$SITE/cart.js"
python3 - <<'PY'
import io, re
REP=[("Estoril Premium Ana Sayfa.dc.html","/"),("Estoril Premium Kategori.dc.html","/kategori"),
     ("Estoril Premium Urun.dc.html","/urun"),("Alpha Platinium Ice.dc.html","/alpha")]
FIX='''<style id="estoril-header-fix">
@media (max-width:640px){
  [data-r~="header"]{flex-wrap:wrap!important;justify-content:space-between!important;align-items:center!important;row-gap:10px!important;column-gap:8px!important;padding:12px 14px!important;}
  [data-r~="header"]>a:first-child{order:0!important;}[data-r~="header"]>a:first-child img{height:30px!important;}
  [data-r~="header"]>div:last-child{order:1!important;margin-left:auto!important;gap:6px!important;flex-shrink:0!important;}
  [data-r~="header"]>div:last-child span[title]{width:36px!important;height:36px!important;}
  [data-r~="search"]{order:5!important;flex:1 1 100%!important;min-width:0!important;padding:9px 16px!important;}
}
</style>'''
for name in ["Estoril Premium Ana Sayfa.dc.html","Estoril Premium Kategori.dc.html","Estoril Premium Urun.dc.html","Alpha Platinium Ice.dc.html"]:
    f="/var/www/estoril/"+name; s=io.open(f,encoding="utf-8").read()
    for a,b in REP: s=s.replace(a,b)
    s=re.sub(r'<style id="estoril-header-fix">.*?</style>','',s,flags=re.S)
    s=s.replace("</head>", FIX+"\n</head>",1)
    if 'cart.js' not in s: s=s.replace("</body>",'<script src="./cart.js"></script>\n</body>',1)
    io.open(f,"w",encoding="utf-8").write(s)
print("   ok")
PY
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
print("   endpoint eklendi/mevcut")
PY
python3 -c "import ast; ast.parse(open('/opt/facette/backend/routes/estoril_site.py').read()); print('   estoril_site.py sözdizimi OK')"
systemctl restart facette-backend; sleep 3
systemctl is-active --quiet facette-backend || { journalctl -u facette-backend -n 30 --no-pager; echo "BACKEND HATA"; exit 1; }

echo "> 3/5 endpoint çalışıyor mu?"
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/estoril/storefront-products || true)
n=$(curl -s http://127.0.0.1:8001/api/estoril/storefront-products | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
echo "   HTTP $code, ürün: $n"

echo "> 4/5 nginx (temiz URL + /products.json -> DB)"
cat > /etc/nginx/sites-available/estoril <<NGINX
server { listen 80; listen [::]:80; server_name estoril.com.tr www.estoril.com.tr panel.estoril.com.tr; return 301 https://\$host\$request_uri; }
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name estoril.com.tr www.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem; ssl_certificate_key ${CERT}/privkey.pem; ssl_protocols TLSv1.2 TLSv1.3;
    root ${SITE}; index index.html;
    location = /kategori { try_files /kategori.dc.html =404; }
    location = /urun     { try_files /urun.dc.html =404; }
    location = /alpha    { try_files /alpha.dc.html =404; }
    location = /products.json { proxy_pass http://127.0.0.1:8001/api/estoril/storefront-products; add_header Cache-Control "no-store"; }
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
echo "TAMAM: vitrin<->panel bağlı. Panelde ürün düzenle -> estoril.com.tr canlı güncellenir."
