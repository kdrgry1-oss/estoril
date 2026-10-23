"""
B2B Google Maps Lead Scraper & Harvester for Estoril Admin (Katı ve Kapsamlı Mod)
Desteklenen 8 Sektör:
1. Güzellik Merkezleri
2. Nail Stüdyoları
3. Op. Doktorlar & Estetik Hekimleri
4. Fizyoterapistler & Fizik Tedavi
5. Hastaneler & Tıp Merkezleri
6. Kadın Kuaförleri
7. Saç Ekim Merkezleri
8. Kalıcı Makyaj Stüdyoları
"""

import json
import logging
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("b2b_lead_scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/maps",
}

DATA_DIR = Path(__file__).parent / "data"
LEADS_FILE = DATA_DIR / "b2b_leads.json"

# Kapsamlı ve katı anahtar kelime haritası (Tek bir işletmenin bile kaçmaması için tüm varyasyonlar)
CATEGORIES = {
    "guzellik_merkezi": {
        "id": "guzellik_merkezi",
        "label": "Güzellik Merkezleri",
        "keywords": [
            "güzellik merkezi",
            "güzellik salonu",
            "estetik ve güzellik",
            "lazer epilasyon",
            "cilt bakımı",
            "buz lazer",
            "hydrafacial",
            "bölgesel incelme zayıflama",
            "iğneli epilasyon",
            "g5 masajı",
            "estetik güzellik merkezi",
        ],
    },
    "nail_studio": {
        "id": "nail_studio",
        "label": "Nail Stüdyoları",
        "keywords": [
            "protez tırnak",
            "nail art stüdyosu",
            "nail studio",
            "tırnak tasarım",
            "manikür pedikür",
            "kalıcı oje",
            "rus manikürü",
            "medikal manikür",
            "tırnak bakım merkezi",
            "ipek kirpik",
        ],
    },
    "op_doktor": {
        "id": "op_doktor",
        "label": "Op. Doktorlar & Plastik Cerrahlar",
        "keywords": [
            "plastik cerrah op dr",
            "estetik cerrahi kliniği",
            "dermatolog",
            "dermatoloji uzmanı",
            "medikal estetik hekimi",
            "kulak burun boğaz estetik op dr",
            "rinoplasti",
            "estetik cerrah",
            "cildiye uzmanı",
            "meme estetiği kliniği",
        ],
    },
    "fizyoterapist": {
        "id": "fizyoterapist",
        "label": "Fizyoterapistler & Fizik Tedavi",
        "keywords": [
            "fizyoterapist kliniği",
            "fizik tedavi merkezi",
            "fizyoterapi ve rehabilitasyon",
            "manuel terapi",
            "kayropraktik",
            "fizyoterapist",
            "fizik tedavi dal merkezi",
            "skolyoz terapi",
        ],
    },
    "hastane": {
        "id": "hastane",
        "label": "Hastaneler & Tıp Merkezleri",
        "keywords": [
            "özel hastane",
            "tıp merkezi",
            "özel poliklinik",
            "cerrahi tıp merkezi",
            "özel dal merkezi",
            "hastane",
        ],
    },
    "kadin_kuaforu": {
        "id": "kadin_kuaforu",
        "label": "Kadın Kuaförleri",
        "keywords": [
            "kadın kuaförü",
            "bayan kuaförü",
            "saç tasarım kuaför",
            "kuaför salonu",
            "saç kaynak merkezi",
            "mikro kaynak kuaför",
            "bayan kuaför salonu",
        ],
    },
    "sac_ekim": {
        "id": "sac_ekim",
        "label": "Saç Ekim Merkezleri",
        "keywords": [
            "saç ekim merkezi",
            "saç ekimi kliniği",
            "hair transplant clinic",
            "fue saç ekimi",
            "dhi saç ekimi",
            "saç ekim",
            "saç mezoterapisi",
        ],
    },
    "kalici_makyaj": {
        "id": "kalici_makyaj",
        "label": "Kalıcı Makyaj & Kaş Tasarım",
        "keywords": [
            "kalıcı makyaj",
            "microblading",
            "kaş tasarım dudak renklendirme",
            "kalıcı makyaj stüdyosu",
            "kalıcı eyeliner",
            "pudralama kaş",
            "kaş laminasyonu",
            "microblading kaş",
        ],
    },
    "medikal_estetik": {
        "id": "medikal_estetik",
        "label": "Medikal Estetik Klinikleri & Hekimleri",
        "keywords": [
            "medikal estetik kliniği",
            "medikal estetik hekimi",
            "botoks dolgu kliniği",
            "mezoterapi prp kliniği",
            "gençlik aşısı",
            "ip askı yüz germe",
            "ameliyatsız estetik merkezi",
            "medikal estetik",
            "estetik polikliniği",
            "dolgu botoks uzmanı",
        ],
    },
}

