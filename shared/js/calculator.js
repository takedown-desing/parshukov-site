(function () {
  "use strict";

  // Калькулятор стоимости (v3): три шага выбора услуг и форма онлайн-встречи.
  // Цены и сроки лежат в data-атрибутах вариантов, разметку собирает tools/build_v3.py.
  var root = document.querySelector("[data-calc]");
  if (!root) return;

  var STEPS = 3;
  var MIN_SPLIT = 60000; // меньше этой суммы: 100% предоплата, скидка недоступна

  var steps = root.querySelectorAll(".calc__step");
  var skips = root.querySelectorAll(".calc__skip");
  var dots = root.querySelectorAll(".calc__dot");
  var dotsBar = root.querySelector(".calc__dots");
  var count = root.querySelector("[data-calc-count]");
  var btnBack = root.querySelector("[data-calc-back]");
  var btnNext = root.querySelector("[data-calc-next]");
  var btnSend = root.querySelector("[data-calc-send]");
  var btnMeet = root.querySelector("[data-calc-meet]");
  var outTotal = root.querySelector("[data-calc-total]");
  var outOld = root.querySelector("[data-calc-old]");
  var outTerm = root.querySelector("[data-calc-term]");
  var outInc = root.querySelector("[data-calc-inc]");
  var outPay = root.querySelector("[data-calc-pay]");
  var disc = root.querySelector("[data-calc-disc]");
  var discRow = disc.closest(".calc__disc");
  var form = root.querySelector("#calc-form");
  var current = 0;

  var money = function (n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " ₽";
  };

  var plural = function (n, one, few, many) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
  };

  var selected = function () {
    return Array.prototype.filter.call(root.querySelectorAll(".calc__opt input:checked"), function (i) {
      return Number(i.getAttribute("data-price")) > 0;
    });
  };

  // Плашка с итогом на мобильных: видна, пока калькулятор на экране, а карточка итога ниже
  var sum = root.querySelector(".calc__sum");
  var bar = document.createElement("div");
  bar.className = "calc-bar";
  bar.hidden = true;
  bar.innerHTML = '<p class="calc-bar__info"><b></b><span></span></p><button class="calc-bar__btn" type="button">Подробнее</button>';
  document.body.appendChild(bar);
  var barTotal = bar.querySelector("b");
  var barTerm = bar.querySelector("span");
  var narrow = window.matchMedia("(max-width: 1100px)");
  var calcSeen = false, sumSeen = false;
  var syncBar = function () {
    bar.hidden = !(narrow.matches && calcSeen && !sumSeen && selected().length);
  };
  bar.querySelector("button").addEventListener("click", function () {
    window.scrollTo({ top: sum.getBoundingClientRect().top + window.pageYOffset - 80, behavior: "smooth" });
  });
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      calcSeen = entries[entries.length - 1].isIntersecting;
      syncBar();
    }).observe(root);
    new IntersectionObserver(function (entries) {
      sumSeen = entries[entries.length - 1].isIntersecting;
      syncBar();
    }, { rootMargin: "0px 0px -80px 0px" }).observe(sum);
  }
  if (narrow.addEventListener) narrow.addEventListener("change", syncBar);

  var update = function () {
    var picked = selected();
    var total = 0, lo = 0, hi = 0;
    outInc.innerHTML = "";
    picked.forEach(function (i) {
      total += Number(i.getAttribute("data-price"));
      lo = Math.max(lo, Number(i.getAttribute("data-wlo")));
      hi = Math.max(hi, Number(i.getAttribute("data-whi")));
      var li = document.createElement("li");
      li.textContent = i.getAttribute("data-inc");
      outInc.appendChild(li);
    });
    if (!picked.length) {
      outInc.innerHTML = '<li class="is-empty">Пока ничего не выбрано</li>';
    }

    // Срок: самая долгая услуга плюс по полнедели на каждую следующую (работы частично идут параллельно)
    var extra = 0.5 * Math.max(picked.length - 1, 0);
    lo = Math.round(lo + extra);
    hi = Math.round(hi + extra);
    if (!picked.length) {
      outTerm.textContent = "Выберите услуги, и здесь появится срок";
    } else if (lo === hi) {
      outTerm.textContent = "Срок: около " + hi + " " + plural(hi, "недели", "недель", "недель");
    } else {
      outTerm.textContent = "Срок: " + lo + "–" + hi + " " + plural(hi, "неделя", "недели", "недель");
    }

    var full = total > 0 && total < MIN_SPLIT;
    disc.disabled = full;
    if (full) disc.checked = false;
    discRow.classList.toggle("is-off", full);
    var withDisc = disc.checked && total > 0;
    outPay.textContent = full ? "100% предоплата" : withDisc ? "80% предоплата" : "50% предоплата";

    outTotal.textContent = (picked.length ? "от " : "") + money(withDisc ? total * 0.8 : total);
    outOld.hidden = !withDisc;
    outOld.textContent = withDisc ? money(total) : "";

    barTotal.textContent = outTotal.textContent;
    barTerm.textContent = outTerm.textContent.replace("Срок: ", "");
    syncBar();
  };

  var hint = function (i, error) {
    var h = steps[i] && steps[i].querySelector(".calc__hint");
    if (!h) return;
    h.classList.toggle("is-error", error);
    h.textContent = error ? "Выберите вариант, чтобы перейти дальше" : "Выберите подходящее";
  };

  var go = function (n) {
    current = Math.max(0, Math.min(n, STEPS));
    Array.prototype.forEach.call(steps, function (s) {
      s.hidden = Number(s.getAttribute("data-step")) !== current;
    });
    Array.prototype.forEach.call(skips, function (s) {
      s.hidden = Number(s.getAttribute("data-skip")) !== current;
    });
    Array.prototype.forEach.call(dots, function (d, i) {
      d.classList.toggle("is-done", i < current);
      d.classList.toggle("is-active", i === current);
    });
    dotsBar.style.setProperty("--p", String(Math.min(current, STEPS - 1) / (STEPS - 1)));
    var left = STEPS - current;
    count.textContent = left > 0 ? left + " " + plural(left, "шаг", "шага", "шагов") : "Встреча";
    btnBack.hidden = current === 0;
    btnNext.hidden = current === STEPS;
    btnSend.hidden = current !== STEPS;
    btnMeet.hidden = current === STEPS;
  };

  var focusStep = function () {
    var box = root.querySelector(".calc__main");
    if (box.getBoundingClientRect().top < 0) box.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  root.addEventListener("change", function (e) {
    if (e.target.matches(".calc__opt input")) hint(current, false);
    update();
  });

  btnNext.addEventListener("click", function () {
    // Вариант «не нужно» лежит вне шага, в нижней строке, но у него то же имя группы
    var name = steps[current].querySelector("input").name;
    if (!root.querySelector('input[name="' + name + '"]:checked')) {
      hint(current, true);
      return;
    }
    go(current + 1);
    focusStep();
  });

  btnBack.addEventListener("click", function () {
    go(current - 1);
    focusStep();
  });

  btnMeet.addEventListener("click", function () {
    go(STEPS);
    focusStep();
    var phone = form.elements.phone;
    if (phone) phone.focus({ preventScroll: true });
  });

  // Форма встречи: та же проверка, что у формы заявки на главной (site.js)
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
    var emailOk = !email.value.trim() || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim());
    setError(email, !emailOk);
    if (!emailOk) ok = false;
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
    if (form.elements.website.value) return; // honeypot

    if (!endpoint) {
      status.innerHTML = 'Форма пока не подключена к серверу. Напишите напрямую в <a href="' + root.getAttribute("data-tg") +
        '" target="_blank" rel="noopener">Telegram</a> или <a href="' + root.getAttribute("data-wa") +
        '" target="_blank" rel="noopener">WhatsApp</a>, расчёт можно приложить скриншотом.';
      return;
    }

    var data = { source: "calculator" };
    new FormData(form).forEach(function (v, k) { data[k] = String(v).trim(); });
    data.services = selected().map(function (i) { return i.getAttribute("data-inc"); });
    data.total = outTotal.textContent;
    data.term = outTerm.textContent;
    data.payment = outPay.textContent;
    data.discount = disc.checked;
    btnSend.disabled = true;
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      form.reset();
      status.textContent = "Спасибо! Заявка отправлена, свяжусь с вами в выбранном мессенджере и предложу время встречи.";
      status.classList.add("is-ok");
    }).catch(function () {
      status.textContent = "Не получилось отправить заявку. Попробуйте ещё раз или напишите в Telegram.";
      status.classList.add("is-error");
    }).then(function () {
      btnSend.disabled = false;
    });
  });

  go(0);
  update();
})();
