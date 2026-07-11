#!/usr/bin/env bash
# Vitrini (estoril.com.tr) yeni bir estoril-site zip'i ile gunceller.
# Kullanim: sudo ./update-storefront.sh ~/estoril-new.zip
set -euo pipefail
SITE_DIR=/var/www/estoril
HOMEPAGE="Estoril Premium Ana Sayfa.dc.html"
[ "$(id -u)" -eq 0 ] || { echo "root: sudo $0 <zip>"; exit 1; }
ZIP="${1:-}"; [ -f "$ZIP" ] || { echo "zip ver: sudo $0 /home/salih/estoril-new.zip"; exit 1; }
command -v unzip >/dev/null || { apt-get update -qq && apt-get install -y -qq unzip; }

TMP=/opt/_estoril_new; rm -rf "$TMP"; mkdir -p "$TMP"
unzip -q -o "$ZIP" -d "$TMP"
S="$(dirname "$(find "$TMP" -name '*.dc.html' -not -path '*__MACOSX*' -not -name '._*' | head -1)")"
[ -n "$S" ] && [ -f "$S/$HOMEPAGE" ] || { echo "HATA: zip'te .dc.html/ana sayfa yok"; exit 1; }

mkdir -p "$SITE_DIR"
cp -a "$S"/. "$SITE_DIR"/
rm -rf "$SITE_DIR/__MACOSX"
find "$SITE_DIR" \( -name '.DS_Store' -o -name '._*' \) -delete 2>/dev/null || true
cp -f "$SITE_DIR/$HOMEPAGE" "$SITE_DIR/index.html"
chown -R www-data:www-data "$SITE_DIR"
echo "TAMAM: vitrin guncellendi ($(ls "$SITE_DIR"/*.dc.html | wc -l) sayfa). https://estoril.com.tr"