# Türkiye İl & İlçe & Önemli Semt/Cadde Haritası
CITIES = {
    "İstanbul": {
        "lat": 41.0082, "lng": 28.9784,
        "districts": [
            "Kadıköy", "Beşiktaş", "Şişli", "Bakırköy", "Üsküdar", "Ataşehir", "Sarıyer",
            "Fatih", "Maltepe", "Pendik", "Kartal", "Ümraniye", "Beylikdüzü", "Bahçelievler",
            "Başakşehir", "Zeytinburnu", "Eyüpsultan", "Beyoğlu", "Tuzla", "Kağıthane",
            "Avcılar", "Büyükçekmece", "Küçükçekmece", "Esenyurt", "Bağcılar", "Gaziosmanpaşa",
            "Sancaktepe", "Çekmeköy", "Beykoz", "Sultangazi", "Esenler", "Güngören", "Silivri"
        ],
        "sub_areas": {
            "Kadıköy": ["Moda", "Bağdat Caddesi", "Caddebostan", "Suadiye", "Erenköy", "Fenerbahçe", "Bostancı", "Acıbadem", "Göztepe", "Kozyatağı", "Osmanağa"],
            "Şişli": ["Nişantaşı", "Teşvikiye", "Fulya", "Mecidiyeköy", "Bomonti", "Harbiye", "Halaskargazi", "Esentepe"],
            "Beşiktaş": ["Levent", "Etiler", "Bebek", "Akaretler", "Ortaköy", "Ulus", "Dikilitaş", "Gayrettepe"],
            "Bakırköy": ["Ataköy", "Yeşilköy", "Yeşilyurt", "Florya", "İncirli", "Zuhuratbaba"],
            "Ataşehir": ["Batı Ataşehir", "Varyap", "Barbaros", "İçerenköy", "Brandium"],
            "Sarıyer": ["Maslak", "Vadi İstanbul", "Tarabya", "Yeniköy", "İstinye"],
            "Üsküdar": ["Altunizade", "Çamlıca", "Bağlarbaşı", "Kuzguncuk"],
            "Beylikdüzü": ["Beykent", "Barış", "Yakuplu", "Kavaklı"],
        }
    },
    "Ankara": {
        "lat": 39.9334, "lng": 32.8597,
        "districts": ["Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan", "Altındağ", "Gölbaşı", "Pursaklar"],
        "sub_areas": {
            "Çankaya": ["Tunalı Hilmi", "Kızılay", "Gaziosmanpaşa", "Çayyolu", "Ümitköy", "Kavaklıdere", "Bahçelievler", "Balgat", "Oran"],
            "Yenimahalle": ["Batıkent", "Demetevler", "Çayyolu"],
        }
    },
    "İzmir": {
        "lat": 38.4237, "lng": 27.1428,
        "districts": ["Konak", "Karşıyaka", "Bornova", "Alsancak", "Bayraklı", "Buca", "Çiğli", "Gaziemir", "Balçova", "Narlıdere", "Urla", "Çeşme"],
        "sub_areas": {
            "Konak": ["Alsancak", "Kordon", "Göztepe", "Kahramanlar"],
            "Karşıyaka": ["Bostanlı", "Mavişehir", "Alaybey"],
            "Bornova": ["Küçükpark", "Özkanlar", "Kazımdirik"],
        }
    },
    "Bursa": {
        "lat": 40.1885, "lng": 29.0610,
        "districts": ["Nilüfer", "Osmangazi", "Yıldırım", "Mudanya", "İnegöl", "Gemlik"],
        "sub_areas": {
            "Nilüfer": ["FSM Bulvarı", "Özlüce", "İhsaniye", "Görükle", "Balat"],
            "Osmangazi": ["Heykel", "Çekirge", "Kükürtlü"],
        }
    },
    "Antalya": {
        "lat": 36.8969, "lng": 30.7133,
        "districts": ["Muratpaşa", "Konyaaltı", "Kepez", "Alanya", "Manavgat", "Kemer", "Kaş"],
        "sub_areas": {
            "Muratpaşa": ["Lara", "Şirinyalı", "Fener", "Işıklar"],
            "Konyaaltı": ["Gürsu", "Arapsuyu", "Altınkum"],
        }
    },
    "Adana": {"lat": 37.0000, "lng": 35.3213, "districts": ["Seyhan", "Çukurova", "Yüreğir", "Sarıçam", "Ceyhan"]},
    "Konya": {"lat": 37.8746, "lng": 32.4932, "districts": ["Selçuklu", "Meram", "Karatay", "Ereğli", "Akşehir"]},
    "Gaziantep": {"lat": 37.0662, "lng": 37.3833, "districts": ["Şahinbey", "Şehitkamil", "Nizip"]},
    "Kocaeli": {"lat": 40.8533, "lng": 29.8815, "districts": ["İzmit", "Gebze", "Darıca", "Gölcük", "Körfez", "Kartepe"]},
    "Mersin": {"lat": 36.8121, "lng": 34.6415, "districts": ["Yenişehir", "Mezitli", "Akdeniz", "Toroslar", "Tarsus"]},
    "Kayseri": {"lat": 38.7205, "lng": 35.4826, "districts": ["Melikgazi", "Kocasinan", "Talas"]},
    "Eskişehir": {"lat": 39.7767, "lng": 30.5206, "districts": ["Tepebaşı", "Odunpazarı"]},
    "Diyarbakır": {"lat": 37.9144, "lng": 40.2306, "districts": ["Bağlar", "Kayapınar", "Yenişehir", "Sur"]},
    "Samsun": {"lat": 41.2867, "lng": 36.33, "districts": ["Atakum", "İlkadım", "Canik", "Bafra"]},
    "Denizli": {"lat": 37.7765, "lng": 29.0864, "districts": ["Pamukkale", "Merkezefendi"]},
    "Şanlıurfa": {"lat": 37.1674, "lng": 38.7955, "districts": ["Haliliye", "Eyyübiye", "Karaköprü"]},
    "Sakarya": {"lat": 40.7569, "lng": 30.3783, "districts": ["Adapazarı", "Serdivan", "Erenler"]},
    "Malatya": {"lat": 38.3552, "lng": 38.3095, "districts": ["Battalgazi", "Yeşilyurt"]},
    "Kahramanmaraş": {"lat": 37.5858, "lng": 36.9371, "districts": ["Onikişubat", "Dulkadiroğlu"]},
    "Erzurum": {"lat": 39.9043, "lng": 41.2679, "districts": ["Yakutiye", "Palandöken"]},
    "Van": {"lat": 38.4891, "lng": 43.4089, "districts": ["İpekyolu", "Tuşba"]},
    "Manisa": {"lat": 38.6191, "lng": 27.4289, "districts": ["Yunusemre", "Şehzadeler", "Akhisar"]},
    "Balıkesir": {"lat": 39.6484, "lng": 27.8826, "districts": ["Karesi", "Altıeylül", "Bandırma", "Edremit", "Ayvalık"]},
    "Trabzon": {"lat": 41.0027, "lng": 39.7168, "districts": ["Ortahisar", "Akçaabat"]},
    "Aydın": {"lat": 37.856, "lng": 27.8416, "districts": ["Efeler", "Kuşadası", "Didim", "Nazilli"]},
    "Tekirdağ": {"lat": 40.9833, "lng": 27.5167, "districts": ["Süleymanpaşa", "Çorlu", "Çerkezköy"]},
    "Muğla": {"lat": 37.2153, "lng": 28.3636, "districts": ["Bodrum", "Fethiye", "Marmaris", "Menteşe"]},
    "Hatay": {"lat": 36.4018, "lng": 36.3498, "districts": ["Antakya", "İskenderun"]},
    "Çanakkale": {"lat": 40.1553, "lng": 26.4142, "districts": ["Merkez"]},
    "Edirne": {"lat": 41.6772, "lng": 26.5557, "districts": ["Merkez"]},
    "Ordu": {"lat": 40.9839, "lng": 37.8764, "districts": ["Altınordu", "Ünye"]},
    "Yalova": {"lat": 40.655, "lng": 29.2769, "districts": ["Merkez"]},
    "Düzce": {"lat": 40.8438, "lng": 31.1565, "districts": ["Merkez"]},
}

