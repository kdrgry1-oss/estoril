#!/usr/bin/env bash
# Vitrin: temiz URL'ler (/ , /kategori, /urun, /alpha) + mobil header duzeltmesi.
# - .dc.html icindeki linkleri temiz yola cevirir
# - nginx'e temiz-URL alias'lari ekler (dosya adlari degismeden)
# - mobil header: logo solda, utility sagda, arama altta
set -euo pipefail
SITE=/var/www/estoril
APP=/opt/facette
CERT=/etc/letsencrypt/live/estoril.com.tr
[ "$(id -u)" -eq 0 ] || { echo "root: sudo bash $0"; exit 1; }

echo "> 1/3 .dc.html: temiz URL + header fix"
python3 - <<'PY'
import glob, io, re
REP=[("Estoril Premium Ana Sayfa.dc.html","/"),
     ("Estoril Premium Kategori.dc.html","/kategori"),
     ("Estoril Premium Urun.dc.html","/urun"),
     ("Alpha Platinium Ice.dc.html","/alpha")]
FIX='''<style id="estoril-header-fix">
@media (max-width:640px){
  [data-r~="header"]{flex-wrap:wrap!important;justify-content:space-between!important;align-items:center!important;row-gap:10px!important;column-gap:8px!important;padding:12px 14px!important;}
  [data-r~="header"]>a:first-child{order:0!important;}
  [data-r~="header"]>a:first-child img{height:30px!important;}
  [data-r~="header"]>div:last-child{order:1!important;margin-left:auto!important;gap:6px!important;flex-shrink:0!important;}
  [data-r~="header"]>div:last-child span[title]{width:36px!important;height:36px!important;}
  [data-r~="search"]{order:5!important;flex:1 1 100%!important;min-width:0!important;padding:9px 16px!important;}
}
</style>'''
import glob
for f in glob.glob("/var/www/estoril/*.dc.html"):
    s=io.open(f,encoding="utf-8").read()
    for a,b in REP: s=s.replace(a,b)
    s=re.sub(r'<style id="estoril-header-fix">.*?</style>','',s,flags=re.S)
    s=s.replace("</head>", FIX+"\n</head>",1)
    io.open(f,"w",encoding="utf-8").write(s)
print("   uygulandi")
PY
cp -f "$SITE/Estoril Premium Ana Sayfa.dc.html" "$SITE/index.html"
chown -R www-data:www-data "$SITE"

echo "> 2/3 nginx (temiz-URL alias + panel)"
cat > /etc/nginx/sites-available/estoril <<NGINX
server { listen 80; listen [::]:80; server_name estoril.com.tr www.estoril.com.tr panel.estoril.com.tr; return 301 https://\$host\$request_uri; }
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name estoril.com.tr www.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem; ssl_certificate_key ${CERT}/privkey.pem; ssl_protocols TLSv1.2 TLSv1.3;
    root ${SITE}; index index.html;
    location = /kategori { alias "${SITE}/Estoril Premium Kategori.dc.html"; default_type text/html; }
    location = /urun     { alias "${SITE}/Estoril Premium Urun.dc.html";     default_type text/html; }
    location = /alpha    { alias "${SITE}/Alpha Platinium Ice.dc.html";      default_type text/html; }
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
ln -sf /etc/nginx/sites-available/estoril /etc/nginx/sites-enabled/estoril

echo "> 3/3 test + reload"
nginx -t && systemctl reload nginx
echo "TAMAM: https://estoril.com.tr/  /kategori  /urun  /alpha  (temiz URL + mobil header)"
