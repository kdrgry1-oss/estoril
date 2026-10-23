import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import {
  Search, Phone, Globe, MapPin, Star, Download, Play, RefreshCw,
  Building2, Sparkles, Filter, ExternalLink, Instagram, CheckCircle2,
  AlertCircle, ChevronRight, Hash, Layers
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const auth = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
});

export default function B2BLeads() {
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [stats, setStats] = useState(null);
  const [meta, setMeta] = useState({ categories: [], cities: [] });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  // Filtreler
  const [selectedCat, setSelectedCat] = useState('');
  const [selectedIl, setSelectedIl] = useState('');
  const [selectedIlce, setSelectedIlce] = useState('');
  const [hasPhoneOnly, setHasPhoneOnly] = useState(false);
  const [hasInstagramOnly, setHasInstagramOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Tarama Modalı
  const [scrapeModal, setScrapeModal] = useState(false);
  const [scrapeForm, setScrapeForm] = useState({
    il: 'İstanbul',
    ilce: 'Kadıköy',
    kategori: 'guzellik_merkezi',
    pages: 1,
  });
  const [scrapeBusy, setScrapeBusy] = useState(false);
  const [scrapeResult, setScrapeResult] = useState('');

  // Meta ve İstatistikleri Yükle
  async function loadMetaAndStats() {
    try {
      const [metaRes, statsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/admin/b2b-leads/meta`, auth()),
        axios.get(`${BACKEND_URL}/api/admin/b2b-leads/stats`, auth()),
      ]);
      setMeta(metaRes.data || { categories: [], cities: [] });
      setStats(statsRes.data || null);
    } catch (e) {
      console.error('Meta/Stats yüklenemedi:', e);
    }
  }

  // Lead Listesini Çek
  async function loadLeads(pageIndex = 1) {
    setLoading(true);
    setErr('');
    try {
      const params = new URLSearchParams();
      params.append('page', pageIndex);
      params.append('limit', 50);
      if (selectedCat) params.append('kategori', selectedCat);
      if (selectedIl) params.append('il', selectedIl);
      if (selectedIlce) params.append('ilce', selectedIlce);
      if (hasPhoneOnly) params.append('has_phone', 'true');
      if (hasInstagramOnly) params.append('has_instagram', 'true');
      if (searchQuery.trim()) params.append('q', searchQuery.trim());

      const res = await axios.get(`${BACKEND_URL}/api/admin/b2b-leads?${params.toString()}`, auth());
      setLeads(res.data.items || []);
      setTotal(res.data.total || 0);
      setPage(res.data.page || 1);
      setTotalPages(res.data.pages || 1);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Lead verileri yüklenirken hata oluştu.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMetaAndStats();
  }, []);

  useEffect(() => {
    loadLeads(1);
    // eslint-disable-next-line
  }, [selectedCat, selectedIl, selectedIlce, hasPhoneOnly, hasInstagramOnly]);

  // Seçilen ile ait ilçeler
  const availableDistricts = useMemo(() => {
    if (!selectedIl || !meta.cities) return [];
    const found = meta.cities.find(c => c.name.toLowerCase() === selectedIl.toLowerCase());
    return found ? found.districts : [];
  }, [selectedIl, meta.cities]);

  // Tarama modalı için seçilen ilin ilçeleri
  const scrapeDistricts = useMemo(() => {
    if (!scrapeForm.il || !meta.cities) return [];
    const found = meta.cities.find(c => c.name.toLowerCase() === scrapeForm.il.toLowerCase());
    return found ? found.districts : [];
  }, [scrapeForm.il, meta.cities]);

  // Tarama Başlat
  async function handleStartScrape(e) {
    e.preventDefault();
    setScrapeBusy(true);
    setScrapeResult('');
    try {
      const res = await axios.post(`${BACKEND_URL}/api/admin/b2b-leads/scrape`, scrapeForm, auth());
      setScrapeResult(res.data.message || 'Tarama tamamlandı.');
      loadMetaAndStats();
      loadLeads(1);
      setTimeout(() => {
        setScrapeModal(false);
        setScrapeResult('');
      }, 2500);
    } catch (e) {
      setScrapeResult(`Hata: ${e.response?.data?.detail || e.message}`);
    } finally {
      setScrapeBusy(false);
    }
  }

  // Excel / CSV İndir
  function handleExportCSV() {
    const params = new URLSearchParams();
    if (selectedCat) params.append('kategori', selectedCat);
    if (selectedIl) params.append('il', selectedIl);
    if (selectedIlce) params.append('ilce', selectedIlce);
    if (hasPhoneOnly) params.append('has_phone', 'true');
    if (hasInstagramOnly) params.append('has_instagram', 'true');
    if (searchQuery.trim()) params.append('q', searchQuery.trim());

    window.open(`${BACKEND_URL}/api/admin/b2b-leads/export?${params.toString()}`, '_blank');
  }

  return (
    <div className="space-y-6">
      {/* Üst Başlık & Aksiyonlar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 p-6 rounded-2xl text-white shadow-xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30">
              <Sparkles className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">B2B Hedef Kitle & Lead Toplayıcı</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1 max-w-2xl">
            Google Maps üzerinden güzellik merkezleri, nail stüdyoları, op. doktorlar, medikal estetik klinikleri, fizyoterapistler, hastaneler, kadın kuaförleri, saç ekimciler ve kalıcı makyaj stüdyolarını il il, ilçe ilçe tarayın.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-sm font-medium transition shadow-sm"
          >
            <Download className="w-4 h-4 text-emerald-400" />
            Excel / CSV İndir
          </button>
          <button
            onClick={() => setScrapeModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-indigo-600/30"
          >
            <Play className="w-4 h-4 fill-white" />
            Yeni Tarama Başlat
          </button>
        </div>
      </div>

      {/* İstatistik Özet Kartları */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Toplam Kayıtlı Lead</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{stats.total_leads.toLocaleString('tr-TR')}</p>
              <p className="text-xs text-slate-400 mt-0.5">Potansiyel B2B müşteri</p>
            </div>
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
              <Building2 className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Telefonu Olanlar</p>
              <p className="text-2xl font-bold text-emerald-600 mt-1">{stats.with_phone.toLocaleString('tr-TR')}</p>
              <p className="text-xs text-emerald-700/70 mt-0.5">%{stats.phone_rate} doğrulandı</p>
            </div>
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
              <Phone className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Instagram Tespit Edilen</p>
              <p className="text-2xl font-bold text-pink-600 mt-1">{stats.with_instagram.toLocaleString('tr-TR')}</p>
              <p className="text-xs text-pink-700/70 mt-0.5">%{stats.instagram_rate} profil bulundu</p>
            </div>
            <div className="p-3 bg-pink-50 text-pink-600 rounded-xl">
              <Instagram className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Web Sitesi Olanlar</p>
              <p className="text-2xl font-bold text-indigo-600 mt-1">{stats.with_website.toLocaleString('tr-TR')}</p>
              <p className="text-xs text-slate-400 mt-0.5">Kurumsal internet sitesi</p>
            </div>
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
              <Globe className="w-6 h-6" />
            </div>
          </div>
        </div>
      )}

      {/* Sektör Hızlı Seçici Rozetler */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          <Layers className="w-4 h-4 text-indigo-600" />
          <span>Sektör Filtresi (9 Ana Kategori)</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedCat('')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              selectedCat === ''
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            Tüm Sektörler ({stats ? stats.total_leads : 0})
          </button>
          {meta.categories.map(c => {
            const foundStat = (stats?.categories || []).find(s => s.key === c.id);
            const count = foundStat ? foundStat.count : 0;
            return (
              <button
                key={c.id}
                onClick={() => setSelectedCat(c.id === selectedCat ? '' : c.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                  selectedCat === c.id
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                }`}
              >
                <span>{c.label}</span>
                {count > 0 && (
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                    selectedCat === c.id ? 'bg-indigo-500 text-white' : 'bg-slate-200 text-slate-600'
                  }`}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* İl, İlçe ve Metin Arama Çubuğu */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
          {/* İl Seçimi */}
          <div className="w-44">
            <select
              value={selectedIl}
              onChange={e => {
                setSelectedIl(e.target.value);
                setSelectedIlce('');
              }}
              className="w-full border border-slate-200 rounded-lg p-2 text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="">Tüm İller (81 İl)</option>
              {meta.cities.map(c => (
                <option key={c.name} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* İlçe Seçimi */}
          <div className="w-44">
            <select
              value={selectedIlce}
              disabled={!selectedIl}
              onChange={e => setSelectedIlce(e.target.value)}
              className="w-full border border-slate-200 rounded-lg p-2 text-sm bg-white disabled:bg-slate-50 disabled:text-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="">{selectedIl ? 'Tüm İlçeler' : 'Önce İl Seçin'}</option>
              {availableDistricts.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Arama Kutusu */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="İşletme adı, adres, telefon veya instagram ara..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && loadLeads(1)}
              className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Hızlı Filtre Checkbox'ları */}
        <div className="flex items-center gap-4 text-xs font-medium text-slate-700">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={hasPhoneOnly}
              onChange={e => setHasPhoneOnly(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500"
            />
            <span>Sadece Telefonlu</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={hasInstagramOnly}
              onChange={e => setHasInstagramOnly(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500"
            />
            <span>Sadece Instagram'lı</span>
          </label>
          <button
            onClick={() => loadLeads(page)}
            disabled={loading}
            className="p-2 border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600"
            title="Yenile"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {err && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{err}</span>
        </div>
      )}

      {/* Lead Tablosu */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <p className="text-sm font-semibold text-slate-700">
            Bulunan İşletmeler ({total.toLocaleString('tr-TR')} sonuç)
          </p>
          <span className="text-xs text-slate-500">
            Sayfa {page} / {totalPages}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[11px] font-semibold border-b border-slate-200 tracking-wider">
              <tr>
                <th className="py-3 px-4">İşletme Adı</th>
                <th className="py-3 px-4">Sektör</th>
                <th className="py-3 px-4">İl / İlçe</th>
                <th className="py-3 px-4">Telefon</th>
                <th className="py-3 px-4">Instagram</th>
                <th className="py-3 px-4">Web Sitesi</th>
                <th className="py-3 px-4">Puan / Yorum</th>
                <th className="py-3 px-4 text-right">Harita</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan="8" className="text-center py-12 text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    <span>Veriler yükleniyor...</span>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-12 text-slate-400">
                    <Building2 className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p className="font-medium text-slate-600">Henüz bu filtreye uygun işletme bulunamadı.</p>
                    <p className="text-xs mt-1">"Yeni Tarama Başlat" butonuna tıklayarak Google Maps'ten anında veri toplayabilirsiniz.</p>
                  </td>
                </tr>
              ) : (
                leads.map(lead => (
                  <tr key={lead.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 leading-tight">{lead.name}</div>
                      <div className="text-xs text-slate-400 mt-0.5 line-clamp-1" title={lead.address}>
                        {lead.address || 'Adres bilgisi yok'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded-md text-xs font-medium">
                        {lead.kategori_label || lead.kategori_key}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="font-medium text-slate-800">{lead.ilce}</div>
                      <div className="text-xs text-slate-400">{lead.il}</div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {lead.phone ? (
                        <a
                          href={`tel:${lead.phone.replace(/\s+/g, '')}`}
                          className="flex items-center gap-1.5 text-emerald-600 hover:text-emerald-700 font-medium font-mono text-xs"
                        >
                          <Phone className="w-3.5 h-3.5" />
                          <span>{lead.phone}</span>
                        </a>
                      ) : (
                        <span className="text-slate-300 text-xs">-</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {lead.instagram_handle ? (
                        <a
                          href={lead.instagram_url || `https://www.instagram.com/${lead.instagram_handle.replace('@', '')}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-gradient-to-r from-pink-500/10 to-purple-500/10 hover:from-pink-500/20 hover:to-purple-500/20 text-pink-600 rounded-lg text-xs font-semibold border border-pink-200 transition"
                        >
                          <Instagram className="w-3 h-3 text-pink-500" />
                          <span>{lead.instagram_handle}</span>
                        </a>
                      ) : (
                        <span className="text-slate-300 text-xs">-</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {lead.website ? (
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 text-xs font-medium"
                          title={lead.website}
                        >
                          <Globe className="w-3.5 h-3.5" />
                          <span className="max-w-[120px] truncate">{lead.website.replace(/^https?:\/\/(www\.)?/, '')}</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      ) : (
                        <span className="text-slate-300 text-xs">-</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {lead.rating ? (
                        <div className="flex items-center gap-1 text-xs">
                          <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                          <span className="font-bold text-slate-800">{lead.rating}</span>
                          <span className="text-slate-400">({lead.reviews_count})</span>
                        </div>
                      ) : (
                        <span className="text-slate-300 text-xs">-</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      {lead.gmaps_url && (
                        <a
                          href={lead.gmaps_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg inline-block transition"
                          title="Google Maps'te Göster"
                        >
                          <MapPin className="w-4 h-4" />
                        </a>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Sayfalama Kontrolleri */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-slate-200 flex items-center justify-between">
            <button
              onClick={() => {
                const prev = Math.max(1, page - 1);
                loadLeads(prev);
              }}
              disabled={page <= 1}
              className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 disabled:opacity-40"
            >
              Önceki
            </button>
            <span className="text-xs text-slate-500">
              Sayfa {page} / {totalPages}
            </span>
            <button
              onClick={() => {
                const next = Math.min(totalPages, page + 1);
                loadLeads(next);
              }}
              disabled={page >= totalPages}
              className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 disabled:opacity-40"
            >
              Sonraki
            </button>
          </div>
        )}
      </div>

      {/* Yeni Tarama Başlat Modalı */}
      {scrapeModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 relative">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Play className="w-5 h-5 text-indigo-600" />
              Google Maps'ten Yeni Veri Tara
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Belirttiğiniz il, ilçe ve sektördeki tüm işletmeler Google Maps üzerinden anlık taranır, web sitelerinden Instagram hesapları ayıklanıp listeye eklenir.
            </p>

            <form onSubmit={handleStartScrape} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hedef Sektör</label>
                <select
                  value={scrapeForm.kategori}
                  onChange={e => setScrapeForm({ ...scrapeForm, kategori: e.target.value })}
                  className="w-full border border-slate-200 rounded-xl p-2.5 text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {meta.categories.map(c => (
                    <option key={c.id} value={c.id}>{c.label}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">İl</label>
                  <select
                    value={scrapeForm.il}
                    onChange={e => setScrapeForm({ ...scrapeForm, il: e.target.value, ilce: '' })}
                    className="w-full border border-slate-200 rounded-xl p-2.5 text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    {meta.cities.map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">İlçe</label>
                  <select
                    value={scrapeForm.ilce}
                    onChange={e => setScrapeForm({ ...scrapeForm, ilce: e.target.value })}
                    className="w-full border border-slate-200 rounded-xl p-2.5 text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="">İlçe Seçin</option>
                    {scrapeDistricts.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Sayfa Derinliği</label>
                <select
                  value={scrapeForm.pages}
                  onChange={e => setScrapeForm({ ...scrapeForm, pages: Number(e.target.value) })}
                  className="w-full border border-slate-200 rounded-xl p-2.5 text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value={1}>1 Sayfa (~20 işletme - Hızlı)</option>
                  <option value={2}>2 Sayfa (~40 işletme - Standart)</option>
                  <option value={3}>3 Sayfa (~60 işletme - Derin)</option>
                </select>
              </div>

              {scrapeResult && (
                <div className={`p-3 rounded-xl text-xs font-medium flex items-center gap-2 ${
                  scrapeResult.startsWith('Hata') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}>
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{scrapeResult}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  disabled={scrapeBusy}
                  onClick={() => setScrapeModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  disabled={scrapeBusy || !scrapeForm.ilce}
                  className="flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-medium disabled:opacity-50 transition shadow-lg shadow-indigo-600/20"
                >
                  {scrapeBusy ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Google Maps Taranıyor...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-white" />
                      <span>Taramayı Başlat</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
