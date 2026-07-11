#!/usr/bin/env bash
#
# Facette — tek sunucu (single VPS) TEMİZ kurulum scripti
# ------------------------------------------------------------------
# Ubuntu 24.04 (Noble) için. Facette'i BOŞ bir MongoDB ile sıfırdan kurar:
# hiçbir gerçek veri (sipariş/ürün/müşteri) taşınmaz. Entegrasyon secret'ları
# boş bırakılır — panel açılır, anahtarları sonradan sen girersin.
#
# Mimari:
#   nginx (80/443)  ─ /api  → 127.0.0.1:8001 (uvicorn, systemd)
#                    └ /     → frontend/build (React statik)
#   MongoDB 127.0.0.1:27017  (yerel, boş DB)
#
# Kullanım (root olarak):
#   sudo ADMIN_PASSWORD='guclu-bir-sifre' ./deploy.sh /path/to/facette-kaynak-ya-da-zip
#
# İlk argüman: içinde backend/ ve frontend/ olan Facette kaynak klasörü,
#              VEYA facette zip dosyası (otomatik açılır).
# ------------------------------------------------------------------
set -euo pipefail

# ─── AYARLAR (gerekirse düzenle ya da env ile geç) ────────────────
DOMAIN="${DOMAIN:-estoril.com.tr}"
WWW="${WWW:-www.estoril.com.tr}"
APP_DIR="${APP_DIR:-/opt/facette}"
DB_NAME="${DB_NAME:-facette}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
PY_VER="${PY_VER:-3.11}"
NODE_MAJOR="${NODE_MAJOR:-20}"
MONGO_VER="${MONGO_VER:-8.0}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@facette.com}"   # reset_admin.py bu e-postayı kullanır
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"              # boşsa script rastgele üretir
SERVICE_USER="www-data"
# ──────────────────────────────────────────────────────────────────

RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; BLU=$'\e[34m'; RST=$'\e[0m'
log()  { echo "${BLU}▶ $*${RST}"; }
ok()   { echo "${GRN}✔ $*${RST}"; }
warn() { echo "${YLW}⚠ $*${RST}"; }
die()  { echo "${RED}✘ HATA: $*${RST}" >&2; exit 1; }
trap 'die "satır $LINENO başarısız oldu (yukarıdaki çıktıya bak)."' ERR

[ "$(id -u)" -eq 0 ] || die "Bu script root ile çalıştırılmalı: sudo ./deploy.sh ..."
SRC_ARG="${1:-}"
[ -n "$SRC_ARG" ] || die "Kaynak belirtmelisin: ./deploy.sh /path/to/facette-kaynak-ya-da-zip"

# ─── 0) Kaynağı çöz (klasör ya da zip) ────────────────────────────
log "0/12  Kaynak hazırlanıyor: $SRC_ARG"
SRC_DIR=""
if [ -d "$SRC_ARG" ]; then
  SRC_DIR="$SRC_ARG"
elif [[ "$SRC_ARG" == *.zip ]]; then
  command -v unzip >/dev/null || { apt-get update -qq && apt-get install -y -qq unzip; }
  TMP_UNZIP="/opt/_facette_src_unzip"
  rm -rf "$TMP_UNZIP"; mkdir -p "$TMP_UNZIP"
  unzip -q -o "$SRC_ARG" -d "$TMP_UNZIP"
  # backend/ ve frontend/ içeren dizini bul
  SRC_DIR="$(dirname "$(find "$TMP_UNZIP" -maxdepth 3 -type d -name backend | head -1)")"
else
  die "Kaynak ne klasör ne de .zip: $SRC_ARG"
fi
[ -d "$SRC_DIR/backend" ] && [ -d "$SRC_DIR/frontend" ] || die "Kaynakta backend/ + frontend/ bulunamadı: $SRC_DIR"
ok "Kaynak: $SRC_DIR"

# ─── 1) Sistem paketleri + Python 3.11 ────────────────────────────
log "1/12  Sistem paketleri ve Python $PY_VER kuruluyor"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg unzip rsync build-essential \
  software-properties-common lsb-release openssl \
  libxml2-dev libxslt1-dev libffi-dev libssl-dev
if ! command -v "python${PY_VER}" >/dev/null; then
  add-apt-repository -y ppa:deadsnakes/ppa
  apt-get update -qq
