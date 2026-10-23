import sys
import time
import csv
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from b2b_lead_scraper import scrape_district_category, load_all_leads, CATEGORIES, LEADS_FILE

SCRATCH_DIR = Path("/Users/kdrgry/.gemini/antigravity/scratch")

# Çok katı taranacak öncelikli ilçe ve sektör kombinasyonları
RUN_TARGETS = [
    # İstanbul Anadolu
    ("İstanbul", "Kadıköy", "guzellik_merkezi"),
    ("İstanbul", "Kadıköy", "nail_studio"),
    ("İstanbul", "Kadıköy", "kalici_makyaj"),
    ("İstanbul", "Kadıköy", "op_doktor"),
    ("İstanbul", "Kadıköy", "sac_ekim"),
    ("İstanbul", "Kadıköy", "fizyoterapist"),
    ("İstanbul", "Kadıköy", "kadin_kuaforu"),
    ("İstanbul", "Kadıköy", "hastane"),

    # İstanbul Avrupa - Şişli (Estetik, Plastik Cerrahi & Saç Ekiminin Kalbi)
    ("İstanbul", "Şişli", "sac_ekim"),
    ("İstanbul", "Şişli", "op_doktor"),
    ("İstanbul", "Şişli", "guzellik_merkezi"),
    ("İstanbul", "Şişli", "nail_studio"),
    ("İstanbul", "Şişli", "kalici_makyaj"),
    ("İstanbul", "Şişli", "hastane"),
    ("İstanbul", "Şişli", "fizyoterapist"),
    ("İstanbul", "Şişli", "kadin_kuaforu"),

    # İstanbul Avrupa - Beşiktaş (Etiler, Levent, Bebek Kuaför & Estetik)
    ("İstanbul", "Beşiktaş", "kadin_kuaforu"),
    ("İstanbul", "Beşiktaş", "op_doktor"),
    ("İstanbul", "Beşiktaş", "guzellik_merkezi"),
    ("İstanbul", "Beşiktaş", "nail_studio"),
    ("İstanbul", "Beşiktaş", "sac_ekim"),
    ("İstanbul", "Beşiktaş", "kalici_makyaj"),
    ("İstanbul", "Beşiktaş", "hastane"),
    ("İstanbul", "Beşiktaş", "fizyoterapist"),

    # İstanbul Avrupa - Bakırköy & Florya
    ("İstanbul", "Bakırköy", "guzellik_merkezi"),
    ("İstanbul", "Bakırköy", "nail_studio"),
    ("İstanbul", "Bakırköy", "op_doktor"),
    ("İstanbul", "Bakırköy", "sac_ekim"),
    ("İstanbul", "Bakırköy", "kalici_makyaj"),
    ("İstanbul", "Bakırköy", "kadin_kuaforu"),
    ("İstanbul", "Bakırköy", "hastane"),
    ("İstanbul", "Bakırköy", "fizyoterapist"),

    # İstanbul - Ataşehir & Üsküdar
    ("İstanbul", "Ataşehir", "guzellik_merkezi"),
    ("İstanbul", "Ataşehir", "nail_studio"),
    ("İstanbul", "Ataşehir", "op_doktor"),
    ("İstanbul", "Ataşehir", "kalici_makyaj"),
    ("İstanbul", "Üsküdar", "guzellik_merkezi"),
    ("İstanbul", "Üsküdar", "kadin_kuaforu"),

    # Ankara - Çankaya (Tunalı, Kızılay, Çayyolu, Gaziosmanpaşa)
    ("Ankara", "Çankaya", "guzellik_merkezi"),
    ("Ankara", "Çankaya", "nail_studio"),
    ("Ankara", "Çankaya", "op_doktor"),
    ("Ankara", "Çankaya", "sac_ekim"),
    ("Ankara", "Çankaya", "kalici_makyaj"),
    ("Ankara", "Çankaya", "kadin_kuaforu"),
    ("Ankara", "Çankaya", "hastane"),
    ("Ankara", "Çankaya", "fizyoterapist"),

    # İzmir - Konak & Karşıyaka (Alsancak, Bostanlı)
    ("İzmir", "Konak", "guzellik_merkezi"),
    ("İzmir", "Konak", "nail_studio"),
    ("İzmir", "Konak", "op_doktor"),
    ("İzmir", "Konak", "kalici_makyaj"),
    ("İzmir", "Karşıyaka", "guzellik_merkezi"),
    ("İzmir", "Karşıyaka", "nail_studio"),
    ("İzmir", "Karşıyaka", "kadin_kuaforu"),

    # Antalya - Muratpaşa (Lara Estetik & Sağlık Turizmi)
    ("Antalya", "Muratpaşa", "guzellik_merkezi"),
    ("Antalya", "Muratpaşa", "sac_ekim"),
    ("Antalya", "Muratpaşa", "op_doktor"),
    ("Antalya", "Muratpaşa", "nail_studio"),
    ("Antalya", "Muratpaşa", "kalici_makyaj"),
]

