/* Estoril sepet — localStorage + drawer + WhatsApp/Havale siparis. Kendine yeten. */
(function () {
  var KEY = "estoril_cart", WA = "905334331251"; // 0533 433 12 51
  var PRODUCTS = null;
  var get = function () { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { return []; } };
  var save = function (c) { localStorage.setItem(KEY, JSON.stringify(c)); paint(); };
  var fmt = function (n) { return "₺" + Number(n || 0).toLocaleString("tr-TR"); };
  var count = function () { return get().reduce(function (s, x) { return s + x.qty; }, 0); };
  var total = function () { return get().reduce(function (s, x) { return s + x.qty * (x.price || 0); }, 0); };

  function add(item) {
    var c = get(), ex = c.find(function (x) { return x.name === item.name; });
    if (ex) ex.qty += item.qty; else c.push(item);
    save(c); openDrawer(); toast(item.name + " sepete eklendi");
  }
  function setQty(name, q) {
    var c = get(), it = c.find(function (x) { return x.name === name; });
    if (!it) return; it.qty = q; if (it.qty <= 0) c = c.filter(function (x) { return x.name !== name; });
    save(c);
  }

  /* --- badge (header sepet ikonu) --- */
  function badges() { return Array.prototype.slice.call(document.querySelectorAll('[title="Sepet"]')); }
  function paint() {
    var n = count();
    badges().forEach(function (b) {
      var bd = b.querySelector("span");
      if (bd) bd.textContent = n;
      b.style.cursor = "pointer";
      if (!b.__wired) { b.__wired = 1; b.addEventListener("click", function (e) { e.preventDefault(); openDrawer(); }); }
    });
    var d = document.getElementById("est-cart"); if (d && d.classList.contains("open")) renderDrawer();
  }

  /* --- drawer --- */
  function ensureDrawer() {
    if (document.getElementById("est-cart")) return;
    var wrap = document.createElement("div");
    wrap.id = "est-cart";
    wrap.innerHTML =
      '<div class="est-cart-ov"></div>' +
      '<aside class="est-cart-panel"><div class="est-cart-hd"><b>Sepetim</b><span class="est-cart-x">✕</span></div>' +
      '<div class="est-cart-items"></div>' +
      '<div class="est-cart-ft"><div class="est-cart-tot"><span>Toplam</span><b class="est-cart-total"></b></div>' +
      '<a class="est-cart-wa" target="_blank">WhatsApp ile Sipariş Ver</a>' +
      '<div class="est-cart-note">Havale/EFT için de WhatsApp’tan yazın.</div></div></aside>';
    document.body.appendChild(wrap);
    wrap.querySelector(".est-cart-ov").onclick = closeDrawer;
    wrap.querySelector(".est-cart-x").onclick = closeDrawer;
    var css = document.createElement("style");
    css.textContent =
      "#est-cart{position:fixed;inset:0;z-index:9999;display:none}#est-cart.open{display:block}" +
      ".est-cart-ov{position:absolute;inset:0;background:rgba(16,24,32,.45)}" +
      ".est-cart-panel{position:absolute;top:0;right:0;height:100%;width:380px;max-width:90vw;background:#fff;display:flex;flex-direction:column;box-shadow:-8px 0 40px rgba(0,0,0,.2)}" +
      ".est-cart-hd{display:flex;justify-content:space-between;align-items:center;padding:18px 20px;border-bottom:1px solid #EEF2F4;font-size:16px}" +
      ".est-cart-x{cursor:pointer;font-size:18px;color:#6B7A82}" +
      ".est-cart-items{flex:1;overflow-y:auto;padding:8px 16px}" +
      ".est-ci{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #F1F4F6}" +
      ".est-ci img{width:60px;height:60px;object-fit:contain;background:#F7F9FA;border-radius:8px;flex-shrink:0}" +
      ".est-ci-b{flex:1;min-width:0}.est-ci-n{font-size:13px;font-weight:600;line-height:1.3}" +
      ".est-ci-p{font-size:13px;color:#101820;margin-top:2px}" +
      ".est-ci-q{display:inline-flex;align-items:center;border:1px solid #DCE3E6;border-radius:99px;margin-top:6px}" +
      ".est-ci-q span{padding:2px 10px;cursor:pointer;user-select:none}.est-ci-q b{padding:0 6px;font-size:13px}" +
      ".est-ci-rm{color:#C0392B;font-size:12px;cursor:pointer;margin-left:10px}" +
      ".est-cart-empty{text-align:center;color:#9AA7AE;padding:48px 20px;font-size:14px}" +
      ".est-cart-ft{border-top:1px solid #EEF2F4;padding:16px 20px}" +
      ".est-cart-tot{display:flex;justify-content:space-between;font-size:15px;margin-bottom:12px}.est-cart-tot b{font-size:18px}" +
      ".est-cart-wa{display:block;text-align:center;background:#25D366;color:#fff;font-weight:700;padding:14px;border-radius:99px;text-decoration:none}" +
      ".est-cart-note{text-align:center;color:#9AA7AE;font-size:11px;margin-top:8px}" +
      ".est-toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:#101820;color:#fff;padding:12px 20px;border-radius:99px;font-size:13px;z-index:10000;opacity:0;transition:opacity .2s}.est-toast.on{opacity:1}";
    document.head.appendChild(css);
  }
  function renderDrawer() {
    var box = document.querySelector(".est-cart-items"), c = get();
    if (!c.length) { box.innerHTML = '<div class="est-cart-empty">Sepetiniz boş.</div>'; }
    else {
      box.innerHTML = c.map(function (x) {
        return '<div class="est-ci"><img src="' + (x.img || "") + '" alt=""><div class="est-ci-b"><div class="est-ci-n">' + x.name + '</div><div class="est-ci-p">' + fmt(x.price) + '</div>' +
          '<span class="est-ci-q"><span data-m="' + x.name + '">−</span><b>' + x.qty + '</b><span data-p="' + x.name + '">+</span></span>' +
          '<span class="est-ci-rm" data-rm="' + x.name + '">kaldır</span></div></div>';
      }).join("");
    }
    document.querySelector(".est-cart-total").textContent = fmt(total());
    var msg = "Merhaba, sipariş vermek istiyorum:%0A" + c.map(function (x) { return "• " + x.qty + "x " + x.name + " (" + fmt(x.price) + ")"; }).join("%0A") + "%0AToplam: " + fmt(total());
    document.querySelector(".est-cart-wa").href = "https://wa.me/" + WA + "?text=" + msg.replace(/ /g, "%20");
    box.querySelectorAll("[data-m]").forEach(function (b) { b.onclick = function () { var n = b.getAttribute("data-m"), it = get().find(function (x) { return x.name === n; }); setQty(n, it.qty - 1); }; });
    box.querySelectorAll("[data-p]").forEach(function (b) { b.onclick = function () { var n = b.getAttribute("data-p"), it = get().find(function (x) { return x.name === n; }); setQty(n, it.qty + 1); }; });
    box.querySelectorAll("[data-rm]").forEach(function (b) { b.onclick = function () { setQty(b.getAttribute("data-rm"), 0); }; });
  }
  function openDrawer() { ensureDrawer(); document.getElementById("est-cart").classList.add("open"); renderDrawer(); }
  function closeDrawer() { var d = document.getElementById("est-cart"); if (d) d.classList.remove("open"); }

  var toEl; function toast(t) { var e = document.querySelector(".est-toast"); if (!e) { e = document.createElement("div"); e.className = "est-toast"; document.body.appendChild(e); } e.textContent = t; e.classList.add("on"); clearTimeout(toEl); toEl = setTimeout(function () { e.classList.remove("on"); }, 1800); }

  /* --- "Sepete Ekle" yakala (urun sayfasi) --- */
  function currentProduct() {
    if (!PRODUCTS) return null;
    var i = parseInt(new URLSearchParams(location.search).get("i") || "-1", 10);
    var p = PRODUCTS[i]; if (!p) return null;
    return { name: p.name, price: (p.sale || p.price || 0), img: p.img || (p.imgs && p.imgs[0]) || "" };
  }
  function readQty() {
    var btn = Array.prototype.slice.call(document.querySelectorAll("span,button")).find(function (el) { return el.textContent.trim() === "Sepete Ekle"; });
    if (!btn) return 1;
    var row = btn.closest("div"); var b = row && row.querySelector("b, [style*='min-width:28px']");
    var q = b ? parseInt(b.textContent, 10) : 1; return q > 0 ? q : 1;
  }
  function addByLink(link) {
    var m = /[?&]i=(\d+)/.exec(link.getAttribute("href") || link.href || "");
    var pi = m ? parseInt(m[1], 10) : -1;
    var pp = PRODUCTS && PRODUCTS[pi];
    if (pp) add({ name: pp.name, price: (pp.sale || pp.price || 0), img: pp.img || (pp.imgs && pp.imgs[0]) || "", qty: 1 });
  }
  document.addEventListener("click", function (e) {
    var t = e.target;
    // 1) kart uzerindeki "+" hizli-ekle (a href=/urun?i= icinde)
    if (t && t.closest && (t.textContent || "").trim() === "+") {
      var link = t.closest('a[href*="/urun?i="]');
      if (link) { e.preventDefault(); e.stopPropagation(); addByLink(link); return; }
    }
    // 2) urun sayfasi "Sepete Ekle"
    var el = e.target; while (el && el !== document.body) {
      if (el.textContent && el.textContent.trim() === "Sepete Ekle") {
        var p = currentProduct(); if (p) { e.preventDefault(); p.qty = readQty(); add(p); }
        return;
      }
      el = el.parentElement;
    }
  }, true);

  fetch("./products.json").then(function (r) { return r.json(); }).then(function (d) { PRODUCTS = d; }).catch(function () {});

  var iv = setInterval(paint, 600); setTimeout(function () { clearInterval(iv); setInterval(paint, 1500); }, 6000);
  if (document.readyState !== "loading") paint(); else document.addEventListener("DOMContentLoaded", paint);
})();
