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
