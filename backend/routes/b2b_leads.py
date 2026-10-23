"""
B2B Leads (Hedef Kitleler) Management & Scraper API
8 Hedef Sektör:
1. Güzellik Merkezleri
2. Nail Stüdyoları
3. Op. Doktorlar & Estetik Hekimleri
4. Fizyoterapistler
5. Hastaneler & Tıp Merkezleri
6. Kadın Kuaförleri
7. Saç Ekim Merkezleri
8. Kalıcı Makyaj Stüdyoları
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from pydantic import BaseModel
from typing import Optional, List
import io
import csv
import logging
from datetime import datetime, timezone

from routes.deps import require_admin
from b2b_lead_scraper import (
    load_all_leads,
    save_leads,
    scrape_district_category,
    CATEGORIES,
    CITIES,
)

logger = logging.getLogger("b2b_leads_api")
router = APIRouter(prefix="/admin/b2b-leads", tags=["b2b-leads"])


class ScrapeRequest(BaseModel):
    il: str
    ilce: str
    kategori: str
    pages: int = 1


@router.get("/meta")
async def get_lead_metadata():
    """Form ve filtreler için il, ilçe ve sektör listelerini döner."""
    return {
        "categories": [
            {"id": k, "label": v["label"], "keywords": v["keywords"]}
            for k, v in CATEGORIES.items()
        ],
        "cities": [
            {"name": k, "districts": v["districts"]}
            for k, v in CITIES.items()
        ],
    }


@router.get("/stats")
async def get_lead_stats():
    """Özet metrikler ve dağılımlar."""
    leads = load_all_leads()
    total = len(leads)
    with_phone = sum(1 for l in leads if l.get("phone"))
    with_instagram = sum(1 for l in leads if l.get("instagram_handle"))
    with_website = sum(1 for l in leads if l.get("website"))

    # Sektör dağılımı
    cat_counts = {}
    for l in leads:
        k = l.get("kategori_key") or "diger"
        cat_counts[k] = cat_counts.get(k, 0) + 1

    categories_stats = []
    for k, info in CATEGORIES.items():
        categories_stats.append({
            "key": k,
            "label": info["label"],
            "count": cat_counts.get(k, 0),
        })

    # İl dağılımı
    city_counts = {}
    for l in leads:
        c = l.get("il") or "Belirtilmemiş"
        city_counts[c] = city_counts.get(c, 0) + 1

    cities_stats = [{"name": c, "count": cnt} for c, cnt in sorted(city_counts.items(), key=lambda x: -x[1])]

    return {
        "total_leads": total,
        "with_phone": with_phone,
        "with_instagram": with_instagram,
        "with_website": with_website,
        "phone_rate": round((with_phone / total * 100) if total else 0, 1),
        "instagram_rate": round((with_instagram / total * 100) if total else 0, 1),
        "categories": categories_stats,
        "cities": cities_stats[:10],
    }


@router.get("")
async def list_leads(
    il: Optional[str] = Query(None),
    ilce: Optional[str] = Query(None),
    kategori: Optional[str] = Query(None),
    has_phone: Optional[bool] = Query(False),
    has_instagram: Optional[bool] = Query(False),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
):
    """Filtrelenmiş lead listesi döner."""
    leads = load_all_leads()

    filtered = []
    for l in leads:
        if il and l.get("il", "").lower() != il.lower():
            continue
        if ilce and l.get("ilce", "").lower() != ilce.lower():
            continue
        if kategori and l.get("kategori_key") != kategori:
            continue
        if has_phone and not l.get("phone"):
            continue
        if has_instagram and not l.get("instagram_handle"):
            continue
        if q:
            term = q.lower()
            name = (l.get("name") or "").lower()
            addr = (l.get("address") or "").lower()
            phone = (l.get("phone") or "").lower()
            ig = (l.get("instagram_handle") or "").lower()
            if term not in name and term not in addr and term not in phone and term not in ig:
                continue
        filtered.append(l)

    # Sıralama: En son eklenenler önce
    filtered.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    items = filtered[start:end]
    pages = max(1, (total + limit - 1) // limit)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
    }


@router.post("/scrape")
async def run_scrape(req: ScrapeRequest):
    """Google Maps üzerinden belirtilen il, ilçe ve sektör için tarama başlatır."""
    if req.kategori not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Geçersiz kategori.")

    added = scrape_district_category(
        il=req.il,
        ilce=req.ilce,
        kategori_key=req.kategori,
        max_pages=req.pages,
        fetch_socials=True,
    )
    all_leads = load_all_leads()

    return {
        "success": True,
        "added_count": len(added),
        "total_leads": len(all_leads),
        "message": f"{req.ilce}/{req.il} için {len(added)} yeni potansiyel müşteri verisi toplandı.",
    }


@router.get("/export")
async def export_leads_csv(
    il: Optional[str] = Query(None),
    ilce: Optional[str] = Query(None),
    kategori: Optional[str] = Query(None),
    has_phone: Optional[bool] = Query(False),
    has_instagram: Optional[bool] = Query(False),
    q: Optional[str] = Query(None),
):
    """Filtrelenmiş verileri Excel uyumlu Türkçe UTF-8-BOM CSV olarak indirir."""
    leads = load_all_leads()
    filtered = []
    for l in leads:
        if il and l.get("il", "").lower() != il.lower(): continue
        if ilce and l.get("ilce", "").lower() != ilce.lower(): continue
        if kategori and l.get("kategori_key") != kategori: continue
        if has_phone and not l.get("phone"): continue
        if has_instagram and not l.get("instagram_handle"): continue
        if q:
            term = q.lower()
            name = (l.get("name") or "").lower()
            addr = (l.get("address") or "").lower()
            phone = (l.get("phone") or "").lower()
            ig = (l.get("instagram_handle") or "").lower()
            if term not in name and term not in addr and term not in phone and term not in ig:
                continue
        filtered.append(l)

    output = io.StringIO()
    # Excel Türkçe karakter uyumu için UTF-8 BOM
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "İşletme Adı",
        "Sektör",
        "İl",
        "İlçe",
        "Telefon",
        "Instagram Kullanıcı Adı",
        "Instagram Profili",
        "Web Sitesi",
        "E-posta",
        "Puan",
        "Yorum Sayısı",
        "Açık Adres",
        "Google Maps Bağlantısı",
        "Kayıt Tarihi",
    ])

    for l in filtered:
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
            l.get("created_at", "")[:10] if l.get("created_at") else "",
        ])

    csv_data = output.getvalue().encode("utf-8")
    filename = f"estoril_b2b_hedef_kitle_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