def safe_get(obj, *indices, default=None):
    current = obj
    for idx in indices:
        try:
            if current is None:
                return default
            current = current[idx]
        except (IndexError, KeyError, TypeError):
            return default
    return current if current is not None else default

def normalize_phone(phone_raw: str) -> str:
    if not phone_raw:
        return ""
    digits = re.sub(r"\D", "", phone_raw)
    if digits.startswith("90") and len(digits) > 10:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) > 10:
        digits = digits[1:]
    if len(digits) == 10:
        return f"0{digits[0:3]} {digits[3:6]} {digits[6:8]} {digits[8:10]}"
    return phone_raw.strip()

def find_instagram_fallback(business_name: str, ilce: str) -> tuple:
    """Web sitesi olmayan veya sitede Instagram bulunmayan işletmeler için arama yapar."""
    clean_name = re.sub(r"[\|\/\-\+].*", "", business_name).strip()
    clean_name = re.sub(r"(Güzellik|Merkezi|Salonu|Saç|Ekim|Kuaför|Tırnak|Nail).*", "", clean_name, flags=re.IGNORECASE).strip()
    if len(clean_name) < 3:
        clean_name = business_name[:25].strip()

    q = f"{clean_name} {ilce} instagram"
    try:
        r = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": q},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "tr-TR,tr;q=0.9"},
            timeout=4
        )
        if r.status_code == 200:
            matches = re.findall(r"instagram\.com/([a-zA-Z0-9_.]+)", r.text)
            for m in matches:
                handle = m.rstrip("/?# ")
                if handle.lower() not in [
                    "p", "explore", "reels", "reel", "stories", "share", "tv", "accounts",
                    "about", "tags", "blog", "kolayrandevu"
                ]:
                    return f"@{handle}", f"https://www.instagram.com/{handle}/"
    except Exception:
        pass
    return "", ""

