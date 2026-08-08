#!/usr/bin/env bash
# ============================================================================
# ROOF — Surum yukseltmesi (beyaz-etiket guncel kod) + marka=Roof + GTM temiz.
#   - Bizim eklerimiz korunur: estoril_site.py (mail+storefront), MailAccounts,
#     EstorilSite, menu/route birlestirme.
#   - .env / venv / node_modules DOKUNULMAZ.
#   - HER ADIMDA yedekli: build/backend/health basarisiz olursa OTOMATIK geri alir.
# Kullanim: sudo bash roof-deploy.sh /home/salih/roof-guncelleme.tar.gz
# ============================================================================
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "root: sudo bash $0 <paket.tar.gz>"; exit 1; }
PKG="${1:-$HOME/roof-guncelleme.tar.gz}"
[ -f "$PKG" ] || { echo "paket yok: $PKG"; echo "kullanim: sudo bash roof-deploy.sh /home/salih/roof-guncelleme.tar.gz"; exit 1; }
APP=/opt/facette
TS=$(date +%Y%m%d-%H%M%S)
BK="/root/roof-yedek-$TS.tar.gz"
DBN=$(grep -oP 'DB_NAME=\K.*' "$APP/backend/.env" 2>/dev/null | tr -d '"'"'"'' ); DBN=${DBN:-facette}

echo "> 1/7 YEDEK -> $BK"
tar czf "$BK" -C "$APP" \
  --exclude='backend/venv' --exclude='__pycache__' --exclude='frontend/node_modules' \
  backend frontend/src frontend/public frontend/build frontend/package.json \
  frontend/craco.config.js frontend/tailwind.config.js frontend/jsconfig.json frontend/yarn.lock 2>/dev/null
echo "   yedek: $(du -h "$BK" | cut -f1)"

restore(){ echo "!! GERI ALINIYOR (yedekten)..."; tar xzf "$BK" -C "$APP"; chown -R www-data:www-data "$APP"; systemctl restart facette-backend; echo "   geri alindi."; }

echo "> 2/7 Paketi ac"
TMP=$(mktemp -d); tar xzf "$PKG" -C "$TMP"
ROOT="$TMP"
[ -d "$ROOT/backend" ] || ROOT="$(dirname "$(find "$TMP" -path '*/backend/server.py' | head -1)")/.."
[ -d "$ROOT/backend" ] && [ -d "$ROOT/frontend" ] || { echo "!! paket bozuk (backend/frontend yok)"; rm -rf "$TMP"; exit 1; }

echo "> 3/7 Kodu yerlestir (.env/venv/node_modules korunur)"
command -v rsync >/dev/null || { apt-get update -qq && apt-get install -y -qq rsync; }
rsync -a --exclude='.env' --exclude='venv' --exclude='__pycache__' "$ROOT/backend/" "$APP/backend/"
rsync -a --exclude='node_modules' --exclude='build' "$ROOT/frontend/" "$APP/frontend/"
rm -rf "$TMP"

echo "> 4/7 Backend derleme dogrulamasi"
if ! ( cd "$APP/backend" && "$APP/backend/venv/bin/python" -m py_compile $(find . -name '*.py' -not -path './venv/*' -not -path '*/__pycache__/*') ) 2>/tmp/roof_py.log; then
  echo "!! PY DERLEME HATASI:"; tail -15 /tmp/roof_py.log; restore; exit 1
fi
echo "   backend py OK"

echo "> 5/7 Frontend build (birkac dakika)"
cd "$APP/frontend"
export NODE_OPTIONS=--max-old-space-size=4096
( yarn install --frozen-lockfile || yarn install ) >/tmp/roof_yarn.log 2>&1 || { echo "!! yarn install HATA:"; tail -20 /tmp/roof_yarn.log; restore; exit 1; }
if ! CI=false yarn build >/tmp/roof_build.log 2>&1; then
  echo "!! BUILD HATASI:"; tail -35 /tmp/roof_build.log; restore; exit 1
fi
chown -R www-data:www-data "$APP"
echo "   build OK"

echo "> 6/7 Backend restart + saglik kontrolu"
systemctl restart facette-backend
sleep 4
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 http://127.0.0.1:8001/api/estoril/storefront-products 2>/dev/null || echo 000)
if [ "$CODE" = "000" ]; then
  echo "!! Backend ayaga kalkmadi. Son loglar:"; journalctl -u facette-backend -n 25 --no-pager
  restore; exit 1
fi
echo "   backend saglikli (HTTP $CODE)"

echo "> 7/7 Marka site_name=Roof + nginx reload"
mongosh "$DBN" --quiet --eval 'db.settings.updateOne({id:"main"},{$set:{site_name:"Roof"}},{upsert:true})' >/dev/null 2>&1 || true
nginx -t >/dev/null 2>&1 && systemctl reload nginx || true
echo ""
echo "==================================================================="
echo ">>> TAMAM. Guncel surum + marka=Roof + GTM temiz."
echo "    Panelde: Tasarim > Estoril Site (Vitrin), Ayarlar > Mail Hesaplari korundu."
echo "    Yedek: $BK"
echo "    Geri almak istersen:"
echo "      sudo tar xzf $BK -C $APP && sudo systemctl restart facette-backend"
echo "==================================================================="
