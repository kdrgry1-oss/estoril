# ESTORIL — KRİTİK MİMARİ KURALLAR (İHLAL EDİLEMEZ)

> Bu dosya kullanıcının **kesin ve kritik** talebidir. Her adımda bu kurallara uyulur.
> Kullanıcı vurgusu: "bu konu benim için çok kritik."

## GÜNCELLEME (kullanıcı yönü netleşti)
Kritik kural **ESKİ Facette firmasının sistemine/verisine karşıydı** — onların canlı
sistemine hiçbir Estoril verisi gitmeyecek, onların verisi de çekilmeyecek. AMA kullanıcının
kendi sunucusundaki (185.126.216.28) **YEREL, boş** veritabanı tamamen Estoril'indir ve
eski Facette ile sıfır bağlantısı vardır. Kullanıcı açık talebi:
- "bu panel Estoril'in", "ürün/kategorileri panelin NORMAL alanlarına koy, ayrı alan açma"
- "XML'den Estoril'in ürün ve kategorilerini çek, normal Ürünler/Kategoriler sayfalarına yaz"
=> Estoril'in KENDİ ürün/kategorileri, kullanıcının KENDİ yerel Mongo'suna yazılabilir
   (native sayfalardan yönetim için). Bu, "eski Facette'e veri gönderme" YASAĞINI ihlal ETMEZ.
YASAK olan hâlâ: eski Facette firmasının canlı sistemi/verisi ile HERHANGİ bir alışveriş.

## 1. VERİ İZOLASYONU — Estoril verisi ASLA Facette'e gitmez
- Estoril'in içeriği ve ürünleri **yalnızca JSON dosyalarında** tutulur:
  `site-content.json`, `products.json` (vitrin klasöründe / `ESTORIL_SITE_DIR`).
- Bu veriler **ASLA** Facette'in MongoDB'sine yazılmaz. Facette Mongo'su Estoril ürünü/
  siparişi/müşterisi görmeyecek — boş kalacak (yalnızca kurulum admin'i).
- Estoril storefront'u **statik** olarak (nginx) servis edilir; verisini JSON'dan `fetch` eder.

## 2. FACETTE VERİSİ ASLA ÇEKİLMEZ
- Facette'in hiçbir gerçek verisi (ürün, sipariş, müşteri, ayar, secret) bu sisteme
  aktarılmaz / geri yüklenmez. `mongorestore` vb. YASAK.
- Facette Mongo'su boş kalır; sadece uygulamanın açılışta oluşturduğu boş koleksiyonlar
  + tek admin kullanıcısı bulunur.

## 3. YALNIZCA YAZILIMSAL MODÜLLER ÇEKİLİR
- Facette'ten alınan tek şey **kod / yazılım modülleri** (ör. Estoril yönetim modülü:
  `estoril_site.py` + `EstorilSite.jsx`). Bunlar Facette'in altyapısını (auth `require_admin`,
  görsel yükleme) kullanır ama veriyi **JSON dosyalarına** yazar — Mongo'ya değil.
- Veri taşımak (import/export/sync) DEĞİL, sadece işlevsel modül taşımak.

## 4. XML BESLEMESİ (estorilcosmetic.com)
- `estorilcosmetic.com` XML'inden gelen ürünler **`products.json`'a** dönüştürülür
  (Estoril'in kendi JSON'u). 
- Facette'in dahili XML/`xml_feeds` (Mongo tabanlı) içe aktarıcısı Estoril için **KULLANILMAZ** —
  çünkü o, veriyi Facette Mongo'suna yazar. Bu YASAK.

## 5. REDDEDİLEN YAKLAŞIM (kullanıcı kesin istemedi)
- ❌ "Facette'in dinamik storefront'unu Estoril'e göre temala + ürünleri Facette Mongo'suna
  aktar" — bu seçenek KESİNLİKLE reddedildi. Bir daha önerilmez, uygulanmaz.

## Özet mimari (izin verilen tek yol)
```
Estoril statik tasarım (.dc.html) + products.json + site-content.json   ← storefront (nginx, ESTORIL_SITE_DIR)
        ↑ düzenler (JSON dosyalarına yazar, Mongo'ya DEĞİL)
Facette paneli + Estoril modülü (yalnızca yazılım)
        ↑ ürünleri products.json'a dönüştürür (Facette Mongo'ya DEĞİL)
estorilcosmetic.com XML
```
Facette Mongo ile Estoril verisi arasında **hiçbir bağlantı yoktur.**
