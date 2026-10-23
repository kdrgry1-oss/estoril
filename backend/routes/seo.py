"""
=============================================================================
seo.py — Dinamik sitemap.xml + robots.txt (app köküne, /api PREFIX'SIZ)
=============================================================================
Google'ın bulabilmesi için bu router api_router'a DEĞİL, doğrudan app'e
include edilir (server.py: app.include_router(seo_router)). Böylece yollar
/sitemap.xml ve /robots.txt olarak kök seviyede yayınlanır.

sitemap.xml: yayında (is_active) ürünler + kategoriler + statik sayfalar +
ana sayfa. URL'ler FRONTEND_PUBLIC_URL (varsayılan https://estoril.com.tr)
üzerinden üretilir.
=============================================================================
"""
from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime, timezone
import os
import html

from .deps import db, logger

router = APIRouter(tags=["seo"])  # PREFIX YOK — kök seviye

_FRONTEND = (os.environ.get("FRONTEND_PUBLIC_URL") or "https://estoril.com.tr").rstrip("/")


def _esc(u: str) -> str:
    return html.escape(u or "", quote=True)


def _url_block(loc: str, lastmod: str = "", changefreq: str = "weekly", priority: str = "0.6") -> str:
    parts = [f"<loc>{_esc(loc)}</loc>"]
    if lastmod:
        parts.append(f"<lastmod>{lastmod}</lastmod>")
    parts.append(f"<changefreq>{changefreq}</changefreq>")
    parts.append(f"<priority>{priority}</priority>")
    return "<url>" + "".join(parts) + "</url>"


@router.get("/sitemap.xml")
async def sitemap_xml():
    """Yayındaki ürünler, kategoriler ve sayfalardan dinamik sitemap üretir."""
    urls: list[str] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Ana sayfa
    urls.append(_url_block(f"{_FRONTEND}/", today, "daily", "1.0"))

    try:
        # Kategoriler
        async for c in db.categories.find(
            {"is_active": {"$ne": False}}, {"_id": 0, "slug": 1}
        ):
            slug = c.get("slug")
            if slug:
                urls.append(_url_block(f"{_FRONTEND}/kategori/{slug}", today, "weekly", "0.8"))

        # Statik sayfalar (CMS)
        async for p in db.pages.find(
            {"is_active": {"$ne": False}}, {"_id": 0, "slug": 1}
        ):
            slug = p.get("slug")
            if slug:
                urls.append(_url_block(f"{_FRONTEND}/sayfa/{slug}", today, "monthly", "0.4"))

        # Ürünler (yalnızca aktif) — lastmod olarak updated_at kullan
        async for prod in db.products.find(
            {"is_active": {"$ne": False}},
            {"_id": 0, "slug": 1, "updated_at": 1},
        ):
            slug = prod.get("slug")
            if not slug:
                continue
            lm = (prod.get("updated_at") or "")[:10] or today
            urls.append(_url_block(f"{_FRONTEND}/urun/{slug}", lm, "weekly", "0.7"))

        # 81 İl Yerel SEO Sayfaları (Programmatic Local SEO)
        try:
            from auto_seo_engine import TR_PROVINCES
            for p in TR_PROVINCES:
                urls.append(_url_block(f"{_FRONTEND}/cihazlar/{p['slug']}-lazer-epilasyon-ve-estetik-cihazlari", today, "weekly", "0.8"))
        except Exception as e:
            logger.warning(f"[seo] yerel sitemap ekleme hatası: {e}")
    except Exception as e:
        logger.warning(f"[seo] sitemap üretim hatası: {e}")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.get("/sitemap-cities.xml")