def extract_website_socials(website_url: str, business_name: str = "", ilce: str = "") -> dict:
    """Verilen internet sitesinden ve fallback motorundan Instagram, e-posta ve WhatsApp'ı tarar."""
    res = {"instagram_handle": "", "instagram_url": "", "email": "", "whatsapp": ""}
    
    # 1. Aşama: Web Sitesi Taraması
    if website_url and website_url.startswith("http"):
        try:
            r = requests.get(
                website_url,
                headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "tr-TR,tr;q=0.9"},
                timeout=4,
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if "instagram.com" in href and not res["instagram_handle"]:
                        m = re.search(r"instagram\.com/([a-zA-Z0-9_.]+)", href)
                        if m:
                            handle = m.group(1).rstrip("/?# ")
                            if handle.lower() not in ["p", "explore", "reels", "reel", "stories", "share", "tv", "accounts", "about"]:
                                res["instagram_handle"] = f"@{handle}"
                                res["instagram_url"] = f"https://www.instagram.com/{handle}/"
                    if not res["whatsapp"] and any(w in href for w in ["wa.me/", "api.whatsapp.com/send"]):
                        w_match = re.search(r"\d{10,13}", href)
                        if w_match:
                            res["whatsapp"] = w_match.group(0)
                    if not res["email"] and href.startswith("mailto:"):
                        raw_mail = href.replace("mailto:", "").split("?")[0].strip()
                        if "@" in raw_mail:
                            res["email"] = raw_mail
                if not res["email"]:
                    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", r.text)
                    clean = [e for e in emails if not e.endswith((".png", ".jpg", ".js", ".css"))]
                    if clean:
                        res["email"] = clean[0]
        except Exception:
            pass

    # 2. Aşama: Sitede Instagram yoksa veya site hiç yoksa fallback arama
    if not res["instagram_handle"] and business_name and ilce:
        fb_handle, fb_url = find_instagram_fallback(business_name, ilce)
        if fb_handle:
            res["instagram_handle"] = fb_handle
            res["instagram_url"] = fb_url

    return res

