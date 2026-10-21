import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Mail, Plus, Trash2, KeyRound, RefreshCw, AtSign } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const DOMAIN = "estoril.com.tr";

export default function MailAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [busy, setBusy] = useState(false);

  const token = localStorage.getItem("token");
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/estoril/mail/accounts`, auth);
      setAccounts(r.data.accounts || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Kutular okunamadı");
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);

  const add = async () => {
    const u = user.trim().toLowerCase().replace(/@.*/, "");
    if (!u) return toast.error("Kullanıcı adı gir");
    if (pass.length < 6) return toast.error("Şifre en az 6 karakter olmalı");
    setBusy(true);
    try {
      await axios.post(`${API}/estoril/mail/accounts`, { email: `${u}@${DOMAIN}`, password: pass }, auth);
      toast.success(`${u}@${DOMAIN} açıldı`);
      setUser(""); setPass("");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Eklenemedi");
    } finally { setBusy(false); }
  };

  const changePw = async (email) => {
    const np = window.prompt(`${email} için yeni şifre (en az 6 karakter):`);
    if (np == null) return;
    if (np.length < 6) return toast.error("Şifre en az 6 karakter olmalı");
    try {
      await axios.post(`${API}/estoril/mail/accounts/password`, { email, password: np }, auth);
      toast.success("Şifre değiştirildi");
    } catch (e) { toast.error(e.response?.data?.detail || "Değiştirilemedi"); }
  };

  const del = async (email) => {
    if (!window.confirm(`${email} kutusu silinsin mi?`)) return;
    try {
      await axios.delete(`${API}/estoril/mail/accounts`, { ...auth, data: { email } });
      toast.success("Silindi");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Silinemedi"); }
  };

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-1">
        <Mail size={22} /> <h1 className="text-xl font-semibold">Mail Hesapları</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        @{DOMAIN} posta kutularını buradan aç ve yönet. Webmail:{" "}
        <a href="https://mail.estoril.com.tr" target="_blank" rel="noreferrer" className="underline">mail.estoril.com.tr</a>
      </p>

      <div className="bg-white border rounded-xl p-4 mb-6 shadow-sm">
        <div className="text-sm font-medium mb-3 flex items-center gap-1.5"><Plus size={15} /> Yeni kutu aç</div>
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="flex items-stretch flex-1 rounded-lg border overflow-hidden">
            <input value={user} onChange={(e) => setUser(e.target.value)} placeholder="örn: satis"
              className="px-3 py-2 flex-1 min-w-0 outline-none text-sm" />
            <span className="px-3 py-2 bg-gray-50 text-gray-500 text-sm border-l flex items-center whitespace-nowrap">@{DOMAIN}</span>
          </div>
          <input type="text" value={pass} onChange={(e) => setPass(e.target.value)} placeholder="şifre (min 6)"
            className="px-3 py-2 rounded-lg border outline-none text-sm sm:w-48" />
          <button onClick={add} disabled={busy}
            className="px-4 py-2 rounded-lg bg-black text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1.5 whitespace-nowrap">
            <Plus size={15} /> Aç
          </button>
        </div>
      </div>

      <div className="bg-white border rounded-xl shadow-sm">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="text-sm font-medium">Kutular ({accounts.length})</div>
          <button onClick={load} title="Yenile" className="text-gray-400 hover:text-black"><RefreshCw size={15} /></button>
        </div>
        {loading ? (
          <div className="p-6 text-center text-gray-400 text-sm">Yükleniyor…</div>
        ) : accounts.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">Henüz kutu yok. Yukarıdan aç.</div>
        ) : (
          <ul className="divide-y">
            {accounts.map((a) => (
              <li key={a} className="flex items-center justify-between px-4 py-3">
                <span className="flex items-center gap-2 text-sm"><AtSign size={14} className="text-gray-400" />{a}</span>
                <span className="flex items-center gap-1">
                  <button onClick={() => changePw(a)} title="Şifre değiştir"
                    className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"><KeyRound size={15} /></button>
                  <button onClick={() => del(a)} title="Sil"
                    className="p-2 rounded-lg hover:bg-red-50 text-red-500"><Trash2 size={15} /></button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
