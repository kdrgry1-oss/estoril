#!/usr/bin/env bash
#
# Estoril storefront + panel modülü entegrasyonu (Facette üzerine)
# ------------------------------------------------------------------
# - estoril.com.tr        → Estoril statik vitrin (/var/www/estoril, .dc.html + JSON)
# - panel.estoril.com.tr  → Facette paneli + Estoril yönetim modülü
# Estoril verisi YALNIZCA JSON dosyalarında tutulur. Facette Mongo'suna hiçbir
# Estoril verisi yazılmaz. (bkz. ESTORIL-MIMARI-KURALLAR.md)
#
# Kullanım (root):
#   sudo ./estoril-integrate.sh /home/salih/estoril-site.zip
# ------------------------------------------------------------------
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/facette}"
SITE_DIR="${SITE_DIR:-/var/www/estoril}"
DOMAIN="${DOMAIN:-estoril.com.tr}"
WWW="${WWW:-www.estoril.com.tr}"
PANEL="${PANEL:-panel.estoril.com.tr}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
EMAIL="${EMAIL:-kdrgry@gmail.com}"
HOMEPAGE="Estoril Premium Ana Sayfa.dc.html"

RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; BLU=$'\e[34m'; RST=$'\e[0m'
log(){ echo "${BLU}> $*${RST}"; }; ok(){ echo "${GRN}OK $*${RST}"; }
warn(){ echo "${YLW}! $*${RST}"; }; die(){ echo "${RED}HATA: $*${RST}">&2; exit 1; }
trap 'die "satir $LINENO basarisiz (yukariya bak)."' ERR

[ "$(id -u)" -eq 0 ] || die "root ile calistir: sudo ./estoril-integrate.sh /home/salih/estoril-site.zip"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/estoril_site.py" ] && [ -f "$SCRIPT_DIR/EstorilSite.jsx" ] || die "estoril_site.py / EstorilSite.jsx script yaninda bulunamadi ($SCRIPT_DIR)"
[ -d "$APP_DIR/backend" ] && [ -d "$APP_DIR/frontend" ] || die "Facette kurulumu yok: $APP_DIR"

SITE_ZIP="${1:-}"
if [ -z "$SITE_ZIP" ]; then SITE_ZIP="$(ls /home/*/estoril-site.zip 2>/dev/null | head -1 || true)"; fi
[ -f "$SITE_ZIP" ] || die "estoril-site.zip bulunamadi; yol ver: ./estoril-integrate.sh /home/salih/estoril-site.zip"
ok "Vitrin zip: $SITE_ZIP"

# ── 1) VİTRİN (statik) ────────────────────────────────────────────
log "1/6  Estoril vitrini $SITE_DIR icine"
rm -rf /opt/_estoril_unzip; mkdir -p /opt/_estoril_unzip
command -v unzip >/dev/null || { apt-get update -qq && apt-get install -y -qq unzip; }
unzip -q -o "$SITE_ZIP" -d /opt/_estoril_unzip
S="$(dirname "$(find /opt/_estoril_unzip -name '*.dc.html' -not -path '*__MACOSX*' -not -name '._*' | head -1)")"
[ -n "$S" ] && [ -d "$S" ] || die "Vitrin zip'inde .dc.html bulunamadi"
mkdir -p "$SITE_DIR"
cp -a "$S"/. "$SITE_DIR"/
rm -rf "$SITE_DIR/__MACOSX"
find "$SITE_DIR" \( -name '.DS_Store' -o -name '._*' \) -delete 2>/dev/null || true
[ -f "$SITE_DIR/$HOMEPAGE" ] || die "Ana sayfa yok: $SITE_DIR/$HOMEPAGE"
cp -f "$SITE_DIR/$HOMEPAGE" "$SITE_DIR/index.html"   # kök / -> ana sayfa
chown -R www-data:www-data "$SITE_DIR"
ok "Vitrin yerlesti ($(ls "$SITE_DIR"/*.dc.html | wc -l) sayfa, ana sayfa index.html'e kopyalandi)"

# ── 2) BACKEND modülü ─────────────────────────────────────────────
log "2/6  Backend: estoril_site.py + router kaydi"
cp -f "$SCRIPT_DIR/estoril_site.py" "$APP_DIR/backend/routes/estoril_site.py"
python3 - "$APP_DIR" <<'PYEOF'
import io, sys
A = sys.argv[1]
def edit(p, fn):
    s = io.open(p, encoding="utf-8").read(); ns = fn(s)
    if ns != s: io.open(p,"w",encoding="utf-8").write(ns); print("  yamalandi:", p)
    else: print("  degisiklik yok (zaten var?):", p)
def p_init(s):
    if "estoril_site_router" in s: return s
    s = s.replace('from .settings import router as settings_router\n',
                  'from .settings import router as settings_router\n'
                  'from .estoril_site import router as estoril_site_router\n',1)
    s = s.replace('    "settings_router",\n',
                  '    "settings_router",\n    "estoril_site_router",\n',1)
    return s
def p_server(s):
    if "estoril_site_router" in s: return s
    return s.replace('api_router = APIRouter(prefix="/api")\n',
                     'from routes.estoril_site import router as estoril_site_router\n'
                     'api_router = APIRouter(prefix="/api")\n'
                     'api_router.include_router(estoril_site_router)\n',1)
edit(f"{A}/backend/routes/__init__.py", p_init)
edit(f"{A}/backend/server.py", p_server)
PYEOF

