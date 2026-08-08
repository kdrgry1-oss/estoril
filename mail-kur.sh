#!/usr/bin/env bash
# ============================================================================
# ESTORIL — Self-host mail (Postfix + Dovecot + OpenDKIM + Roundcube webmail)
#   - Alma + Gönderme (giden 25 acik) + webmail (https://mail.estoril.com.tr)
#   - TEK kutu: info@estoril.com.tr
#   - Mevcut nginx (80/443) ve estoril/panel siteleri BOZULMAZ.
#
# ONCE Cloudflare'e sunlari ekle (hepsi DNS-only / GRI bulut):
#   A     mail            185.126.216.28
#   MX    @               mail.estoril.com.tr   (oncelik 10)
#   TXT   @               v=spf1 mx a ip4:185.126.216.28 ~all
#   TXT   _dmarc          v=DMARC1; p=none; rua=mailto:info@estoril.com.tr
# (DKIM TXT'yi script SONUNDA yazdiracak — onu da ekleyeceksin.)
#
# Calistir:  sudo MAIL_PASS='istedigin-sifre' bash mail-kur.sh
#   (MAIL_PASS vermezsen script rastgele guclu bir sifre uretir ve yazdirir.)
# ============================================================================
set -euo pipefail
trap 'echo "!! HATA: satir $LINENO — durdu. Yukaridaki son adima bak."' ERR
[ "$(id -u)" -eq 0 ] || { echo "root gerek: sudo bash $0"; exit 1; }

DOMAIN="estoril.com.tr"
HOST="mail.estoril.com.tr"
MAILUSER="info@${DOMAIN}"
MAILPASS="${MAIL_PASS:-$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)}"
RCVER="1.6.9"
CFMAIL="/etc/letsencrypt/live/${HOST}"
CFBASE="/etc/letsencrypt/live/${DOMAIN}"
export DEBIAN_FRONTEND=noninteractive

echo "==================================================================="
echo ">>> ESTORIL MAIL kurulumu — kutu: ${MAILUSER}"
echo "==================================================================="

# ------------------------------------------------------------------ 1) paketler
echo "> 1/9 Paketler kuruluyor (postfix, dovecot, opendkim, php, roundcube dep)"
debconf-set-selections <<EOF
postfix postfix/main_mailer_type string Internet Site
postfix postfix/mailname string ${HOST}
EOF
apt-get update -qq
apt-get install -y -qq \
  postfix postfix-pcre \
  dovecot-core dovecot-imapd dovecot-lmtpd \
  opendkim opendkim-tools \
  certbot python3-certbot-nginx \
  php-fpm php-cli php-common php-sqlite3 php-intl php-mbstring php-xml php-gd php-zip php-curl \
  curl ca-certificates >/dev/null
echo "   paketler tamam"

PHPV="$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')"
PHPSOCK="/run/php/php${PHPV}-fpm.sock"
echo "   PHP ${PHPV}, fpm sock: ${PHPSOCK}"

# --------------------------------------------------------- 2) vmail kullanicisi
echo "> 2/9 vmail kullanicisi + maildir"
getent group vmail >/dev/null || groupadd -g 5000 vmail
getent passwd vmail >/dev/null || useradd -g vmail -u 5000 -d /var/mail/vhosts -s /usr/sbin/nologin -m vmail
mkdir -p "/var/mail/vhosts/${DOMAIN}"
chown -R vmail:vmail /var/mail/vhosts
echo "   ok"

