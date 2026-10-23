import React, { useEffect, useState } from 'react';
import axios from 'axios';
import B2BLeads from './B2BLeads';

const API = `${process.env.REACT_APP_BACKEND_URL}/api/analytics-extra/audience`;
const SEG = `${process.env.REACT_APP_BACKEND_URL}/api/analytics-extra/rfm`;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
const fmt = x => new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 }).format(Number(x) || 0);
const n = x => new Intl.NumberFormat('tr-TR').format(Number(x) || 0);

// Kendi (first-party) müşteri verisinden reklam hedef-kitle profili. Kişisel liste çıkarmaz;
// yalnızca toplulaştırılmış dağılımlar gösterir (KVKK-uyumlu).
export default function AudienceInsights() {
  const [activeTab, setActiveTab] = useState('b2b'); // 'b2b' | 'rfm'
  const [data, setData] = useState(null);
  const [days, setDays] = useState(365);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  async function load() {
    setBusy(true); setErr('');
    try {
      const { data } = await axios.get(`${API}?lookback_days=${days}`, auth());
      setData(data);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Veri alınamadı.');
    } finally { setBusy(false); }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days]);

  async function exportAudienceCSV() {
    // Custom Audience için: kendi müşterilerinin e-posta/telefonu (Meta/Google yüklerken kendisi hash'ler).
    try {
      const { data } = await axios.get(`${SEG}?lookback_days=${days}`, auth());
      const rows = (data.items || []).map(i => [i.email || '', i.phone || '']);
      const csv = 'email,phone\n' + rows.map(r => r.join(',')).join('\n');
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
      const a = document.createElement('a'); a.href = url;
      a.download = `custom-audience-${Date.now()}.csv`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch { setErr('Custom Audience CSV oluşturulamadı.'); }
  }

  const s = data?.summary;
  const maxCityOrders = Math.max(1, ...(data?.cities || []).map(c => c.orders));
  const maxCatQty = Math.max(1, ...(data?.categories || []).map(c => c.qty));
  const ctype = data?.customer_type || { corporate: 0, individual: 0 };
  const ctypeTotal = Math.max(1, ctype.corporate + ctype.individual);

  const Card = ({ title, children, right }) => (
    <div className="bg-white border rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">{title}</h2>{right}
      </div>
      {children}
    </div>
  );
  const Bar = ({ label, value, pct, sub }) => (
    <div className="mb-2">
      <div className="flex justify-between text-sm"><span className="truncate pr-2">{label}</span><span className="text-slate-500 whitespace-nowrap">{sub}</span></div>
      <div className="h-2 bg-slate-100 rounded mt-1"><div className="h-2 bg-blue-600 rounded" style={{ width: `${pct}%` }} /></div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Ana Tab Seçici */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('b2b')}
          className={`pb-3 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
            activeTab === 'b2b'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span className="p-1 rounded bg-indigo-50 text-indigo-600">🎯</span>
          <span>B2B Google Maps Hedef Kitleler (9 Sektör)</span>
        </button>

        <button
          onClick={() => setActiveTab('rfm')}
          className={`pb-3 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
            activeTab === 'rfm'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span className="p-1 rounded bg-slate-100 text-slate-600">📊</span>
          <span>Müşteri Reklam Kitle Profili (Lookalike / Kendi Verin)</span>
        </button>
      </div>

      {activeTab === 'b2b' ? (
        <B2BLeads />
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold">Müşteri Reklam Kitlesi (Lookalike / KVKK)</h1>
              <p className="text-sm text-slate-500">Kendi müşteri verinden reklam hedefleme profili — coğrafya, ilgi, kitle tipi. (KVKK-uyumlu: kişisel liste değil, toplu dağılım.)</p>
            </div>
            <div className="flex items-center gap-2">
              <select value={days} onChange={e => setDays(Number(e.target.value))} className="border rounded-lg p-2 bg-white text-sm">
                <option value={90}>Son 90 gün</option>
                <option value={180}>Son 180 gün</option>
                <option value={365}>Son 1 yıl</option>
                <option value={730}>Son 2 yıl</option>
              </select>
              <button onClick={load} disabled={busy} className="border rounded-lg px-3 py-2 text-sm disabled:opacity-50">Yenile</button>
              <button onClick={exportAudienceCSV} className="bg-blue-700 text-white rounded-lg px-3 py-2 text-sm">Custom Audience CSV</button>
            </div>
          </div>

          {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
          {!data ? <p className="text-slate-500">{busy ? 'Yükleniyor…' : 'Veri yok.'}</p> : (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-white border rounded-xl p-4"><p className="text-xs text-slate-500">Müşteri</p><p className="text-2xl font-semibold">{n(s.total_customers)}</p></div>
                <div className="bg-white border rounded-xl p-4"><p className="text-xs text-slate-500">Sipariş</p><p className="text-2xl font-semibold">{n(s.total_orders)}</p></div>
                <div className="bg-white border rounded-xl p-4"><p className="text-xs text-slate-500">Ort. Sepet (AOV)</p><p className="text-2xl font-semibold">{fmt(s.aov)}</p></div>
                <div className="bg-white border rounded-xl p-4"><p className="text-xs text-slate-500">Tekrar Eden Oranı</p><p className="text-2xl font-semibold">%{s.repeat_rate}</p></div>
              </div>

              <div className="grid lg:grid-cols-2 gap-5">
                <Card title="En Çok Satış Yapılan Şehirler" right={<span className="text-xs text-slate-400">reklam coğrafi hedefleme</span>}>
                  {(data.cities || []).length ? data.cities.map(c => (
                    <Bar key={c.name} label={c.name} value={c.orders} pct={Math.round(c.orders / maxCityOrders * 100)} sub={`${n(c.orders)} sipariş · ${fmt(c.revenue)}`} />
                  )) : <p className="text-sm text-slate-500">Şehir verisi yok.</p>}
                </Card>

                <Card title="İlgi Alanı — Satın Alınan Kategoriler" right={<span className="text-xs text-slate-400">ilgi hedefleme</span>}>
                  {(data.categories || []).length ? data.categories.map(c => (
                    <Bar key={c.name} label={c.name} value={c.qty} pct={Math.round(c.qty / maxCatQty * 100)} sub={`${n(c.qty)} adet`} />
                  )) : <p className="text-sm text-slate-500">Kategori verisi yok.</p>}
                </Card>

                <Card title="Kitle Tipi">
                  <div className="flex gap-4">
                    <div className="flex-1 text-center p-4 bg-slate-50 rounded-lg">
                      <p className="text-2xl font-semibold">%{Math.round(ctype.individual / ctypeTotal * 100)}</p>
                      <p className="text-sm text-slate-500">Bireysel ({n(ctype.individual)})</p>
                    </div>
                    <div className="flex-1 text-center p-4 bg-slate-50 rounded-lg">
                      <p className="text-2xl font-semibold">%{Math.round(ctype.corporate / ctypeTotal * 100)}</p>
                      <p className="text-sm text-slate-500">Kurumsal / B2B ({n(ctype.corporate)})</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 mt-3">Kurumsal oranı yüksekse reklamda "klinik / işletme sahibi" hedeflemesi + LinkedIn mantıklı; bireysel yüksekse Meta/TikTok geniş kitle.</p>
                </Card>

                <Card title="Sipariş Tutar Bantları" right={<span className="text-xs text-slate-400">bütçe/teklif kurgusu</span>}>
                  {(data.order_value_bands || []).map(b => (
                    <div key={b.band} className="flex justify-between text-sm py-1 border-b last:border-0"><span>{b.band}</span><span className="text-slate-500">{n(b.count)} sipariş</span></div>
                  ))}
                </Card>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 text-sm text-blue-900 space-y-2">
                <p className="font-semibold">Reklamda nasıl kullanılır?</p>
                <ul className="list-disc pl-5 space-y-1">
                  <li><b>Coğrafi hedefleme:</b> Yukarıdaki en çok satan şehir/ilçeleri Meta/Google kampanyasında konum olarak seç.</li>
                  <li><b>İlgi hedefleme:</b> En çok satın alınan kategorileri ilgi alanı/anahtar kelime olarak kullan.</li>
                  <li><b>Custom Audience:</b> "Custom Audience CSV" ile kendi müşteri listeni indir, Meta/Google'a yükle (platform hash'ler). Onlardan <b>Lookalike (Benzer Kitle)</b> üret — en etkili yöntem.</li>
                  <li><b>KVKK:</b> Yalnızca kendi müşteri verin kullanılır; dışarıdan kişi listesi toplanmaz. Custom Audience yüklerken platformun açık rıza/şart koşullarına uy.</li>
                </ul>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
