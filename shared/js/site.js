// Отправка заявок для всех форм: время на странице и токен Яндекс SmartCaptcha для проверки в send.php.
// Капча включается ключом в <html data-captcha="...">, без него заявка уходит сразу.
(function () {
  "use strict";
  var started = Date.now();
  var key = document.documentElement.getAttribute("data-captcha");
  var widget = null;
  var waiting = null;
  var loading = null;

  var load = function () {
    if (!loading) {
      loading = new Promise(function (ok, fail) {
        window.vpCaptchaReady = ok;
        var s = document.createElement("script");
        s.src = "https://smartcaptcha.yandexcloud.net/captcha.js?render=onload&onload=vpCaptchaReady";
        s.defer = true;
        s.onerror = fail;
        document.head.appendChild(s);
      });
    }
    return loading;
  };

  var token = function () {
    if (!key) return Promise.resolve("");
    return load().then(function () {
      return new Promise(function (ok, fail) {
        var sc = window.smartCaptcha;
        if (widget === null) {
          var box = document.createElement("div");
          document.body.appendChild(box);
          widget = sc.render(box, { sitekey: key, invisible: true, hl: "ru", callback: function (t) {
            if (waiting) waiting.ok(t);
            waiting = null;
          } });
          sc.subscribe(widget, "challenge-hidden", function () {
            if (waiting) waiting.fail(new Error("captcha"));
            waiting = null;
          });
        }
        waiting = { ok: ok, fail: fail };
        sc.execute(widget);
      });
    });
  };

  window.vpSend = function (endpoint, data) {
    data._elapsed = Date.now() - started;
    return token().then(function (t) {
      if (t) data._captcha = t;
      return fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(data)
      });
    }).then(function (r) {
      if (widget !== null) window.smartCaptcha.reset(widget);
      // Цель «lead» в Метрике: счётчик и window.vpMetrika есть только на parkovagency.com
      if (r.ok && window.ym && window.vpMetrika) window.ym(window.vpMetrika, "reachGoal", "lead");
      return r;
    });
  };
})();

(function () {
  "use strict";

  // Мобильное меню
  var burger = document.querySelector(".burger");
  var menu = document.getElementById("mobile-menu");
  if (burger && menu) {
    var setOpen = function (open) {
      burger.setAttribute("aria-expanded", String(open));
      burger.setAttribute("aria-label", open ? "Закрыть меню" : "Открыть меню");
      menu.hidden = !open;
      document.body.classList.toggle("menu-open", open);
    };
    burger.addEventListener("click", function () {
      setOpen(burger.getAttribute("aria-expanded") !== "true");
    });
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) setOpen(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setOpen(false);
    });
    window.matchMedia("(min-width: 1101px)").addEventListener("change", function (mq) {
      if (mq.matches) setOpen(false);
    });
  }

  // Карточки над формой «вылетают» из центральной, когда блок попадает в экран
  var cards = document.querySelector(".contact__cards[data-fly]");
  if (cards && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          cards.classList.add("is-in");
          io.disconnect();
        }
      });
    }, { threshold: 0.35 });
    io.observe(cards);
  } else if (cards) {
    cards.classList.add("is-in");
  }

  // Форма заявки: проверка в браузере. Серверная проверка обязательна отдельно (см. README).
  var form = document.getElementById("lead-form");
  if (!form) return;
  var status = form.querySelector(".form__status");
  var endpoint = form.getAttribute("data-endpoint");

  var setError = function (input, on) {
    var field = input.closest(".field, .check");
    if (field) field.classList.toggle("is-error", on);
    input.setAttribute("aria-invalid", on ? "true" : "false");
  };

  var validate = function () {
    var ok = true;
    var phone = form.elements.phone;
    var digits = (phone.value.match(/\d/g) || []).length;
    var phoneOk = digits >= 10 && digits <= 15;
    setError(phone, !phoneOk);
    if (!phoneOk) ok = false;

    var email = form.elements.email;
    if (email) {
      var emailOk = !email.value.trim() || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim());
      setError(email, !emailOk);
      if (!emailOk) ok = false;
    }

    var consent = form.elements.consent;
    setError(consent, !consent.checked);
    if (!consent.checked) ok = false;
    return ok;
  };

  form.addEventListener("input", function (e) {
    if (e.target.getAttribute("aria-invalid") === "true") validate();
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    status.className = "form__status";
    if (!validate()) {
      status.textContent = "Проверьте телефон и отметьте согласие с политикой конфиденциальности.";
      status.classList.add("is-error");
      return;
    }
    if (form.elements.website && form.elements.website.value) return; // honeypot

    if (!endpoint) {
      status.innerHTML = 'Форма пока не подключена к серверу. Напишите напрямую в <a href="https://t.me/Vadim_Parshukov" target="_blank" rel="nofollow noindex noopener">Telegram</a> или <a href="https://wa.me/79537808623" target="_blank" rel="nofollow noindex noopener">WhatsApp</a>.';
      return;
    }

    var data = {};
    new FormData(form).forEach(function (v, k) {
      v = String(v).trim();
      data[k] = k in data ? data[k] + ", " + v : v; // несколько галочек с одним именем (бриф)
    });
    var btn = form.querySelector("[type=submit]");
    btn.disabled = true;
    window.vpSend(endpoint, data).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      form.reset();
      status.textContent = "Спасибо! Заявка отправлена, свяжусь с вами в выбранном мессенджере.";
      status.classList.add("is-ok");
    }).catch(function () {
      status.textContent = "Не получилось отправить заявку. Попробуйте ещё раз или напишите в Telegram.";
      status.classList.add("is-error");
    }).then(function () {
      btn.disabled = false;
    });
  });
})();

(function () {
  "use strict";

  // Уведомление о cookie (152-ФЗ). Выбор хранится год в cookie vp_cookie: all (принять) или necessary (только технические).
  // Метрика подключается только при all: window.vpAnalytics задаётся счётчиком на parkovagency.com, на GitHub Pages его нет.
  var box = document.getElementById("cookie");
  if (!box) return;
  var read = function () {
    var m = document.cookie.match(/(?:^|; )vp_cookie=([^;]*)/);
    return m ? m[1] : "";
  };
  var save = function (v) {
    document.cookie = "vp_cookie=" + v + "; max-age=31536000; path=/; SameSite=Lax" + (location.protocol === "https:" ? "; Secure" : "");
  };
  if (read()) return;
  // Показываем после загрузки шрифтов: иначе карточка меняет высоту при подмене шрифта и сдвигает макет (CLS)
  var show = function () { box.hidden = false; };
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(show, show); else show();
  box.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-cookie]");
    if (!btn) return;
    var v = btn.getAttribute("data-cookie");
    save(v);
    box.hidden = true;
    if (v === "all" && window.vpAnalytics) window.vpAnalytics();
  });
})();
