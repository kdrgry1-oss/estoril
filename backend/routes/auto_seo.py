"""
=============================================================================
auto_seo.py — Estoril Otomatik SEO API Uç Noktaları
=============================================================================
Yerel SEO (81 İl), Teknik SEO (Denetim, Şema & Auto-Fix) ve TR/Global SEO
işlevlerini yönetici paneline sunar.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json

from .deps import db, require_admin, logger
from auto_seo_engine import (
    TechnicalAuditor,
    SEOAutoFixer,
    SERPAnalyzer,
    SchemaOrgBuilder,
    KeywordMatrixBuilder,
    LocalSEOGenerator,
    TR_PROVINCES,
    SECTOR_PRODUCTS,
    INTENT_MODIFIERS
)

router = APIRouter(prefix="/admin/auto-seo", tags=["admin-auto-seo"])


@router.get("/audit")
async def get_seo_audit(current_user: dict = Depends(require_admin)):
    """Kataloğun canlı Teknik SEO Sağlık Skorunu (0-100%) ve eksikleri döner."""
    try:
        report = await TechnicalAuditor.run_audit(db)
        return {"success": True, "report": report}
    except Exception as e:
        logger.error(f"[auto_seo] Audit hatası: {e}")
        raise HTTPException(status_code=500, detail=f"SEO denetimi çalıştırılamadı: {str(e)}")


@router.post("/fix-all")
async def run_auto_fix(current_user: dict = Depends(require_admin)):
    """Katalogdaki tüm eksik meta başlık, açıklama ve ALT etiketlerini tek tıkla otomatik doldurur."""
    try:
        res = await SEOAutoFixer.fix_all_catalog(db)
        return res
    except Exception as e:
        logger.error(f"[auto_seo] Auto-fix hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Oto-düzeltme başarısız: {str(e)}")


@router.post("/serp-preview")
async def analyze_serp_preview(payload: dict, current_user: dict = Depends(require_admin)):
    """Verilen başlık ve açıklamanın Google masaüstü & mobil piksel/karakter önizlemesini hesaplar."""
    title = payload.get("title", "")
    description = payload.get("description", "")
    url = payload.get("url", "https://estoril.com.tr")
    analysis = SERPAnalyzer.analyze_meta(title, description, url)
    return {"success": True, "analysis": analysis}


@router.post("/generate-single")
async def generate_single_meta(payload: dict, current_user: dict = Depends(require_admin)):
    """Tek bir ürün veya konu için anında optimize edilmiş SEO başlığı ve açıklaması üretir."""
    name = (payload.get("name") or "").strip()
    category = (payload.get("category") or "").strip()
    price = payload.get("price")
    
    if not name:
        raise HTTPException(status_code=400, detail="Ürün veya konu adı gerekli")

    title = SEOAutoFixer.generate_optimized_title(name, category)
    desc = SEOAutoFixer.generate_optimized_description(name, category, price)
    analysis = SERPAnalyzer.analyze_meta(title, desc, f"https://estoril.com.tr/urun/{payload.get('slug', 'ornek-urun')}")

    return {
        "success": True,
        "title": title,
        "description": desc,
        "analysis": analysis
    }


@router.post("/keyword-matrix")
async def generate_keyword_matrix(payload: dict, current_user: dict = Depends(require_admin)):
    """Advertools tarzı programmatik anahtar kelime kombinasyonları matrisi üretir."""
    products = payload.get("products")
    intents = payload.get("intents")
    locations = payload.get("locations")
    limit = int(payload.get("limit", 150))
    
    matrix = KeywordMatrixBuilder.generate_matrix(
        products=products,
        intents=intents,
        locations=locations,
        limit=limit
    )
    return {
        "success": True,
        "total": len(matrix),
        "items": matrix
    }


@router.get("/local-provinces")
async def list_local_provinces(current_user: dict = Depends(require_admin)):
    """81 il ve ilçeler listesini döner."""
    return {
        "success": True,
        "provinces": TR_PROVINCES,
        "sector_products": SECTOR_PRODUCTS,
        "intent_modifiers": INTENT_MODIFIERS
    }


@router.get("/local-page")
async def get_local_page_seo(
    province_slug: str = Query(..., description="Örn: istanbul, ankara, izmir"),
    district: Optional[str] = Query(None, description="Örn: Kadıköy, Çankaya"),
    current_user: dict = Depends(require_admin)
):
    """Belirli bir il ve ilçe için programmatik yerel SEO iniş sayfası içeriklerini ve şemalarını döner."""
    page_data = LocalSEOGenerator.generate_province_page(province_slug, district)
    return {
        "success": True,
        "page": page_data
    }


@router.get("/schema-preview")
async def get_schema_preview(
    schema_type: str = Query("product", description="product | local | faq"),
    product_id: Optional[str] = Query(None),
    province_slug: Optional[str] = Query("istanbul"),
    current_user: dict = Depends(require_admin)
):
    """Google Zengin Arama ve AEO için Schema.org JSON-LD önizlemesi."""
    if schema_type == "product":
        sample = {
            "name": "Estoril Alpha Platinium Diode Buz Lazer Epilasyon Cihazı",
            "slug": "alpha-platinium-diode-lazer",
            "price": 450000,
            "currency": "TRY",
            "sku": "EST-DIODE-01",
            "description": "3 dalga boylu (755nm, 808nm, 1064nm) hibrit buz başlıklı profesyonel klinik tipi lazer epilasyon cihazı.",
            "stock": 5
        }
        if product_id:
            db_p = await db.products.find_one({"$or": [{"id": product_id}, {"_id": product_id}]})
            if db_p:
                sample = db_p
        schema = SchemaOrgBuilder.build_product_schema(sample)
    elif schema_type == "local":
        prov = next((p for p in TR_PROVINCES if p["slug"] == province_slug), TR_PROVINCES[33])
        schema = SchemaOrgBuilder.build_local_business_schema(prov)
    elif schema_type == "faq":
        prov_page = LocalSEOGenerator.generate_province_page(province_slug or "istanbul")
        schema = SchemaOrgBuilder.build_faq_schema(prov_page["faqs"])
    else:
        raise HTTPException(status_code=400, detail="Geçersiz şema tipi")

    return {
        "success": True,
        "schema_type": schema_type,
        "json_ld": schema,
        "json_ld_string": json.dumps(schema, indent=2, ensure_ascii=False)
    }
