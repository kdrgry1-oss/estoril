#!/usr/bin/env bash
# ============================================================================
# Panel admin girisini OLUSTURUR / SIFIRLAR (SUNUCUDA calistirilir).
#   Kullanim:  sudo bash yeni-admin.sh [email] [sifre]
#   Varsayilan: estorilcosmetics@gmail.com / Estoril2026!
# Not: Bu script SUNUCUDA calismali. GitHub'a push etmek tek basina
#      admin'i olusturmaz — sunucuda calistirilmasi gerekir.
# ============================================================================
set -euo pipefail
EMAIL="${1:-estorilcosmetics@gmail.com}"
PASS="${2:-Estoril2026!}"
BE=/opt/facette/backend
[ -f "$BE/reset_admin.py" ] || { echo "HATA: $BE/reset_admin.py yok"; exit 1; }
cd "$BE"
set -a; . ./.env; set +a
ADMIN_EMAIL="$EMAIL" ADMIN_RESET_PASSWORD="$PASS" venv/bin/python reset_admin.py
echo ""
echo ">>> TAMAM. Giris: https://panel.estoril.com.tr"
echo "    E-posta: $EMAIL"
echo "    Sifre  : $PASS"
