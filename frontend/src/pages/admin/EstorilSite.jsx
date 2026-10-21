import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Save, Plus, Trash2, UploadCloud, Monitor, Smartphone, ChevronDown, ChevronUp } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/* Görsel alanı: sürükle-bırak, tek slot */
function ImageSlot({ label, icon: Icon, url, onChange }) {
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);

  const upload = useCallback(async (file) => {
    if (!file || !file.type.startsWith("image/")) return toast.error("Sadece görsel dosyası");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const token = localStorage.getItem("token");
      const res = await axios.post(`${API}/upload/image`, fd, {
        headers: { Authorization: `Bearer ${token}` },
      });
      onChange(res.data.url);
      toast.success(`${label} görseli yüklendi`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Yükleme başarısız");
    } finally {
      setBusy(false);
    }
  }, [label, onChange]);

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-1.5 text-xs font-medium text-gray-600 mb-1">
        <Icon size={13} /> {label}
      </div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files[0]); }}
        onClick={() => {
          const inp = document.createElement("input");
          inp.type = "file"; inp.accept = "image/*";
          inp.onchange = () => upload(inp.files[0]);
          inp.click();
        }}
        className={`relative aspect-video rounded-lg border-2 border-dashed cursor-pointer overflow-hidden flex items-center justify-center bg-gray-50 transition-colors ${drag ? "border-black bg-gray-100" : "border-gray-300 hover:border-gray-400"}`}
      >
        {url ? (
          <img src={url} alt={label} className="absolute inset-0 w-full h-full object-cover" />
        ) : (
          <div className="text-center text-gray-400 text-xs px-2">
            <UploadCloud size={20} className="mx-auto mb-1" />
            Sürükle ya da tıkla
          </div>
        )}
        {busy && <div className="absolute inset-0 bg-white/70 flex items-center justify-center text-xs font-medium">Yükleniyor…</div>}
      </div>
      {url && (
        <button onClick={() => onChange("")} className="text-[11px] text-red-500 hover:underline mt-1">Görseli kaldır</button>
      )}
    </div>
  );
}

/* img alanı { desktop, mobile } objesi */
function ImagePair({ value, onChange }) {
  const v = (value && typeof value === "object") ? value : { desktop: value || "", mobile: "" };
  return (
    <div className="flex gap-3">
      <ImageSlot label="Masaüstü" icon={Monitor} url={v.desktop} onChange={(u) => onChange({ ...v, desktop: u })} />
      <ImageSlot label="Mobil" icon={Smartphone} url={v.mobile} onChange={(u) => onChange({ ...v, mobile: u })} />
    </div>
  );
}

function Field({ label, value, onChange, textarea }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {textarea ? (
        <textarea value={value || ""} onChange={(e) => onChange(e.target.value)} rows={3}
          className="w-full border px-3 py-2 rounded text-sm" />
      ) : (
        <input type="text" value={value || ""} onChange={(e) => onChange(e.target.value)}
          className="w-full border px-3 py-2 rounded text-sm" />
      )}
    </div>
  );
}

function Card({ title, children, onDelete, onMove }) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm">{title}</span>
        <div className="flex gap-1">
          {onMove && <>
            <button onClick={() => onMove(-1)} className="p-1 text-gray-400 hover:text-black"><ChevronUp size={15} /></button>
            <button onClick={() => onMove(1)} className="p-1 text-gray-400 hover:text-black"><ChevronDown size={15} /></button>
          </>}
          {onDelete && <button onClick={onDelete} className="p-1 text-red-400 hover:text-red-600"><Trash2 size={15} /></button>}
        </div>
      </div>
      {children}
    </div>
  );
}

const TABS = [
  { key: "home", label: "Ana Sayfa" },
  { key: "lazer", label: "Lazer Kategori Slider" },
  { key: "alpha", label: "Alpha Tanıtım Sayfası" },
  { key: "products", label: "Ürünler" },
];

const DEFAULT_DISCOVERY = [{"name": "Kalıcı Makyaj", "href": "/kategori/kalici-makyaj", "img": "/uploads/editorial/pmu-context.png"}, {"name": "Cilt Bakım Cihazları", "href": "/kategori/cilt-bakim-cihazlari", "img": "/uploads/editorial/skincare-context.png"}, {"name": "Cilt Tedavi Cihazları", "href": "/kategori/cilt-tedavi-cihazlari", "img": "/uploads/editorial/treatment-context.png"}, {"name": "Salon Ekipmanları", "href": "/kategori/salon-ekipmanlari", "img": "/uploads/editorial/equipment-context.png"}, {"name": "Salon Mobilya", "href": "/kategori/salon-mobilya", "img": "/uploads/editorial/furniture-context.png"}, {"name": "Zayıflama Sistemleri", "href": "/kategori/zayiflama-sistemleri", "img": "/uploads/editorial/bodycare-context.png"}, {"name": "Lazer Epilasyon Sistemleri", "href": "/kategori/lazer-epilasyon-sistemleri", "img": "/uploads/editorial/laser-context.png"}, {"name": "İpek Kirpik", "href": "/kategori/ipek-kirpik", "img": "/uploads/editorial/lashes-context.png"}, {"name": "Kirpik Lifting", "href": "/kategori/kirpik-lifting", "img": "/uploads/editorial/lifting-context.png"}, {"name": "Jilong Pigment", "href": "/kategori/jilong-pigment", "img": "/uploads/editorial/pigment-context.png"}];

