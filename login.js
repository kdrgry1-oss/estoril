/* Estoril üye giriş/kayıt — panel auth API'sine bağlı (/api/auth). */
(function () {
  var API = "/api", UKEY = "estoril_user";
  function user() { try { return JSON.parse(localStorage.getItem(UKEY) || "null"); } catch (e) { return null; } }
  function setUser(u) { if (u) localStorage.setItem(UKEY, JSON.stringify(u)); else localStorage.removeItem(UKEY); paint(); }
  function post(path, body) {
    return fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { if (!r.ok) throw new Error(d.detail || "İşlem başarısız"); return d; }); });
  }
  function accBtns() { return Array.prototype.slice.call(document.querySelectorAll('[title="Hesabım"]')); }
  function paint() {
    var u = user();
    accBtns().forEach(function (b) {
      b.style.cursor = "pointer";
      if (!b.__wired) { b.__wired = 1; b.addEventListener("click", function (e) { e.preventDefault(); open(); }); }
      if (u && u.first_name) b.setAttribute("data-logged", "1");
    });
  }
  function ensure() {
    if (document.getElementById("est-auth")) return;
    var w = document.createElement("div"); w.id = "est-auth";
    w.innerHTML = '<div class="est-a-ov"></div><div class="est-a-modal"><span class="est-a-x">✕</span><div class="est-a-body"></div></div>';
    document.body.appendChild(w);
    w.querySelector(".est-a-ov").onclick = close; w.querySelector(".est-a-x").onclick = close;
    var css = document.createElement("style");
    css.textContent =
      "#est-auth{position:fixed;inset:0;z-index:10001;display:none}#est-auth.open{display:block}" +
      ".est-a-ov{position:absolute;inset:0;background:rgba(16,24,32,.5)}" +
      ".est-a-modal{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:400px;max-width:92vw;max-height:90vh;overflow-y:auto;background:#fff;border-radius:18px;padding:32px 30px;box-shadow:0 20px 60px rgba(0,0,0,.25)}" +
      ".est-a-x{position:absolute;top:16px;right:20px;cursor:pointer;color:#6B7A82;font-size:18px}" +
      ".est-a-modal h3{font-size:20px;font-weight:700;margin:0 0 4px}.est-a-sub{color:#6B7A82;font-size:13px;margin-bottom:20px}" +
      ".est-a-modal input{width:100%;border:1.5px solid #DCE3E6;border-radius:10px;padding:12px 14px;font-size:15px;margin-bottom:12px;outline:none}" +
      ".est-a-modal input:focus{border-color:#101820}" +
      ".est-a-sub-btn{width:100%;background:#101820;color:#fff;border:0;border-radius:99px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;margin-top:4px}" +
      ".est-a-toggle{text-align:center;font-size:13px;color:#6B7A82;margin-top:16px}.est-a-toggle b{color:#101820;cursor:pointer;text-decoration:underline}" +
      ".est-a-err{color:#C0392B;font-size:13px;margin-bottom:10px;min-height:16px}" +
      ".est-a-row{display:flex;gap:10px}.est-a-row input{flex:1}" +
      ".est-a-acc{display:flex;flex-direction:column;gap:10px}.est-a-acc .est-a-name{font-size:17px;font-weight:700}" +
      ".est-a-logout{background:#F4F7F8;border:1px solid #DCE3E6;border-radius:99px;padding:12px;cursor:pointer;font-weight:600}";
    document.head.appendChild(css);
  }
  var mode = "login";
  function render() {
    var box = document.querySelector(".est-a-body"), u = user();
    if (u && u.first_name) {
      box.innerHTML = '<div class="est-a-acc"><h3>Merhaba, ' + u.first_name + '</h3>' +
        '<div class="est-a-sub">' + (u.email || "") + '</div>' +
        '<a href="https://wa.me/905334331251?text=' + encodeURIComponent("Siparişlerim hakkında bilgi almak istiyorum.") + '" target="_blank" class="est-a-sub-btn" style="display:block;text-align:center;text-decoration:none">Siparişlerim (WhatsApp)</a>' +
        '<div class="est-a-logout" id="est-logout">Çıkış Yap</div></div>';
      document.getElementById("est-logout").onclick = function () { setUser(null); render(); };
      return;
    }
    if (mode === "login") {
      box.innerHTML = '<h3>Üye Girişi</h3><div class="est-a-sub">Hesabınıza giriş yapın.</div>' +
        '<div class="est-a-err"></div>' +
        '<input id="est-le" type="email" placeholder="E-posta" autocomplete="email">' +
        '<input id="est-lp" type="password" placeholder="Şifre" autocomplete="current-password">' +
        '<button class="est-a-sub-btn" id="est-lbtn">Giriş Yap</button>' +
        '<div class="est-a-toggle">Hesabın yok mu? <b id="est-toreg">Üye ol</b></div>';
      document.getElementById("est-toreg").onclick = function () { mode = "register"; render(); };
      document.getElementById("est-lbtn").onclick = function () {
        var btn = this; btn.textContent = "..."; err("");
        post("/auth/login", { email: val("est-le"), password: val("est-lp") })
          .then(function (d) { setUser(Object.assign({ token: d.token }, d.user || {})); render(); })
          .catch(function (e) { err(e.message); btn.textContent = "Giriş Yap"; });
      };
    } else {
      box.innerHTML = '<h3>Üye Ol</h3><div class="est-a-sub">Yeni hesap oluşturun.</div>' +
        '<div class="est-a-err"></div>' +
        '<div class="est-a-row"><input id="est-rf" placeholder="Ad"><input id="est-rl" placeholder="Soyad"></div>' +
        '<input id="est-re" type="email" placeholder="E-posta" autocomplete="email">' +
        '<input id="est-rph" placeholder="Telefon (opsiyonel)">' +
        '<input id="est-rp" type="password" placeholder="Şifre (en az 6 karakter)" autocomplete="new-password">' +
        '<button class="est-a-sub-btn" id="est-rbtn">Üye Ol</button>' +
        '<div class="est-a-toggle">Zaten üye misin? <b id="est-tolog">Giriş yap</b></div>';
      document.getElementById("est-tolog").onclick = function () { mode = "login"; render(); };
      document.getElementById("est-rbtn").onclick = function () {
        var btn = this; btn.textContent = "..."; err("");
        post("/auth/register", { first_name: val("est-rf"), last_name: val("est-rl"), email: val("est-re"), phone: val("est-rph"), password: val("est-rp") })
          .then(function (d) { setUser(Object.assign({ token: d.token }, d.user || { first_name: val("est-rf"), email: val("est-re") })); render(); })
          .catch(function (e) { err(e.message); btn.textContent = "Üye Ol"; });
      };
    }
  }
  function val(id) { var e = document.getElementById(id); return e ? e.value.trim() : ""; }
  function err(t) { var e = document.querySelector(".est-a-err"); if (e) e.textContent = t; }
  function open() { ensure(); document.getElementById("est-auth").classList.add("open"); render(); }
  function close() { var m = document.getElementById("est-auth"); if (m) m.classList.remove("open"); }
  setInterval(paint, 900);
  if (document.readyState !== "loading") paint(); else document.addEventListener("DOMContentLoaded", paint);
})();
