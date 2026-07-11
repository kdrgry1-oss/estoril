#!/usr/bin/env bash
# Giris maili -> estorilcosmetics@gmail.com + panelde TUM gorunur "Facette" -> "Estoril"
# (kod tanimlayicilari/URL/lowercase 'facette' DOKUNULMAZ) + panel koku -> /admin.
set -euo pipefail
APP=/opt/facette
NEW_EMAIL="estorilcosmetics@gmail.com"
[ "$(id -u)" -eq 0 ] || { echo "root: sudo bash $0"; exit 1; }

echo "> 1/4 Giris maili -> $NEW_EMAIL"
mongosh facette --quiet --eval 'db.users.updateOne({email:"admin@facette.com"},{$set:{email:"'"$NEW_EMAIL"'"}})'
mongosh facette --quiet --eval 'db.users.find({},{_id:0,email:1,is_admin:1}).toArray()'

echo "> 2/4 Panel metinleri: Facette -> Estoril (gorunur olanlar)"
python3 - <<'PY'
import os, io, re
A = "/opt/facette/frontend"
def repl(p):
    s = io.open(p, encoding="utf-8").read()
    ns = s.replace("FACETTE", "ESTORIL").replace("Facette", "Estoril")
    if ns != s:
        io.open(p, "w", encoding="utf-8").write(ns); return 1
    return 0
n = 0
for root, _, files in os.walk(A + "/src"):
    for f in files:
        if f.endswith((".js", ".jsx")) and ".bak" not in f:
            n += repl(os.path.join(root, f))
ix = A + "/public/index.html"
s = io.open(ix, encoding="utf-8").read()
s = re.sub(r"<title>.*?</title>", "<title>Estoril Cosmetic — Yönetim</title>", s, count=1)
s = s.replace("FACETTE", "ESTORIL").replace("Facette", "Estoril")
io.open(ix, "w", encoding="utf-8").write(s)
print("   degisen kaynak dosya:", n)
PY

echo "> 3/4 Frontend build (birkac dakika)"
cd "$APP/frontend"
NODE_OPTIONS=--max-old-space-size=4096 CI=false yarn build >/tmp/estoril_rebrand.log 2>&1 || { tail -30 /tmp/estoril_rebrand.log; echo BUILD_FAIL; exit 1; }
mkdir -p build/static/brand; cp -f "$APP"/backend/static/brand/* build/static/brand/ 2>/dev/null || true
chown -R www-data:www-data "$APP"

echo "> 4/4 nginx (panel koku -> /admin)"
CERT=/etc/letsencrypt/live/estoril.com.tr
cat > /etc/nginx/sites-available/estoril <<NGINX
server { listen 80; listen [::]:80; server_name estoril.com.tr www.estoril.com.tr panel.estoril.com.tr; return 301 https://\$host\$request_uri; }
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name estoril.com.tr www.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem; ssl_certificate_key ${CERT}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /var/www/estoril; index index.html;
    location ~* \.json\$ { add_header Cache-Control "no-store, must-revalidate"; try_files \$uri =404; }
    location / { try_files \$uri \$uri/ /index.html; }
}
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name panel.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem; ssl_certificate_key ${CERT}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
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
nginx -t && systemctl reload nginx
systemctl restart facette-backend
echo "TAMAM. Giris: ${NEW_EMAIL} / (ayni sifre). Panelde tum 'Facette' -> 'Estoril'."
