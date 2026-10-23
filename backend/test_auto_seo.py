"""
test_auto_seo.py — Estoril Auto-SEO Motoru Doğrulama ve Birim Testleri
"""

import sys
from auto_seo_engine import (
    SERPAnalyzer,
    SchemaOrgBuilder,
    KeywordMatrixBuilder,
    LocalSEOGenerator,
    SEOAutoFixer,
    TR_PROVINCES,
    SECTOR_PRODUCTS,
    INTENT_MODIFIERS
)

def test_serp_analyzer():
    print("[1/6] SERPAnalyzer testi...")
    title = "Estoril Alpha Platinium Diode Lazer Epilasyon Cihazı Satışı"
    desc = "Estoril güvencesiyle 3 dalga boylu profesyonel diode lazer cihazları. 2 Yıl Garanti ve yerinde kurulum avantajıyla hemen sipariş verin."
    res = SERPAnalyzer.analyze_meta(title, desc, "https://estoril.com.tr/urun/alpha-diode")
    
    assert res["title"]["length"] == len(title)
    assert res["title"]["pixel_width"] > 0
    assert res["description"]["length"] == len(desc)
    assert "desktop_preview" in res
    assert "mobile_preview" in res
    print("  -> SERPAnalyzer Başarılı: Title", res["title"]["length"], "kr,", res["title"]["pixel_width"], "px")

def test_schema_org_builder():
    print("[2/6] SchemaOrgBuilder testi...")
    sample_prod = {
        "name": "Alpha Platinium Diode Lazer",
        "slug": "alpha-platinium-diode-lazer",
        "price": 380000,
        "currency": "TRY",
        "sku": "EST-DIODE-01",
        "description": "Profesyonel buz başlıklı 3 dalga boylu lazer cihazı.",
        "images": ["https://estoril.com.tr/images/diode1.jpg"]
    }
    schema = SchemaOrgBuilder.build_product_schema(sample_prod)
    assert schema["@context"] == "https://schema.org/"
    assert "Product" in schema["@type"]
    assert "MedicalDevice" in schema["@type"]
    assert schema["name"] == sample_prod["name"]
    assert schema["brand"]["name"] == "Estoril"
    assert schema["offers"]["price"] == "380000"
    print("  -> Product Schema.org Başarılı")

    # Local schema
    local_schema = SchemaOrgBuilder.build_local_business_schema(TR_PROVINCES[33], "Kadıköy")
    assert local_schema["@type"] == "MedicalBusiness"
    assert "İstanbul" in local_schema["name"]
    assert local_schema["address"]["addressCountry"] == "TR"
    print("  -> LocalBusiness Schema.org Başarılı")

def test_local_seo_generator():
    print("[3/6] LocalSEOGenerator (81 İl) testi...")
    assert len(TR_PROVINCES) == 81
    
    # Test Istanbul
    ist_page = LocalSEOGenerator.generate_province_page("istanbul", "Kadıköy")
    assert "İstanbul" in ist_page["seo_title"]
    assert "Kadıköy" in ist_page["seo_title"]
    assert len(ist_page["seo_title"]) <= 60
    assert len(ist_page["faqs"]) >= 4
    assert "schemas" in ist_page
    assert "local_business" in ist_page["schemas"]
    print("  -> İstanbul Yerel SEO Sayfası Başarılı:", ist_page["seo_title"])

    # Test Ankara
    ank_page = LocalSEOGenerator.generate_province_page("ankara", "Çankaya")
    assert "Ankara" in ank_page["seo_title"]
    assert len(ank_page["seo_title"]) <= 60
    print("  -> Ankara Yerel SEO Sayfası Başarılı:", ank_page["seo_title"])

def test_keyword_matrix():
    print("[4/6] KeywordMatrixBuilder testi...")
    matrix = KeywordMatrixBuilder.generate_matrix(
        products=["Buz Diode Lazer Cihazı"],
        intents=["Fiyatları", "Satın Al", "Yetkili Satıcı"],
        locations=["İstanbul", "Ankara"],
        limit=20
    )
    assert len(matrix) == 6
    assert matrix[0]["location"] in ("İstanbul", "Ankara")
    assert "suggested_slug" in matrix[0]
    assert "suggested_title" in matrix[0]
    print(f"  -> {len(matrix)} Anahtar Kelime Kombinasyonu Başarıyla Üretildi")

def test_auto_fixer_templates():
    print("[5/6] SEOAutoFixer Şablon testi...")
    title = SEOAutoFixer.generate_optimized_title("Estoril Diode Buz Lazer Epilasyon Cihazı 2026 Model")
    assert len(title) <= 60
    assert "Estoril" in title

    desc = SEOAutoFixer.generate_optimized_description("Estoril Diode Buz Lazer", "Lazer Epilasyon", 350000)
    assert len(desc) <= 160
    assert "Garanti" in desc
    print("  -> SEOAutoFixer Şablonları Başarılı:", title)

def test_provinces_integrity():
    print("[6/6] 81 İl Veri Bütünlüğü testi...")
    slugs = set()
    codes = set()
    for p in TR_PROVINCES:
        assert p["code"] not in codes, f"Mükerrer il kodu: {p['code']}"
        assert p["slug"] not in slugs, f"Mükerrer il slug: {p['slug']}"
        codes.add(p["code"])
        slugs.add(p["slug"])
    assert len(codes) == 81
    print("  -> 81 İl ve İl Kodları Eksiksiz ve Benzersiz!")

if __name__ == "__main__":
    print("=== Estoril Auto-SEO Motoru Birim Testleri ===")
    test_serp_analyzer()
    test_schema_org_builder()
    test_local_seo_generator()
    test_keyword_matrix()
    test_auto_fixer_templates()
    test_provinces_integrity()
    print("=== TÜM TESTLER BAŞARIYLA GEÇTİ ===")