# .env: ESTORIL_SITE_DIR + CORS (panel dahil)
ENVF="$APP_DIR/backend/.env"
grep -q '^ESTORIL_SITE_DIR=' "$ENVF" || echo "ESTORIL_SITE_DIR=$SITE_DIR" >> "$ENVF"
sed -i "s#^CORS_ORIGINS=.*#CORS_ORIGINS=https://$DOMAIN,https://$WWW,https://$PANEL,http://$DOMAIN,http://$WWW,http://$PANEL#" "$ENVF"
ok "Backend modülü + .env hazir"

# ── 3) FRONTEND modülü ────────────────────────────────────────────
log "3/6  Frontend: EstorilSite.jsx + route/menu"
cp -f "$SCRIPT_DIR/EstorilSite.jsx" "$APP_DIR/frontend/src/pages/admin/EstorilSite.jsx"
python3 - "$APP_DIR" <<'PYEOF'
import io, sys
A = sys.argv[1]
def edit(p, fn):
    s = io.open(p, encoding="utf-8").read(); ns = fn(s)
    if ns != s: io.open(p,"w",encoding="utf-8").write(ns); print("  yamalandi:", p)
    else: print("  degisiklik yok (zaten var?):", p)
def p_admin(s):
    if "EstorilSite" in s: return s
    s = s.replace('import AdminBanners from "./pages/admin/Banners";\n',
                  'import AdminBanners from "./pages/admin/Banners";\n'
                  'import EstorilSite from "./pages/admin/EstorilSite";\n',1)
    s = s.replace('        <Route path="bannerlar" element={<AdminBanners />} />\n',
                  '        <Route path="bannerlar" element={<AdminBanners />} />\n'
                  '        <Route path="estoril-site" element={<EstorilSite />} />\n',1)
    return s
def p_nav(s):
    if "estoril-site" in s: return s
    return s.replace('{ label: "Sayfalar (CMS)", path: "/admin/sayfalar", icon: FileText },',
                     '{ label: "Sayfalar (CMS)", path: "/admin/sayfalar", icon: FileText },\n'
                     '      { label: "Estoril Site", path: "/admin/estoril-site", icon: Store },',1)
    return s
edit(f"{A}/frontend/src/AdminApp.jsx", p_admin)
edit(f"{A}/frontend/src/lib/adminNav.js", p_nav)
PYEOF

# Panel artik panel.estoril.com.tr'de -> API ayni origin
echo "REACT_APP_BACKEND_URL=https://$PANEL" > "$APP_DIR/frontend/.env"
log "    Frontend build (birkac dakika)..."
cd "$APP_DIR/frontend"
NODE_OPTIONS=--max-old-space-size=4096 CI=false yarn build >/tmp/estoril_build.log 2>&1 || { tail -30 /tmp/estoril_build.log; die "frontend build patladi (log: /tmp/estoril_build.log)"; }
mkdir -p "$APP_DIR/frontend/build/static/brand"
cp -f "$APP_DIR"/backend/static/brand/* "$APP_DIR/frontend/build/static/brand/" 2>/dev/null || true
ok "Frontend build tamam"

# ── 4) İzinler + backend restart ──────────────────────────────────
log "4/6  Izinler + backend restart"
chown -R www-data:www-data "$APP_DIR" "$SITE_DIR"
systemctl restart facette-backend
sleep 3
systemctl is-active --quiet facette-backend || die "backend baslamadi: journalctl -u facette-backend -n 50"
ok "Backend calisiyor"

# ── 5) nginx (2 sunucu bloğu: vitrin + panel) ─────────────────────
log "5/6  nginx yapilandirmasi (HTTP; SSL'i certbot ekleyecek)"
cat > /etc/nginx/sites-available/estoril <<NGINX
# ── Estoril statik vitrin ──
server {
    listen 80; listen [::]:80;
    server_name ${DOMAIN} ${WWW};
    root ${SITE_DIR};
    index index.html;

    # panel kaydedince aninda gorunsun: JSON cache'lenmesin
    location ~* \.json\$ {
        add_header Cache-Control "no-store, must-revalidate";
        try_files \$uri =404;
    }
    location / { try_files \$uri \$uri/ /index.html; }
}
# ── Facette paneli ──
server {
    listen 80; listen [::]:80;
    server_name ${PANEL};
    root ${APP_DIR}/frontend/build;
    index index.html;
    client_max_body_size 25M;

    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
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
ln -sf /etc/nginx/sites-available/estoril /etc/nginx/sites-enabled/estoril
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
ok "nginx HTTP hazir"

# ── 6) SSL (panel dahil, sertifikayi genislet) ────────────────────
log "6/6  SSL (Let's Encrypt) — panel dahil"
certbot --nginx -d "$DOMAIN" -d "$WWW" -d "$PANEL" --expand --redirect -m "$EMAIL" --agree-tos -n
ok "SSL hazir"

# ── Ozet ──────────────────────────────────────────────────────────
S1="$(curl -s -o /dev/null -w '%{http_code}' https://$DOMAIN/ || true)"
S2="$(curl -s -o /dev/null -w '%{http_code}' https://$PANEL/api/ || true)"
echo
echo "${GRN}============= ENTEGRASYON TAMAM =============${RST}"
echo "  Vitrin : https://${DOMAIN}        (HTTP ${S1}) — SENIN Estoril tasarimin"
echo "  Panel  : https://${PANEL}   (api HTTP ${S2})"
echo "  Panelde: Tasarim > Estoril Site  (4 sekme: Ana Sayfa/Lazer/Alpha/Urunler)"
echo "  Veri   : ${SITE_DIR}/*.json  (Facette Mongo'ya DEGIL)"
echo "${GRN}=============================================${RST}"
echo "  Test: panelde bir sey degistir > Kaydet > vitrinde yenile."
