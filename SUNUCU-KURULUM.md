# Facette — Tek Sunucu Temiz Kurulum (Runbook)

Bu rehber, Facette panelini **kendi sunucuna** (Ubuntu 24.04, `185.126.216.28`),
**boş bir MongoDB** ile sıfırdan kurar. Mevcut Facette'in **hiçbir gerçek verisi**
(sipariş / ürün / müşteri / secret) taşınmaz. Entegrasyon anahtarları boş bırakılır;
panel açıldıktan sonra kendi anahtarlarını girersin.

- **Domain:** `estoril.com.tr` (+ `www`)
- **Mimari:** nginx (80/443) → `/api` uvicorn (127.0.0.1:8001, systemd) + `/` React build; yerel MongoDB.
- **Otomasyon:** `deploy.sh` her şeyi kurar (MongoDB, Python 3.11, Node 20, nginx, servis, admin).

---

## Ön koşul: DNS

Cloudflare'de **yalnızca** şu iki A kaydı kalmalı (yanlış `93.89.230.125` kayıtlarını sil):

| Name | Type | Content | Proxy |
|---|---|---|---|
| `estoril.com.tr` | A | `185.126.216.28` | **DNS only (gri)** |
| `www.estoril.com.tr` | A | `185.126.216.28` | **DNS only (gri)** |

Doğrula — ikisi de **sadece** `185.126.216.28` dönmeli:
```bash
dig +short estoril.com.tr
dig +short www.estoril.com.tr
```
> SSL kurulana kadar gri bulut kalsın. HTTPS çalışınca turuncu buluta çevirip
> Cloudflare SSL/TLS modunu **Full (strict)** yaparsın.

---

## Adım 1 — Dosyaları sunucuya at

Kendi bilgisayarından (Facette zip'i ve bu script sende):
```bash
# Facette kaynak zip'i
scp facettemain_1.zip salih@185.126.216.28:~/

# deploy.sh (bu repodan)
scp deploy.sh salih@185.126.216.28:~/
```
> Alternatif: sunucuda bu repoyu klonlayıp `deploy.sh`'yi oradan da alabilirsin.

## Adım 2 — Kurulumu çalıştır

Sunucuda (SSH):
```bash
chmod +x ~/deploy.sh
sudo ADMIN_PASSWORD='buraya-guclu-bir-sifre' ~/deploy.sh ~/facettemain_1.zip
```
- İlk argüman: Facette **zip'i** ya da açılmış **klasörü** (script ikisini de kabul eder).
- `ADMIN_PASSWORD` vermezsen script rastgele üretir ve sonda ekrana yazar.
- Süre: pip + yarn build ile ~5–10 dk. Sonda kurulum özeti + admin bilgileri gösterilir.

Ne yapar (12 adım): sistem paketleri + Python 3.11 → MongoDB 8 → Node 20 + yarn →
nginx + certbot → kodu `/opt/facette`'e kopyalar → backend venv + `pip install` →
temiz `backend/.env` → taze admin (`admin@facette.com`) → frontend build →
systemd servisi (`facette-backend`) → nginx (HTTP) → doğrulama.

## Adım 3 — HTTP testi

```bash
curl -I http://estoril.com.tr        # 200/30x beklenir
systemctl status facette-backend      # active (running)
```
Tarayıcıdan `http://estoril.com.tr` → panel açılmalı, `admin@facette.com` + şifrenle giriş.

## Adım 4 — HTTPS (Let's Encrypt)

DNS sunucuya bakıyorsa (Adım 0 doğrulandıysa, www dahil):
```bash
sudo certbot --nginx -d estoril.com.tr -d www.estoril.com.tr --redirect \
  -m senin@eposta.com --agree-tos -n
```
certbot nginx'i otomatik HTTPS'e çevirir ve 80'i 443'e yönlendirir.
Sonra Cloudflare'de bulutu **turuncu** yapıp SSL/TLS modunu **Full (strict)** seç.

## Adım 5 — Entegrasyon anahtarları (sonradan, istediğinde)

Boş bırakılan modülleri (R2 görsel yükleme, Trendyol, İYS, İyzico, e-posta) kullanmak için:
```bash
sudo nano /opt/facette/backend/.env     # ilgili satırların # işaretini kaldır, değerleri gir
sudo systemctl restart facette-backend
```
Anahtar tabloları için repodaki Facette `SELF_HOSTING.md` → "Env Değişkenleri Tablosu".

---

## Yönetim / Sorun giderme

```bash
# Backend logları
journalctl -u facette-backend -f
sudo systemctl restart facette-backend

# nginx
sudo nginx -t && sudo systemctl reload nginx
sudo tail -f /var/log/nginx/error.log

# MongoDB
systemctl status mongod
mongosh facette --eval 'db.getCollectionNames()'   # boş DB → []

# Admin şifresini yeniden ayarla
cd /opt/facette/backend && set -a && . .env && set +a
ADMIN_RESET_PASSWORD='yeni-sifre' venv/bin/python reset_admin.py
```

### Sık sorunlar
- **`pip install` patlarsa:** `requirements.txt` bazı sıra dışı sürümlere / Emergent özel
  paket aynasına dayanıyor. Çıktıyı paylaş; pin'leri birlikte gevşetiriz.
- **`mongod` başlamıyor:** CPU'da AVX yoksa MongoDB 8 çalışmaz → `journalctl -u mongod`.
- **Panel açılıyor ama API 502:** backend düşmüştür → `journalctl -u facette-backend -n 50`.
- **Görsel yüklenmiyor:** R2 anahtarları boş; `.env`'e R2_* gir + restart.

---

## Notlar
- Kurulum **boş DB** ile gelir; hiçbir gerçek veri yüklenmez (`mongorestore` çalıştırılmaz).
- `deploy.sh`, kopyalarken `db_backup/`, `*.bak-*`, `.iys-*`, `node_modules` gibi
  gereksiz/hassas dosyaları hariç tutar.
- Estoril vitrin entegrasyonu (ayrı paket: `facette-entegrasyon/`) bu temel kurulum
  ayağa kalktıktan sonra `KURULUM.md`'deki adımlarla eklenir.
