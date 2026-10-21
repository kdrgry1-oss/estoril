"""Customer quote requests and authenticated admin proposals."""
import hashlib, json, secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from xml.sax.saxutils import escape
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from .deps import db, require_admin
from .estoril_wholesale import authenticated, HEADERS, now, check_origin, result

router = APIRouter(prefix='/estoril/quotes', tags=['Estoril quotes'])
class ItemRequest(BaseModel):
    product_id: str | None = Field(default=None, max_length=150)
    name: str | None = Field(default=None, max_length=500)
    qty: int = Field(ge=1, le=999, strict=True)
class QuoteRequest(BaseModel):
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{20,64}$')
    company: str = Field(min_length=2, max_length=200)
    contact: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=10, max_length=30)
    address: str = Field(min_length=10, max_length=1500)
    note: str = Field(default='', max_length=2000)
    items: list[ItemRequest] = Field(min_length=1, max_length=100)
    wholesale_token: str | None = Field(default=None, min_length=43, max_length=43)
class EditItem(BaseModel):
    product_id: str = Field(max_length=150)
    qty: int = Field(ge=1, le=999, strict=True)
    unit_price: str = Field(max_length=30)
    line_discount: str = Field(default='0', max_length=10)
    vat_rate: str = Field(default='0', max_length=10)
class QuoteEdit(BaseModel):
    revision: int = Field(ge=1)
    items: list[EditItem] = Field(min_length=1, max_length=100)
    discount_percent: str = Field(default='0', max_length=10)
    valid_days: int = Field(default=15, ge=1, le=365)
    note: str = Field(default='', max_length=3000)
    status: str = Field(pattern=r'^(new|draft|ready|closed)$')
    title: str = Field(default='', max_length=200)

def decimal(value, maximum=Decimal('100000000'), allow_zero=True):
    try:
        d=Decimal(str(value).replace(',','.'))
        if not d.is_finite() or d<0 or (not allow_zero and d==0) or d>maximum or d!=d.quantize(Decimal('.01')): raise ValueError()
        return d
    except (InvalidOperation,ValueError): raise HTTPException(400,'Geçerli bir tutar girin (en fazla iki ondalık).')
