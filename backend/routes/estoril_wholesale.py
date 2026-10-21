"""Private wholesale prices; never merged into public product documents."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .deps import db, require_admin

router = APIRouter(prefix='/estoril/wholesale', tags=['Estoril private wholesale'])
BASE = 'https://estoril.com.tr/toptan#'
PREFIX = '/api/estoril/wholesale/catalog/'
HEADERS = {'Cache-Control': 'private, no-store, max-age=0', 'Pragma': 'no-cache',
           'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet, noimageindex',
           'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff',
           'X-Frame-Options': 'DENY'}
ALLOWED_ORIGINS = {'https://estoril.com.tr', 'https://www.estoril.com.tr', 'https://panel.estoril.com.tr'}

def now(): return datetime.now(timezone.utc)
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()
def cookie_name(token): return 'estoril_w_' + digest(token)[:16]
def check_origin(request):
    if request.headers.get('origin') not in ALLOWED_ORIGINS:
        raise HTTPException(403, 'Geçersiz istek kaynağı', headers=HEADERS)
def fail(): raise HTTPException(401, 'Bağlantı veya şifre geçersiz ya da süresi dolmuş.', headers=HEADERS)
def result(data): return JSONResponse(data, headers=HEADERS)

class PriceInput(BaseModel):
    amount: str = Field(max_length=30)
    enabled: bool = False
    vat_included: bool = True

class LinkInput(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    days: int = Field(default=30, ge=1, le=365)

class LoginInput(BaseModel):
    password: str = Field(min_length=1, max_length=128)

@router.get('/admin/prices/{product_id}')
async def read_price(product_id: str, user=Depends(require_admin)):
    row = await db.estoril_wholesale_prices.find_one({'product_id': product_id}, {'_id': 0})
    return result(row or {'product_id': product_id, 'amount': '', 'enabled': False, 'vat_included': True})

@router.put('/admin/prices/{product_id}')
async def write_price(product_id: str, payload: PriceInput, user=Depends(require_admin)):
    if not await db.products.find_one({'id': product_id}, {'id': 1}): raise HTTPException(404, 'Ürün bulunamadı')
    try:
        amount = Decimal(payload.amount.replace(',', '.'))
        if not amount.is_finite() or amount <= 0 or amount > 100000000 or amount != amount.quantize(Decimal('.01')):
            raise ValueError()
    except (ValueError, InvalidOperation): raise HTTPException(400, 'Pozitif, en fazla iki ondalıklı bir fiyat girin.')
    row = {'product_id': product_id, 'amount': str(amount.quantize(Decimal('.01'))),
           'enabled': payload.enabled, 'vat_included': payload.vat_included, 'currency': 'TRY',
           'updated_at': now().isoformat(), 'updated_by': str(user.get('id', ''))}
    await db.estoril_wholesale_prices.update_one({'product_id': product_id}, {'$set': row}, upsert=True)
    return result(row)

@router.get('/admin/links')
async def list_links(user=Depends(require_admin)):
    rows = await db.estoril_wholesale_links.find({}, {'_id': 0, 'id': 1, 'label': 1, 'expires_at': 1, 'revoked': 1}).sort('created_at', -1).to_list(500)
    for row in rows: row['expires_at'] = row['expires_at'].isoformat()
    return result(rows)

@router.post('/admin/links')
async def create_link(payload: LinkInput, user=Depends(require_admin)):
    token, password, salt = secrets.token_urlsafe(32), secrets.token_urlsafe(15), secrets.token_hex(16)
    row = {'id': secrets.token_hex(16), 'token_hash': digest(token), 'label': payload.label.strip(),
           'salt': salt, 'password_hash': await run_in_threadpool(password_hash, password, salt),
           'expires_at': now() + timedelta(days=payload.days), 'created_at': now(),
           'created_by': str(user.get('id', '')), 'revoked': False}
    if not row['label']: raise HTTPException(400, 'Alıcı adı gerekli')
    await db.estoril_wholesale_links.insert_one(row)
    return result({'id': row['id'], 'url': BASE + token, 'password': password, 'expires_at': row['expires_at'].isoformat()})

@router.delete('/admin/links/{link_id}')
async def revoke_link(link_id: str, user=Depends(require_admin)):
    await db.estoril_wholesale_links.update_one({'id': link_id}, {'$set': {'revoked': True}})
    await db.estoril_wholesale_sessions.delete_many({'link_id': link_id})
    return result({'ok': True})

async def active_link(token):
    if len(token) != 43: fail()
    row = await db.estoril_wholesale_links.find_one({'token_hash': digest(token), 'revoked': False, 'expires_at': {'$gt': now()}})
    if not row: fail()
    return row

async def authenticated(token, request):
    link = await active_link(token)
    session = request.cookies.get(cookie_name(token), '')
    if not session: fail()
    valid = await db.estoril_wholesale_sessions.find_one({'session_hash': digest(session), 'link_id': link['id'], 'expires_at': {'$gt': now()}})
    if not valid: fail()
    return link

@router.get('/catalog/{token}', response_class=HTMLResponse)
async def catalog_shell(token: str):
    # Only the login shell is public; no product or price data in this HTML.
    if len(token) != 43: fail()
    html = (Path(__file__).parent / 'estoril_wholesale.html').read_text()
    return HTMLResponse(html, headers={**HEADERS, 'Content-Security-Policy': "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' https://www.estorilcosmetic.com https://estorilcosmetic.com; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"})

@router.post('/catalog/{token}/login')
async def login(token: str, payload: LoginInput, request: Request):
    check_origin(request)
    # nginx supplies the real client IP; do not trust arbitrary forwarded-for chains.
    ip = request.client.host if request.client else ''
    key = digest(ip)
    bucket = int(now().timestamp()) // 600
    from pymongo import ReturnDocument
    attempt = await db.estoril_wholesale_attempts.find_one_and_update(
        {'_id': f'{key}:{bucket}'}, {'$inc': {'count': 1}, '$set': {'expires_at': now()+timedelta(minutes=20)}},
        upsert=True, return_document=ReturnDocument.AFTER)
    if attempt['count'] > 10:
        raise HTTPException(429, 'Çok fazla deneme. 10 dakika sonra yeniden deneyin.', headers={**HEADERS, 'Retry-After': '600'})
    link = await active_link(token)
    calculated = await run_in_threadpool(password_hash, payload.password, link['salt'])
    if not hmac.compare_digest(calculated, link['password_hash']): fail()
    session = secrets.token_urlsafe(32)
    old = request.cookies.get(cookie_name(token))
    if old: await db.estoril_wholesale_sessions.delete_many({'session_hash': digest(old)})
    await db.estoril_wholesale_sessions.insert_one({'session_hash': digest(session), 'link_id': link['id'], 'expires_at': now()+timedelta(hours=8)})
    response = result({'ok': True})
    response.set_cookie(cookie_name(token), session, max_age=28800, secure=True, httponly=True, samesite='strict', path=PREFIX+token)
    return response

@router.get('/catalog/{token}/products')
async def private_products(token: str, request: Request):
    await authenticated(token, request)
    rows = await db.estoril_wholesale_prices.find({'enabled': True}, {'_id': 0}).to_list(5000)
    prices = {x['product_id']: x for x in rows}
    public = await db.products.find({'id': {'$in': list(prices)}}, {'_id': 0, 'id': 1, 'name': 1, 'images': 1}).to_list(5000)
    out = []
    for p in public:
        price = prices[p['id']]
        images = p.get('images') or []
        image = images[0] if images else ''
        if isinstance(image, dict): image = image.get('url', '')
        out.append({'id': p['id'], 'name': p.get('name', ''), 'image': image, 'amount': price['amount'], 'currency': 'TRY', 'vat_included': price.get('vat_included', True)})
    return result({'products': out})

@router.post('/catalog/{token}/logout')
async def logout(token: str, request: Request):
    check_origin(request)
    session = request.cookies.get(cookie_name(token), '')
    if session: await db.estoril_wholesale_sessions.delete_many({'session_hash': digest(session)})
    response = result({'ok': True})
    response.delete_cookie(cookie_name(token), path=PREFIX+token, secure=True, httponly=True, samesite='strict')
    return response

@router.on_event('startup')
async def indexes():
    await db.estoril_wholesale_prices.create_index('product_id', unique=True)
    await db.estoril_wholesale_links.create_index('token_hash', unique=True)
    await db.estoril_wholesale_sessions.create_index('session_hash', unique=True)
    await db.estoril_wholesale_sessions.create_index('expires_at', expireAfterSeconds=0)
    await db.estoril_wholesale_attempts.create_index('expires_at', expireAfterSeconds=0)