async def sitemap_cities_xml():
    """81 il ve büyük ilçelerin yerel SEO iniş sayfaları için özel XML sitemap."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = []
    try:
        from auto_seo_engine import TR_PROVINCES
        for p in TR_PROVINCES:
            urls.append(_url_block(f"{_FRONTEND}/cihazlar/{p['slug']}-lazer-epilasyon-ve-estetik-cihazlari", today, "weekly", "0.8"))
            for dist in p.get("districts", [])[:3]:
                dist_slug = dist.lower().replace("ç", "c").replace("ğ", "g").replace("ı", "i").replace("ö", "o").replace("ş", "s").replace("ü", "u")
                urls.append(_url_block(f"{_FRONTEND}/cihazlar/{p['slug']}-{dist_slug}-lazer-epilasyon-cihazi", today, "monthly", "0.7"))
    except Exception as e:
        logger.warning(f"[seo] sitemap-cities hatası: {e}")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.get("/robots.txt")
async def robots_txt():
    """Robots.txt — Ana ve Yerel Sitemap indekslerini içerir (estoril.com.tr)."""
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /sepet\n"
        "Disallow: /odeme\n"
        "Disallow: /hesabim\n"
        "Disallow: /giris\n"
        "Disallow: /kayit\n"
        "Disallow: /odeme-bildirimi\n"
        "Disallow: /admin\n"
        f"Sitemap: {_FRONTEND}/sitemap.xml\n"
        f"Sitemap: {_FRONTEND}/sitemap-cities.xml\n"
    )
    return Response(content=body, media_type="text/plain")


# ===========================================================================
# YEREL SEO İNİŞ SAYFALARI — public, SUNUCU-RENDER (/cihazlar/{slug})
# ---------------------------------------------------------------------------
# Sitemap bu URL'leri Google'a bildiriyordu ama hiçbir route servis etmiyordu
# → hepsi 404 → oto-SEO zarar veriyordu. Bu route, auto_seo_engine'in ürettiği
# içeriği gerçek, taranabilir HTML olarak yayınlar (title/meta/canonical/H1/
# içerik/FAQ + LocalBusiness/FAQPage/BreadcrumbList JSON-LD).
# ===========================================================================
_PROV_SUFFIX = "-lazer-epilasyon-ve-estetik-cihazlari"
_DIST_SUFFIX = "-lazer-epilasyon-cihazi"


def _slugify_tr(s: str) -> str:
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    return (s or "").strip().lower().translate(table).replace(" ", "-")


@router.get("/cihazlar/{slug}")
async def local_seo_landing(slug: str):
    """İl/ilçe yerel SEO iniş sayfası — sunucu-render, taranabilir HTML."""
    try:
        from auto_seo_engine import TR_PROVINCES, LocalSEOGenerator
    except Exception as e:
        logger.warning(f"[seo] auto_seo_engine yüklenemedi: {e}")
        return Response(status_code=404, content="Sayfa bulunamadı", media_type="text/plain")

    base = slug
    if base.endswith(_PROV_SUFFIX):
        base = base[: -len(_PROV_SUFFIX)]
    elif base.endswith(_DIST_SUFFIX):
        base = base[: -len(_DIST_SUFFIX)]

    # İl eşleştir (en uzun önek kazanır) + varsa ilçe
    prov = None
    for p in sorted(TR_PROVINCES, key=lambda x: -len(x["slug"])):
        if base == p["slug"] or base.startswith(p["slug"] + "-"):
            prov = p
            break
    if not prov:
        return Response(status_code=404, content="Sayfa bulunamadı", media_type="text/plain")

    district = None
    rest = base[len(prov["slug"]):].lstrip("-")
    if rest:
        for d in prov.get("districts", []):
            if _slugify_tr(d) == rest:
                district = d
                break

    page = LocalSEOGenerator.generate_province_page(prov["slug"], district)
    # Canonical = SERVİS EDİLEN il URL'si (sitemap ile birebir; ilçe → il'e konsolide)
    canonical = f"{_FRONTEND}/cihazlar/{prov['slug']}{_PROV_SUFFIX}"
    title = page["seo_title"]
    desc = page["seo_description"]
    h1 = page["h1"]
    intro = page["intro_content"]
    faqs = page.get("faqs", [])
    schemas = page.get("schemas", {})

    def esc(s):
        return html.escape(str(s or ""), quote=True)

    import json as _json
    ld = []
    for key in ("local_business", "faq", "breadcrumb"):
        if schemas.get(key):
            ld.append('<script type="application/ld+json">' +
                       _json.dumps(schemas[key], ensure_ascii=False) + '</script>')
    faq_html = "".join(
        f'<section class="faq"><h3>{esc(f.get("q"))}</h3><p>{esc(f.get("a"))}</p></section>'
        for f in faqs
    )

    page_html = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{_FRONTEND}/og-estoril.jpg">
<meta name="twitter:card" content="summary_large_image">
{"".join(ld)}
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:860px;margin:0 auto;padding:24px 16px;color:#1f2d3a;line-height:1.6}}
h1{{font-size:1.7rem;line-height:1.3}} h3{{margin:1.2rem 0 .3rem}}
a.cta{{display:inline-block;background:#2563c9;color:#fff;padding:12px 22px;border-radius:10px;text-decoration:none;margin:14px 8px 14px 0}}
.faq{{border-top:1px solid #e6edf4;padding-top:10px}} .lead{{font-size:1.05rem}}
nav a{{color:#2563c9;text-decoration:none}} footer{{margin-top:32px;color:#6b7b8c;font-size:.9rem}}
</style>
</head>
<body>
<nav><a href="{_FRONTEND}/">Ana Sayfa</a> › <span>{esc(page.get("loc_display"))}</span></nav>
<h1>{esc(h1)}</h1>
<p class="lead">{esc(intro)}</p>
<p>
<a class="cta" href="{_FRONTEND}/">Cihazları İncele</a>
<a class="cta" href="tel:+905433300310" style="background:#0f9d58">Hemen Ara: 0543 330 03 10</a>
</p>
<h2>Sık Sorulan Sorular</h2>
{faq_html}
<footer>Estoril Cosmetic — {esc(page.get("loc_display"))} ve tüm Türkiye'ye CE belgeli medikal estetik cihaz satışı, kurulum ve teknik servis. İçerik bilgilendirme amaçlıdır.</footer>
</body>
</html>"""
    return Response(content=page_html, media_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=3600"})