def export_csv(leads):
    csv_path = SCRATCH_DIR / "estoril_hedef_kitleler_kati_tarama.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "İşletme Adı", "Sektör", "İl", "İlçe", "Telefon",
            "Instagram Hesabı", "Instagram Linki", "Web Sitesi", "E-posta",
            "Puan", "Yorum Sayısı", "Açık Adres", "Google Maps Linki", "Kayıt Tarihi"
        ])
        for l in leads:
            writer.writerow([
                l.get("name", ""),
                l.get("kategori_label", ""),
                l.get("il", ""),
                l.get("ilce", ""),
                l.get("phone", ""),
                l.get("instagram_handle", ""),
                l.get("instagram_url", ""),
                l.get("website", ""),
                l.get("email", ""),
                l.get("rating", "") or "",
                l.get("reviews_count", 0),
                l.get("address", ""),
                l.get("gmaps_url", ""),
                l.get("created_at", "")[:10] if l.get("created_at") else ""
            ])
    return csv_path

def main():
    print("=================================================================")
    print("🚀 ESTORIL B2B GOOGLE MAPS KATI & EKSİKSİZ TARAMA MOTORU BAŞLATILDI")
    print(f"Toplam Hedef Görev Sayısı: {len(RUN_TARGETS)}")
    print("=================================================================\n")

    initial_leads = load_all_leads()
    print(f"Mevcut Kayıtlı Lead Sayısı: {len(initial_leads)}")

    for idx, (il, ilce, cat_key) in enumerate(RUN_TARGETS, 1):
        cat_label = CATEGORIES[cat_key]["label"]
        print(f"\n[{idx}/{len(RUN_TARGETS)}] >>> TARANIYOR: {il} / {ilce} -> {cat_label}")
        try:
            new_batch = scrape_district_category(
                il=il,
                ilce=ilce,
                kategori_key=cat_key,
                max_pages=2,
                fetch_socials=True,
                delay_sec=0.3,
                include_sub_areas=True,
            )
            total_now = len(load_all_leads())
            print(f"    Sonuç: +{len(new_batch)} yeni işletme bulundu. (Toplam Veritabanı: {total_now})")
            
            # Her adımda güncel CSV oluştur
            export_csv(load_all_leads())
        except Exception as e:
            print(f"    Hata oluştu ({il} - {ilce}): {e}")

        time.sleep(0.5)

    final_leads = load_all_leads()
    csv_file = export_csv(final_leads)
    print("\n=================================================================")
    print(f"✅ TÜM KATI TARAMA TAMAMLANDI!")
    print(f"Toplam Toplanan İşletme: {len(final_leads)}")
    print(f"Excel / CSV Çıktısı: {csv_file}")
    print("=================================================================")

if __name__ == "__main__":
    main()