# -------------------------------------------------- 3) sertifika (mail host)
echo "> 3/9 TLS sertifikasi (${HOST})"
# ACME icin gecici http blok
cat > /etc/nginx/sites-available/estoril-mail <<NG
server {
    listen 80; listen [::]:80;
    server_name ${HOST};
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
NG
mkdir -p /var/www/html
ln -sf /etc/nginx/sites-available/estoril-mail /etc/nginx/sites-enabled/estoril-mail
nginx -t && systemctl reload nginx
RESOLVED="$(dig +short A ${HOST} @1.1.1.1 | tail -1)"
if [ "$RESOLVED" = "185.126.216.28" ]; then
  certbot certonly --webroot -w /var/www/html -d "${HOST}" \
    --non-interactive --agree-tos -m "${MAILUSER}" --keep-until-expiring || true
else
  echo "   !! DNS henuz yayilmamis (${HOST} -> '${RESOLVED}'). Sertifika atlaniyor."
fi
if [ -f "${CFMAIL}/fullchain.pem" ]; then
  CERT="${CFMAIL}/fullchain.pem"; KEY="${CFMAIL}/privkey.pem"
  echo "   ${HOST} sertifikasi hazir"
else
  CERT="${CFBASE}/fullchain.pem"; KEY="${CFBASE}/privkey.pem"
  echo "   !! mail sertifikasi yok — gecici olarak ${DOMAIN} sertifikasi kullanilacak"
  echo "      (Roundcube localhost'a baglandigi icin sorun cikarmaz; DNS yayilinca"
  echo "       'sudo certbot certonly --webroot -w /var/www/html -d ${HOST}' + bu scripti tekrar calistir.)"
fi

# ------------------------------------------------------------- 4) OpenDKIM
echo "> 4/9 OpenDKIM (imza anahtari)"
mkdir -p "/etc/opendkim/keys/${DOMAIN}"
if [ ! -f "/etc/opendkim/keys/${DOMAIN}/default.private" ]; then
  opendkim-genkey -b 2048 -d "${DOMAIN}" -s default -D "/etc/opendkim/keys/${DOMAIN}"
fi
chown -R opendkim:opendkim /etc/opendkim
chmod 600 "/etc/opendkim/keys/${DOMAIN}/default.private"
cat > /etc/opendkim.conf <<DKIM
Syslog                  yes
UMask                   002
Mode                    sv
Canonicalization        relaxed/simple
Domain                  ${DOMAIN}
Selector                default
KeyFile                 /etc/opendkim/keys/${DOMAIN}/default.private
Socket                  inet:8891@127.0.0.1
OversignHeaders         From
AutoRestart             yes
AutoRestartRate         10/1h
PidFile                 /run/opendkim/opendkim.pid
UserID                  opendkim
DKIM
mkdir -p /run/opendkim; chown opendkim:opendkim /run/opendkim
systemctl enable opendkim >/dev/null 2>&1 || true
systemctl restart opendkim
echo "   opendkim calisiyor"

# ------------------------------------------------------------- 5) Postfix
echo "> 5/9 Postfix"
echo "${HOST}" > /etc/mailname
postconf -e "myhostname = ${HOST}"
postconf -e "mydomain = ${DOMAIN}"
postconf -e "myorigin = \$mydomain"
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ipv4"
postconf -e "mydestination = localhost"
postconf -e "biff = no"
postconf -e "append_dot_mydomain = no"
postconf -e "smtpd_banner = \$myhostname ESMTP"
# virtual (Dovecot LMTP teslimi)
postconf -e "virtual_mailbox_domains = ${DOMAIN}"
postconf -e "virtual_mailbox_maps = hash:/etc/postfix/vmailbox"
postconf -e "virtual_alias_maps = hash:/etc/postfix/virtual"
postconf -e "virtual_transport = lmtp:unix:private/dovecot-lmtp"
# TLS
postconf -e "smtpd_tls_cert_file = ${CERT}"
postconf -e "smtpd_tls_key_file = ${KEY}"
postconf -e "smtpd_tls_security_level = may"
postconf -e "smtp_tls_security_level = may"
postconf -e "smtpd_tls_auth_only = yes"
# SASL (Dovecot)
postconf -e "smtpd_sasl_type = dovecot"
postconf -e "smtpd_sasl_path = private/auth"
postconf -e "smtpd_sasl_auth_enable = yes"
postconf -e "smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated reject_unauth_destination"
# DKIM milter
postconf -e "milter_default_action = accept"
postconf -e "milter_protocol = 6"
postconf -e "smtpd_milters = inet:127.0.0.1:8891"
postconf -e "non_smtpd_milters = inet:127.0.0.1:8891"

printf '%s\t%s\n' "${MAILUSER}" "${DOMAIN}/info/" > /etc/postfix/vmailbox
postmap /etc/postfix/vmailbox
: > /etc/postfix/virtual
printf '%s\t%s\n' "postmaster@${DOMAIN}" "${MAILUSER}" >> /etc/postfix/virtual
printf '%s\t%s\n' "abuse@${DOMAIN}"      "${MAILUSER}" >> /etc/postfix/virtual
postmap /etc/postfix/virtual

# submission(587) + smtps(465) — yoksa ekle
if ! postconf -M submission.inet >/dev/null 2>&1; then
cat >> /etc/postfix/master.cf <<'MCF'

# ===== ESTORIL-MAIL =====
submission inet n       -       y       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
smtps     inet  n       -       y       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
MCF
fi
echo "   postfix yapilandirildi"

# ------------------------------------------------------------- 6) Dovecot
echo "> 6/9 Dovecot (IMAP + LMTP + SASL)"
DPASS="$(doveadm pw -s SHA512-CRYPT -p "${MAILPASS}")"
printf '%s:%s\n' "${MAILUSER}" "${DPASS}" > /etc/dovecot/users
chown root:dovecot /etc/dovecot/users; chmod 640 /etc/dovecot/users
cat > /etc/dovecot/local.conf <<DCONF
protocols = imap lmtp
mail_location = maildir:/var/mail/vhosts/%d/%n
mail_privileged_group = mail
first_valid_uid = 5000
first_valid_gid = 5000

ssl = required
ssl_cert = <${CERT}
ssl_key = <${KEY}

disable_plaintext_auth = yes
auth_mechanisms = plain login

passdb {
  driver = passwd-file
  args = scheme=SHA512-CRYPT username_format=%u /etc/dovecot/users
}
userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n
}

