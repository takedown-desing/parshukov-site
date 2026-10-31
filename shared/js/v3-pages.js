(function () {
  "use strict";

  // Выпадающее меню «Услуги» в шапке: наведение работает через CSS, клик и клавиатура здесь
  var drops = document.querySelectorAll(".nav__drop");
  var closeAll = function (except) {
    Array.prototype.forEach.call(drops, function (d) {
      if (d === except) return;
      d.classList.remove("is-open");
      d.querySelector(".nav__drop-btn").setAttribute("aria-expanded", "false");
    });
  };
  Array.prototype.forEach.call(drops, function (d) {
    var btn = d.querySelector(".nav__drop-btn");
    btn.addEventListener("click", function () {
      var open = !d.classList.contains("is-open");
      closeAll(d);
      d.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", String(open));
    });
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".nav__drop")) closeAll();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var open = document.querySelector(".nav__drop.is-open .nav__drop-btn");
    closeAll();
    if (open) open.focus();
  });

  // Рекомендательные письма: открываются крупно поверх страницы
  var openers = document.querySelectorAll(".letters__open");
  if (openers.length) {
    var box = document.createElement("div");
    box.className = "lb";
    box.hidden = true;
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Рекомендательное письмо");
    box.innerHTML = '<button class="lb__close" type="button" aria-label="Закрыть">&#10005;</button><img class="lb__img" alt="">';
    document.body.appendChild(box);
    var boxImg = box.querySelector(".lb__img");
    var boxClose = box.querySelector(".lb__close");
    var lastOpener = null;
    var closeBox = function () {
      if (box.hidden) return;
      box.hidden = true;
      boxImg.removeAttribute("src");
      document.documentElement.classList.remove("is-locked");
      if (lastOpener) lastOpener.focus();
    };
    Array.prototype.forEach.call(openers, function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        lastOpener = a;
        boxImg.src = a.getAttribute("href");
        boxImg.alt = a.querySelector("img").alt;
        box.hidden = false;
        document.documentElement.classList.add("is-locked");
        boxClose.focus();
      });
    });
    boxClose.addEventListener("click", closeBox);
    box.addEventListener("click", function (e) {
      if (e.target !== boxImg) closeBox();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeBox();
      if (e.key === "Tab" && !box.hidden) { e.preventDefault(); boxClose.focus(); }
    });
  }

  // «Получить презентацию проекта»: окно с email, заявка с названием проекта уходит на почту
  var presBtns = document.querySelectorAll(".case__pres");
  if (presBtns.length) {
    var pop = document.createElement("div");
    pop.className = "pop";
    pop.hidden = true;
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-modal", "true");
    pop.setAttribute("aria-labelledby", "pop-title");
    pop.innerHTML = '<form class="pop__box" novalidate>' +
      '<button class="pop__close" type="button" aria-label="Закрыть">&#10005;</button>' +
      '<p class="pop__title" id="pop-title">Получить презентацию проекта</p>' +
      '<p class="pop__project"></p>' +
      '<p class="pop__text">Оставьте email, и я пришлю полную презентацию проекта.</p>' +
      '<label class="hp" aria-hidden="true">Не заполняйте это поле <input type="text" name="website" tabindex="-1" autocomplete="off"></label>' +
      '<label class="field"><span class="sr-only">Email</span><input type="email" name="email" placeholder="* Email" autocomplete="email" required maxlength="150"></label>' +
      '<label class="check"><input type="checkbox" name="consent" required><span class="check__box"><svg><use href="#i-check"/></svg></span><span>Я согласен с <a class="pop__policy link" href="#" target="_blank">политикой конфиденциальности</a></span></label>' +
      '<button class="btn btn--blue pop__send" type="submit">Получить презентацию</button>' +
      '<p class="form__status" role="status" aria-live="polite"></p></form>';
    document.body.appendChild(pop);
    var popForm = pop.querySelector("form");
    var popStatus = pop.querySelector(".form__status");
    var popSend = pop.querySelector(".pop__send");
    var popClose = pop.querySelector(".pop__close");
    var popBtn = null;
    var closePop = function () {
      if (pop.hidden) return;
      pop.hidden = true;
      document.documentElement.classList.remove("is-locked");
      if (popBtn) popBtn.focus();
    };
    var popError = function (input, on) {
      input.closest(".field, .check").classList.toggle("is-error", on);
      input.setAttribute("aria-invalid", on ? "true" : "false");
    };
    Array.prototype.forEach.call(presBtns, function (b) {
      b.addEventListener("click", function () {
        popBtn = b;
        popForm.reset();
        popStatus.className = "form__status";
        popStatus.textContent = "";
        pop.querySelector(".pop__project").textContent = b.getAttribute("data-project");
        pop.querySelector(".pop__policy").href = b.getAttribute("data-policy");
        pop.hidden = false;
        document.documentElement.classList.add("is-locked");
        popForm.elements.email.focus();
      });
    });
    popClose.addEventListener("click", closePop);
    pop.addEventListener("click", function (e) {
      if (e.target === pop) closePop();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closePop();
    });
    popForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = popForm.elements.email;
      var consent = popForm.elements.consent;
      var emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim());
      popError(email, !emailOk);
      popError(consent, !consent.checked);
      popStatus.className = "form__status";
      if (!emailOk || !consent.checked) {
        popStatus.textContent = "Проверьте email и отметьте согласие с политикой конфиденциальности.";
        popStatus.classList.add("is-error");
        return;
      }
      if (popForm.elements.website.value) return; // honeypot
      var project = popBtn.getAttribute("data-project");
      popSend.disabled = true;
      fetch(popBtn.getAttribute("data-endpoint"), {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({ _subject: "Запрос презентации: " + project, _template: "table",
          project: project, email: email.value.trim(), page: location.href })
      }).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        popForm.reset();
        popStatus.textContent = "Спасибо! Пришлю презентацию на указанный email.";
        popStatus.classList.add("is-ok");
      }).catch(function () {
        popStatus.textContent = "Не получилось отправить. Попробуйте ещё раз или напишите в Telegram.";
        popStatus.classList.add("is-error");
      }).then(function () {
        popSend.disabled = false;
      });
    });
  }

  // Лента работ: стрелки листают её на ширину экрана
  Array.prototype.forEach.call(document.querySelectorAll(".works"), function (w) {
    var strip = w.querySelector(".works__strip");
    var prev = w.querySelector(".works__arrow--prev");
    var next = w.querySelector(".works__arrow--next");
    if (!strip || !prev || !next) return;
    var sync = function () {
      prev.disabled = strip.scrollLeft < 4;
      next.disabled = strip.scrollLeft + strip.clientWidth > strip.scrollWidth - 4;
    };
    var go = function (dir) {
      strip.scrollBy({ left: dir * strip.clientWidth * 0.8, behavior: "smooth" });
    };
    prev.addEventListener("click", function () { go(-1); });
    next.addEventListener("click", function () { go(1); });
    strip.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync);
    sync();
  });

  // Оглавление статьи: подсветка текущего раздела
  var toc = document.querySelector(".toc");
  if (!toc || !("IntersectionObserver" in window)) return;
  var links = {};
  Array.prototype.forEach.call(toc.querySelectorAll("a[href^='#']"), function (a) {
    links[a.getAttribute("href").slice(1)] = a;
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting || !links[en.target.id]) return;
      Object.keys(links).forEach(function (k) { links[k].classList.remove("is-current"); });
      links[en.target.id].classList.add("is-current");
    });
  }, { rootMargin: "-90px 0px -70% 0px" });
  Object.keys(links).forEach(function (id) {
    var h = document.getElementById(id);
    if (h) io.observe(h);
  });
})();
