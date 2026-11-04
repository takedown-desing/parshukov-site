"""Экспорт v3 для своего сервера: сайт в корне домена, формы на /send.php.

python3 tools/export_prod.py --site-url https://parkovagency.com --index [--captcha SITEKEY]

Сам собирает боевой набор страниц (build_v3.py без --stage), пишет dist/: страницы v3 в корне, shared/ рядом,
send.php, robots.txt, sitemap.xml, затем возвращает v3/ в состояние полигона (build_v3.py --stage), чтобы
в GitHub уходил хаб «SEO по тематикам», а на боевой сайт нет. Без --index все страницы остаются noindex,
а robots.txt закрывает сайт целиком (так сайт живёт до подключения домена).
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
GH = "https://takedown-desing.github.io/parshukov-site"
FORMSUBMIT = re.compile(r"https://formsubmit\.co/ajax/[^\"']+")
# v3 лежит на уровень глубже корня репозитория, в dist страницы в корне: один «../» лишний
UP_TO_REPO = re.compile(r"(?<![\w./])((?:\.\./)+)(shared/|favicon\.svg|apple-touch-icon\.png)")
SKIP = {"NOTES.md", "privacy.html"}

METRIKA = 114008431
# Метрика на всех страницах сразу после <meta charset>, но грузится только после согласия на cookie
# (кнопка «Принять» в уведомлении, cookie vp_cookie=all; обработчик в shared/js/site.js зовёт window.vpAnalytics()).
# Clarity снят по просьбе Вадима 03.11.2026 (зарубежный сервис). vpMetrika нужен site.js для цели «lead».
COUNTERS = f"""  <!-- Yandex.Metrika: только после согласия на cookie -->
  <script type="text/javascript">
    window.vpMetrika = {METRIKA};
    window.vpAnalytics = function () {{
      if (window.vpAnalyticsOn) return;
      window.vpAnalyticsOn = true;
      (function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}}; m[i].l=1*new Date(); for (var j = 0; j < document.scripts.length; j++) {{if (document.scripts[j].src === r) {{ return; }}}} k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id={METRIKA}', 'ym');
      ym({METRIKA}, 'init', {{ssr:true, clickmap:true, ecommerce:"dataLayer", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true}});
    }};
    if (/(?:^|; )vp_cookie=all(?:;|$)/.test(document.cookie)) window.vpAnalytics();
  </script>
"""
# Подтверждение прав в Search Console и Вебмастере, только на главной
VERIFY = """  <meta name="google-site-verification" content="ssSsEiFfuk6bJg-j2vVc7yzAH2A_gXkggspEFrWbvi8" />
  <meta name="yandex-verification" content="3312dc05dde62653" />
"""
CHARSET = '<meta charset="utf-8">\n'


def export(site, index, captcha):
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "v3", DIST, ignore=lambda d, names: [n for n in names if n in SKIP])
    shutil.copytree(ROOT / "shared", DIST / "shared", ignore=shutil.ignore_patterns(".DS_Store"))
    shutil.copy2(ROOT / "favicon.svg", DIST / "favicon.svg")
    shutil.copy2(ROOT / "apple-touch-icon.png", DIST / "apple-touch-icon.png")
    shutil.copy2(ROOT / "server" / "send.php", DIST / "send.php")

    for f in DIST.rglob("*.html"):
        h = f.read_text(encoding="utf-8")
        h = h.replace(GH + "/v3", site).replace(GH + "/", site + "/")
        h = FORMSUBMIT.sub("/send.php", h)
        h = UP_TO_REPO.sub(lambda m: m.group(1)[3:] + m.group(2), h)
        if f.parent.name == "404":
            # 404 отдаётся по любому адресу, поэтому пути в ней от корня
            h = re.sub(r'((?:href|src)=")(?:\.\./)+', r"\1/", h)
        if index:
            h = h.replace('<meta name="robots" content="noindex, nofollow">\n', "")
        if captcha:
            h = h.replace('<html lang="ru"', f'<html lang="ru" data-captcha="{captcha}"', 1)
        h = h.replace(CHARSET, CHARSET + (VERIFY if f == DIST / "index.html" else "") + COUNTERS, 1)
        f.write_text(h, encoding="utf-8")

    sm = DIST / "sitemap.xml"
    sm.write_text(sm.read_text(encoding="utf-8").replace(GH + "/v3", site), encoding="utf-8")
    # Адреса с GET-параметрами (utm, yclid и т. п.) закрыты, чтобы не плодить дубли страниц
    robots = (f"User-agent: *\nDisallow: /*?\n\nSitemap: {site}/sitemap.xml\n" if index
              else "User-agent: *\nDisallow: /\n")
    (DIST / "robots.txt").write_text(robots, encoding="utf-8")


def check():
    """Все локальные href/src из dist ведут на существующие файлы"""
    bad = []
    for f in DIST.rglob("*.html"):
        h = f.read_text(encoding="utf-8")
        for u in re.findall(r'(?:href|src)="([^"]+)"', h):
            if u.startswith(("http", "mailto:", "tel:", "#", "data:", "javascript:")) or u == "/send.php":
                continue
            path = unquote(urlsplit(u).path)
            base = DIST if path.startswith("/") else f.parent
            target = (base / path.lstrip("/")).resolve()
            if not str(target).startswith(str(DIST)) or not (target / "index.html" if target.is_dir() else target).exists():
                bad.append(f"{f.relative_to(DIST)}: {u}")
        if "formsubmit" in h or "takedown-desing" in h:
            bad.append(f"{f.relative_to(DIST)}: остался адрес GitHub Pages или FormSubmit")
        if f"ym({METRIKA}, 'init'" not in h or "window.vpAnalytics = function" not in h:
            bad.append(f"{f.relative_to(DIST)}: нет Метрики с загрузкой по согласию")
        if "clarity.ms" in h:
            bad.append(f"{f.relative_to(DIST)}: остался Microsoft Clarity")
        if 'id="cookie"' not in h:
            bad.append(f"{f.relative_to(DIST)}: нет уведомления о cookie")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-url", required=True, help="адрес сайта без слеша в конце")
    ap.add_argument("--index", action="store_true", help="открыть сайт для поисковиков")
    ap.add_argument("--captcha", default="", help="клиентский ключ Яндекс SmartCaptcha")
    a = ap.parse_args()
    build = [sys.executable, str(ROOT / "tools" / "build_v3.py")]
    subprocess.run(build, check=True)  # боевой набор страниц (LIVE), без полигонных
    export(a.site_url.rstrip("/"), a.index, a.captcha)
    bad = check()
    subprocess.run(build + ["--stage"], check=True)  # v3/ в репозитории снова в состоянии полигона
    pages = len(list(DIST.rglob("index.html")))
    print(f"dist: страниц {pages}, {'индексация открыта' if a.index else 'noindex'}, "
          f"капча {'включена' if a.captcha else 'выключена'}")
    for b in bad:
        print("  !", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
