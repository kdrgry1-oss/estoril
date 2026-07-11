#!/usr/bin/env bash
# Admin "Facette" -> "Estoril" (görünen) + panel kökünü /admin'e yönlendir.
# Sadece GÖRÜNEN marka değişir; kod kimlikleri (facette_defaults vb.) DOKUNULMAZ.
set -euo pipefail
APP=/opt/facette
GRN=$'\e[32m'; RED=$'\e[31m'; RST=$'\e[0m'
[ "$(id -u)" -eq 0 ] || { echo "root ile calistir: sudo $0"; exit 1; }

echo "> 1/4 Admin marka yamalari"
python3 - <<'PY'
import io
def ed(p,old,new):
    s=io.open(p,encoding="utf-8").read()
    if new in s: print("   zaten:",p); return
    if old not in s: print("   BULUNAMADI(atla):",p); return
    io.open(p,"w",encoding="utf-8").write(s.replace(old,new,1)); print("   ok:",p)
A="/opt/facette/frontend"
ed(f"{A}/src/pages/admin/AdminLogin.jsx", ">FACETTE ADMIN<", ">ESTORIL ADMIN<")
ed(f"{A}/src/pages/admin/AdminLayout.jsx", "          FACETTE\n        </Link>", "          ESTORIL\n        </Link>")
ed(f"{A}/public/index.html", "<title>FACETTE | Yeni Sezon Kadın Giyim & Moda</title>", "<title>Estoril Cosmetic — Yönetim</title>")
ed(f"{A}/public/index.html", 'content="FACETTE"', 'content="Estoril Cosmetic"')
PY

echo "> 2/4 Frontend build (birkac dakika)"
cd "$APP/frontend"
NODE_OPTIONS=--max-old-space-size=4096 CI=false yarn build >/tmp/rebrand_build.log 2>&1 || { tail -30 /tmp/rebrand_build.log; echo "${RED}build patladi${RST}"; exit 1; }
mkdir -p build/static/brand; cp -f "$APP"/backend/static/brand/* build/static/brand/ 2>/dev/null || true
chown -R www-data:www-data "$APP"

echo "> 3/4 nginx (panel koku -> /admin, HTTPS)"
CERT=/etc/letsencrypt/live/estoril.com.tr
cat > /etc/nginx/sites-available/estoril <<NGINX
# HTTP -> HTTPS
server {
    listen 80; listen [::]:80;
    server_name estoril.com.tr www.estoril.com.tr panel.estoril.com.tr;
    return 301 https://\$host\$request_uri;
}
# Estoril statik vitrin
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name estoril.com.tr www.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem;
    ssl_certificate_key ${CERT}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /var/www/estoril; index index.html;
    location ~* \.json\$ { add_header Cache-Control "no-store, must-revalidate"; try_files \$uri =404; }
    location / { try_files \$uri \$uri/ /index.html; }
}
# Facette paneli (kok -> /admin)
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name panel.estoril.com.tr;
    ssl_certificate ${CERT}/fullchain.pem;
    ssl_certificate_key ${CERT}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root ${APP}/frontend/build; index index.html;
    client_max_body_size 25M;
    location = / { return 301 /admin; }
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
    location / { try_files \$uri \$uri/ /index.html; }
}
NGINX
nginx -t
systemctl reload nginx

echo "> 4/4 Restart backend (guvenli)"
systemctl restart facette-backend
echo "${GRN}TAMAM: admin=ESTORIL, panel koku -> /admin, HTTPS hazir.${RST}"