service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}
service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0660
    user = postfix
    group = postfix
  }
  unix_listener auth-userdb {
    mode = 0600
    user = vmail
  }
}
service auth-worker {
  user = vmail
}
DCONF
systemctl restart dovecot
systemctl restart postfix
echo "   dovecot + postfix calisiyor"

# ------------------------------------------------------------- 7) Roundcube
echo "> 7/9 Roundcube webmail (${RCVER})"
if [ ! -f /var/www/roundcube/index.php ]; then
  cd /tmp
  curl -fsSL -o rc.tgz "https://github.com/roundcube/roundcubemail/releases/download/${RCVER}/roundcubemail-${RCVER}-complete.tar.gz"
  tar xzf rc.tgz
  rm -rf /var/www/roundcube
  mv "roundcubemail-${RCVER}" /var/www/roundcube
  rm -f rc.tgz
fi
mkdir -p /var/www/roundcube/db
DESKEY="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)"
cat > /var/www/roundcube/config/config.inc.php <<RC
<?php
\$config = [];
\$config['db_dsnw'] = 'sqlite:////var/www/roundcube/db/sqlite.db?mode=0646';
\$config['imap_host'] = 'tls://localhost:143';
\$config['imap_conn_options'] = ['ssl' => ['verify_peer'=>false,'verify_peer_name'=>false,'allow_self_signed'=>true]];
\$config['smtp_host'] = 'tls://localhost:587';
\$config['smtp_user'] = '%u';
\$config['smtp_pass'] = '%p';
\$config['smtp_conn_options'] = ['ssl' => ['verify_peer'=>false,'verify_peer_name'=>false,'allow_self_signed'=>true]];
\$config['support_url'] = '';
\$config['product_name'] = 'Estoril Webmail';
\$config['des_key'] = '${DESKEY}';
\$config['plugins'] = ['archive','zipdownload'];
\$config['skin'] = 'elastic';
\$config['enable_installer'] = false;
\$config['mail_domain'] = '${DOMAIN}';
RC
# DB semasi
cd /var/www/roundcube
php bin/initdb.sh --dir=SQL >/dev/null 2>&1 || php -r '
  $db=new PDO("sqlite:/var/www/roundcube/db/sqlite.db");
  $db->exec(file_get_contents("/var/www/roundcube/SQL/sqlite.initial.sql"));
' 2>/dev/null || true
chown -R www-data:www-data /var/www/roundcube
chmod -R 0755 /var/www/roundcube/temp /var/www/roundcube/logs /var/www/roundcube/db
echo "   roundcube kuruldu"

# ------------------------------------------------------------- 8) nginx (webmail)
echo "> 8/9 nginx (https://${HOST})"
cat > /etc/nginx/sites-available/estoril-mail <<NG
server {
    listen 80; listen [::]:80;
    server_name ${HOST};
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name ${HOST};
    ssl_certificate ${CERT};
    ssl_certificate_key ${KEY};
    ssl_protocols TLSv1.2 TLSv1.3;
    root /var/www/roundcube; index index.php;
    client_max_body_size 25M;

    location ~ ^/(config|temp|logs|SQL|bin|vendor)/ { deny all; }
    location ~ /\. { deny all; }
    location / { try_files \$uri \$uri/ /index.php\$is_args\$args; }
    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:${PHPSOCK};
    }
}
NG
nginx -t && systemctl reload nginx

# firewall (varsa)
if command -v ufw >/dev/null && ufw status 2>/dev/null | grep -qi active; then
  for p in 25 143 465 587 993; do ufw allow ${p}/tcp >/dev/null 2>&1 || true; done
  echo "   ufw: mail portlari acildi"