fi
apt-get install -y -qq "python${PY_VER}" "python${PY_VER}-venv" "python${PY_VER}-dev"
ok "Python: $(python${PY_VER} --version)"

# ─── 2) MongoDB ───────────────────────────────────────────────────
log "2/12  MongoDB $MONGO_VER kuruluyor"
if ! command -v mongod >/dev/null; then
  CODENAME="$(. /etc/os-release && echo "$UBUNTU_CODENAME")"
  curl -fsSL "https://www.mongodb.org/static/pgp/server-${MONGO_VER}.asc" \
    | gpg -o "/usr/share/keyrings/mongodb-server-${MONGO_VER}.gpg" --dearmor --yes
  echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-${MONGO_VER}.gpg ] https://repo.mongodb.org/apt/ubuntu ${CODENAME}/mongodb-org/${MONGO_VER} multiverse" \
    > "/etc/apt/sources.list.d/mongodb-org-${MONGO_VER}.list"
  apt-get update -qq
  apt-get install -y -qq mongodb-org
fi
systemctl enable --now mongod
sleep 2
systemctl is-active --quiet mongod || die "mongod başlamadı. (CPU AVX desteği yoksa Mongo 8 çalışmaz — 'journalctl -u mongod' bak.)"
ok "MongoDB çalışıyor"

# ─── 3) Node + yarn ───────────────────────────────────────────────
log "3/12  Node $NODE_MAJOR + yarn kuruluyor"
if ! command -v node >/dev/null; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - >/dev/null
  apt-get install -y -qq nodejs
fi
command -v yarn >/dev/null || npm install -g yarn >/dev/null 2>&1
ok "Node: $(node --version) / yarn: $(yarn --version)"

# ─── 4) nginx + certbot ───────────────────────────────────────────
log "4/12  nginx + certbot kuruluyor"
apt-get install -y -qq nginx python3-certbot-nginx
ok "nginx: $(nginx -v 2>&1 | cut -d/ -f2)"

# ─── 5) Kodu yerleştir (gereksiz/hassas dosyaları hariç tut) ──────
log "5/12  Kod $APP_DIR içine kopyalanıyor"
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude 'node_modules' --exclude '.git' --exclude 'db_backup' \
  --exclude '*.bak-*' --exclude '*.bak' --exclude '.iys-*' \
  --exclude 'frontend/build' --exclude 'backend/venv' \
  "$SRC_DIR"/ "$APP_DIR"/
ok "Kod yerleşti"

# ─── 6) Backend: venv + bağımlılıklar ─────────────────────────────
log "6/12  Backend venv + pip install (uzun sürebilir)"
cd "$APP_DIR/backend"
"python${PY_VER}" -m venv venv
venv/bin/pip install --upgrade pip wheel >/dev/null
if ! venv/bin/pip install -r requirements.txt; then
  die "pip install başarısız. requirements.txt bazı sıra dışı sürümlere / Emergent özel aynasına dayanıyor olabilir. Çıktıyı paylaş, pin'leri birlikte gevşetelim."
fi
ok "Python bağımlılıkları kuruldu"

# ─── 7) backend/.env (TEMİZ — secret'lar boş) ─────────────────────
log "7/12  backend/.env yazılıyor (boş DB, secret'lar boş)"
JWT_SECRET_VAL="$(openssl rand -hex 32)"
cat > "$APP_DIR/backend/.env" <<ENV
# ── Facette — temiz kurulum (otomatik üretildi) ──
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=${DB_NAME}
CORS_ORIGINS=https://${DOMAIN},https://${WWW},http://${DOMAIN},http://${WWW}
PUBLIC_BASE_URL=https://${DOMAIN}
JWT_SECRET=${JWT_SECRET_VAL}

# ── Entegrasyonlar (kendi anahtarlarınla doldur — boşken ilgili modül pasif) ──
# R2_ACCOUNT_ID=
# R2_ACCESS_KEY_ID=
# R2_SECRET_ACCESS_KEY=
# R2_BUCKET=
# R2_ENDPOINT=
# R2_PUBLIC_URL=
# TRENDYOL_SUPPLIER_ID=
# TRENDYOL_API_KEY=
# TRENDYOL_API_SECRET=
# IYS_APPKEY=
# IYS_PASSWORD=
# IYS_BRAND_CODE=
# IYZICO_API_KEY=
# IYZICO_SECRET_KEY=
# RESEND_API_KEY=
ENV
chmod 600 "$APP_DIR/backend/.env"
mkdir -p "$APP_DIR/backend/data"
ok "backend/.env hazır"

