"""
=============================================================================
auto_seo_engine.py — Estoril Gelişmiş Açık Kaynak Tabanlı Otomatik SEO Motoru
=============================================================================
Açık kaynak projelerden sentezlenen özellikler:
1. sour4bh/auto-seo:
   - Zengin Schema.org JSON-LD motoru (Product, MedicalDevice, LocalBusiness, FAQPage)
   - Generative Engine Optimization (GEO/AEO) & AI SGE uyumlu SSS şablonları
   - Akıllı Meta Title & Description üretimi
2. eliasdabbas/advertools:
   - Programmatik Anahtar Kelime Matrisi (Niyet x Ürün x Lokasyon)
   - SERP Piksel & Karakter Denetleyicisi (Desktop 600px, Mobile 960px)
3. sethblack/python-seo-analyzer:
   - Katalog Teknik SEO Denetimi (Health Score 0-100%, Hata & Uyarı tespiti)
   - Tek tıkla katalog oto-düzeltme (Auto-Fixer)
4. Programmatic-SEO:
   - 81 İl ve İlçe bazlı Yerel Landing Page içerik ve şema üreticisi
=============================================================================
"""

import os
import re
import html
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("auto_seo")

# ---------------------------------------------------------------------------
# Türkiye 81 İl ve Önemli İlçeler Listesi
# ---------------------------------------------------------------------------
TR_PROVINCES = [
    {"code": 1, "name": "Adana", "slug": "adana", "region": "Akdeniz", "districts": ["Seyhan", "Çukurova", "Yüreğir", "Sarıçam"]},
    {"code": 2, "name": "Adıyaman", "slug": "adiyaman", "region": "Güneydoğu Anadolu", "districts": ["Merkez", "Kahta", "Besni"]},
    {"code": 3, "name": "Afyonkarahisar", "slug": "afyonkarahisar", "region": "Ege", "districts": ["Merkez", "Sandıklı", "Dinar"]},
    {"code": 4, "name": "Ağrı", "slug": "agri", "region": "Doğu Anadolu", "districts": ["Merkez", "Patnos", "Doğubayazıt"]},
    {"code": 5, "name": "Amasya", "slug": "amasya", "region": "Karadeniz", "districts": ["Merkez", "Merzifon", "Suluova"]},
    {"code": 6, "name": "Ankara", "slug": "ankara", "region": "İç Anadolu", "districts": ["Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan", "Gölbaşı"]},
    {"code": 7, "name": "Antalya", "slug": "antalya", "region": "Akdeniz", "districts": ["Muratpaşa", "Kepez", "Konyaaltı", "Alanya", "Manavgat", "Serik", "Kemer"]},
    {"code": 8, "name": "Artvin", "slug": "artvin", "region": "Karadeniz", "districts": ["Merkez", "Hopa", "Borçka"]},
    {"code": 9, "name": "Aydın", "slug": "aydin", "region": "Ege", "districts": ["Efeler", "Kuşadası", "Söke", "Nazilli", "Didim"]},
    {"code": 10, "name": "Balıkesir", "slug": "balikesir", "region": "Marmara", "districts": ["Karesi", "Altıeylül", "Bandırma", "Edremit", "Ayvalık"]},
    {"code": 11, "name": "Bilecik", "slug": "bilecik", "region": "Marmara", "districts": ["Merkez", "Bozüyük"]},
    {"code": 12, "name": "Bingöl", "slug": "bingol", "region": "Doğu Anadolu", "districts": ["Merkez", "Genç"]},
    {"code": 13, "name": "Bitlis", "slug": "bitlis", "region": "Doğu Anadolu", "districts": ["Tatvan", "Merkez", "Ahlat"]},
    {"code": 14, "name": "Bolu", "slug": "bolu", "region": "Karadeniz", "districts": ["Merkez", "Gerede"]},
    {"code": 15, "name": "Burdur", "slug": "burdur", "region": "Akdeniz", "districts": ["Merkez", "Bucak"]},
    {"code": 16, "name": "Bursa", "slug": "bursa", "region": "Marmara", "districts": ["Osmangazi", "Nilüfer", "Yıldırım", "İnegöl", "Gemlik", "Mudanya"]},
    {"code": 17, "name": "Çanakkale", "slug": "canakkale", "region": "Marmara", "districts": ["Merkez", "Biga", "Çan", "Gelibolu"]},
    {"code": 18, "name": "Çankırı", "slug": "cankiri", "region": "İç Anadolu", "districts": ["Merkez", "Ilgaz"]},
    {"code": 19, "name": "Çorum", "slug": "corum", "region": "Karadeniz", "districts": ["Merkez", "Sungurlu", "Osmancık"]},
    {"code": 20, "name": "Denizli", "slug": "denizli", "region": "Ege", "districts": ["Pamukkale", "Merkezefendi", "Çivril", "Acıpayam"]},
    {"code": 21, "name": "Diyarbakır", "slug": "diyarbakir", "region": "Güneydoğu Anadolu", "districts": ["Kayapınar", "Bağlar", "Yenişehir", "Sur", "Bismil", "Ergani"]},
    {"code": 22, "name": "Edirne", "slug": "edirne", "region": "Marmara", "districts": ["Merkez", "Keşan", "Uzunköprü"]},
    {"code": 23, "name": "Elazığ", "slug": "elazig", "region": "Doğu Anadolu", "districts": ["Merkez", "Kovancılar"]},
    {"code": 24, "name": "Erzincan", "slug": "erzincan", "region": "Doğu Anadolu", "districts": ["Merkez", "Üzümlü"]},
    {"code": 25, "name": "Erzurum", "slug": "erzurum", "region": "Doğu Anadolu", "districts": ["Yakutiye", "Palandöken", "Aziziye"]},
    {"code": 26, "name": "Eskişehir", "slug": "eskisehir", "region": "İç Anadolu", "districts": ["Odunpazarı", "Tepebaşı", "Sivrihisar"]},
    {"code": 27, "name": "Gaziantep", "slug": "gaziantep", "region": "Güneydoğu Anadolu", "districts": ["Şahinbey", "Şehitkamil", "Nizip", "İslahiye"]},
    {"code": 28, "name": "Giresun", "slug": "giresun", "region": "Karadeniz", "districts": ["Merkez", "Bulancak", "Espiye"]},
    {"code": 29, "name": "Gümüşhane", "slug": "gumushane", "region": "Karadeniz", "districts": ["Merkez", "Kelkit"]},
    {"code": 30, "name": "Hakkari", "slug": "hakkari", "region": "Doğu Anadolu", "districts": ["Yüksekova", "Merkez"]},
    {"code": 31, "name": "Hatay", "slug": "hatay", "region": "Akdeniz", "districts": ["Antakya", "İskenderun", "Defne", "Dörtyol", "Samandağ"]},
    {"code": 32, "name": "Isparta", "slug": "isparta", "region": "Akdeniz", "districts": ["Merkez", "Yalvaç", "Eğirdir"]},
    {"code": 33, "name": "Mersin", "slug": "mersin", "region": "Akdeniz", "districts": ["Yenişehir", "Mezitli", "Toroslar", "Akdeniz", "Tarsus", "Erdemli", "Silifke"]},
    {"code": 34, "name": "İstanbul", "slug": "istanbul", "region": "Marmara", "districts": ["Kadıköy", "Beşiktaş", "Şişli", "Bakırköy", "Üsküdar", "Ataşehir", "Sarıyer", "Beylikdüzü", "Fatih", "Pendik", "Kartal", "Maltepe", "Ümraniye"]},
    {"code": 35, "name": "İzmir", "slug": "izmir", "region": "Ege", "districts": ["Konak", "Karşıyaka", "Bornova", "Buca", "Çiğli", "Bayraklı", "Gaziemir", "Balçova", "Torbalı", "Menemen", "Çeşme", "Urla"]},
    {"code": 36, "name": "Kars", "slug": "kars", "region": "Doğu Anadolu", "districts": ["Merkez", "Kağızman", "Sarıkamış"]},
    {"code": 37, "name": "Kastamonu", "slug": "kastamonu", "region": "Karadeniz", "districts": ["Merkez", "Tosya", "Taşköprü"]},
    {"code": 38, "name": "Kayseri", "slug": "kayseri", "region": "İç Anadolu", "districts": ["Melikgazi", "Kocasinan", "Talas", "Develi"]},
    {"code": 39, "name": "Kırklareli", "slug": "kirklareli", "region": "Marmara", "districts": ["Merkez", "Lüleburgaz", "Babaeski"]},
    {"code": 40, "name": "Kırşehir", "slug": "kirsehir", "region": "İç Anadolu", "districts": ["Merkez", "Kaman"]},
    {"code": 41, "name": "Kocaeli", "slug": "kocaeli", "region": "Marmara", "districts": ["İzmit", "Gebze", "Darıca", "Gölcük", "Körfez", "Kartepe", "Başiskele"]},
    {"code": 42, "name": "Konya", "slug": "konya", "region": "İç Anadolu", "districts": ["Selçuklu", "Meram", "Karatay", "Ereğli", "Akşehir"]},
    {"code": 43, "name": "Kütahya", "slug": "kutahya", "region": "Ege", "districts": ["Merkez", "Tavşanlı", "Simav"]},
    {"code": 44, "name": "Malatya", "slug": "malatya", "region": "Doğu Anadolu", "districts": ["Battalgazi", "Yeşilyurt", "Doğanşehir"]},
    {"code": 45, "name": "Manisa", "slug": "manisa", "region": "Ege", "districts": ["Yunusemre", "Şehzadeler", "Akhisar", "Turgutlu", "Salihli", "Soma"]},
    {"code": 46, "name": "Kahramanmaraş", "slug": "kahramanmaras", "region": "Akdeniz", "districts": ["Onikişubat", "Dulkadiroğlu", "Elbistan", "Afşin"]},
    {"code": 47, "name": "Mardin", "slug": "mardin", "region": "Güneydoğu Anadolu", "districts": ["Artuklu", "Kızıltepe", "Midyat", "Nusaybin"]},
    {"code": 48, "name": "Muğla", "slug": "mugla", "region": "Ege", "districts": ["Bodrum", "Fethiye", "Marmaris", "Menteşe", "Milas", "Ortaca"]},
    {"code": 49, "name": "Muş", "slug": "mus", "region": "Doğu Anadolu", "districts": ["Merkez", "Bulanık", "Malazgirt"]},
    {"code": 50, "name": "Nevşehir", "slug": "nevsehir", "region": "İç Anadolu", "districts": ["Merkez", "Ürgüp", "Avanos"]},
    {"code": 51, "name": "Niğde", "slug": "nigde", "region": "İç Anadolu", "districts": ["Merkez", "Bor"]},
    {"code": 52, "name": "Ordu", "slug": "ordu", "region": "Karadeniz", "districts": ["Altınordu", "Ünye", "Fatsa"]},
    {"code": 53, "name": "Rize", "slug": "rize", "region": "Karadeniz", "districts": ["Merkez", "Çayeli", "Ardeşen", "Pazar"]},
    {"code": 54, "name": "Sakarya", "slug": "sakarya", "region": "Marmara", "districts": ["Adapazarı", "Serdivan", "Erenler", "Akyazı", "Hendek"]},
    {"code": 55, "name": "Samsun", "slug": "samsun", "region": "Karadeniz", "districts": ["İlkadım", "Atakum", "Canik", "Bafra", "Çarşamba"]},
    {"code": 56, "name": "Siirt", "slug": "siirt", "region": "Güneydoğu Anadolu", "districts": ["Merkez", "Kurtalan"]},
    {"code": 57, "name": "Sinop", "slug": "sinop", "region": "Karadeniz", "districts": ["Merkez", "Boyabat", "Gerze"]},
    {"code": 58, "name": "Sivas", "slug": "sivas", "region": "İç Anadolu", "districts": ["Merkez", "Şarkışla", "Suşehri"]},
    {"code": 59, "name": "Tekirdağ", "slug": "tekirdag", "region": "Marmara", "districts": ["Süleymanpaşa", "Çorlu", "Çerkezköy", "Kapaklı"]},
    {"code": 60, "name": "Tokat", "slug": "tokat", "region": "Karadeniz", "districts": ["Merkez", "Erbaa", "Turhal", "Niksar"]},
    {"code": 61, "name": "Trabzon", "slug": "trabzon", "region": "Karadeniz", "districts": ["Ortahisar", "Akçaabat", "Araklı", "Of", "Yomra"]},
    {"code": 62, "name": "Tunceli", "slug": "tunceli", "region": "Doğu Anadolu", "districts": ["Merkez", "Pertek"]},
    {"code": 63, "name": "Şanlıurfa", "slug": "sanliurfa", "region": "Güneydoğu Anadolu", "districts": ["Haliliye", "Eyyübiye", "Karaköprü", "Siverek", "Viranşehir", "Birecik"]},
    {"code": 64, "name": "Uşak", "slug": "usak", "region": "Ege", "districts": ["Merkez", "Banaz", "Eşme"]},
    {"code": 65, "name": "Van", "slug": "van", "region": "Doğu Anadolu", "districts": ["İpekyolu", "Tuşba", "Edremit", "Erciş"]},
    {"code": 66, "name": "Yozgat", "slug": "yozgat", "region": "İç Anadolu", "districts": ["Merkez", "Sorgun", "Akdağmadeni"]},
    {"code": 67, "name": "Zonguldak", "slug": "zonguldak", "region": "Karadeniz", "districts": ["Merkez", "Ereğli", "Çaycuma", "Devrek"]},
    {"code": 68, "name": "Aksaray", "slug": "aksaray", "region": "İç Anadolu", "districts": ["Merkez", "Ortaköy"]},
    {"code": 69, "name": "Bayburt", "slug": "bayburt", "region": "Karadeniz", "districts": ["Merkez", "Demirözü"]},
    {"code": 70, "name": "Karaman", "slug": "karaman", "region": "İç Anadolu", "districts": ["Merkez", "Ermenek"]},
    {"code": 71, "name": "Kırıkkale", "slug": "kirikkale", "region": "İç Anadolu", "districts": ["Merkez", "Yahşihan"]},
    {"code": 72, "name": "Batman", "slug": "batman", "region": "Güneydoğu Anadolu", "districts": ["Merkez", "Kozluk"]},
    {"code": 73, "name": "Şırnak", "slug": "sirnak", "region": "Güneydoğu Anadolu", "districts": ["Cizre", "Silopi", "Merkez"]},
    {"code": 74, "name": "Bartın", "slug": "bartin", "region": "Karadeniz", "districts": ["Merkez", "Amasra"]},
    {"code": 75, "name": "Ardahan", "slug": "ardahan", "region": "Doğu Anadolu", "districts": ["Merkez", "Göle"]},
    {"code": 76, "name": "Iğdır", "slug": "igdir", "region": "Doğu Anadolu", "districts": ["Merkez", "Tuzluca"]},
    {"code": 77, "name": "Yalova", "slug": "yalova", "region": "Marmara", "districts": ["Merkez", "Çiftlikköy", "Çınarcık", "Altınova"]},
    {"code": 78, "name": "Karabük", "slug": "karabuk", "region": "Karadeniz", "districts": ["Merkez", "Safranbolu"]},
    {"code": 79, "name": "Kilis", "slug": "kilis", "region": "Güneydoğu Anadolu", "districts": ["Merkez"]},
    {"code": 80, "name": "Osmaniye", "slug": "osmaniye", "region": "Akdeniz", "districts": ["Merkez", "Kadirli", "Düziçi"]},
    {"code": 81, "name": "Düzce", "slug": "duzce", "region": "Karadeniz", "districts": ["Merkez", "Akçakoca", "Kaynaşlı"]}
]