def money(d):return str(d.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def pct(item,key):
    try:return Decimal(str(item.get(key,'0') or '0').replace(',','.'))
    except InvalidOperation:return Decimal(0)
def line_net(item):
    # Birim fiyat x adet, satir iskontosu dusulmus net tutar (genel iskonto haric).
    return Decimal(item['unit_price'])*item['qty']*(100-pct(item,'line_discount'))/100
def totals(items, discount):
    subtotal=sum((line_net(x) for x in items), Decimal(0)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    deduction=(subtotal*discount/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    net=subtotal-deduction
    factor=(net/subtotal) if subtotal>0 else Decimal(0)
    vat=sum((line_net(x)*factor*pct(x,'vat_rate')/100 for x in items), Decimal(0)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return {'subtotal':money(subtotal),'discount_amount':money(deduction),'net_total':money(net),'vat_total':money(vat),'total':money(net+vat)}
def quote_title(company, contact):
    # Firma varsa "<Firma> fiyat teklifi"; birey ise "<Ad Soyad> teklifi".
    company=(company or '').strip();contact=(contact or '').strip()
    if company and company.lower()!=contact.lower():return company+' fiyat teklifi'
    return (contact+' teklifi') if contact else (company+' fiyat teklifi')

@router.post('')
async def submit(payload:QuoteRequest, request:Request):
    check_origin(request)
    data=payload.model_dump(exclude={'wholesale_token'})
    signature=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    link=await authenticated(payload.wholesale_token,request) if payload.wholesale_token else None
    old=await db.estoril_quotes.find_one({'_id':payload.request_id})
    if old:
        if old['request_hash']!=signature or old.get('link_id')!=(link['id'] if link else None):raise HTTPException(409,'Bu istek numarası kullanılmış.')
        return result({'number':old['number']})
    if len(''.join(c for c in payload.phone if c.isdigit()))<10 or not payload.company.strip() or not payload.contact.strip():raise HTTPException(400,'Firma, yetkili ve telefon bilgilerini kontrol edin.')
    from pymongo import ReturnDocument
    ip=hashlib.sha256((request.client.host if request.client else '').encode()).hexdigest()
    attempt=await db.estoril_quote_attempts.find_one_and_update({'_id':ip+':'+str(int(now().timestamp())//3600)}, {'$inc':{'count':1},'$set':{'expires_at':now()+timedelta(hours=2)}},upsert=True,return_document=ReturnDocument.AFTER)
    if attempt['count']>20:raise HTTPException(429,'Çok fazla talep. Daha sonra tekrar deneyin.',headers=HEADERS)
    items=[];seen=set()
    for item in payload.items:
        query={'id':item.product_id} if item.product_id else {'name':item.name}
        found=await db.products.find(query,{'id':1,'name':1,'price':1,'sale_price':1,'images':1}).to_list(2)
        if len(found)!=1:raise HTTPException(400,'Sepetteki ürün bulunamadı veya eşleşme belirsiz. Sepeti yenileyin.')
        p=found[0]
        if p['id'] in seen:raise HTTPException(400,'Aynı ürün birden fazla satırda gönderilemez.')
        seen.add(p['id']);vat=True
        if link:
            price=await db.estoril_wholesale_prices.find_one({'product_id':p['id'],'enabled':True})
            if not price:raise HTTPException(400,'Ürün toptan listede artık bulunmuyor. Sepeti yenileyin.')
            amount=decimal(price['amount'],allow_zero=False);vat=price.get('vat_included',True)
        else:amount=decimal(p.get('sale_price') or p.get('price') or 0,allow_zero=False)
        items.append({'product_id':p['id'],'name':p['name'],'image':((p.get('images') or [''])[0]),'qty':item.qty,'unit_price':money(amount),'vat_included':vat,'line_discount':'0.00','vat_rate':'0.00'})
    timestamp=now().isoformat()
    row={'_id':payload.request_id,'id':payload.request_id,'number':'EST-'+now().strftime('%Y%m%d')+'-'+secrets.token_hex(4).upper(),'request_hash':signature,'company':payload.company.strip(),'contact':payload.contact.strip(),'phone':payload.phone.strip(),'address':payload.address.strip(),'customer_note':payload.note,'items':items,'original_items':items,'source':'wholesale' if link else 'retail','link_id':link['id'] if link else None,'discount_percent':'0.00','valid_days':15,'note':'','status':'new','title':quote_title(payload.company,payload.contact),'revision':1,'created_at':timestamp,'updated_at':timestamp,**totals(items,Decimal(0))}
    try:await db.estoril_quotes.insert_one(row)
    except DuplicateKeyError:
        old=await db.estoril_quotes.find_one({'_id':payload.request_id})
        if old['request_hash']!=signature or old.get('link_id')!=row['link_id']:raise HTTPException(409,'İstek çakışması.')
        return result({'number':old['number']})
    return result({'number':row['number']})

@router.get('/admin')
async def listing(user=Depends(require_admin)):
    rows=await db.estoril_quotes.find({}, {'_id':0,'request_hash':0}).sort('created_at',-1).to_list(1000)
    return result(rows)

@router.put('/admin/{quote_id}')
async def edit(quote_id:str,payload:QuoteEdit,user=Depends(require_admin)):
    row=await db.estoril_quotes.find_one({'id':quote_id})
    if not row:raise HTTPException(404,'Teklif bulunamadı.')
    old={x['product_id']:x for x in row['items']}
    if len(payload.items)!=len(old) or {x.product_id for x in payload.items}!=set(old):raise HTTPException(400,'Teklifin ürünleri değiştirilemez; adet, fiyat, iskonto ve KDV düzenleyebilirsiniz.')
    items=[{**old[x.product_id],'qty':x.qty,'unit_price':money(decimal(x.unit_price)),'line_discount':money(decimal(x.line_discount,Decimal('100'))),'vat_rate':money(decimal(x.vat_rate,Decimal('100')))} for x in payload.items]
    discount=decimal(payload.discount_percent,Decimal('100'))
    title=payload.title.strip() or quote_title(row.get('company'),row.get('contact'))
    changes={'items':items,'discount_percent':money(discount),'valid_days':payload.valid_days,'note':payload.note,'status':payload.status,'title':title,'updated_at':now().isoformat(),'updated_by':str(user.get('id','')),'revision':payload.revision+1,**totals(items,discount)}
    updated=await db.estoril_quotes.update_one({'id':quote_id,'revision':payload.revision},{'$set':changes})
    if updated.matched_count!=1:raise HTTPException(409,'Teklif başka bir işlemde değişti. Listeyi yenileyin.')
    return result({**{k:v for k,v in row.items() if k not in ('_id','request_hash')},**changes})

@router.delete('/admin/{quote_id}')
async def remove(quote_id:str,user=Depends(require_admin)):
    deleted=await db.estoril_quotes.delete_one({'id':quote_id})
    if deleted.deleted_count!=1:raise HTTPException(404,'Teklif bulunamadı.')
    return result({'deleted':True})

def product_image(source):
    from pathlib import Path
    from urllib.parse import urlsplit,unquote
    if isinstance(source,dict):source=source.get('url','')
    if not isinstance(source,str) or not source:return None
    root=Path('/var/www/estoril')
    try:
        mapping=json.loads((root/'product-photos.js').read_text().split('=',1)[1].strip().rstrip(';'))
        source=mapping.get(source,source)
    except (OSError,ValueError):pass
    parsed=urlsplit(source)
    if not parsed.netloc or parsed.hostname in ('estoril.com.tr','www.estoril.com.tr'):
        candidate=(root/unquote(parsed.path).lstrip('/')).resolve()
        if candidate.is_relative_to((root/'uploads').resolve()) and candidate.is_file():return candidate
    cached=Path(__file__).parent/'quote-images'/(hashlib.sha256(source.encode()).hexdigest()+'.png')
    return cached if cached.is_file() else None

def make_pdf(row):
    from reportlab.pdfgen import canvas
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if 'Estoril' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('Estoril','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('EstorilBold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    styles=getSampleStyleSheet()
    normal=ParagraphStyle('normal',fontName='Estoril',fontSize=9,leading=14,textColor=colors.HexColor('#243e53'))
    heading=ParagraphStyle('heading',parent=normal,fontName='EstorilBold',fontSize=22,leading=28)
    def P(text,style=normal):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    def fmt(v):return f'{Decimal(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')+' TL'
    buf=BytesIO();doc=SimpleDocTemplate(buf,pagesize=(595.28,841.89),leftMargin=40,rightMargin=40,topMargin=44,bottomMargin=48)
    from pathlib import Path
    from PIL import Image as PILImage
    def photo(path,w,h):
        try:
            im=PILImage.open(path).convert('RGBA');im.thumbnail((600,600));out=BytesIO();im.save(out,format='PNG');out.seek(0)
            scale=min(w/im.width,h/im.height)
            return Image(out,width=im.width*scale,height=im.height*scale)
        except Exception:return P('Görsel yok')
    logo=photo('/var/www/estoril/uploads/estoril-metallic-transparent.png',155,52)
    company=[P('ESTORIL COSMETIC'),P('Halkalı Merkez Mah. Filiz Sok. No:34'),P('Küçükçekmece / İstanbul'),P('0533 433 12 51'),P('info@estorilcosmetic.com · estoril.com.tr')]
    header=Table([[logo,company]],colWidths=[215,300]);header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0)]))
    subtitle=ParagraphStyle('subtitle',parent=normal,fontName='EstorilBold',fontSize=12,leading=16,textColor=colors.HexColor('#2563c9'))
    def pctfmt(v):return str(Decimal(str(v or 0)).normalize()).replace('.',',')
    title_line=[P(row['title'],subtitle)] if row.get('title') else []
    parts=[header,Spacer(1,22),P('FİYAT TEKLİFİ',heading)]+([Spacer(1,4)]+title_line if title_line else [])+[Spacer(1,12),P(row['number']+' · Revizyon '+str(row['revision'])),P('Güncelleme: '+row['updated_at'][:10]+' · Geçerlilik: '+str(row['valid_days'])+' gün'),Spacer(1,18),P(row['company']),P(row['contact']+' · '+row['phone']),P(row['address']),Spacer(1,20)]
    data=[[P(x) for x in ['Görsel','Ürün','Adet','Birim fiyat','İskonto','KDV','Satır tutarı']]]
    for x in row['items']:
        net=line_net(x)
        vr=pct(x,'vat_rate');ld=pct(x,'line_discount')
        data.append([photo(product_image(x.get('image','')),52,62),P(x['name']+'\n'+('KDV dahil' if x.get('vat_included',True) else 'KDV hariç')),P(x['qty']),P(fmt(x['unit_price'])),P('%'+pctfmt(ld) if ld else '—'),P('%'+pctfmt(vr) if vr else '—'),P(fmt(net))])
    table=Table(data,colWidths=[58,150,30,78,44,40,95],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7eef6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#dce4ec'))]))
    summary=[P('Ara toplam: '+fmt(row['subtotal']))]
    if Decimal(str(row.get('discount_amount','0') or 0))>0:summary.append(P('İskonto (%'+pctfmt(row['discount_percent'])+'): -'+fmt(row['discount_amount'])))
    if Decimal(str(row.get('vat_total','0') or 0))>0:summary+=[P('Net toplam: '+fmt(row.get('net_total',row['total']))),P('KDV: +'+fmt(row['vat_total']))]
    summary.append(P('Teklif toplamı: '+fmt(row['total'])))
    parts += [table,Spacer(1,18)]+summary+[Spacer(1,14),P('KDV oranları ürün satırlarında belirtilmiştir. KDV tutarı genel toplama dahildir. Bu belge fatura değildir.')]
    if row.get('note'):parts += [Spacer(1,14),P('Teklif notu'),P(row['note'])]
    def footer(c,doc):
        c.setFont('Estoril',8);c.setFillColor(colors.HexColor('#6b7b8c'));c.drawString(40,26,'estoril.com.tr | '+row['number']);c.drawRightString(555,26,str(doc.page))
    doc.build(parts,onFirstPage=footer,onLaterPages=footer);return buf.getvalue()

@router.get('/admin/{quote_id}/pdf')
async def pdf(quote_id:str,user=Depends(require_admin)):
    row=await db.estoril_quotes.find_one({'id':quote_id})
    if not row:raise HTTPException(404,'Teklif bulunamadı.')
    from starlette.concurrency import run_in_threadpool
    for item in row['items']:
        if not item.get('image'):
            product=await db.products.find_one({'id':item['product_id']},{'images':1})
            item['image']=((product or {}).get('images') or [''])[0]
    content=await run_in_threadpool(make_pdf,row)
    return Response(content,media_type='application/pdf',headers={**HEADERS,'Content-Disposition':f'attachment; filename="{row["number"]}-r{row["revision"]}.pdf"'})

@router.on_event('startup')
async def indexes():
    await db.estoril_quotes.create_index('id',unique=True)
    await db.estoril_quotes.create_index('created_at')
    await db.estoril_quote_attempts.create_index('expires_at',expireAfterSeconds=0)

# Keep private requests under the existing session-cookie path.
from .estoril_wholesale import router as wholesale_router
@wholesale_router.post('/catalog/{token}/quote')
async def wholesale_submit(token:str,payload:QuoteRequest,request:Request):
    if payload.wholesale_token!=token:raise HTTPException(400,'Erişim bağlantısı eşleşmiyor.')
    return await submit(payload,request)
