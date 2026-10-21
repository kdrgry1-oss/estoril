#!/usr/bin/env bash
# ============================================================================
# Estoril vitrin — GitHub -> CANLI otomatik deploy (tek seferlik kurulum)
#   - Deploy anahtari (read-only) uretir; GitHub Deploy Keys'e eklenir.
#   - /opt/estoril-storefront klonu + systemd timer (2 dk) ile main'i cekip
#     /var/www/estoril'e uygular.
#   - products.json / site-content.json DOKUNULMAZ (panel/backend yonetir).
# Calistir:  sudo bash estoril-vitrin-autodeploy.sh   (anahtari ekleyip TEKRAR)
# ============================================================================
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "root: sudo bash $0"; exit 1; }
REPO_SSH="git@github.com:kdrgry1-oss/estoril-storefront.git"
REPO_DIR=/opt/estoril-storefront
SITE=/var/www/estoril
KEY=/root/.ssh/estoril_deploy

command -v git   >/dev/null || { apt-get update -qq && apt-get install -y -qq git; }
command -v rsync >/dev/null || { apt-get install -y -qq rsync; }

mkdir -p /root/.ssh; chmod 700 /root/.ssh
[ -f "$KEY" ] || ssh-keygen -t ed25519 -f "$KEY" -N "" -C "estoril-deploy" >/dev/null
if ! grep -q estoril_deploy /root/.ssh/config 2>/dev/null; then
  printf 'Host github.com\n  HostName github.com\n  User git\n  IdentityFile %s\n  IdentitiesOnly yes\n  StrictHostKeyChecking accept-new\n' "$KEY" >> /root/.ssh/config
  chmod 600 /root/.ssh/config
fi

echo ""
echo ">>> SUNUCUNUN DEPLOY ANAHTARI (GitHub'a eklenecek public key):"
echo "----------------------------------------------------------------"
cat "$KEY.pub"
echo "----------------------------------------------------------------"

# clone / fetch dene
CLONE_OK=1
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" fetch origin main --quiet 2>/tmp/giterr || CLONE_OK=0
else
  git clone --depth 1 "$REPO_SSH" "$REPO_DIR" 2>/tmp/giterr || CLONE_OK=0
fi

if [ "$CLONE_OK" != "1" ]; then
  echo ""
  echo "=================================================================="
  echo " Repo'ya henuz erisemiyorum. Yukaridaki public key'i ekle:"
  echo "  GitHub -> estoril-storefront -> Settings -> Deploy keys ->"
  echo "  Add deploy key -> Key: yukaridaki tek satir -> Add key"
  echo "  (Allow write access'i ISARETLEME; read-only yeterli.)"
  echo " Sonra bu komutu AYNEN tekrar calistir."
  echo "------------------------------------------------------------------"
  tail -3 /tmp/giterr 2>/dev/null
  echo " (Hata 'port 22' / 'Connection timed out' ise sunucunun GIDEN 22"
  echo "  portu kapali olabilir; o zaman HTTPS+token yoluna geceriz - haber ver.)"
  echo "=================================================================="
  exit 0
fi

# deploy scripti
cat > /usr/local/bin/estoril-vitrin-deploy <<'DEPLOY'
#!/usr/bin/env bash
set -uo pipefail
REPO=/opt/estoril-storefront; SITE=/var/www/estoril
cd "$REPO" || exit 0
B=$(git rev-parse HEAD 2>/dev/null || echo none)
git fetch origin main --quiet || exit 0
git reset --hard origin/main --quiet
A=$(git rev-parse HEAD)
[ "$B" = "$A" ] && exit 0
rsync -a --exclude='.git' --exclude='README.md' --exclude='serve.sh' \
      --exclude='.gitignore' --exclude='products.json' --exclude='site-content.json' \
      "$REPO"/ "$SITE"/
chown -R www-data:www-data "$SITE"
logger -t estoril-vitrin "deployed $B -> $A"
DEPLOY
chmod +x /usr/local/bin/estoril-vitrin-deploy

# systemd timer (2 dk)
printf '[Unit]\nDescription=Estoril vitrin GitHub auto-deploy\n[Service]\nType=oneshot\nExecStart=/usr/local/bin/estoril-vitrin-deploy\n' > /etc/systemd/system/estoril-vitrin.service
printf '[Unit]\nDescription=Estoril vitrin auto-deploy (2dk)\n[Timer]\nOnBootSec=1min\nOnUnitActiveSec=2min\n[Install]\nWantedBy=timers.target\n' > /etc/systemd/system/estoril-vitrin.timer
systemctl daemon-reload
systemctl enable --now estoril-vitrin.timer >/dev/null 2>&1
/usr/local/bin/estoril-vitrin-deploy || true

echo ""
echo "=================================================================="
echo ">>> TAMAM. GitHub (main) -> CANLI otomatik deploy AKTIF."
echo "    Her 2 dakikada bir cekip /var/www/estoril'e uygular."
echo "    products.json / site-content.json korunur (panel yonetir)."
echo "    Durum:  systemctl status estoril-vitrin.timer"
echo "    Log:    journalctl -t estoril-vitrin -n 20"
echo "=================================================================="