def fetch_maps_page(query: str, lat: float, lng: float, viewport_meters: int = 10000, offset: int = 0) -> list:
    params = {
        "tbm": "map", "authuser": "0", "hl": "tr", "gl": "tr", "q": query,
        "pb": f"!1m3!1d{viewport_meters}!2d{lng}!3d{lat}!2i1024!3i768!4f13.1!7i20!8i{offset}!10b1",
    }
    url = f"https://www.google.com/search?{urllib.parse.urlencode(params)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return []
    except Exception:
        return []

    cleaned = r.text
    for prefix in [")]}'", ")]}'\n", ")]}\n"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    try:
        data = json.loads(cleaned)
    except Exception:
        return []

    entries = safe_get(data, 0, 1, default=[])
    if not entries:
        return []

    items = []
    for entry in entries:
        inner = safe_get(entry, 14)
        if not inner:
            continue
        name = safe_get(inner, 11)
        if not name:
            continue
        cid = safe_get(inner, 10)
        place_id = safe_get(inner, 78)
        addr = safe_get(inner, 39) or ", ".join(safe_get(inner, 2, default=[]))
        phone_raw = safe_get(inner, 178, 0, 0)
        cat = safe_get(inner, 13, 0)
        rating = safe_get(inner, 4, 7)
        reviews = safe_get(inner, 4, 8)
        website = safe_get(inner, 7, 0)
        hours = safe_get(inner, 203, 1, 4, 0)
        p_lat = safe_get(inner, 9, 2)
        p_lng = safe_get(inner, 9, 3)

        gmaps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else (f"https://maps.google.com/?cid={cid}" if cid else "")

        items.append({
            "name": name.strip(),
            "address": addr.strip() if addr else "",
            "phone": normalize_phone(phone_raw),
            "phone_raw": phone_raw or "",
            "category_raw": cat or "",
            "rating": float(rating) if rating else None,
            "reviews_count": int(reviews) if reviews else 0,
            "website": website or "",
            "opening_hours": hours or "",
            "gmaps_url": gmaps_url,
            "place_id": place_id or cid or name,
            "latitude": p_lat,
            "longitude": p_lng,
        })
    return items

def load_all_leads() -> list:
    if LEADS_FILE.exists():
        try:
            with open(LEADS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lead JSON okuma hatası: {e}")
    return []

def save_leads(leads: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

def scrape_district_category(
    il: str,
    ilce: str,
    kategori_key: str,
    max_pages: int = 3,
    fetch_socials: bool = True,
    delay_sec: float = 0.5,
    include_sub_areas: bool = True,
) -> list:
    """
    Belirli bir il, ilçe ve kategori için çok katı (exhaustive) tarama yapar.
    Alt semtler ve çoklu sayfalar taranarak hiçbir işletme atlanmaz.
    """
    cat_info = CATEGORIES.get(kategori_key)
    if not cat_info:
        logger.error(f"Geçersiz kategori anahtarı: {kategori_key}")
        return []
    city_info = CITIES.get(il, {"lat": 39.0, "lng": 35.0})
    lat, lng = city_info["lat"], city_info["lng"]

    existing_leads = load_all_leads()
    seen_keys = {lead.get("place_id") or lead.get("name") for lead in existing_leads}
    new_leads = []

    # Hedef lokasyon listesi (İlçe ana merkezi + varsa meşhur semtler/caddeler)
    target_locations = [ilce]
    if include_sub_areas and "sub_areas" in city_info and ilce in city_info["sub_areas"]:
        target_locations.extend(city_info["sub_areas"][ilce])

    logger.info(f"==> KATI TARAMA BAŞLADI: {il} / {ilce} | {cat_info['label']} | Lokasyonlar: {target_locations}")

    for loc in target_locations:
        for kw in cat_info["keywords"]:
            query = f"{loc} {il} {kw}".strip()
            for page in range(max_pages):
                offset = page * 20
                batch = fetch_maps_page(query, lat, lng, offset=offset)
                if not batch:
                    break

                for b in batch:
                    dedup_id = b["place_id"]
                    if dedup_id in seen_keys:
                        continue
                    seen_keys.add(dedup_id)

                    socials = {"instagram_handle": "", "instagram_url": "", "email": "", "whatsapp": ""}
                    if fetch_socials:
                        socials = extract_website_socials(b["website"], business_name=b["name"], ilce=ilce)

                    record = {
                        "id": f"lead_{len(existing_leads) + len(new_leads) + 1}",
                        "name": b["name"],
                        "kategori_key": kategori_key,
                        "kategori_label": cat_info["label"],
                        "il": il,
                        "ilce": ilce,
                        "address": b["address"],
                        "phone": b["phone"],
                        "website": b["website"],
                        "instagram_handle": socials.get("instagram_handle", ""),
                        "instagram_url": socials.get("instagram_url", ""),
                        "email": socials.get("email", ""),
                        "whatsapp": socials.get("whatsapp", ""),
                        "rating": b["rating"],
                        "reviews_count": b["reviews_count"],
                        "opening_hours": b["opening_hours"],
                        "gmaps_url": b["gmaps_url"],
                        "place_id": b["place_id"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    new_leads.append(record)
                    logger.info(f"  [+] {record['name']} | Tel: {record['phone'] or '-'} | IG: {record['instagram_handle'] or '-'}")

                time.sleep(delay_sec)

        # Her lokasyon bitiminde anlık kaydet (checkpoint)
        if new_leads:
            all_leads = existing_leads + new_leads
            save_leads(all_leads)
            logger.info(f"  -> Checkpoint kaydedildi: Toplam {len(all_leads)} kayıt.")

    return new_leads

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Google Maps B2B Lead Scraper (Exhaustive)")
    parser.add_argument("--il", default="İstanbul", help="İl adı")
    parser.add_argument("--ilce", default="Kadıköy", help="İlçe adı")
    parser.add_argument("--kategori", default="guzellik_merkezi", choices=list(CATEGORIES.keys()))
    parser.add_argument("--pages", type=int, default=2, help="Sayfa adedi")
    args = parser.parse_args()
    results = scrape_district_category(args.il, args.ilce, args.kategori, max_pages=args.pages)
    print(f"\nToplam çekilen yeni lead: {len(results)}")