# ---------------------------------------------------------------------------
# Sektörel Terimler & Cihaz Kategorileri (Estoril B2B Hedefleri)
# ---------------------------------------------------------------------------
SECTOR_PRODUCTS = [
    {
        "key": "lazer_epilasyon",
        "name": "Lazer Epilasyon Cihazı",
        "keywords": ["buz lazer", "diode lazer epilasyon", "alexandrite lazer", "3 dalga boylu lazer", "hibrit lazer cihazı", "ütüleme lazer"],
        "price_range": "250.000 TL - 750.000 TL",
        "warranty": "2 Yıl Tam Garanti, 20 Milyon Atış Garantisi"
    },
    {
        "key": "cilt_bakim",
        "name": "Hydrafacial & Medikal Cilt Bakım Cihazı",
        "keywords": ["hydrafacial cihazı", "cilt analiz cihazı", "aquapeel", "dermapen", "oksijen terapi cihazı", "karbon peeling"],
        "price_range": "45.000 TL - 180.000 TL",
        "warranty": "2 Yıl Garanti & Yerinde Uygulama Eğitimi"
    },
    {
        "key": "bolgesel_incelme",
        "name": "Bölgesel İncelme & Vücut Şekillendirme Cihazı",
        "keywords": ["ems zayıflama", "kavitasyon cihazı", "g5 masaj cihazı", "soğuk lipoliz", "lenf drenaj", "radyofrekans"],
        "price_range": "80.000 TL - 350.000 TL",
        "warranty": "2 Yıl Garanti & CE Sertifikalı"
    },
    {
        "key": "kalici_makyaj_ipek_kirpik",
        "name": "Kalıcı Makyaj & İpek Kirpik Ekipmanları",
        "keywords": ["kalıcı makyaj cihazı", "microblading boyaları", "ipek kirpik malzemeleri", "titanyum iğneli dermapen", "dudak renklendirme cihazı"],
        "price_range": "5.000 TL - 65.000 TL",
        "warranty": "1 Yıl Distribütör Garantisi"
    },
    {
        "key": "sac_ekim_ekipmanlari",
        "name": "Saç Ekim Cihazları & Medikal Sarf Malzemeleri",
        "keywords": ["fue motoru", "safir uçlu saç ekim kalemi", "dhi implant kalemi", "saç analiz mikroskobu"],
        "price_range": "20.000 TL - 120.000 TL",
        "warranty": "2 Yıl Garanti"
    }
]

