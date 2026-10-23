import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  MapPin,
  Layers,
  Globe,
  Search,
  FileText,
  RefreshCw,
  Wand2,
  Copy,
  Download,
  ExternalLink,
  Laptop,
  Smartphone,
  Check,
  Zap,
  Tag,
  ArrowRight
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

export default function AutoSeoHub() {
  const [activeTab, setActiveTab] = useState("audit"); // audit, serp, local, matrix, schema
  const [loading, setLoading] = useState(false);
  const [fixing, setFixing] = useState(false);

  // Tab 1: Audit Data
  const [auditReport, setAuditReport] = useState(null);

  // Tab 2: SERP Simulator
  const [serpDevice, setSerpDevice] = useState("desktop");
  const [serpForm, setSerpForm] = useState({
    title: "Estoril Alpha Platinium Diode Buz Lazer Cihazı - Fiyatı & Satışı",
    description: "Estoril güvencesiyle 3 dalga boylu profesyonel diode buz lazer epilasyon cihazı. 2 Yıl Garanti, yerinde kurulum ve sertifikalı eğitim avantajıyla hemen inceleyin.",
    url: "https://estoril.com.tr/urun/alpha-platinium-diode-lazer"
  });
  const [serpAnalysis, setSerpAnalysis] = useState(null);
  const [singleGeneratorName, setSingleGeneratorName] = useState("");

  // Tab 3: Local SEO
  const [provinces, setProvinces] = useState([]);
  const [selectedProvSlug, setSelectedProvSlug] = useState("istanbul");
  const [selectedDistrict, setSelectedDistrict] = useState("");
  const [localPageData, setLocalPageData] = useState(null);
  const [localLoading, setLocalLoading] = useState(false);

  // Tab 4: Keyword Matrix
  const [matrixData, setMatrixData] = useState([]);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [matrixLocFilter, setMatrixLocFilter] = useState("Türkiye Geneli");

  // Tab 5: Schema.org
  const [schemaType, setSchemaType] = useState("product");
  const [schemaJson, setSchemaJson] = useState("");
  const [copied, setCopied] = useState(false);

  // Load Initial Audit & Local Data
  useEffect(() => {
    fetchAudit();
    fetchProvinces();
    analyzeSerp(serpForm.title, serpForm.description, serpForm.url);
    fetchSchema("product");
  }, []);

  // Fetch Audit
  const fetchAudit = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/admin/auto-seo/audit`, { headers: authHeaders() });
      if (res.data?.success) {
        setAuditReport(res.data.report);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "SEO denetimi yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  // Run Auto-Fix All
  const handleFixAll = async () => {
    if (!window.confirm("Katalogdaki tüm eksik SEO başlıkları, açıklamaları ve görsel ALT etiketleri otomatik olarak optimize edilsin mi?")) return;
    setFixing(true);
    try {
      const res = await axios.post(`${API}/admin/auto-seo/fix-all`, {}, { headers: authHeaders() });
      if (res.data?.success) {
        toast.success(res.data.message || "Tüm ürünler başarıyla optimize edildi!");
        fetchAudit();
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Oto-düzeltme sırasında hata oluştu");
    } finally {
      setFixing(false);
    }
  };

  // Analyze SERP
  const analyzeSerp = async (title, desc, url) => {
    try {
      const res = await axios.post(`${API}/admin/auto-seo/serp-preview`, {
        title,
        description: desc,
        url
      }, { headers: authHeaders() });
      if (res.data?.success) {
        setSerpAnalysis(res.data.analysis);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Quick single generate
  const handleSingleGenerate = async () => {
    if (!singleGeneratorName.trim()) return toast.warning("Lütfen bir ürün veya konu adı girin");
    try {
      const res = await axios.post(`${API}/admin/auto-seo/generate-single`, {
        name: singleGeneratorName
      }, { headers: authHeaders() });
      if (res.data?.success) {
        setSerpForm({
          ...serpForm,
          title: res.data.title,
          description: res.data.description
        });
        setSerpAnalysis(res.data.analysis);
        toast.success("SEO Meta başarıyla türetildi!");
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Meta türetilemedi");
    }
  };

  // Fetch Provinces
  const fetchProvinces = async () => {
    try {
      const res = await axios.get(`${API}/admin/auto-seo/local-provinces`, { headers: authHeaders() });
      if (res.data?.success) {
        setProvinces(res.data.provinces || []);
        loadLocalPage("istanbul");
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Load Local Page Data
  const loadLocalPage = async (provSlug, dist = "") => {
    setLocalLoading(true);
    try {
      const res = await axios.get(`${API}/admin/auto-seo/local-page`, {
        params: { province_slug: provSlug, district: dist || undefined },
        headers: authHeaders()
      });
      if (res.data?.success) {
        setLocalPageData(res.data.page);
      }
    } catch (e) {
      toast.error("Yerel SEO sayfası yüklenemedi");
    } finally {
      setLocalLoading(false);
    }
  };

  // Generate Keyword Matrix
  const handleGenerateMatrix = async () => {
    setMatrixLoading(true);
    try {
      const res = await axios.post(`${API}/admin/auto-seo/keyword-matrix`, {
        locations: [matrixLocFilter]
      }, { headers: authHeaders() });
      if (res.data?.success) {
        setMatrixData(res.data.items || []);
        toast.success(`${res.data.total} adet anahtar kelime kombinasyonu üretildi!`);
      }
    } catch (e) {
      toast.error("Matris üretilemedi");
    } finally {
      setMatrixLoading(false);
    }
  };

  // Export Matrix to CSV
  const exportMatrixCSV = () => {
    if (matrixData.length === 0) return toast.warning("Dışa aktarılacak veri yok");
    const headers = ["Anahtar Kelime", "Lokasyon", "Ürün", "Niyet", "Niyet Türü", "Önerilen Slug", "Önerilen Başlık"];
    const rows = matrixData.map(m => [
      `"${m.keyword}"`,
      `"${m.location}"`,
      `"${m.product}"`,
      `"${m.intent}"`,
      `"${m.intent_type}"`,
      `"${m.suggested_slug}"`,
      `"${m.suggested_title}"`
    ]);
    const csvContent = "\uFEFF" + [headers.join(";"), ...rows.map(r => r.join(";"))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `estoril_anahtar_kelime_matrisi_${matrixLocFilter.toLowerCase().replace(/[^a-z0-9]/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Fetch Schema
  const fetchSchema = async (type) => {
    setSchemaType(type);
    try {
      const res = await axios.get(`${API}/admin/auto-seo/schema-preview`, {
        params: { schema_type: type, province_slug: selectedProvSlug },
        headers: authHeaders()
      });
      if (res.data?.success) {
        setSchemaJson(res.data.json_ld_string);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Panoya kopyalandı");
    setTimeout(() => setCopied(false), 2000);
  };

  // Current selected province object
  const currentProv = provinces.find(p => p.slug === selectedProvSlug) || provinces[0];

  return (
    <div className="space-y-6 pb-12" data-testid="auto-seo-hub">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 shadow-xl border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <Sparkles size={12} /> Açık Kaynak Auto-SEO Motoru v2.0
              </span>
              <span className="text-xs text-slate-400">| Advertools + AEO + Programmatic SEO</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Estoril Otomatik SEO Komuta Merkezi</h1>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl">
              Medikal estetik ve güzellik cihazları kataloğunuz için 81 İl Yerel SEO iniş sayfaları, canlı SERP simülatörü, Schema.org zengin verileri ve tek tıkla teknik SEO iyileştirmesi.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={fetchAudit}
              disabled={loading}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-medium flex items-center gap-2 transition"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              Denetimi Yenile
            </button>
            <button
              onClick={handleFixAll}
              disabled={fixing}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-lg shadow-emerald-900/30 transition"
            >
              <Wand2 size={15} className={fixing ? "animate-spin" : ""} />
              {fixing ? "Optimize Ediliyor..." : "Tek Tıkla Kataloğu Düzelt"}
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 overflow-x-auto mt-6 pt-4 border-t border-slate-800/80">
          {[
            { id: "audit", label: "Teknik SEO & Sağlık Skoru", icon: CheckCircle2, badge: auditReport?.health_score ? `%${auditReport.health_score}` : null },
            { id: "serp", label: "Canlı SERP & Meta Simülatörü", icon: Search },
            { id: "local", label: "81 İl Yerel SEO Motoru", icon: MapPin, badge: "81 İl" },
            { id: "matrix", label: "Programmatik Kelime Matrisi", icon: Layers },
            { id: "schema", label: "Schema.org (JSON-LD)", icon: Globe }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-xl text-xs font-medium flex items-center gap-2 whitespace-nowrap transition ${
                  isActive
                    ? "bg-white text-slate-900 shadow-md font-semibold"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <Icon size={14} className={isActive ? "text-indigo-600" : ""} />
                {tab.label}
                {tab.badge && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    isActive ? "bg-indigo-100 text-indigo-700 font-bold" : "bg-slate-800 text-slate-300"
                  }`}>
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SEKME 1: TEKNİK SEO DENETİMİ (SITE AUDIT) */}
      {/* ========================================================================= */}
      {activeTab === "audit" && (
        <div className="space-y-6">
          {/* Health Score & Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Health Score Gauge */}
            <div className="bg-white rounded-2xl border p-5 shadow-sm flex items-center gap-4">
              <div className="relative w-20 h-20 flex-shrink-0 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                  <path
                    className="text-gray-100"
                    strokeWidth="3.5"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className={
                      (auditReport?.health_score || 0) >= 80 ? "text-emerald-500" :
                      (auditReport?.health_score || 0) >= 50 ? "text-amber-500" : "text-rose-500"
                    }
                    strokeDasharray={`${auditReport?.health_score || 0}, 100`}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <span className="absolute text-xl font-extrabold text-slate-800">
                  %{auditReport?.health_score || 0}
                </span>
              </div>
              <div>
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">SEO Sağlık Skoru</div>
                <div className="text-sm font-bold text-slate-800 mt-0.5">
                  {(auditReport?.health_score || 0) >= 80 ? "Mükemmel Durum" :
                   (auditReport?.health_score || 0) >= 50 ? "İyileştirme Gerekli" : "Kritik Eksikler Var"}
                </div>
                <div className="text-[11px] text-gray-400 mt-1">
                  Toplam {auditReport?.total_products || 0} ürün incelendi
                </div>
              </div>
            </div>

            {/* Missing Titles */}
            <div className="bg-white rounded-2xl border p-5 shadow-sm">
              <div className="flex items-center justify-between text-gray-500 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider">Eksik Başlık (Title)</span>
                <AlertCircle size={16} className={auditReport?.metrics?.missing_titles ? "text-rose-500" : "text-emerald-500"} />
              </div>
              <div className="text-2xl font-bold text-slate-800">{auditReport?.metrics?.missing_titles || 0}</div>
              <div className="text-[11px] text-gray-400 mt-1">Arama motorlarında görünmeyen başlıklar</div>
            </div>

            {/* Missing Descriptions */}
            <div className="bg-white rounded-2xl border p-5 shadow-sm">
              <div className="flex items-center justify-between text-gray-500 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider">Eksik Açıklama (Meta)</span>
                <AlertTriangle size={16} className={auditReport?.metrics?.missing_descriptions ? "text-amber-500" : "text-emerald-500"} />
              </div>
              <div className="text-2xl font-bold text-slate-800">{auditReport?.metrics?.missing_descriptions || 0}</div>
              <div className="text-[11px] text-gray-400 mt-1">SERP snippet tıklama oranını düşürür</div>
            </div>

            {/* Missing Alt Tags */}
            <div className="bg-white rounded-2xl border p-5 shadow-sm">
              <div className="flex items-center justify-between text-gray-500 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider">Eksik Görsel ALT</span>
                <Tag size={16} className={auditReport?.metrics?.missing_alts ? "text-amber-500" : "text-emerald-500"} />
              </div>
              <div className="text-2xl font-bold text-slate-800">{auditReport?.metrics?.missing_alts || 0}</div>
              <div className="text-[11px] text-gray-400 mt-1">Google Görseller arama kaybı</div>
            </div>
          </div>

          {/* Quick Auto-Fix Callout Banner */}
          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-md">
                <Zap size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-emerald-950">Otomatik SEO Güçlendirici (Tek Tık Çözüm)</h3>
                <p className="text-xs text-emerald-800 mt-0.5 max-w-xl">
                  Eksik olan tüm başlıkları Estoril B2B kurallarına uygun olarak <b>"[Ürün Adı] - Fiyatı & Satışı | Estoril"</b> şeklinde doldurur, 150 karakterlik yüksek dönüşümlü açıklamalar ve görsel ALT etiketleri üretir.
                </p>
              </div>
            </div>
            <button
              onClick={handleFixAll}
              disabled={fixing}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 shadow transition whitespace-nowrap"
            >
              <Wand2 size={14} className={fixing ? "animate-spin" : ""} />
              {fixing ? "Uygulanıyor..." : "Tüm Kataloğu Otomatik Düzelt"}
            </button>
          </div>

          {/* Issues List Table */}
          <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-800">Tespit Edilen SEO Eksikleri & Öneriler</h3>
                <p className="text-xs text-gray-500 mt-0.5">Python-SEO-Analyzer algoritması tarafından işaretlenen sorunlar</p>
              </div>
              <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-lg font-medium">
                {auditReport?.issues_count || 0} Sorun Bulundu
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold uppercase border-b">
                  <tr>
                    <th className="text-left p-3.5">Önem</th>
                    <th className="text-left p-3.5">Ürün / Sayfa</th>
                    <th className="text-left p-3.5">Hata Kodu</th>
                    <th className="text-left p-3.5">Açıklama & Düzeltme Önerisi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(!auditReport?.issues || auditReport.issues.length === 0) ? (
                    <tr>
                      <td colSpan={4} className="p-8 text-center text-gray-400">
                        <CheckCircle2 size={32} className="mx-auto mb-2 text-emerald-500" />
                        Harika! Katalogda hiçbir kritik teknik SEO hatası bulunmuyor.
                      </td>
                    </tr>
                  ) : (
                    auditReport.issues.map((iss, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/60 transition">
                        <td className="p-3.5 whitespace-nowrap">
                          {iss.type === "error" ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700">Kritik</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700">Uyarı</span>
                          )}
                        </td>
                        <td className="p-3.5 font-medium text-slate-800 max-w-[200px] truncate">
                          {iss.product_name}
                        </td>
                        <td className="p-3.5 font-mono text-[11px] text-slate-500">
                          {iss.code}
                        </td>
                        <td className="p-3.5 text-slate-600">
                          {iss.message}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SEKME 2: CANLI SERP SİMÜLATÖRÜ & META ÜRETİCİ */}
      {/* ========================================================================= */}
      {activeTab === "serp" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sol Kolon: Girdi ve Hızlı Üretici */}
          <div className="lg:col-span-5 space-y-5">
            {/* Quick Generator Box */}
            <div className="bg-white rounded-2xl border p-5 shadow-sm space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                <Wand2 size={15} className="text-indigo-600" />
                Hızlı SEO Meta Üretici
              </div>
              <p className="text-xs text-gray-500">
                Ürün veya konu adını girin; Advertools ve Estoril standartlarına göre mükemmel başlık ve açıklama üretilsin.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={singleGeneratorName}
                  onChange={(e) => setSingleGeneratorName(e.target.value)}
                  placeholder="Örn: Diyot Lazer Epilasyon Cihazı"
                  className="flex-1 px-3 py-2 border rounded-xl text-xs focus:ring-2 focus:ring-black outline-none"
                />
                <button
                  onClick={handleSingleGenerate}
                  className="px-4 py-2 bg-slate-900 hover:bg-black text-white rounded-xl text-xs font-semibold transition"
                >
                  Üret
                </button>
              </div>
            </div>

            {/* Inputs & Character/Pixel Meters */}
            <div className="bg-white rounded-2xl border p-5 shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Snippet Ayarları</h3>

              <div>
                <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                  <label className="font-medium">SEO Başlığı (Meta Title)</label>
                  <span className={`text-[11px] font-mono font-semibold ${
                    (serpAnalysis?.title?.length || 0) > 60 ? "text-rose-600" : "text-emerald-600"
                  }`}>
                    {serpForm.title.length}/60 kr ({int(serpAnalysis?.title?.pixel_width || 0)}/600 px)
                  </span>
                </div>
                <input
                  type="text"
                  value={serpForm.title}
                  onChange={(e) => {
                    setSerpForm({ ...serpForm, title: e.target.value });
                    analyzeSerp(e.target.value, serpForm.description, serpForm.url);
                  }}
                  className="w-full px-3 py-2 border rounded-xl text-xs font-medium focus:ring-2 focus:ring-black outline-none"
                />
                {serpAnalysis?.title?.warning && (
                  <p className="text-[11px] text-amber-600 mt-1 flex items-center gap-1">
                    <AlertTriangle size={12} /> {serpAnalysis.title.warning}
                  </p>
                )}
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                  <label className="font-medium">SEO Açıklaması (Meta Description)</label>
                  <span className={`text-[11px] font-mono font-semibold ${
                    (serpAnalysis?.description?.length || 0) > 160 ? "text-rose-600" : "text-emerald-600"
                  }`}>
                    {serpForm.description.length}/160 kr ({int(serpAnalysis?.description?.pixel_width || 0)}/960 px)
                  </span>
                </div>
                <textarea
                  rows={3}
                  value={serpForm.description}
                  onChange={(e) => {
                    setSerpForm({ ...serpForm, description: e.target.value });
                    analyzeSerp(serpForm.title, e.target.value, serpForm.url);
                  }}
                  className="w-full px-3 py-2 border rounded-xl text-xs font-medium focus:ring-2 focus:ring-black outline-none"
                />
                {serpAnalysis?.description?.warning && (
                  <p className="text-[11px] text-amber-600 mt-1 flex items-center gap-1">
                    <AlertTriangle size={12} /> {serpAnalysis.description.warning}
                  </p>
                )}
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Hedef URL</label>
                <input
                  type="text"
                  value={serpForm.url}
                  onChange={(e) => {
                    setSerpForm({ ...serpForm, url: e.target.value });
                    analyzeSerp(serpForm.title, serpForm.description, e.target.value);
                  }}
                  className="w-full px-3 py-2 border rounded-xl text-xs font-mono text-gray-600 focus:ring-2 focus:ring-black outline-none"
                />
              </div>
            </div>
          </div>

          {/* Sağ Kolon: Google Canlı SERP Mockup */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-white rounded-2xl border p-6 shadow-sm">
              <div className="flex items-center justify-between pb-4 border-b mb-5">
                <div className="flex items-center gap-2">
                  <Search size={16} className="text-blue-600" />
                  <span className="text-sm font-bold text-slate-800">Google Arama Sonucu Önizlemesi</span>
                </div>
                {/* Device Switcher */}
                <div className="flex bg-slate-100 p-1 rounded-xl text-xs font-medium">
                  <button
                    onClick={() => setSerpDevice("desktop")}
                    className={`px-3 py-1 rounded-lg flex items-center gap-1.5 transition ${
                      serpDevice === "desktop" ? "bg-white text-slate-900 shadow-sm" : "text-gray-500 hover:text-gray-800"
                    }`}
                  >
                    <Laptop size={13} /> Masaüstü
                  </button>
                  <button
                    onClick={() => setSerpDevice("mobile")}
                    className={`px-3 py-1 rounded-lg flex items-center gap-1.5 transition ${
                      serpDevice === "mobile" ? "bg-white text-slate-900 shadow-sm" : "text-gray-500 hover:text-gray-800"
                    }`}
                  >
                    <Smartphone size={13} /> Mobil
                  </button>
                </div>
              </div>

              {/* SERP Rendering Container */}
              {serpDevice === "desktop" ? (
                /* Desktop Preview */
                <div className="p-6 bg-slate-50/50 rounded-xl border border-slate-200/80 font-sans max-w-[650px]">
                  {/* Google Breadcrumb */}
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className="w-5 h-5 rounded-full bg-slate-900 flex items-center justify-center text-[10px] text-white font-bold">
                      E
                    </div>
                    <div>
                      <div className="text-[12px] text-slate-800 font-medium leading-none">Estoril Dış Ticaret</div>
                      <div className="text-[11px] text-slate-500 font-normal leading-none mt-0.5">{serpForm.url}</div>
                    </div>
                  </div>
                  {/* Title */}
                  <h3 className="text-[19px] text-[#1a0dab] hover:underline cursor-pointer font-normal leading-snug tracking-tight">
                    {serpAnalysis?.desktop_preview?.title || serpForm.title}
                  </h3>
                  {/* Snippet */}
                  <p className="text-[13px] text-[#4d5156] mt-1.5 leading-relaxed font-normal">
                    {serpAnalysis?.desktop_preview?.description || serpForm.description}
                  </p>
                </div>
              ) : (
                /* Mobile Preview */
                <div className="p-4 bg-slate-50/50 rounded-2xl border border-slate-200/80 font-sans max-w-[380px] mx-auto shadow-sm">
                  {/* Mobile Google Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-slate-900 flex items-center justify-center text-[11px] text-white font-bold">
                      E
                    </div>
                    <div className="min-w-0">
                      <div className="text-[12px] text-slate-800 font-medium truncate">Estoril</div>
                      <div className="text-[10px] text-slate-500 truncate">{serpForm.url}</div>
                    </div>
                  </div>
                  {/* Title */}
                  <h3 className="text-[17px] text-[#1a0dab] font-normal leading-snug tracking-tight">
                    {serpAnalysis?.mobile_preview?.title || serpForm.title}
                  </h3>
                  {/* Snippet */}
                  <p className="text-[12px] text-[#4d5156] mt-1.5 leading-relaxed">
                    {serpAnalysis?.mobile_preview?.description || serpForm.description}
                  </p>
                </div>
              )}

              {/* SERP Guidelines box */}
              <div className="mt-6 pt-4 border-t grid grid-cols-2 gap-4 text-xs text-gray-500">
                <div className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                  <span>Google masaüstü başlık piksel sınırı: <b>600 px</b> (Mevcut: ~{int(serpAnalysis?.title?.pixel_width || 0)} px)</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                  <span>Google açıklama piksel sınırı: <b>960 px</b> (Mevcut: ~{int(serpAnalysis?.description?.pixel_width || 0)} px)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SEKME 3: 81 İL YEREL SEO MOTORU (PROGRAMMATIC SEO) */}
      {/* ========================================================================= */}
      {activeTab === "local" && (
        <div className="space-y-6">
          {/* Controls: Province and District Selector */}
          <div className="bg-white rounded-2xl border p-5 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full md:w-auto">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0">
                <MapPin size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800">Yerel SEO İniş Sayfası Seçicisi</h3>
                <p className="text-xs text-gray-500">81 il ve ilçeler için dinamik pSEO içerik ve şema üretimi</p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 w-full md:w-auto flex-wrap">
              {/* Province Selector */}
              <select
                value={selectedProvSlug}
                onChange={(e) => {
                  setSelectedProvSlug(e.target.value);
                  setSelectedDistrict("");
                  loadLocalPage(e.target.value, "");
                }}
                className="px-3 py-2 border rounded-xl text-xs font-semibold bg-white outline-none focus:ring-2 focus:ring-black min-w-[160px]"
              >
                {provinces.map(p => (
                  <option key={p.slug} value={p.slug}>{p.code} - {p.name} ({p.region})</option>
                ))}
              </select>

              {/* District Selector */}
              <select
                value={selectedDistrict}
                onChange={(e) => {
                  setSelectedDistrict(e.target.value);
                  loadLocalPage(selectedProvSlug, e.target.value);
                }}
                className="px-3 py-2 border rounded-xl text-xs font-semibold bg-white outline-none focus:ring-2 focus:ring-black min-w-[140px]"
              >
                <option value="">Tüm İl Geneli</option>
                {(currentProv?.districts || []).map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>

              <a
                href={`${process.env.REACT_APP_BACKEND_URL}/sitemap-cities.xml`}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium flex items-center gap-1.5 transition"
              >
                <ExternalLink size={13} />
                sitemap-cities.xml
              </a>
            </div>
          </div>

          {/* Local Page Preview Card */}
          {localPageData && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Metadata & SERP */}
              <div className="lg:col-span-6 space-y-5">
                <div className="bg-white rounded-2xl border p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b">
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Yerel Meta Verileri</span>
                    <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2.5 py-0.5 rounded-full">
                      Google Uyumlu
                    </span>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase block mb-1">SEO Title</label>
                    <div className="p-3 bg-slate-50 rounded-xl text-xs font-medium text-slate-800 border">
                      {localPageData.seo_title}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase block mb-1">Meta Description</label>
                    <div className="p-3 bg-slate-50 rounded-xl text-xs text-slate-700 border leading-relaxed">
                      {localPageData.seo_description}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase block mb-1">Kanonik URL & Slug</label>
                    <div className="p-3 bg-slate-50 rounded-xl text-xs font-mono text-indigo-700 border">
                      {localPageData.canonical_url}
                    </div>
                  </div>

                  {/* SERP Snippet Preview */}
                  <div className="pt-2">
                    <label className="text-[11px] font-semibold text-gray-500 uppercase block mb-2">Google Görünümü</label>
                    <div className="p-4 bg-slate-50 rounded-xl border font-sans text-xs">
                      <div className="text-[#1a0dab] font-medium text-sm hover:underline">{localPageData.seo_title}</div>
                      <div className="text-emerald-700 text-[11px] mt-0.5">{localPageData.canonical_url}</div>
                      <div className="text-gray-600 text-xs mt-1 leading-snug">{localPageData.seo_description}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Dynamic Content & FAQ Accordion */}
              <div className="lg:col-span-6 space-y-5">
                <div className="bg-white rounded-2xl border p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b">
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">İçerik Şablonu (H1 & Tanıtım)</span>
                    <span className="text-xs text-gray-400">Otomatik pSEO</span>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase block mb-1">Sayfa H1 Başlığı</label>
                    <h2 className="text-base font-bold text-slate-900 bg-indigo-50/50 p-3 rounded-xl border border-indigo-100">
                      {localPageData.h1}
                    </h2>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase block mb-1">Yerel Değer Önerisi (Hero Text)</label>
                    <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-xl border">
                      {localPageData.intro_content}
                    </p>
                  </div>

                  {/* Regional FAQs */}
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase block mb-2">
                      Sıkça Sorulan Sorular (Google FAQPage Schema)
                    </label>
                    <div className="space-y-2">
                      {localPageData.faqs.map((f, i) => (
                        <div key={i} className="border rounded-xl p-3 bg-slate-50/40">
                          <div className="font-semibold text-xs text-slate-800 flex items-center gap-2">
                            <span className="text-indigo-600 font-bold">S:</span> {f.q}
                          </div>
                          <div className="text-xs text-slate-600 mt-1 pl-4 leading-relaxed">
                            {f.a}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SEKME 4: PROGRAMMATİK ANAHTAR KELİME MATRİSİ (ADVERTOOLS) */}
      {/* ========================================================================= */}
      {activeTab === "matrix" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border p-5 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center flex-shrink-0">
                <Layers size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800">Advertools Anahtar Kelime Matrisi Motoru</h3>
                <p className="text-xs text-gray-500">Ürünler, Satın Alma Niyetleri ve Lokasyonları permütasyonla birleştirir</p>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <select
                value={matrixLocFilter}
                onChange={(e) => setMatrixLocFilter(e.target.value)}
                className="px-3 py-2 border rounded-xl text-xs font-semibold bg-white outline-none focus:ring-2 focus:ring-black"
              >
                <option value="Türkiye Geneli">Türkiye Geneli</option>
                <option value="İstanbul">İstanbul</option>
                <option value="Ankara">Ankara</option>
                <option value="İzmir">İzmir</option>
                <option value="Bursa">Bursa</option>
                <option value="Antalya">Antalya</option>
                <option value="Adana">Adana</option>
                <option value="Gaziantep">Gaziantep</option>
              </select>

              <button
                onClick={handleGenerateMatrix}
                disabled={matrixLoading}
                className="px-4 py-2 bg-slate-900 hover:bg-black text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition"
              >
                <RefreshCw size={14} className={matrixLoading ? "animate-spin" : ""} />
                Matrisi Üret
              </button>

              <button
                onClick={exportMatrixCSV}
                disabled={matrixData.length === 0}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50"
              >
                <Download size={14} />
                Excel (CSV) İndir
              </button>
            </div>
          </div>

          {/* Matrix Results Table */}
          <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800">
                Üretilen Hedef Kelimeler ({matrixData.length} Adet)
              </span>
              <span className="text-xs text-gray-400">Google Ads & SEO İniş Sayfaları İçin Hazır</span>
            </div>

            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold uppercase sticky top-0 border-b">
                  <tr>
                    <th className="text-left p-3.5">Hedef Anahtar Kelime</th>
                    <th className="text-left p-3.5">Lokasyon</th>
                    <th className="text-left p-3.5">Niyet Türü</th>
                    <th className="text-left p-3.5">Önerilen Başlık (Title)</th>
                    <th className="text-left p-3.5">Hedef URL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {matrixData.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-gray-400">
                        Henüz matris üretilmedi. Yukarıdaki "Matrisi Üret" butonuna basarak kombinasyonları listeleyebilirsiniz.
                      </td>
                    </tr>
                  ) : (
                    matrixData.map((m, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/60 transition">
                        <td className="p-3.5 font-semibold text-slate-900">{m.keyword}</td>
                        <td className="p-3.5 text-slate-600">{m.location}</td>
                        <td className="p-3.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                            m.intent_type.includes("Satın Alma") ? "bg-emerald-100 text-emerald-800" :
                            m.intent_type.includes("Ticari") ? "bg-indigo-100 text-indigo-800" : "bg-slate-100 text-slate-700"
                          }`}>
                            {m.intent_type}
                          </span>
                        </td>
                        <td className="p-3.5 text-slate-700 max-w-[220px] truncate">{m.suggested_title}</td>
                        <td className="p-3.5 font-mono text-[11px] text-blue-600">{m.suggested_slug}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SEKME 5: SCHEMA.ORG (JSON-LD) CANLI ÖNİZLEME */}
      {/* ========================================================================= */}
      {activeTab === "schema" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border p-5 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Google Rich Results & AEO Schema.org (JSON-LD)</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Google, Perplexity ve ChatGPT yapay zeka arama motorları için yapılandırılmış veri şemaları
              </p>
            </div>

            <div className="flex items-center gap-2">
              {[
                { id: "product", label: "Product & MedicalDevice" },
                { id: "local", label: "MedicalBusiness (Yerel)" },
                { id: "faq", label: "FAQPage (Sıkça Sorulanlar)" }
              ].map(s => (
                <button
                  key={s.id}
                  onClick={() => fetchSchema(s.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition ${
                    schemaType === s.id ? "bg-black text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* JSON-LD Code Box */}
          <div className="bg-slate-900 rounded-2xl p-5 shadow-xl border border-slate-800 relative">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500" />
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-xs font-mono text-slate-400 ml-2">&lt;script type="application/ld+json"&gt;</span>
              </div>
              <button
                onClick={() => copyToClipboard(schemaJson)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                {copied ? "Kopyalandı!" : "Kodu Kopyala"}
              </button>
            </div>

            <pre className="font-mono text-xs text-emerald-400 overflow-x-auto max-h-[450px] p-2 leading-relaxed">
              {schemaJson || "// Yükleniyor..."}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

function int(val) {
  return Math.round(Number(val) || 0);
}