fi

systemctl enable postfix dovecot opendkim >/dev/null 2>&1 || true

# ------------------------------------------- 8.5) estoril-mail yonetim komutu
echo "> 8.5 estoril-mail komutu (istedigin adresi sen ac)"
cat > /usr/local/bin/estoril-mail <<'EMAIL'
#!/usr/bin/env bash
set -euo pipefail
DOMAIN="estoril.com.tr"; USERS="/etc/dovecot/users"; VBOX="/etc/postfix/vmailbox"
[ "$(id -u)" -eq 0 ] || { echo "root gerek: sudo estoril-mail ..."; exit 1; }
norm(){ case "$1" in *@*) printf '%s' "$1";; *) printf '%s@%s' "$1" "$DOMAIN";; esac; }
cmd="${1:-}"; a="${2:-}"; p="${3:-}"
case "$cmd" in
  add)
    [ -n "$a" ] && [ -n "$p" ] || { echo "kullanim: sudo estoril-mail add ad 'Sifre'"; exit 1; }
    addr="$(norm "$a")"; lp="${addr%@*}"
    grep -q "^${addr}:" "$USERS" 2>/dev/null && { echo "zaten var: $addr"; exit 1; }
    h="$(doveadm pw -s SHA512-CRYPT -p "$p")"
    printf '%s:%s\n' "$addr" "$h" >> "$USERS"
    printf '%s\t%s/%s/\n' "$addr" "$DOMAIN" "$lp" >> "$VBOX"; postmap "$VBOX"
    mkdir -p "/var/mail/vhosts/${DOMAIN}/${lp}"; chown -R vmail:vmail "/var/mail/vhosts/${DOMAIN}"
    systemctl reload postfix 2>/dev/null || true
    echo "EKLENDI: ${addr}" ;;
  passwd)
    addr="$(norm "$a")"; grep -q "^${addr}:" "$USERS" 2>/dev/null || { echo "yok: $addr"; exit 1; }
    h="$(doveadm pw -s SHA512-CRYPT -p "$p")"
    ea="$(printf '%s' "$addr" | sed 's/[.[\*^$/]/\\&/g')"; eh="$(printf '%s' "$h" | sed 's/[&/\]/\\&/g')"
    sed -i "s/^${ea}:.*/${ea}:${eh}/" "$USERS"; echo "SIFRE DEGISTI: ${addr}" ;;
  del)
    addr="$(norm "$a")"; es="$(printf '%s' "$addr" | sed 's/[.[\*^$/]/\\&/g')"
    sed -i "/^${es}:/d" "$USERS"; sed -i "/^${es}$(printf '\t')/d" "$VBOX"; postmap "$VBOX"
    systemctl reload postfix 2>/dev/null || true; echo "SILINDI: ${addr}" ;;
  list) echo "Posta kutulari:"; cut -d: -f1 "$USERS" 2>/dev/null | sed 's/^/  /' ;;
  *) echo "sudo estoril-mail add|passwd|del|list  (or: add satis 'Sifre')" ;;
esac
EMAIL
chmod +x /usr/local/bin/estoril-mail

# ------------------------------------------------------------- 9) OZET
echo "> 9/9 DKIM kaydi + ozet"
DKVAL="$(python3 - <<'PY'
import re,io
try:
    s=io.open("/etc/opendkim/keys/estoril.com.tr/default.txt").read()
    print("".join(re.findall(r'"([^"]*)"',s)))
except Exception as e:
    print("DEFAULT.TXT-OKUNAMADI")
PY
)"

echo ""
echo "==================================================================="
echo ">>> KURULUM TAMAM"
echo "==================================================================="
echo "WEBMAIL : https://${HOST}"
echo "KUTU    : ${MAILUSER}"
echo "SIFRE   : ${MAILPASS}"
echo ""
echo ">>> Cloudflare'e SON kaydi ekle (DNS-only / gri bulut):"
echo "    Tip : TXT"
echo "    Ad  : default._domainkey"
echo "    Deger:"
echo "    ${DKVAL}"
echo ""
echo ">>> Zaten eklemis olman gerekenler (kontrol et):"
echo "    A     mail    -> 185.126.216.28"
echo "    MX    @       -> ${HOST} (oncelik 10)"
echo "    TXT   @       -> v=spf1 mx a ip4:185.126.216.28 ~all"
echo "    TXT   _dmarc  -> v=DMARC1; p=none; rua=mailto:${MAILUSER}"
echo "==================================================================="