INTENT_MODIFIERS = [
    "Fiyatları",
    "Satın Al",
    "En İyi",
    "Yetkili Satıcı & Distribütör",
    "Sıfır",
    "Teknik Servis & Yedek Parça",
    "Kurulum ve Eğitim Dahil",
    "Toptan Satış",
    "Klinik Tipi",
    "Güzellik Salonu İçin"
]


# ===========================================================================
# 1. SERP Analizcisi (advertools esintisi: Karakter & Piksel Genişliği)
# ===========================================================================
class SERPAnalyzer:
    """
    Google SERP başlık (600px / ~60 karakter) ve açıklama (960px / ~155-160 karakter)
    sınırlarını piksel ve karakter olarak hesaplayan ve önizleme üreten motor.
    """
    # Ortalama harf piksel genişlikleri (Google Roboto / Arial simülasyonu)
    CHAR_WIDTHS = {
        'W': 13, 'M': 12, 'w': 9, 'm': 9, 'O': 10, 'Q': 10, 'C': 9, 'D': 9,
        'i': 3, 'l': 3, 'I': 3, 't': 4, 'j': 4, 'f': 4, 'r': 4,
        ' ': 4, '.': 3, ',': 3, '-': 4, '|': 3, '/': 4
    }
    DEFAULT_CHAR_WIDTH = 7.5

    @classmethod
    def estimate_pixel_width(cls, text: str) -> float:
        if not text:
            return 0.0
        width = 0.0
        for ch in text:
            width += cls.CHAR_WIDTHS.get(ch, cls.DEFAULT_CHAR_WIDTH)
        return round(width, 1)

    @classmethod
    def analyze_meta(cls, title: str, description: str, url: str = "https://estoril.com.tr") -> Dict[str, Any]:
        title = (title or "").strip()
        description = (description or "").strip()
        
        t_len = len(title)
        t_px = cls.estimate_pixel_width(title)
        d_len = len(description)
        d_px = cls.estimate_pixel_width(description)

        title_status = "ideal"
        title_warning = None
        if t_len == 0:
            title_status = "missing"
            title_warning = "Başlık eksik! Google için mutlaka bir başlık belirleyin."
        elif t_px > 600 or t_len > 60:
            title_status = "too_long"
            title_warning = f"Başlık Google'da kesilebilir ({t_len} kr, ~{int(t_px)}px). İdeal: 50-60 karakter."
        elif t_len < 30:
            title_status = "too_short"
            title_warning = f"Başlık çok kısa ({t_len} kr). Anahtar kelimeleri ve marka adını ekleyerek zenginleştirin."

        desc_status = "ideal"
        desc_warning = None
        if d_len == 0:
            desc_status = "missing"
            desc_warning = "Meta açıklaması eksik! Arama tıklama oranını (CTR) artırmak için açıklama girin."
        elif d_px > 960 or d_len > 160:
            desc_status = "too_long"
            desc_warning = f"Açıklama Google'da kesilebilir ({d_len} kr, ~{int(d_px)}px). İdeal: 130-155 karakter."
        elif d_len < 70:
            desc_status = "too_short"
            desc_warning = f"Açıklama çok kısa ({d_len} kr). Avantajları ve harekete geçirici mesajı (CTA) ekleyin."

        truncated_title = title if t_px <= 600 else title[:52] + "..."
        truncated_desc = description if d_px <= 960 else description[:150] + "..."

        return {
            "title": {
                "text": title,
                "length": t_len,
                "pixel_width": t_px,
                "status": title_status,
                "warning": title_warning,
                "truncated": truncated_title
            },
            "description": {
                "text": description,
                "length": d_len,
                "pixel_width": d_px,
                "status": desc_status,
                "warning": desc_warning,
                "truncated": truncated_desc
            },
            "url": url,
            "desktop_preview": {
                "title": truncated_title,
                "url": url,
                "description": truncated_desc
            },
            "mobile_preview": {
                "title": title[:55] + ("..." if len(title) > 55 else ""),
                "url": url.replace("https://", "").replace("http://", ""),
                "description": description[:120] + ("..." if len(description) > 120 else "")
            }
        }


