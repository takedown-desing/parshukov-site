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
      status.innerHTML = 'Форма пока не подключена к серверу. Напишите напрямую в <a href="https://t.me/Vadim_Parshukov" target="_blank" rel="noopener">Telegram</a> или <a href="https://wa.me/79537808623" target="_blank" rel="noopener">WhatsApp</a>.';
      return;
    }

    var data = {};
    new FormData(form).forEach(function (v, k) { data[k] = String(v).trim(); });
    var btn = form.querySelector("[type=submit]");
    btn.disabled = true;
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) {
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
