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