const LAZER_PATH = ["categoryPages", "Lazer Epilasyon Sistemleri", "heroSlides"];

export default function EstorilSite() {
  const [dragCategory, setDragCategory] = useState(null);
  const [tab, setTab] = useState("home");
  const [content, setContent] = useState(null);
  const [products, setProducts] = useState([]);
  const [saving, setSaving] = useState(false);
  const [q, setQ] = useState("");
  const [openIdx, setOpenIdx] = useState(null);
  const token = localStorage.getItem("token");
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    axios.get(`${API}/estoril/site-content`).then((r) => setContent(r.data)).catch(() => toast.error("site-content.json okunamadı — ESTORIL_SITE_DIR ayarlı mı?"));
    axios.get(`${API}/estoril/products`).then((r) => setProducts(r.data || [])).catch(() => {});
  }, []);

  const saveContent = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/estoril/site-content`, content, auth);
      toast.success("Site içeriği kaydedildi — vitrin anında güncellendi");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Kaydedilemedi");
    } finally { setSaving(false); }
  };

  const saveProducts = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/estoril/products`, products, auth);
      toast.success("Ürünler kaydedildi");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Kaydedilemedi");
    } finally { setSaving(false); }
  };

  const set = (path, val) => {
    setContent((c) => {
      const next = structuredClone(c);
      let o = next;
      for (let i = 0; i < path.length - 1; i++) {
        if (o[path[i]] == null) o[path[i]] = typeof path[i + 1] === "number" ? [] : {};
        o = o[path[i]];
      }
      o[path[path.length - 1]] = val;
      return next;
    });
  };

  const moveItem = (arrPath, i, dir) => {
    setContent((c) => {
      const next = structuredClone(c);
      let arr = next;
      for (const k of arrPath) arr = arr[k];
      const j = i + dir;
      if (j < 0 || j >= arr.length) return c;
      [arr[i], arr[j]] = [arr[j], arr[i]];
      return next;
    });
  };

  if (!content) return <div className="py-16 text-center text-gray-500">Yükleniyor…</div>;

  const home = content.home || {};
  const lazer = (content.categoryPages || {})["Lazer Epilasyon Sistemleri"] || { heroSlides: [] };
  const alpha = content.alpha || {};
  const filtered = products.map((p, i) => ({ p, i })).filter(({ p }) => !q || p.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div data-testid="admin-estoril-site">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Estoril Site Yönetimi</h1>
        <button
          onClick={tab === "products" ? saveProducts : saveContent}
          disabled={saving}
          className="flex items-center gap-2 bg-black text-white px-5 py-2 rounded hover:bg-gray-800 disabled:opacity-50"
        >
          <Save size={16} /> {saving ? "Kaydediliyor…" : "Kaydet ve Yayınla"}
        </button>
      </div>

      <div className="flex gap-1 mb-6 border-b">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.key ? "border-black text-black" : "border-transparent text-gray-500 hover:text-black"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "home" && (
        <div className="space-y-4 max-w-3xl">
          <Card title="Anasayfa kategori sırası">
            <p className="text-sm text-gray-500">Kategorileri sürükleyerek sıralayın, ardından üstteki Kaydet düğmesine basın.</p>
            {(home.discoveryCategories || DEFAULT_DISCOVERY).map((c, i, items) => (
              <div key={c.href} draggable onDragStart={(e) => { setDragCategory(i); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", String(i)); }}
                onDragEnd={() => setDragCategory(null)} onDragOver={(e) => { if (dragCategory !== null) e.preventDefault(); }}
                onDrop={(e) => { e.preventDefault(); if (dragCategory === null) return; const next = [...items]; const [item] = next.splice(dragCategory, 1); next.splice(i, 0, item); set(["home", "discoveryCategories"], next); setDragCategory(null); }}
                className={`flex items-center gap-3 rounded border p-3 bg-white ${dragCategory === i ? "opacity-40" : ""}`}>
                <span aria-hidden="true" className="cursor-grab text-gray-400">☰</span>
                <span className="flex-1 text-sm">{i + 1}. {c.name}</span>
                <button type="button" aria-label={`${c.name} yukarı taşı`} disabled={i === 0} onClick={() => { const next = [...items]; [next[i-1], next[i]] = [next[i], next[i-1]]; set(["home", "discoveryCategories"], next); }} className="p-2 disabled:opacity-30"><ChevronUp size={16}/></button>
                <button type="button" aria-label={`${c.name} aşağı taşı`} disabled={i === items.length-1} onClick={() => { const next = [...items]; [next[i+1], next[i]] = [next[i], next[i+1]]; set(["home", "discoveryCategories"], next); }} className="p-2 disabled:opacity-30"><ChevronDown size={16}/></button>
              </div>
            ))}
          </Card>

          <Card title="Duyuru Bandı">
            <Field label="Metin" value={home.promoText} onChange={(v) => set(["home", "promoText"], v)} />
          </Card>

          <h2 className="text-sm font-semibold text-gray-500 pt-2">HERO SLIDER (AKORDEON KARTLAR)</h2>
          {(home.heroSlides || []).map((s, i) => (
            <Card key={i} title={`Slide ${i + 1} — ${s.title || "Başlıksız"}`}
              onDelete={() => set(["home", "heroSlides"], home.heroSlides.filter((_, j) => j !== i))}
              onMove={(d) => moveItem(["home", "heroSlides"], i, d)}>
              <div className="grid md:grid-cols-2 gap-3">
                <Field label="Başlık" value={s.title} onChange={(v) => set(["home", "heroSlides", i, "title"], v)} />
                <Field label="Alt başlık" value={s.sub} onChange={(v) => set(["home", "heroSlides", i, "sub"], v)} />
              </div>
              <Field label="Link (Keşfet butonu)" value={s.href} onChange={(v) => set(["home", "heroSlides", i, "href"], v)} />
              <ImagePair value={s.img} onChange={(v) => set(["home", "heroSlides", i, "img"], v)} />
            </Card>
          ))}
          <button onClick={() => set(["home", "heroSlides"], [...(home.heroSlides || []), { title: "", sub: "", href: "", img: { desktop: "", mobile: "" } }])}
            className="flex items-center gap-2 text-sm border rounded px-4 py-2 hover:bg-gray-50"><Plus size={15} /> Slide ekle</button>

          <h2 className="text-sm font-semibold text-gray-500 pt-2">TAM GENİŞLİK BANNER</h2>
          <Card title="Kampanya Banner'ı">
            <div className="grid md:grid-cols-2 gap-3">
              <Field label="Başlık" value={(home.banner || {}).title} onChange={(v) => set(["home", "banner", "title"], v)} />
              <Field label="Link" value={(home.banner || {}).href} onChange={(v) => set(["home", "banner", "href"], v)} />
            </div>
            <ImagePair value={(home.banner || {}).img} onChange={(v) => set(["home", "banner", "img"], v)} />
          </Card>
        </div>
      )}

      {tab === "lazer" && (
        <div className="space-y-4 max-w-3xl">
          <p className="text-sm text-gray-500">Lazer Epilasyon kategori sayfasının üstündeki dönen manifesto slide'ları.</p>
          {(lazer.heroSlides || []).map((s, i) => (
            <Card key={i} title={`Slide ${i + 1} — ${s.title1 || "Başlıksız"}`}
              onDelete={() => set(LAZER_PATH, lazer.heroSlides.filter((_, j) => j !== i))}
              onMove={(d) => moveItem(LAZER_PATH, i, d)}>
              <Field label="Üst etiket (eyebrow)" value={s.eyebrow} onChange={(v) => set([...LAZER_PATH, i, "eyebrow"], v)} />
              <div className="grid md:grid-cols-2 gap-3">
                <Field label="Başlık 1. satır" value={s.title1} onChange={(v) => set([...LAZER_PATH, i, "title1"], v)} />
                <Field label="Başlık 2. satır" value={s.title2} onChange={(v) => set([...LAZER_PATH, i, "title2"], v)} />
              </div>
              <Field label="Açıklama" textarea value={s.sub} onChange={(v) => set([...LAZER_PATH, i, "sub"], v)} />
              <Field label="Link (boş = 'Cihazları Gör' kaydırma)" value={s.href} onChange={(v) => set([...LAZER_PATH, i, "href"], v)} />
              <ImagePair value={s.img} onChange={(v) => set([...LAZER_PATH, i, "img"], v)} />
            </Card>
          ))}
          <button onClick={() => set(LAZER_PATH, [...(lazer.heroSlides || []), { eyebrow: "", title1: "", title2: "", sub: "", href: "", img: { desktop: "", mobile: "" } }])}
            className="flex items-center gap-2 text-sm border rounded px-4 py-2 hover:bg-gray-50"><Plus size={15} /> Slide ekle</button>
        </div>
      )}

      {tab === "alpha" && (
        <div className="space-y-4 max-w-3xl">
          <Card title="Hero">
            <div className="grid md:grid-cols-2 gap-3">
              <Field label="Başlık 1. satır" value={alpha.heroTitle1} onChange={(v) => set(["alpha", "heroTitle1"], v)} />
              <Field label="Başlık 2. satır" value={alpha.heroTitle2} onChange={(v) => set(["alpha", "heroTitle2"], v)} />
            </div>
            <Field label="Açıklama" textarea value={alpha.heroSub} onChange={(v) => set(["alpha", "heroSub"], v)} />
            <div className="grid md:grid-cols-2 gap-3">
              <Field label="Fiyat (görünen metin)" value={alpha.price} onChange={(v) => set(["alpha", "price"], v)} />
              <Field label="YouTube embed URL" value={alpha.videoUrl} onChange={(v) => set(["alpha", "videoUrl"], v)} />
            </div>
          </Card>
          <h2 className="text-sm font-semibold text-gray-500 pt-2">TEKNİK ÖZELLİKLER TABLOSU</h2>
          {(alpha.specs || []).map((r, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input value={r.k} onChange={(e) => set(["alpha", "specs", i, "k"], e.target.value)} className="border px-3 py-2 rounded text-sm w-1/3" placeholder="Özellik" />
              <input value={r.v} onChange={(e) => set(["alpha", "specs", i, "v"], e.target.value)} className="border px-3 py-2 rounded text-sm flex-1" placeholder="Değer" />
              <button onClick={() => set(["alpha", "specs"], alpha.specs.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600"><Trash2 size={15} /></button>
            </div>
          ))}
          <button onClick={() => set(["alpha", "specs"], [...(alpha.specs || []), { k: "", v: "" }])}
            className="flex items-center gap-2 text-sm border rounded px-4 py-2 hover:bg-gray-50"><Plus size={15} /> Satır ekle</button>
        </div>
      )}

      {tab === "products" && (
        <div className="space-y-3 max-w-4xl">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ürün ara…"
            className="w-full border px-3 py-2 rounded text-sm" />
          <p className="text-xs text-gray-500">{filtered.length} ürün — düzenlemek için tıklayın. Ürün sırası vitrindeki ?i= linklerini belirler; sıralamayı değiştirmeyin.</p>
          {filtered.map(({ p, i }) => (
            <div key={i} className="bg-white rounded-lg shadow-sm">
              <button onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="w-full flex items-center gap-3 p-3 text-left">
                {p.img && <img src={p.img} alt="" className="w-10 h-10 object-contain bg-gray-50 rounded" />}
                <span className="flex-1 text-sm font-medium truncate">{p.name}</span>
                <span className="text-sm text-gray-500">{p.price ? `₺${Number(p.price).toLocaleString("tr-TR")}` : "—"}</span>
                <ChevronDown size={15} className={`text-gray-400 transition-transform ${openIdx === i ? "rotate-180" : ""}`} />
              </button>
              {openIdx === i && (
                <div className="p-4 pt-0 space-y-3 border-t">
                  <Field label="Ürün adı" value={p.name} onChange={(v) => setProducts((ps) => ps.map((x, j) => j === i ? { ...x, name: v } : x))} />
                  <div className="grid md:grid-cols-3 gap-3">
                    <Field label="Fiyat (₺)" value={String(p.price ?? "")} onChange={(v) => setProducts((ps) => ps.map((x, j) => j === i ? { ...x, price: parseFloat(v) || null } : x))} />
                    <Field label="İndirimli fiyat (₺)" value={String(p.sale ?? "")} onChange={(v) => setProducts((ps) => ps.map((x, j) => j === i ? { ...x, sale: parseFloat(v) || null } : x))} />
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Stok</label>
                      <select value={p.stock ? "1" : "0"} onChange={(e) => setProducts((ps) => ps.map((x, j) => j === i ? { ...x, stock: e.target.value === "1" } : x))}
                        className="w-full border px-3 py-2 rounded text-sm">
                        <option value="1">Stokta var</option>
                        <option value="0">Ön sipariş</option>
                      </select>
                    </div>
                  </div>
                  <Field label="Açıklama / Özellikler" textarea value={p.desc} onChange={(v) => setProducts((ps) => ps.map((x, j) => j === i ? { ...x, desc: v } : x))} />
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Ana görsel</label>
                    <ImageSlot label="Ürün görseli" icon={Monitor} url={p.img}
                      onChange={(u) => setProducts((ps) => ps.map((x, j) => j === i ? { ...x, img: u, imgs: [u, ...(x.imgs || []).slice(1)] } : x))} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