# ===========================================================================
# 2. Schema.org Zengin Veri Üreticisi (sour4bh/auto-seo uyarlaması)
# ===========================================================================
class SchemaOrgBuilder:
    """
    Google Zengin Arama Sonuçları (Rich Results) ve Generative Engine Optimization (GEO)
    için JSON-LD yapılandırılmış veri üreticisi.
    """
    BASE_URL = os.environ.get("FRONTEND_PUBLIC_URL", "https://estoril.com.tr").rstrip("/")

    @classmethod
    def build_product_schema(cls, product: Dict[str, Any]) -> Dict[str, Any]:
        """Ürün & Medikal Cihaz Schema.org JSON-LD (Product & MedicalDevice)"""
        title = product.get("name") or product.get("title") or "Estoril Medikal Cihaz"
        slug = product.get("slug") or ""
        url = f"{cls.BASE_URL}/urun/{slug}" if slug else cls.BASE_URL
        price = product.get("price") or product.get("selling_price") or product.get("fiyat") or 0
        currency = product.get("currency") or "TRY"
        sku = product.get("sku") or product.get("stok_kodu") or product.get("id") or "EST-01"
        desc = re.sub(r'<[^>]+>', '', product.get("description") or product.get("seo_description") or title)[:300]
        
        images = []
        for im in (product.get("images") or []):
            if isinstance(im, str) and im.startswith("http"):
                images.append(im)
            elif isinstance(im, dict) and im.get("url"):
                images.append(im["url"])
        if not images and product.get("image"):
            images.append(product["image"])
        if not images:
            images.append(f"{cls.BASE_URL}/logo.png")

        return {
            "@context": "https://schema.org/",
            "@type": ["Product", "MedicalDevice"],
            "name": title,
            "image": images,
            "description": desc,
            "sku": str(sku),
            "mpn": str(sku),
            "brand": {
                "@type": "Brand",
                "name": "Estoril"
            },
            "manufacturer": {
                "@type": "Organization",
                "name": "Estoril Dış Tic. A.Ş.",
                "url": cls.BASE_URL
            },
            "offers": {
                "@type": "Offer",
                "url": url,
                "priceCurrency": currency,
                "price": str(price),
                "priceValidUntil": "2027-12-31",
                "availability": "https://schema.org/InStock" if (product.get("stock", 1) or 1) > 0 else "https://schema.org/PreOrder",
                "itemCondition": "https://schema.org/NewCondition",
                "seller": {
                    "@type": "Organization",
                    "name": "Estoril"
                }
            },
            "medicalSpecialty": [
                "https://schema.org/Dermatology",
                "https://schema.org/PlasticSurgery"
            ]
        }

    @classmethod
    def build_local_business_schema(cls, province: Dict[str, Any], district: Optional[str] = None) -> Dict[str, Any]:
        """81 İl Yerel Açılış Sayfaları için LocalBusiness / MedicalBusiness JSON-LD"""
        prov_name = province["name"]
        loc_str = f"{district}, {prov_name}" if district else prov_name
        url = f"{cls.BASE_URL}/cihazlar/{province['slug']}-lazer-epilasyon-ve-estetik-cihazlari"

        return {
            "@context": "https://schema.org",
            "@type": "MedicalBusiness",
            "name": f"Estoril {loc_str} Güzellik & Medikal Estetik Cihazları Yetkili Satış ve Servis",
            "url": url,
            "logo": f"{cls.BASE_URL}/logo.png",
            "image": f"{cls.BASE_URL}/og-estoril.jpg",
            "description": f"{loc_str} genelinde güzellik merkezleri, hekimler ve klinikler için CE belgeli profesyonel lazer epilasyon, cilt bakım ve estetik cihazları satışı, 2 yıl garanti ve yerinde teknik servis desteği.",
            "telephone": "+90 543 330 03 10",
            "email": "info@estoril.com.tr",
            "priceRange": "₺₺₺₺",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": prov_name,
                "addressCountry": "TR"
            },
            "areaServed": {
                "@type": "AdministrativeArea",
                "name": prov_name
            },
            "hasOfferCatalog": {
                "@type": "OfferCatalog",
                "name": "Medikal Estetik ve Güzellik Cihazları Kataloğu",
                "itemListElement": [
                    {
                        "@type": "Offer",
                        "itemOffered": {
                            "@type": "Service",
                            "name": f"{loc_str} Buz Diode Lazer Epilasyon Cihazı Kurulumu ve Uzman Eğitimi"
                        }
                    },
                    {
                        "@type": "Offer",
                        "itemOffered": {
                            "@type": "Service",
                            "name": f"{loc_str} Profesyonel Hydrafacial & Cilt Bakım Cihazları Tedariği"
                        }
                    }
                ]
            }
        }

    @classmethod
    def build_faq_schema(cls, faqs: List[Dict[str, str]]) -> Dict[str, Any]:
        """Google Zengin Sonuçlar & GEO/AEO (Perplexity/ChatGPT) için FAQPage JSON-LD"""
        elements = []
        for f in faqs:
            elements.append({
                "@type": "Question",
                "name": f.get("q", ""),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f.get("a", "")
                }
            })
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": elements
        }

    @classmethod
    def build_breadcrumb_schema(cls, items: List[Dict[str, str]]) -> Dict[str, Any]:
        """BreadcrumbList Schema.org"""
        itemListElement = []
        for idx, item in enumerate(items, start=1):
            itemListElement.append({
                "@type": "ListItem",
                "position": idx,
                "name": item.get("name", ""),
                "item": item.get("url", "")
            })
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": itemListElement
        }