# ─── 8) Admin kullanıcı (taze) ────────────────────────────────────
log "8/12  Admin kullanıcı oluşturuluyor"
[ -n "$ADMIN_PASSWORD" ] || { ADMIN_PASSWORD="$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-14)"; warn "ADMIN_PASSWORD verilmedi — rastgele üretildi (aşağıda gösterilecek)."; }
set -a; . "$APP_DIR/backend/.env"; set +a
ADMIN_RESET_PASSWORD="$ADMIN_PASSWORD" venv/bin/python reset_admin.py
ok "Admin: $ADMIN_EMAIL"

# ─── 9) Frontend build ────────────────────────────────────────────
log "9/12  Frontend .env + build (birkaç dakika)"
cd "$APP_DIR/frontend"
echo "REACT_APP_BACKEND_URL=https://${DOMAIN}" > .env
yarn install --frozen-lockfile 2>/dev/null || yarn install
NODE_OPTIONS=--max-old-space-size=4096 CI=false yarn build
# backend/static/brand logolarını build içine kopyala (nginx /static'i doğrudan servis eder)
mkdir -p "$APP_DIR/frontend/build/static/brand"
cp -f "$APP_DIR"/backend/static/brand/* "$APP_DIR/frontend/build/static/brand/" 2>/dev/null || true
ok "Frontend build hazır: $APP_DIR/frontend/build"

# ─── 10) İzinler + systemd servisi ────────────────────────────────
log "10/12 systemd servisi kuruluyor"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"
cat > /etc/systemd/system/facette-backend.service <<UNIT
[Unit]
Description=Facette FastAPI backend (uvicorn)
After=network.target mongod.service
Wants=mongod.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${APP_DIR}/backend
ExecStart=${APP_DIR}/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port ${BACKEND_PORT}
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now facette-backend
sleep 3
systemctl is-active --quiet facette-backend || die "facette-backend başlamadı: journalctl -u facette-backend -n 50"
ok "Backend servisi çalışıyor (127.0.0.1:${BACKEND_PORT})"

# ─── 11) nginx site (HTTP) ────────────────────────────────────────
log "11/12 nginx yapılandırması"
cat > /etc/nginx/sites-available/estoril <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} ${WWW};

    root ${APP_DIR}/frontend/build;
    index index.html;
    client_max_body_size 25M;

    # API → FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    # SPA + statik (React /static/js, /static/css, /static/brand dahil)
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/estoril /etc/nginx/sites-enabled/estoril
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
# UFW açıksa portları aç
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 'Nginx Full' >/dev/null || true
  ufw allow OpenSSH >/dev/null || true
fi
ok "nginx yayında (http://${DOMAIN})"

# ─── 12) Özet ─────────────────────────────────────────────────────
log "12/12 Doğrulama"
BACK_CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${BACKEND_PORT}/api/" || true)"
NGINX_CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1/" || true)"
echo
echo "${GRN}════════════════════ KURULUM TAMAM ════════════════════${RST}"
echo "  Site (HTTP)   : http://${DOMAIN}"
echo "  Backend local : http://127.0.0.1:${BACKEND_PORT}/api/  (HTTP ${BACK_CODE})"
echo "  nginx         : HTTP ${NGINX_CODE}"
echo "  Admin giriş   : ${ADMIN_EMAIL}"
echo "  Admin şifre   : ${ADMIN_PASSWORD}"
echo "  DB            : ${DB_NAME} (BOŞ — gerçek veri yok)"
echo
echo "  ${YLW}HTTPS için (DNS sunucuya bakıyorsa, www dahil):${RST}"
echo "    sudo certbot --nginx -d ${DOMAIN} -d ${WWW} --redirect -m senin@eposta.com --agree-tos -n"
echo
echo "  Servis yönetimi:"
echo "    systemctl status facette-backend   |  journalctl -u facette-backend -f"
echo "${GRN}════════════════════════════════════════════════════════${RST}"
