#!/usr/bin/env bash
# Mail kurulum ön-teşhis: giden 25, gelen 25, mevcut MX, port çakışması.
echo "=== 1) Giden 25. port (relay yerine self-send mümkün mü?) ==="
timeout 8 bash -c 'exec 3<>/dev/tcp/gmail-smtp-in.l.google.com/25 && head -1 <&3' 2>/dev/null \
  && echo "  -> GIDEN 25 ACIK" || echo "  -> GIDEN 25 KAPALI (zaten relay kullanacagiz, sorun degil)"

echo "=== 2) Gelen 25. port dinleniyor mu / firewall ==="
ss -ltnp 2>/dev/null | grep -E ':25\b' || echo "  -> su an :25 dinleyen yok (Postfix henuz kurulmadi - normal)"
command -v ufw >/dev/null && ufw status | grep -Ei '25|status' || echo "  -> ufw yok/pasif"

echo "=== 3) Sunucunun gordugu genel IP (PTR bu IP icin gerekli) ==="
curl -s --max-time 8 https://api.ipify.org; echo

echo "=== 4) estoril.com.tr mevcut MX / mail DNS ==="
for r in MX TXT; do echo "-- $r estoril.com.tr --"; dig +short $r estoril.com.tr @1.1.1.1; done
echo "-- MX mail.estoril.com.tr --"; dig +short A mail.estoril.com.tr @1.1.1.1

echo "=== 5) 80/443 kim dinliyor (nginx ile cakisma kontrolu) ==="
ss -ltnp 2>/dev/null | grep -E ':80\b|:443\b' | sed 's/^/  /'

echo "=== 6) RAM/disk (Roundcube+Dovecot icin) ==="
free -h | awk 'NR==1||/Mem/'; df -h / | awk 'NR==1||NR==2'
echo "=== TESHIS TAMAM ==="