# ===========================================================================
# 3. Programmatik Anahtar Kelime Matrisi (advertools esintisi)
# ===========================================================================
class KeywordMatrixBuilder:
    """
    Advertools benzeri permütasyon matrisi:
    [Ürün Adı] x [Arama Niyeti] x [İl / İlçe / Hedef Kitle] kombinasyonlarını
    otomatik türetir.
    """
    @classmethod
    def generate_matrix(
        cls,
        products: Optional[List[str]] = None,
        intents: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        if not products:
            products = [
                "Lazer Epilasyon Cihazı",
                "Buz Diode Lazer Cihazı",
                "Hydrafacial Cilt Bakım Cihazı",
                "Bölgesel İncelme Cihazı",
                "Kalıcı Makyaj Cihazı",
                "İpek Kirpik Malzemeleri",
                "Dermapen Cihazı",
                "EMS Zayıflama Cihazı"
            ]
        if not intents:
            intents = INTENT_MODIFIERS
        if not locations:
            locations = ["Türkiye Geneli", "İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Gaziantep", "Kocaeli", "Konya"]

        results = []
        for loc in locations:
            for prod in products:
                for intent in intents:
                    if loc == "Türkiye Geneli":
                        kw = f"{prod} {intent}".strip()
                    else:
                        kw = f"{loc} {prod} {intent}".strip()
                    
                    intent_type = "Ticari (Commercial)"
                    if any(x in intent.lower() for x in ["satın al", "fiyat", "toptan"]):
                        intent_type = "Satın Alma (Transactional)"
                    elif any(x in intent.lower() for x in ["en iyi", "nedir", "nasıl"]):
                        intent_type = "Bilgilendirici (Informational)"

                    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ ", "cgiosuCGIOSU-")
                    slug = re.sub(r'[^a-zA-Z0-9\-]+', '', kw.translate(tr_map).lower()).strip('-')
                    
                    results.append({
                        "keyword": kw,
                        "location": loc,
                        "product": prod,
                        "intent": intent,
                        "intent_type": intent_type,
                        "suggested_slug": f"/cihazlar/{slug}",
                        "suggested_title": f"{kw} | Estoril Resmi Distribütör",
                        "suggested_meta": f"{kw} arayanlar için Estoril garantili estetik ve medikal cihazlar. 2 yıl garanti, yerinde kurulum & sertifikalı eğitim. Hemen inceleyin!"
                    })
                    if len(results) >= limit:
                        return results
        return results


# ===========================================================================
# 4. Programmatik Yerel SEO Motoru (pSEO 81 İl ve İlçe Sayfa Üreticisi)
# ===========================================================================
class LocalSEOGenerator:
    """
    Türkiye'nin 81 ili ve ilçeleri için yerel SEO iniş sayfası içerikleri,
    başlıkları, SSS ve zengin şemalarını üreten motor.
    """
    @classmethod
    def get_provinces(cls) -> List[Dict[str, Any]]:
        return TR_PROVINCES

    @classmethod
    def generate_province_page(cls, province_slug: str, district: Optional[str] = None) -> Dict[str, Any]:
        prov = next((p for p in TR_PROVINCES if p["slug"] == province_slug), None)
        if not prov:
            prov = TR_PROVINCES[33]  # Varsayılan: İstanbul

        prov_name = prov["name"]
        loc_display = f"{prov_name} - {district}" if district else prov_name

        title = f"{loc_display} Lazer Epilasyon ve Estetik Cihazları | Estoril"
        if len(title) > 60:
            title = f"{loc_display} Lazer Epilasyon Cihazları | Estoril"

        meta_desc = (
            f"{loc_display} güzellik merkezleri ve klinikleri için profesyonel diode lazer, "
            f"cilt bakım ve incelme cihazları. 2 yıl garanti & yerinde kurulum desteği."
        )

        h1 = f"{loc_display} Profesyonel Lazer Epilasyon & Medikal Estetik Cihazları Satışı"

        intro_content = (
            f"Estoril Dış Ticaret A.Ş. olarak {loc_display} bölgesindeki güzellik salonları, "
            f"medikal estetik poliklinikleri, dermatologlar, hastaneler ve saç ekim merkezleri için "
            f"dünya standartlarında CE belgeli estetik cihazları sunuyoruz. "
            f"{prov_name} ilindeki tüm işletmelere yerinde kurulum, cihaz başı birebir sertifikalı uzman eğitimi "
            f"ve 48 saat içinde yerinde teknik servis garantisi sağlıyoruz."
        )

        faqs = [
            {
                "q": f"{loc_display} bölgesine teslimat ve yerinde kurulum nasıl yapılır?",
                "a": f"Estoril teknik ekibi, {loc_display} bölgesine sipariş edilen tüm lazer epilasyon ve cilt bakım cihazlarını kendi uzman personeliyle ulaştırır, yerinde anahtar teslim kurulumunu yapar ve salon ekibinize sertifikalı kullanım eğitimi verir."
            },
            {
                "q": f"{prov_name} için lazer epilasyon cihazı teknik servis ve başlık değişim süresi nedir?",
                "a": f"{prov_name} genelindeki anlaşmalı ve doğrudan servis ağımız sayesinde olası bir arıza veya başlık yenileme ihtiyacında 24-48 saat içerisinde yerinde müdahale sağlanır. Cihazınızın atış garantisi sözleşmeyle güvence altındadır."
            },
            {
                "q": f"Estoril cihazları Sağlık Bakanlığı ve CE standartlarına uygun mudur?",
                "a": "Evet. Tüm cihazlarımız Avrupa CE standartlarına, medikal regülasyonlara ve salon işletmelerinin ruhsat denetimlerine %100 uyumludur."
            },
            {
                "q": f"{loc_display} merkezli işletmeler için taksit veya leasing imkânı var mı?",
                "a": "Evet, kurumsal B2B müşterilerimize özel leasing, vade farksız taksit ve ticari kredi kartı ödeme seçenekleri sunulmaktadır."
            }
        ]

        local_schema = SchemaOrgBuilder.build_local_business_schema(prov, district)
        faq_schema = SchemaOrgBuilder.build_faq_schema(faqs)

        breadcrumbs = [
            {"name": "Ana Sayfa", "url": SchemaOrgBuilder.BASE_URL},
            {"name": "Yerel Hizmetler & Cihaz Satışı", "url": f"{SchemaOrgBuilder.BASE_URL}/yerel-hizmetler"},
            {"name": loc_display, "url": f"{SchemaOrgBuilder.BASE_URL}/cihazlar/{prov['slug']}-lazer-epilasyon-cihazi"}
        ]
        breadcrumb_schema = SchemaOrgBuilder.build_breadcrumb_schema(breadcrumbs)

        serp = SERPAnalyzer.analyze_meta(title, meta_desc, f"{SchemaOrgBuilder.BASE_URL}/cihazlar/{prov['slug']}-lazer-epilasyon-cihazi")

        return {
            "province": prov,
            "district": district,
            "loc_display": loc_display,
            "seo_title": title,
            "seo_description": meta_desc,
            "h1": h1,
            "intro_content": intro_content,
            "faqs": faqs,
            "serp_metrics": serp,
            "schemas": {
                "local_business": local_schema,
                "faq": faq_schema,
                "breadcrumb": breadcrumb_schema
            },
            "canonical_url": f"{SchemaOrgBuilder.BASE_URL}/cihazlar/{prov['slug']}-lazer-epilasyon-cihazi"
        }


# ===========================================================================
# 5. Teknik SEO Denetleyicisi & Tek Tıkla Düzeltme (python-seo-analyzer esintisi)
# ===========================================================================
class TechnicalAuditor:
    """
    Veritabanındaki tüm ürün ve kategorileri tarayarak teknik SEO sağlığını (0-100%)
    hesaplar, sorunları kategorize eder ve eksikleri raporlar.
    """
    @classmethod
    async def run_audit(cls, db) -> Dict[str, Any]:
        issues = []
        total_products = 0
        missing_titles = 0
        missing_descriptions = 0
        missing_alts = 0
        bad_slugs = 0
        too_long_titles = 0
        too_short_descriptions = 0

        cursor = db.products.find(
            {"is_active": {"$ne": False}},
            {"_id": 1, "id": 1, "name": 1, "title": 1, "slug": 1, "seo_title": 1, "seo_description": 1, "images": 1, "image": 1, "category": 1, "price": 1}
        )
        
        async for p in cursor:
            total_products += 1
            pid = str(p.get("id") or p.get("_id"))
            pname = p.get("name") or p.get("title") or "İsimsiz Ürün"
            slug = p.get("slug") or ""
            seo_t = (p.get("seo_title") or "").strip()
            seo_d = (p.get("seo_description") or "").strip()
            
            # Slug kontrolü
            if not slug or " " in slug or re.search(r'[^a-z0-9\-]', slug):
                bad_slugs += 1
                issues.append({
                    "product_id": pid,
                    "product_name": pname,
                    "type": "error",
                    "code": "BAD_SLUG",
                    "message": f"URL slug formatı SEO uyumsuz: '{slug}'"
                })

            # Title kontrolü
            if not seo_t:
                missing_titles += 1
                issues.append({
                    "product_id": pid,
                    "product_name": pname,
                    "type": "error",
                    "code": "MISSING_TITLE",
                    "message": "Özel SEO Başlığı (Meta Title) eksik!"
                })
            elif len(seo_t) > 60:
                too_long_titles += 1
                issues.append({
                    "product_id": pid,
                    "product_name": pname,
                    "type": "warning",
                    "code": "TITLE_TOO_LONG",
                    "message": f"Başlık Google için uzun ({len(seo_t)} kr, maks 60 kr önerilir)"
                })

            # Description kontrolü
            if not seo_d:
                missing_descriptions += 1
                issues.append({
                    "product_id": pid,
                    "product_name": pname,
                    "type": "error",
                    "code": "MISSING_DESC",
                    "message": "SEO Açıklaması (Meta Description) eksik!"
                })
            elif len(seo_d) < 70:
                too_short_descriptions += 1
                issues.append({
                    "product_id": pid,
                    "product_name": pname,
                    "type": "warning",
                    "code": "DESC_TOO_SHORT",
                    "message": f"Açıklama çok kısa ({len(seo_d)} kr, min 70 kr önerilir)"
                })

            # Görsel ALT kontrolü
            images = p.get("images") or []
            has_alt = False
            for im in images:
                if isinstance(im, dict) and im.get("alt"):
                    has_alt = True
                    break
            if not has_alt and images:
                missing_alts += 1
                issues.append({
                    "product_id": pid,
                    "product_name": pname,
                    "type": "warning",
                    "code": "MISSING_ALT",
                    "message": "Ürün görsellerinde SEO 'alt' etiketi bulunmuyor"
                })

        score = 100
        if total_products > 0:
            penalty = (
                (missing_titles / total_products) * 35 +
                (missing_descriptions / total_products) * 30 +
                (missing_alts / total_products) * 15 +
                (bad_slugs / total_products) * 10 +
                (too_long_titles / total_products) * 5 +
                (too_short_descriptions / total_products) * 5
            )
            score = max(5, int(100 - penalty))

        return {
            "health_score": score,
            "total_products": total_products,
            "metrics": {
                "missing_titles": missing_titles,
                "missing_descriptions": missing_descriptions,
                "missing_alts": missing_alts,
                "bad_slugs": bad_slugs,
                "too_long_titles": too_long_titles,
                "too_short_descriptions": too_short_descriptions
            },
            "issues_count": len(issues),
            "issues": issues[:100],
            "audited_at": datetime.now(timezone.utc).isoformat()
        }


# ===========================================================================
# 6. Tek Tıkla Katalog Düzeltici (Auto-Fix Engine)
# ===========================================================================
class SEOAutoFixer:
    """
    Eksik SEO meta başlıklarını, açıklamalarını ve görsel ALT etiketlerini
    sektörel olarak optimize edilmiş şablonlarla otomatik doldurur.
    """
    @classmethod
    def generate_optimized_title(cls, product_name: str, category: str = "") -> str:
        clean_name = product_name.strip()
        if len(clean_name) > 38:
            clean_name = clean_name[:35].rsplit(" ", 1)[0]
        
        title = f"{clean_name} - Fiyatı & Satışı | Estoril"
        if len(title) > 60:
            title = f"{clean_name} | Estoril"
        return title[:60]

    @classmethod
    def generate_optimized_description(cls, product_name: str, category: str = "", price: Optional[float] = None) -> str:
        clean_name = product_name.strip()
        return (
            f"{clean_name} estetik ve güzellik salonları için Estoril güvencesiyle. "
            f"2 Yıl Garanti, yerinde kurulum ve sertifikalı eğitim avantajıyla hemen sipariş verin."
        )[:155]

    @classmethod
    async def fix_all_catalog(cls, db) -> Dict[str, Any]:
        """Tüm eksik ürünlerin meta ve alt etiketlerini otomatik olarak düzeltir"""
        fixed_titles = 0
        fixed_descs = 0
        fixed_alts = 0

        cursor = db.products.find(
            {"is_active": {"$ne": False}},
            {"_id": 1, "id": 1, "name": 1, "title": 1, "slug": 1, "seo_title": 1, "seo_description": 1, "images": 1, "category": 1, "price": 1}
        )

        async for p in cursor:
            pid = p.get("_id")
            pname = p.get("name") or p.get("title") or "Estoril Ürün"
            cat = p.get("category") or ""
            seo_t = (p.get("seo_title") or "").strip()
            seo_d = (p.get("seo_description") or "").strip()
            images = p.get("images") or []

            updates = {}
            if not seo_t:
                new_t = cls.generate_optimized_title(pname, cat)
                updates["seo_title"] = new_t
                fixed_titles += 1

            if not seo_d:
                new_d = cls.generate_optimized_description(pname, cat, p.get("price"))
                updates["seo_description"] = new_d
                fixed_descs += 1

            updated_images = []
            img_changed = False
            for idx, im in enumerate(images):
                if isinstance(im, str):
                    updated_images.append({
                        "url": im,
                        "alt": f"{pname} - Estoril Medikal Cihaz Görseli {idx+1}"
                    })
                    img_changed = True
                elif isinstance(im, dict):
                    if not im.get("alt"):
                        im_copy = dict(im)
                        im_copy["alt"] = f"{pname} - Estoril {idx+1}"
                        updated_images.append(im_copy)
                        img_changed = True
                    else:
                        updated_images.append(im)
            
            if img_changed:
                updates["images"] = updated_images
                fixed_alts += 1

            if updates:
                updates["updated_at"] = datetime.now(timezone.utc).isoformat()
                await db.products.update_one({"_id": pid}, {"$set": updates})

        return {
            "success": True,
            "fixed_titles_count": fixed_titles,
            "fixed_descriptions_count": fixed_descs,
            "fixed_alts_count": fixed_alts,
            "message": f"{fixed_titles} başlık, {fixed_descs} açıklama ve {fixed_alts} görsel ALT etiketi başarıyla optimize edildi."
        }
