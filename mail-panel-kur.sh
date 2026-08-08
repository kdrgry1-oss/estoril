#!/usr/bin/env bash
# ============================================================================
# ESTORIL — Panele "Mail Hesapları" ekrani ekler.
#   - Backend: /api/estoril/mail/* (list/add/passwd/del) — sadece admin
#   - sudoers: www-data -> /usr/local/bin/estoril-mail (sifresiz, tek komut)
#   - Panel: pages/admin/MailAccounts.jsx + route + menu (adminNav)
#   - build + restart
# Onkosul: mail-kur.sh calisti + /usr/local/bin/estoril-mail mevcut.
# ============================================================================
set -euo pipefail
trap 'echo "!! HATA satir $LINENO — durdu."' ERR
[ "$(id -u)" -eq 0 ] || { echo "root: sudo bash $0"; exit 1; }

APP=/opt/facette
FE=$APP/frontend
EST=$APP/backend/routes/estoril_site.py

[ -x /usr/local/bin/estoril-mail ] || { echo "!! /usr/local/bin/estoril-mail yok. Once onu kur."; exit 1; }
[ -f "$EST" ] || { echo "!! $EST yok"; exit 1; }

echo "> 1/5 Backend uclari (estoril_site.py)"
python3 - <<'PY'
import io
f="/opt/facette/backend/routes/estoril_site.py"
s=io.open(f,encoding="utf-8").read()
if "ESTORIL MAIL ACCOUNTS" in s:
    print("   zaten ekli, atlaniyor")
else:
    block='''

# ===== ESTORIL MAIL ACCOUNTS =====
import subprocess as _subprocess
import re as _re
from typing import Optional as _Optional
from pydantic import BaseModel as _BaseModel

_MAIL_BIN = "/usr/local/bin/estoril-mail"

class _MailAcct(_BaseModel):
    email: str
    password: _Optional[str] = None

def _run_mail(args):
    try:
        return _subprocess.run(["sudo", "-n", _MAIL_BIN, *args],
                               capture_output=True, text=True, timeout=30)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"mail komutu calismadi: {e}")

@router.get("/mail/accounts")
async def mail_accounts_list(current_user: dict = Depends(require_admin)):
    p = _run_mail(["list"])
    accs = [ln.strip() for ln in p.stdout.splitlines() if "@" in ln]
    return {"accounts": accs}

@router.post("/mail/accounts")
async def mail_accounts_add(payload: _MailAcct, current_user: dict = Depends(require_admin)):
    email = (payload.email or "").strip().lower()
    pw = payload.password or ""
    local = email.split("@")[0] if "@" in email else email
    if not local or not _re.match(r"^[a-z0-9._-]+$", local):
        raise HTTPException(status_code=400, detail="Gecersiz kullanici adi (a-z 0-9 . _ -)")
    if len(pw) < 6:
        raise HTTPException(status_code=400, detail="Sifre en az 6 karakter olmali")
    p = _run_mail(["add", email, pw])
    if p.returncode != 0:
        raise HTTPException(status_code=400, detail=(p.stdout + p.stderr).strip() or "Eklenemedi")
    return {"ok": True, "message": p.stdout.strip()}

@router.post("/mail/accounts/password")
async def mail_accounts_pw(payload: _MailAcct, current_user: dict = Depends(require_admin)):
    email = (payload.email or "").strip().lower()
    pw = payload.password or ""
    if len(pw) < 6:
        raise HTTPException(status_code=400, detail="Sifre en az 6 karakter olmali")
    p = _run_mail(["passwd", email, pw])
    if p.returncode != 0:
        raise HTTPException(status_code=400, detail=(p.stdout + p.stderr).strip() or "Degistirilemedi")
    return {"ok": True, "message": p.stdout.strip()}

@router.delete("/mail/accounts")
async def mail_accounts_del(payload: _MailAcct, current_user: dict = Depends(require_admin)):
    email = (payload.email or "").strip().lower()
    p = _run_mail(["del", email])
    if p.returncode != 0:
        raise HTTPException(status_code=400, detail=(p.stdout + p.stderr).strip() or "Silinemedi")
    return {"ok": True, "message": p.stdout.strip()}
'''
    io.open(f,"a",encoding="utf-8").write(block)
    print("   eklendi")
PY
python3 -m py_compile "$EST" && echo "   py derleme OK"

echo "> 2/5 sudoers (www-data -> estoril-mail)"
echo 'www-data ALL=(root) NOPASSWD: /usr/local/bin/estoril-mail' > /etc/sudoers.d/estoril-mail
chmod 440 /etc/sudoers.d/estoril-mail
visudo -c >/dev/null && echo "   sudoers OK"

echo "> 3/5 Panel sayfasi MailAccounts.jsx"
cat > "$FE/src/pages/admin/MailAccounts.jsx" <<'JSX'
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
JSX
echo "   yazildi"

echo "> 4/5 Route + menu (AdminApp.jsx, adminNav.js)"
python3 - <<'PY'
import io, re
a="/opt/facette/frontend/src/AdminApp.jsx"
s=io.open(a,encoding="utf-8").read()
if "MailAccounts" in s:
    print("   AdminApp.jsx zaten ekli")
else:
    s=s.replace('import EstorilSite from "./pages/admin/EstorilSite";',
                'import EstorilSite from "./pages/admin/EstorilSite";\nimport MailAccounts from "./pages/admin/MailAccounts";',1)
    s=s.replace('<Route path="estoril-site" element={<EstorilSite />} />',
                '<Route path="estoril-site" element={<EstorilSite />} />\n        <Route path="mail-accounts" element={<MailAccounts />} />',1)
    io.open(a,"w",encoding="utf-8").write(s)
    print("   AdminApp.jsx guncellendi")

n="/opt/facette/frontend/src/lib/adminNav.js"
s=io.open(n,encoding="utf-8").read()
if "mail-accounts" in s:
    print("   adminNav.js zaten ekli")
else:
    if re.search(r'[\s{,]Mail[\s,}]', s) is None:
        s=s.replace('\n} from "lucide-react";','\n  Mail,\n} from "lucide-react";',1)
    s=s.replace('{ label: "Estoril Site", path: "/admin/estoril-site", icon: Store },',
                '{ label: "Estoril Site", path: "/admin/estoril-site", icon: Store },\n      { label: "Mail Hesapları", path: "/admin/mail-accounts", icon: Mail },',1)
    io.open(n,"w",encoding="utf-8").write(s)
    print("   adminNav.js guncellendi")
PY

echo "> 5/5 Build + restart (birkac dakika)"
cd "$FE"
NODE_OPTIONS=--max-old-space-size=4096 CI=false yarn build >/tmp/mailpanel_build.log 2>&1 || { tail -40 /tmp/mailpanel_build.log; echo BUILD_FAIL; exit 1; }
chown -R www-data:www-data "$APP"
systemctl restart facette-backend
systemctl reload nginx
echo ""
echo "==================================================================="
echo ">>> TAMAM. Panel > sol menu > 'Mail Hesapları'"
echo "    Kullanici adi + sifre yaz -> Ac. Adres: kullanici@estoril.com.tr"
echo "==================================================================="
