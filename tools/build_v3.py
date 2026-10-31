#!/usr/bin/env python3
"""Сборка внутренних страниц v3 из content/v3/*.md (формат описан в content/v3/_FORMAT.md).

python3 tools/build_v3.py          # все страницы + sitemap.xml + HTML-карта сайта + ссылки на главной

Пишет v3/<url>/index.html, v3/sitemap.xml. Главную v3/index.html не генерирует, только обновляет в ней
меню, подвал и блок калькулятора (между маркерами <!-- calc:start --> и <!-- calc:end -->).
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

import markdown
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "v3"
OUT = ROOT / "v3"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pages import PAGES, BY_URL, LIVE  # noqa: E402

SITE_URL = "https://takedown-desing.github.io/parshukov-site/v3"
TODAY = date.today().isoformat()

TG = "https://t.me/Vadim_Parshukov"
WA = "https://wa.me/79537808623"
MAX = "https://max.ru/u/f9LHodD0cOIs4CHhwMIhBUViP9rKrKHaghDD8JHPwcmXLQgLXrDkUR_mceY"
SOCIAL = [("Behance", "https://www.behance.net/vadimporsh"),
          ("LinkedIn", "https://www.linkedin.com/in/vadim-parshukov-b2021a212/en"),
          ("Instagram*", "https://www.instagram.com/vadim_parshukov/")]
THREADS = "https://www.threads.com/@vadim_parshukov"
EMAIL = "Vadim.parshukov.199d@mail.ru"  # подвал, «Или напишите сразу», политика, адресат форм
# Формы шлют JSON в FormSubmit, он пересылает заявку на EMAIL (первая отправка присылает письмо активации)
FORM_ENDPOINT = f"https://formsubmit.co/ajax/{EMAIL}"

PERSON = {"@type": "Person", "name": "Вадим Паршуков", "jobTitle": "Графический и индустриальный дизайнер",
          "url": SITE_URL + "/about/", "sameAs": [SOCIAL[0][1], SOCIAL[1][1], TG]}

# Имена служебных страниц, у которых нет своего файла контента (для крошек и карточек «Смотрите также»)
FALLBACK_NAMES = {"/": "Главная", "/sitemap/": "Карта сайта"}

# Меню: (название, url, подпункты)
# Услуги пока ведут на те же страницы, что и кейсы (правки Вадима 31.10): у них внизу блок цен
SERVICES_MENU = [("Фирменный стиль", "/portfolio/branding/"), ("Сайты", "/portfolio/web/"),
                 ("3D-визуализация", "/portfolio/3d/"), ("Комплексные решения", "/portfolio/complex/"),
                 ("Презентации и каталоги", "/portfolio/catalogs/"), ("Дизайн-поддержка", "/design-support/")]
CASES_MENU = [("Фирменный стиль", "/portfolio/branding/"), ("Сайты", "/portfolio/web/"),
              ("3D-визуализация", "/portfolio/3d/"), ("Комплексные решения", "/portfolio/complex/"),
              ("Презентации и каталоги", "/portfolio/catalogs/")]
NAV = [("Главная", "/", None), ("Обо мне", "/#about", None), ("Услуги", None, SERVICES_MENU), ("Кейсы", None, CASES_MENU),
       ("Контакты", "/contact/", None)]

FOOTER_COLS = [
    ("Навигация", [("Главная", "/"), ("Обо мне", "/#about"), ("Услуги", "/#services"), ("Кейсы", "/portfolio/complex/"),
                   ("Контакты", "/contact/")]),
    ("Услуги", [("Комплексные работы", "/portfolio/complex/"), ("Брендинг", "/portfolio/branding/"),
                ("Разработка", "/portfolio/web/"), ("3D-визуализация", "/portfolio/3d/")]),
]

# Группы HTML-карты сайта: заголовок -> отбор страниц
SITEMAP_GROUPS = [
    ("Основное", lambda u: u in ("/", "/reviews/", "/contact/", "/brief/")),
    ("Услуги", lambda u: u in ("/brand-identity/", "/3d/", "/web-design/", "/presentation/", "/design-support/")),
    ("Кейсы", lambda u: u.startswith("/portfolio/")),
    ("Документы", lambda u: u in ("/sitemap/", "/privacy-policy/", "/terms-of-service/")),
]

# ---------- Калькулятор (данные из «Калькулятор.docx», сроки в неделях: ориентиры, см. v3/NOTES.md) ----------
CALC_STEPS = [
    ("style", "Разработка фирменного стиля", [
        ("basic", "Базовый", "Логотип, цветовая палитра, типографика и основные правила использования стиля.",
         30000, 1, 2, "Разработка фирменного стиля (Базовый)"),
        ("full", "Полный", "Разработка визуальной концепции бренда, полноценная айдентика, рекламные материалы и гайдлайн.",
         60000, 2, 3, "Разработка фирменного стиля (Полный)"),
        ("none", "Уже есть или не нужен", "", 0, 0, 0, ""),
    ]),
    ("site", "Разработка сайта", [
        ("code", "Разработка на коде", "Подходит для индивидуальных решений, крупных тяжёлых проектов и разработки сервисов.",
         150000, 6, 10, "Разработка сайта на коде"),
        ("tilda", "Сайт на Tilda", "Подходит для большинства решений и позволяет вручную менять информацию на сайте.",
         80000, 2, 3, "Сайт на Tilda"),
        ("ai", "Сайт с использованием ИИ", "Подходит для MVP и небольших сайтов.", 50000, 1, 1,
         "Сайт с использованием ИИ"),
        ("none", "Сайт не нужен", "", 0, 0, 0, ""),
    ]),
    ("3d", "3D-визуализация и моделирование", [
        ("product", "Продукт", "3D-модель и визуализация продукции или упаковки для презентаций, каталогов и маркетинга.",
         30000, 1, 1, "3D-визуализация продукта"),
        ("equipment", "Оборудование", "3D-моделирование техники, деталей и промышленного оборудования.",
         60000, 1, 2, "3D-моделирование оборудования"),
        ("space", "Пространства", "3D-визуализация производственных помещений, коммерческих пространств и выставочных стендов.",
         100000, 2, 3, "3D-визуализация пространства"),
        ("none", "3D не нужно", "", 0, 0, 0, ""),
    ])]


def esc(s):
    return html.escape(str(s), quote=True)


def calc_opt(key, val, name, text, price, wlo, whi, inc, extra=""):
    body = f'<span class="calc__opt-title">{esc(name)}</span>'
    if text:
        body += f'<span class="calc__opt-text">{esc(text)}</span>'
    if price:
        body += f'<span class="calc__opt-price">{"около" if val == "ai" else "от"} {price:,} ₽</span>'.replace(",", "\u00a0")
    return (f'<label class="calc__opt{extra}"><input type="radio" name="calc-{key}" value="{val}" data-price="{price}" '
            f'data-wlo="{wlo}" data-whi="{whi}" data-inc="{esc(inc)}"><span class="calc__radio" aria-hidden="true"></span>'
            f'<span class="calc__opt-body">{body}</span></label>')


def calc_html(rel):
    """Разметка калькулятора по макету (3 шага + онлайн-встреча). rel(url) -> относительная ссылка."""
    dots = "".join(f'<li class="calc__dot{" is-active" if i == 0 else ""}" data-dot="{i}"></li>' for i in range(3))
    steps, skips = [], []
    for i, (key, title, opts) in enumerate(CALC_STEPS):
        items = "".join(calc_opt(key, *o) for o in opts if o[0] != "none")
        skip = "".join(calc_opt(key, *o, extra=" calc__opt--skip") for o in opts if o[0] == "none")
        hid = "" if i == 0 else " hidden"
        steps.append(f'<div class="calc__step" role="radiogroup" aria-labelledby="calc-t{i}"{hid} data-step="{i}">'
                     f'<p class="calc__step-title" id="calc-t{i}">{esc(title)}</p>'
                     f'<p class="calc__hint">Выберите подходящее</p><div class="calc__opts">{items}</div></div>')
        skips.append(f'<div class="calc__skip"{hid} data-skip="{i}">{skip}</div>')
    final = f"""<div class="calc__step calc__final" hidden data-step="3">
          <p class="calc__step-title">Провести онлайн-встречу</p>
          <p class="calc__hint">Обсудим задачи, уточним объём работ и оперативно запустим процесс.</p>
          <form class="calc__form" id="calc-form" novalidate data-endpoint="{FORM_ENDPOINT}">
            <input type="hidden" name="_subject" value="Заявка с калькулятора на сайте">
            <input type="hidden" name="_template" value="table">
            <label class="hp" aria-hidden="true">Не заполняйте это поле <input type="text" name="website" tabindex="-1" autocomplete="off"></label>
            <div class="form__row">
              <label class="field"><span class="sr-only">Телефон для связи</span><input type="tel" name="phone" placeholder="* Телефон для связи" autocomplete="tel" required maxlength="30"></label>
              <label class="field"><span class="sr-only">Email</span><input type="email" name="email" placeholder="Email" autocomplete="email" maxlength="150"></label>
            </div>
            <fieldset class="seg">
              <legend class="seg__label">Удобный способ связи:</legend>
              <div class="seg__opts">
                <label><input type="radio" name="channel" value="Telegram" checked><span>Telegram</span></label>
                <label><input type="radio" name="channel" value="WhatsApp"><span>WhatsApp</span></label>
                <label><input type="radio" name="channel" value="MAX"><span>MAX</span></label>
              </div>
            </fieldset>
            <label class="check"><input type="checkbox" name="consent" required><span class="check__box"><svg><use href="#i-check"/></svg></span><span>Я согласен с <a href="{rel('/privacy-policy/')}" class="link" target="_blank">политикой конфиденциальности</a></span></label>
            <p class="form__status" role="status" aria-live="polite"></p>
          </form>
        </div>"""
    return f"""<div class="calc" data-calc data-tg="{TG}" data-wa="{WA}">
      <div class="calc__main">
        <div class="calc__top">
          <p class="calc__count"><span data-calc-count>3 шага</span></p>
          <ol class="calc__dots" aria-hidden="true">{dots}</ol>
        </div>
        {"".join(steps)}
        {final}
        <div class="calc__bottom">
        {"".join(skips)}
        <div class="calc__nav">
          <button class="btn btn--line calc__back" type="button" data-calc-back hidden>Назад</button>
          <button class="btn btn--line calc__next" type="button" data-calc-next>Следующий шаг</button>
          <button class="btn btn--blue calc__send" type="submit" form="calc-form" data-calc-send hidden>Отправить заявку</button>
        </div>
        </div>
      </div>
      <aside class="calc__sum" aria-live="polite">
                <p class="calc__total"><span data-calc-total>0 ₽</span> <s class="calc__old" data-calc-old hidden></s></p>
        <p class="calc__term" data-calc-term>Выберите услуги, и здесь появится срок</p>
        <div class="calc__inc"><p class="calc__sum-h">Включено:</p><ul data-calc-inc><li class="is-empty">Пока ничего не выбрано</li></ul></div>
        <div class="calc__pay"><p class="calc__sum-h">Оплата:</p><p data-calc-pay>50% предоплата</p>
          <label class="calc__disc"><input type="checkbox" data-calc-disc><span class="calc__radio" aria-hidden="true"></span><span>Готов рассмотреть скидку 20%<small>* Предоплата составит 80%</small></span></label>
        </div>
        <button class="btn btn--blue calc__meet" type="button" data-calc-meet>Назначить встречу</button>
        <p class="calc__note">Это предварительный расчёт. Итоговая стоимость зависит от объёма и сложности работ.</p>
      </aside>
    </div>"""


# ---------- Разбор файлов контента ----------
def load_page(slug):
    p = CONTENT / f"{slug}.md"
    if not p.exists():
        return None
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", p.read_text(encoding="utf-8"), re.S)
    meta = yaml.safe_load(m.group(1))
    meta["body"] = m.group(2)
    return meta


def load_manifest():
    p = ROOT / "tools" / "images.json"
    if not p.exists():
        return []
    return [im for im in json.loads(p.read_text(encoding="utf-8")) if (ROOT / "shared" / "img" / im["file"]).exists()]


def parse_attrs(s):
    return dict(re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', s) and
                [(k, a or b) for k, a, b in re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', s)])


def split_items(text):
    """Элементы блока по строкам ### Заголовок -> [(title, body)]"""
    items, cur = [], None
    for line in text.split("\n"):
        if line.startswith("### "):
            cur = [line[4:].strip(), []]
            items.append(cur)
        elif cur is not None:
            cur[1].append(line)
    return [(t, "\n".join(b).strip()) for t, b in items]


def parse_body(body):
    """-> [{'h2':..., 'attrs':{}, 'parts':[('md', text) | ('block', name, params, text)]}]"""
    sections = [{"h2": None, "attrs": {}, "parts": []}]
    buf, block = [], None

    def flush():
        if buf and "\n".join(buf).strip():
            sections[-1]["parts"].append(("md", "\n".join(buf).strip()))
        buf.clear()

    for line in body.split("\n"):
        s = line.strip()
        if block is not None:
            if s == ":::":
                sections[-1]["parts"].append(("block", block[0], block[1], "\n".join(block[2]).strip()))
                block = None
            else:
                block[2].append(line)
            continue
        if s.startswith(":::") and len(s) > 3:
            flush()
            name, _, params = s[3:].partition(" ")
            block = [name, parse_attrs(params), []]
            continue
        m = re.match(r"^##\s+(.+?)\s*(\{(.*)\})?\s*$", line)
        if m and not line.startswith("###"):
            flush()
            sections.append({"h2": m.group(1).strip(), "attrs": parse_attrs(m.group(3) or ""), "parts": []})
            continue
        buf.append(line)
    flush()
    if not sections[0]["parts"]:
        sections.pop(0)
    return sections


# ---------- Markdown и типографика ----------
def prep_md(text):
    """Пустая строка перед списками и таблицами: python-markdown без неё не распознаёт их."""
    out = []
    for line in text.split("\n"):
        starts = re.match(r"^\s*([-*] |\d+\. |\|)", line)
        if starts and out and out[-1].strip() and not re.match(r"^\s*([-*] |\d+\. |\||\s{2,}\S)", out[-1]):
            out.append("")
        out.append(line)
    return "\n".join(out)


class Ctx:
    def __init__(self, url):
        self.url = url
        self.depth = len([x for x in url.strip("/").split("/") if x])
        self.up = "../" * self.depth  # до папки v3
        self.root = self.up + "../"  # до корня репозитория

    def rel(self, u):
        if u.startswith(("http", "mailto:", "#")):
            return u
        path, _, frag = u.partition("#")
        r = (self.up + path.lstrip("/")) or "./"
        return r + ("#" + frag if frag else "")

    def asset(self, p):
        return self.root + p


def md(text, ctx, inline=False):
    h = markdown.markdown(prep_md(text), extensions=["tables", "sane_lists"])
    h = re.sub(r'href="(/[^"]*)"', lambda m: f'href="{ctx.rel(m.group(1))}"', h)
    h = h.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    if inline:
        h = re.sub(r"^<p>(.*)</p>$", r"\1", h.strip(), flags=re.S)
    return h


NBSP_RES = [
    (re.compile(r"(\d) (?=000\b|₽|%|тыс|руб|недел|дн|лет|год|мин|м²|кг|стран|отрасл|проект)"), "\\1\u00a0"),
    (re.compile(r"(?<![\wА-Яа-яЁё])([вксуоиаяВКСУОИАЯ]|до|на|по|от|за|из|не|для|без|при) (?=\S)"), "\\1\u00a0"),
]


def typograph(h):
    parts = re.split(r"(<[^>]+>)", h)
    in_script = False
    for i, p in enumerate(parts):
        if p.startswith("<"):
            low = p.lower()
            if low.startswith(("<script", "<style")):
                in_script = True
            elif low.startswith(("</script", "</style")):
                in_script = False
            continue
        if in_script or not p.strip():
            continue
        for r, rep in NBSP_RES:
            p = r.sub(rep, p)
        parts[i] = p
    return "".join(parts)


# ---------- Блоки ----------
def arrow():
    return '<svg class="ico-arrow"><use href="#i-arrow"/></svg>'


def b_cards(text, params, ctx, **_):
    cols = params.get("cols", "3")
    out = []
    for title, body in split_items(text):
        link = ""
        lines = body.rstrip().split("\n")
        m = re.match(r"^\[([^\]]+)\]\(([^)]+)\)\s*$", lines[-1].strip()) if lines else None
        if m:
            body = "\n".join(lines[:-1])
            link = f'<a class="card__link" href="{ctx.rel(m.group(2))}">{esc(m.group(1))} {arrow()}</a>'
        out.append(f'<article class="card"><h3 class="card__title">{md(title, ctx, True)}</h3>'
                   f'<div class="card__text">{md(body, ctx)}</div>{link}</article>')
    return f'<div class="cards cards--{cols}">{"".join(out)}</div>'


def b_steps(text, params, ctx, **_):
    out = [f'<li class="step"><span class="step__num">{i:02d}</span><h3 class="step__title">{md(t, ctx, True)}</h3>'
           f'<div class="step__text">{md(b, ctx)}</div></li>' for i, (t, b) in enumerate(split_items(text), 1)]
    return f'<ol class="steps">{"".join(out)}</ol>'


def b_prices(text, params, ctx, **_):
    out = []
    for title, body in split_items(text):
        lines = [l for l in body.split("\n")]
        price, term, rest = "", "", []
        for l in lines:
            s = l.strip()
            if not price and re.match(r"^\*\*.+\*\*$", s):
                price = s.strip("*")
            elif s.startswith("Срок:"):
                term = s[5:].strip()
            else:
                rest.append(l)
        out.append(f'<article class="price"><h3 class="price__title">{md(title, ctx, True)}</h3>'
                   f'<p class="price__sum">{esc(price)}</p><div class="price__list">{md(chr(10).join(rest), ctx)}</div>'
                   + (f'<p class="price__term">Срок: {esc(term)}</p>' if term else "")
                   + f'<a class="btn btn--line price__btn" href="{ctx.rel("/#calculator")}">Рассчитать стоимость</a></article>')
    return f'<div class="prices">{"".join(out)}</div>'


def b_facts(text, params, ctx, **_):
    out = []
    for line in text.split("\n"):
        m = re.match(r"^\s*-\s*\*\*(.+?)\*\*\s*(.*)$", line)
        if m:
            out.append(f'<li class="fact"><span class="fact__num">{esc(m.group(1))}</span>'
                       f'<span class="fact__text">{md(m.group(2), ctx, True)}</span></li>')
    return f'<ul class="facts">{"".join(out)}</ul>'


def b_faq(text, params, ctx, page, **_):
    items = split_items(text)
    page.setdefault("faq", []).extend(items)
    out = [f'<li class="qa__item"><details><summary><h3 class="qa__q">{md(q, ctx, True)}</h3>'
           f'<span class="qa__plus" aria-hidden="true"></span></summary><div class="qa__a">{md(a, ctx)}</div></details></li>'
           for q, a in items]
    return f'<ul class="qa">{"".join(out)}</ul>'


def b_links(text, params, ctx, **_):
    out = []
    for line in text.split("\n"):
        m = re.match(r"^\s*-\s*\[([^\]]+)\]\(([^)]+)\)\s*:?\s*(.*)$", line)
        if m:
            out.append(f'<a class="lcard" href="{ctx.rel(m.group(2))}"><span class="lcard__title">{esc(m.group(1))}</span>'
                       + (f'<span class="lcard__text">{md(m.group(3), ctx, True)}</span>' if m.group(3) else "")
                       + f'{arrow()}</a>')
            continue
        m = re.match(r"^\s*-\s*([^:]+):\s*(.*)$", line)  # пункт без ссылки: карточка без перехода
        if m:
            out.append(f'<div class="lcard"><span class="lcard__title">{esc(m.group(1))}</span>'
                       f'<span class="lcard__text">{md(m.group(2), ctx, True)}</span></div>')
    return f'<div class="lcards">{"".join(out)}</div>'


def b_button(text, params, ctx, **_):
    """Одна кнопка под блоком: :::button text="Смотреть проекты" href=/portfolio/branding/"""
    return (f'<p class="blk-btn"><a class="btn btn--blue" href="{ctx.rel(params.get("href", "/contact/"))}">'
            f'{esc(params.get("text", "Подробнее"))}</a></p>')


def b_note(text, params, ctx, **_):
    return f'<div class="note">{md(text, ctx)}</div>'


def b_cta(text, params, ctx, **_):
    items = split_items(text)
    title, body = items[0] if items else ("Обсудим проект?", text)
    if params.get("btn"):  # одна кнопка со своим текстом
        btns = f'<a class="btn btn--white" href="{ctx.rel(params.get("href", "/contact/"))}">{esc(params["btn"])}</a>'
    else:
        btns = (f'<a class="btn btn--white" href="{ctx.rel("/contact/")}">Обсудить проект</a>'
                f'<a class="btn btn--outline" href="{ctx.rel("/#calculator")}">Рассчитать стоимость</a>')
    return (f'<div class="cta-band"><div class="cta-band__text"><p class="cta-band__title">{md(title, ctx, True)}</p>'
            f'<div class="cta-band__sub">{md(body, ctx)}</div></div><div class="cta-band__btns">{btns}</div></div>')


def b_price(text, params, ctx, **_):
    """Выделенная цена с кнопкой: :::price sum="от 30 000 ₽" btn="Заказать" href=/contact/"""
    return (f'<div class="price-hl"><div class="price-hl__text"><p class="price-hl__k">Стоимость</p>'
            f'<p class="price-hl__sum">{esc(params.get("sum", ""))}</p>{md(text, ctx) if text else ""}</div>'
            f'<a class="btn btn--blue price-hl__btn" href="{ctx.rel(params.get("href", "/contact/"))}">'
            f'{esc(params.get("btn", "Заказать"))}</a></div>')


# ---------- Страницы кейсов (макеты Figma от 30.10.2026) ----------
CASE_IMG = ROOT / "shared" / "img" / "cases"


def img_tag(ctx, rel_file, alt, cls=""):
    """rel_file: путь внутри shared/img/cases без расширения"""
    f = CASE_IMG / f"{rel_file}.webp"
    w, h = Image.open(f).size
    return (f'<img{f" class={cls}" if cls else ""} src="{ctx.asset("shared/img/cases/" + rel_file + ".webp")}" '
            f'alt="{esc(alt)}" width="{w}" height="{h}" loading="lazy" decoding="async">')


def ex_head(name, tag="h2"):
    return (f'<{tag} class="ex-head"><span class="ex-head__k">Пример:</span>'
            f'<span class="ex-head__name">{esc(name)}</span></{tag}>')


def ext_link(url, inner, cls):
    """Ссылка на чужой сайт: nofollow, чтобы не передавать вес, и <!--noindex--> для Яндекса"""
    return (f'<!--noindex--><a class="{cls}" href="{url}" target="_blank" rel="nofollow noopener noreferrer">'
            f'{inner}</a><!--/noindex-->')


def b_own(text, params, ctx, **_):
    """Первый абзац: синий подзаголовок, остальное: текст за серым пунктиром"""
    lead, _, rest = text.strip().partition("\n\n")
    return (f'<div class="own"><p class="own__k">От себя:</p><p class="own__lead">{md(lead, ctx, True)}</p>'
            f'<div class="own__body">{md(rest, ctx)}</div></div>')


def b_case(text, params, ctx, **_):
    """:::case name="СОКОЛ" pills="а|б|в" img=web/sokol [n=8] [layout=grid|laptop|row] [site=https://…] [pres=1]"""
    name = params["name"]
    pills = "".join(f"<li>{esc(x.strip())}</li>" for x in params.get("pills", "").split("|") if x.strip())
    n = int(params.get("n", 1))
    files = [params["img"]] if n == 1 else [f'{params["img"]}-{i}' for i in range(1, n + 1)]
    media = "".join(f'<figure class="case__img">{img_tag(ctx, f, f"{name}: пример работы {i}")}</figure>'
                    for i, f in enumerate(files, 1))
    parts = "".join(f'<div class="case__part"><h3 class="case__label">{md(t, ctx, True)}</h3>'
                    f'<div class="case__text">{md(b, ctx)}</div></div>' for t, b in split_items(text))
    site = params.get("site")
    link = ext_link(site, f'Смотреть сайт компании {arrow()}', "case__site") if site else ""
    if params.get("pres"):  # окно запроса презентации, см. v3-pages.js
        link += (f'<button class="btn btn--line case__pres" type="button" data-project="{esc(name)}" '
                 f'data-policy="{ctx.rel("/privacy-policy/")}" data-endpoint="{FORM_ENDPOINT}">Получить презентацию проекта</button>')
    return (f'<article class="case case--{params.get("layout", "grid")}">{ex_head(name)}'
            + (f'<ul class="pills">{pills}</ul>' if pills else "")
            + f'<div class="case__body"><div class="case__info">{parts}{link}</div>'
            f'<div class="case__media">{media}</div></div></article>')


def b_tiles(text, params, ctx, **_):
    """Сетка карточек с подписями. Строки элемента: img: путь, flags: ru cn | подпись, link: текст | url;
    остальное: подзаголовок. Элемент ### !note: синяя карточка-примечание."""
    out = []
    for title, body in split_items(text):
        if title == "!note":
            out.append(f'<div class="tile tile--note">{md(body, ctx)}</div>')
            continue
        img, geo, link, sub = "", "", "", []
        for line in body.split("\n"):
            k, _, v = line.partition(":")
            if k.strip() == "img":
                img = img_tag(ctx, v.strip(), f"{title}: {' '.join(sub) or title}")
            elif k.strip() == "flags":
                codes, _, cap = v.partition("|")
                flags = "".join(f'<img class="flag" src="{ctx.asset("shared/img/cases/flags/" + c + ".webp")}" alt="" '
                                f'width="15" height="15">' for c in codes.split())
                geo = f'<span class="tile__geo">{flags}<span>{esc(cap.strip())}</span></span>'
            elif k.strip() == "link":
                lt, _, lu = v.partition("|")
                link = " " + ext_link(lu.strip(), esc(lt.strip()), "tile__link")
            elif line.strip():
                sub.append(line.strip())
        out.append(f'<figure class="tile"><div class="tile__img">{img}</div><figcaption><b class="tile__name">{esc(title)}</b>'
                   f'<span class="tile__sub">{esc(" ".join(sub))}{link}</span>{geo}</figcaption></figure>')
    head = ex_head(params["title"]) if params.get("title") else ""
    return f'{head}<div class="tiles">{"".join(out)}</div>'


def b_partners(text, params, ctx, **_):
    return (f'<div class="partners"><div class="partners__text">{md(text, ctx)}</div>'
            f'<div class="partners__band">{img_tag(ctx, params["img"], params.get("alt", ""))}</div></div>')


def home_part(pattern, ctx):
    """Кусок главной (лента работ, форма с наклонными фото) с путями, пересчитанными под страницу ctx"""
    h = (OUT / "index.html").read_text(encoding="utf-8")
    part = re.search(pattern, h, re.S).group(0)
    part = part.replace('"../shared/', f'"{ctx.asset("shared/")}')
    part = part.replace(f'name="page" value="{SITE_URL}/"', f'name="page" value="{SITE_URL}{ctx.url}"')
    return re.sub(r'href="(brief/|privacy-policy/)"', lambda m: f'href="{ctx.rel("/" + m.group(1))}"', part)


def contact_sec(ctx):
    return home_part(r'<section class="section section--light contact" id="contact">.*?</section>', ctx)


def works_sec(ctx):
    return home_part(r'<section class="works".*?</section>', ctx)


def b_contact(text, params, ctx, **_):
    return contact_sec(ctx)


def b_gallery(text, params, ctx, page, pages, manifest, **_):
    url = page["url"]
    if page.get("type") == "hub" and url.startswith("/portfolio/"):
        cards = case_cards(url, ctx, pages, manifest)
        if cards:
            return cards
    ims = [im for im in manifest if url in im.get("pages", [])]
    cover = page_cover(url, manifest)
    if page.get("type") == "case" and cover and len(ims) > 1:
        ims = [im for im in ims if im is not cover] or ims
    if not ims:
        return ""
    out = [f'<figure class="gal__item"><img src="{ctx.asset("shared/img/" + im["file"])}" alt="{esc(im["alt"])}" '
           f'width="{im["w"]}" height="{im["h"]}" loading="lazy" decoding="async"></figure>' for im in ims]
    return f'<div class="gal{" gal--one" if len(ims) == 1 else ""}">{"".join(out)}</div>'


def case_cards(hub_url, ctx, pages, manifest):
    cases = [p for p in pages.values() if p.get("type") == "case"]
    if hub_url != "/portfolio/":
        cases = [p for p in cases if any(hub_url in im.get("pages", []) and p["url"] in im.get("pages", [])
                                         for im in manifest) or hub_url in (p.get("related") or [])]
    out = []
    for p in cases:
        cover = page_cover(p["url"], manifest)
        img = (f'<img src="{ctx.asset("shared/img/" + cover["file"])}" alt="{esc(cover["alt"])}" width="{cover["w"]}" '
               f'height="{cover["h"]}" loading="lazy" decoding="async">' if cover else '<span class="ccard__ph"></span>')
        meta = " · ".join(x for x in [p.get("country"), ", ".join(p.get("services") or [])] if x)
        out.append(f'<a class="ccard" href="{ctx.rel(p["url"])}"><span class="ccard__img">{img}</span>'
                   f'<span class="ccard__body"><span class="ccard__meta">{esc(meta)}</span>'
                   f'<span class="ccard__title">{esc(p.get("crumb") or p["h1"])}</span>'
                   f'<span class="ccard__text">{esc(p["h1"])}</span></span></a>')
    return f'<div class="ccards">{"".join(out)}</div>' if out else ""


def b_calculator(text, params, ctx, **_):
    return calc_html(ctx.rel)


def b_form(text, params, ctx, **_):
    return lead_form(ctx, brief=ctx.url == "/brief/")


def b_sitemap(text, params, ctx, pages, **_):
    out = []
    for title, f in SITEMAP_GROUPS:
        items = []
        for url, slug, parent in PAGES:
            if not f(url) or (url != "/" and url not in pages):
                continue
            name = FALLBACK_NAMES.get(url) or pages[url].get("h1")
            cls = ' class="smap__sub"' if parent not in ("/", None) else ""
            items.append(f'<li{cls}><a href="{ctx.rel(url)}">{esc(name)}</a></li>')
        if items:
            out.append(f'<div class="smap__group"><h2 class="smap__h">{esc(title)}</h2><ul>{"".join(items)}</ul></div>')
    return f'<div class="smap">{"".join(out)}</div>'


BLOCKS = {"cards": b_cards, "steps": b_steps, "prices": b_prices, "facts": b_facts, "faq": b_faq,
          "links": b_links, "note": b_note, "cta": b_cta, "gallery": b_gallery, "calculator": b_calculator,
          "form": b_form, "sitemap": b_sitemap, "price": b_price, "own": b_own, "case": b_case, "tiles": b_tiles,
          "catalogs": b_tiles, "partners": b_partners, "contact": b_contact, "button": b_button}


def lead_form(ctx, brief=False):
    extra = ""
    if brief:
        extra = """
        <fieldset class="seg">
          <legend class="seg__label">Что нужно:</legend>
          <div class="seg__opts seg__opts--wrap">
            <label><input type="checkbox" name="need" value="Фирменный стиль"><span>Фирменный стиль</span></label>
            <label><input type="checkbox" name="need" value="Сайт"><span>Сайт</span></label>
            <label><input type="checkbox" name="need" value="Упаковка"><span>Упаковка</span></label>
            <label><input type="checkbox" name="need" value="3D"><span>3D</span></label>
            <label><input type="checkbox" name="need" value="Презентация"><span>Презентация</span></label>
            <label><input type="checkbox" name="need" value="Другое"><span>Другое</span></label>
          </div>
        </fieldset>"""
    msg = ("Расскажите о компании, продукте и задаче: что нужно сделать, для кого, к какому сроку, есть ли примеры, "
           "которые нравятся" if brief else "Предварительная информация")
    subject = "Бриф с сайта" if brief else "Заявка с сайта"
    return f"""<form class="form" id="lead-form" novalidate data-endpoint="{FORM_ENDPOINT}">
        <input type="hidden" name="_subject" value="{subject}">
        <input type="hidden" name="_template" value="table">
        <input type="hidden" name="page" value="{SITE_URL}{ctx.url}">
        <label class="hp" aria-hidden="true">Не заполняйте это поле <input type="text" name="website" tabindex="-1" autocomplete="off"></label>
        <div class="form__row">
          <label class="field"><span class="sr-only">Ваше имя</span><input type="text" name="name" placeholder="Ваше имя" autocomplete="name" maxlength="100"></label>
          <label class="field"><span class="sr-only">Название компании</span><input type="text" name="company" placeholder="Название компании" autocomplete="organization" maxlength="150"></label>
        </div>
        <div class="form__row">
          <label class="field"><span class="sr-only">Email</span><input type="email" name="email" placeholder="Email" autocomplete="email" maxlength="150"></label>
          <label class="field"><span class="sr-only">Телефон для связи</span><input type="tel" name="phone" placeholder="* Телефон для связи" autocomplete="tel" required maxlength="30"></label>
        </div>
        <label class="field field--area"><span class="sr-only">{esc(msg)}</span><textarea name="message" rows="{5 if brief else 3}" placeholder="{esc(msg)}" maxlength="2000"></textarea></label>{extra}
        <fieldset class="seg">
          <legend class="seg__label">Бюджет:</legend>
          <div class="seg__opts">
            <label><input type="radio" name="budget" value="от 30 тыс." checked><span>от&nbsp;30&nbsp;тыс.</span></label>
            <label><input type="radio" name="budget" value="от 60 тыс."><span>от&nbsp;60&nbsp;тыс.</span></label>
            <label><input type="radio" name="budget" value="от 100 тыс."><span>от&nbsp;100&nbsp;тыс.</span></label>
          </div>
        </fieldset>
        <fieldset class="seg">
          <legend class="seg__label">Удобный способ связи:</legend>
          <div class="seg__opts">
            <label><input type="radio" name="channel" value="Telegram" checked><span>Telegram</span></label>
            <label><input type="radio" name="channel" value="WhatsApp"><span>WhatsApp</span></label>
            <label><input type="radio" name="channel" value="MAX"><span>MAX</span></label>
          </div>
        </fieldset>
        <div class="form__bottom">
          <label class="check"><input type="checkbox" name="consent" required><span class="check__box"><svg><use href="#i-check"/></svg></span><span>Я согласен с <a href="{ctx.rel('/privacy-policy/')}" class="link" target="_blank">политикой конфиденциальности</a></span></label>
          <button class="btn btn--black form__submit" type="submit">{"Отправить бриф" if brief else "Отправить заявку"}</button>
        </div>
        <p class="form__status" role="status" aria-live="polite"></p>
      </form>
      <div class="messengers">
        <p class="messengers__title">Или напишите сразу</p>
        <div class="messengers__btns">
          <a class="btn btn--black" href="{TG}" target="_blank" rel="nofollow noopener">Telegram</a>
          <a class="btn btn--black" href="{WA}" target="_blank" rel="nofollow noopener">WhatsApp</a>
          <a class="btn btn--black" href="{MAX}" target="_blank" rel="nofollow noopener">MAX</a>{email_btn("btn--black")}
        </div>
      </div>"""


def email_btn(cls):
    return f'\n          <a class="btn {cls}" href="mailto:{EMAIL}">{EMAIL}</a>' if EMAIL else ""


def page_cover(url, manifest):
    ims = [im for im in manifest if url in im.get("pages", [])]
    for im in ims:
        if im.get("cover"):
            return im
    return ims[0] if ims else None


# ---------- Каркас страницы ----------
SPRITE = None


def sprite():
    global SPRITE
    if SPRITE is None:
        h = (OUT / "index.html").read_text(encoding="utf-8")
        SPRITE = re.search(r'<svg width="0" height="0".*?</svg>', h, re.S).group(0)
    return SPRITE


def nav_html(ctx, current, mobile=False):
    out = []
    for name, url, sub in NAV:
        if sub:
            active = any(current.startswith(u) for _, u in sub)
            links = "".join(f'<a href="{ctx.rel(u)}"{" aria-current=page" if current == u else ""}>{esc(n)}</a>'
                            for n, u in sub)
            if mobile:
                out.append(f'<details class="mnav__group"><summary>{name}</summary><div>{links}</div></details>')
            else:
                out.append(f'<div class="nav__drop{" is-active" if active else ""}"><button class="nav__drop-btn" type="button" '
                           f'aria-haspopup="true" aria-expanded="false">{name}<svg aria-hidden="true" viewBox="0 0 12 12"><path d="M2.5 4.5 6 8l3.5-3.5" '
                           f'fill="none" stroke="currentColor" stroke-width="1.6"/></svg></button><div class="nav__menu">{links}</div></div>')
        else:
            act = " aria-current=page" if current == url else (" class=is-active" if url != "/" and current.startswith(url) else "")
            out.append(f'<a href="{ctx.rel(url)}"{act}>{name}</a>')
    return "\n      ".join(out)


def header_html(ctx, current):
    cta = "#contact" if current == "/" else ctx.rel("/contact/")
    socials = (f'<a href="{TG}" target="_blank" rel="nofollow noopener" aria-label="Telegram" class="soc"><svg><use href="#i-tg"/></svg></a>\n'
               f'      <a href="{WA}" target="_blank" rel="nofollow noopener" aria-label="WhatsApp" class="soc"><svg><use href="#i-wa"/></svg></a>\n'
               f'      <a href="{MAX}" target="_blank" rel="nofollow noopener" aria-label="MAX" class="soc"><svg><use href="#i-max"/></svg></a>')
    return f"""<header class="header" id="top">
  <div class="container header__inner">
    <a class="logo" href="{ctx.rel('/')}">Вадим Паршуков</a>
    <nav class="nav" aria-label="Основная навигация">
      {nav_html(ctx, current)}
    </nav>
    <div class="header__social">
      {socials}
    </div>
    <a class="btn btn--white header__cta" href="{cta}">Обсудить проект</a>
    <button class="burger" type="button" aria-label="Открыть меню" aria-expanded="false" aria-controls="mobile-menu"><span></span><span></span><span></span></button>
  </div>
  <div class="mobile-menu" id="mobile-menu" hidden>
    <nav class="mnav" aria-label="Мобильная навигация">
      {nav_html(ctx, current, mobile=True)}
    </nav>
    <div class="mobile-menu__social">
      {socials}
    </div>
    <a class="btn btn--white" href="{cta}">Обсудить проект</a>
  </div>
</header>"""


def footer_html(ctx):
    cols = []
    for title, links in FOOTER_COLS:
        a = "".join(f'<a href="{ctx.rel(u)}">{esc(n)}</a>' for n, u in links)
        cols.append(f'<nav class="footer__col" aria-label="{title}">\n        <p class="footer__h">{title}</p>\n        {a}\n      </nav>')
    cols.append(f"""<nav class="footer__col" aria-label="Контакты">
        <p class="footer__h">Контакты</p>
        <a href="{MAX}" target="_blank" rel="nofollow noopener">Макс</a>
        <a href="{TG}" target="_blank" rel="nofollow noopener">Телеграм</a>
        <a href="{WA}" target="_blank" rel="nofollow noopener">WhatsApp</a>{f'{chr(10)}        <a href="mailto:{EMAIL}">Email</a>' if EMAIL else ""}
      </nav>""")
    social = SOCIAL[1:] + ([("Threads", THREADS)] if THREADS else [])
    soc = "".join(f'\n        <a href="{u}" target="_blank" rel="nofollow noopener">{n}</a>' for n, u in social)
    cols.append(f'<nav class="footer__col" aria-label="Соцсети">\n        <p class="footer__h">Соцсети</p>{soc}\n      </nav>')
    nl = "\n      "
    return f"""<footer class="footer">
  <div class="container">
    <div class="footer__cols">
      {nl.join(cols)}
    </div>
    <div class="footer__meta">
      <p class="footer__docs"><a class="footer__privacy" href="{ctx.rel('/privacy-policy/')}">Политика конфиденциальности</a></p>
      <p class="footer__disclaimer">*Meta Platforms Inc. признана экстремистской организацией, её деятельность запрещена на территории Российской Федерации.</p>
    </div>
    <div class="wordmark footer__wordmark" aria-hidden="true">PARSHUKOV</div>
    <div class="footer__legal">
      <p>ИНН: 540310719242. Работаю официально: договор, закрывающие документы, ЭДО, международные форматы сотрудничества.</p>
      <p>© 2026 Вадим Паршуков. Все права защищены.</p>
    </div>
  </div>
</footer>"""


def crumbs_chain(url, pages):
    chain, u = [], url
    while u:
        name = FALLBACK_NAMES.get(u) or (pages.get(u) or {}).get("crumb") or u
        chain.append((name, u))
        u = BY_URL[u][2] if u in BY_URL else None
    return list(reversed(chain))


def hero_html(page, ctx, pages, manifest):
    t = page["type"]
    chain = crumbs_chain(page["url"], pages)
    crumbs = "".join(
        (f'<li><a href="{ctx.rel(u)}">{esc(n)}</a></li>' if i < len(chain) - 1 else f'<li aria-current="page">{esc(n)}</li>')
        for i, (n, u) in enumerate(chain))
    chips = "".join(f"<li>{esc(c)}</li>" for c in page.get("chips") or [])
    meta = ""
    if t == "article":
        d = page.get("date")
        dd = d.strftime("%d.%m.%Y") if hasattr(d, "strftime") else str(d)
        meta = f'<p class="phero__meta"><time datetime="{d}">{dd}</time><span>{page.get("read_time")} мин чтения</span><span>Вадим Паршуков</span></p>'
    btns = ""
    plain = page.get("hero") == "plain" or t == "cases"  # компактный hero без картинки и кнопок
    if not plain and (t in ("service", "industry", "hub", "case") or page["url"] in ("/about/", "/process/", "/reviews/")):
        btns = (f'<div class="phero__btns"><a class="btn btn--white" href="{ctx.rel("/contact/")}">Обсудить проект</a>'
                f'<a class="btn btn--outline" href="{ctx.rel("/#calculator")}">Рассчитать стоимость</a></div>')
    cover = page_cover(page["url"], manifest) if t != "article" and not plain else None
    img = ""
    if cover:
        img = (f'<div class="phero__media"><img src="{ctx.asset("shared/img/" + cover["file"])}" alt="{esc(cover["alt"])}" '
               f'width="{cover["w"]}" height="{cover["h"]}" fetchpriority="high" decoding="async"></div>')
    label = f'<p class="label label--light">{esc(page["label"])}</p>' if page.get("label") else ""
    return f"""<section class="phero{" phero--media" if img else ""}{" phero--plain" if plain else ""}">
    <div class="hero__planet" aria-hidden="true"></div>
    <div class="container phero__inner">
      <nav class="crumbs" aria-label="Хлебные крошки"><ol>{crumbs}</ol></nav>
      <div class="phero__grid">
        <div class="phero__text">
          {label}
          <h1 class="phero__title">{esc(page["h1"])}</h1>
          <p class="phero__lead">{esc(page["lead"])}</p>
          {meta}
          {f'<ul class="phero__chips">{chips}</ul>' if chips else ""}
          {btns}
        </div>
        {img}
      </div>
    </div>
  </section>"""


def render_parts(parts, ctx, page, pages, manifest):
    out = []
    for p in parts:
        if p[0] == "md":
            out.append(f'<div class="prose">{md(p[1], ctx)}</div>')
        else:
            fn = BLOCKS.get(p[1])
            if not fn:
                print(f"  ! неизвестный блок {p[1]} в {page['url']}")
                continue
            h = fn(p[3], p[2], ctx, page=page, pages=pages, manifest=manifest)
            if h:
                out.append(f'<div class="blk blk--{p[1]}">{h}</div>')
    return "\n      ".join(out)


def h2_head(h2, attrs, ctx, light=False, idx=None):
    label = f'<p class="label{" label--light" if light else ""}">{esc(attrs["label"])}</p>' if attrs.get("label") else ""
    ida = f' id="s{idx}"' if idx is not None else ""
    return f'<div class="shead">{label}<h2 class="h2s"{ida}>{md(h2, ctx, True)}</h2></div>'


LEGAL = ("/privacy-policy/", "/terms-of-service/")


def body_html(page, ctx, pages, manifest):
    sections = parse_body(page["body"])
    if page["type"] == "article":
        toc, chunks = [], []
        for i, s in enumerate(sections):
            if s["h2"]:
                toc.append(f'<li><a href="#s{i}">{esc(re.sub(r"[*_`]", "", s["h2"]))}</a></li>')
                chunks.append(f'<h2 class="h2a" id="s{i}">{md(s["h2"], ctx, True)}</h2>')
            chunks.append(render_parts(s["parts"], ctx, page, pages, manifest))
        toc_html = (f'<nav class="toc" aria-label="Содержание"><p class="toc__h">Содержание</p><ol>{"".join(toc)}</ol></nav>'
                    if len(toc) > 2 else "")
        aside = (f'<aside class="article__aside">{toc_html}<div class="side-cta"><p class="side-cta__title">Нужен дизайн для бизнеса?</p>'
                 f'<p>Фирменный стиль, сайт, упаковка и 3D в одном проекте.</p>'
                 f'<a class="btn btn--blue" href="{ctx.rel("/#calculator")}">Рассчитать стоимость</a>'
                 f'<a class="btn btn--line" href="{ctx.rel("/contact/")}">Обсудить проект</a></div></aside>')
        return (f'<section class="section section--light sec article"><div class="container article__grid">'
                f'<div class="article__body">{"".join(chunks)}</div>{aside}</div></section>')
    if page["url"] in LEGAL:
        chunks = []
        for i, s in enumerate(sections):
            if s["h2"]:
                chunks.append(f'<h2 class="h2a" id="s{i}">{md(s["h2"], ctx, True)}</h2>')
            chunks.append(render_parts(s["parts"], ctx, page, pages, manifest))
        return (f'<section class="section section--light sec doc-sec"><div class="container">'
                f'<div class="doc">{"".join(chunks)}</div></div></section>')
    if page["type"] == "cases":
        # Кейсы идут одним блоком; разделы с заголовком (цены) стоят под ними, перед формой
        cases = "".join(render_parts(s["parts"], ctx, page, pages, manifest) for s in sections if not s["h2"])
        extra = "".join(f'<section class="section section--{s["attrs"].get("tone", "light")} sec">\n    <div class="container">'
                        f'\n      {h2_head(s["h2"], s["attrs"], ctx)}\n      {render_parts(s["parts"], ctx, page, pages, manifest)}'
                        f'\n    </div>\n  </section>\n  ' for s in sections if s["h2"])
        return (f'<section class="section section--light sec cs"><div class="container">{cases}</div></section>'
                f'\n  {extra}{contact_sec(ctx)}\n  {works_sec(ctx)}')
    out, prev = [], None
    for i, s in enumerate(sections):
        blocks = [p for p in s["parts"] if not (p[0] == "md" and not p[1].strip())]
        if not s["h2"] and len(blocks) == 1 and blocks[0][0] != "md" and blocks[0][1] == "contact":
            out.append(contact_sec(ctx))  # форма как на главной, своя секция без обёртки
            continue
        tone = s["attrs"].get("tone", "light")
        tone = tone if tone in ("light", "grey", "dark") else "light"
        if tone == prev == "light" and False:
            tone = "grey"
        prev = tone
        head = h2_head(s["h2"], s["attrs"], ctx, light=tone == "dark") if s["h2"] else ""
        out.append(f'<section class="section section--{tone} sec">\n    <div class="container">\n      {head}\n      '
                   f'{render_parts(s["parts"], ctx, page, pages, manifest)}\n    </div>\n  </section>')
    return "\n  ".join(out)


def cta_html(ctx):
    return f"""<section class="cta">
    <div class="container cta__inner">
      <p class="cta__title">Брендинг, веб-разработка, 3D <br><span>Обсудим проект?</span></p>
      <a class="btn btn--black" href="{ctx.rel('/contact/')}">Связаться</a>
    </div>
  </section>"""


def jsonld(page, ctx, pages, manifest):
    url = SITE_URL + page["url"]
    chain = crumbs_chain(page["url"], pages)
    data = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": SITE_URL + u} for i, (n, u) in enumerate(chain, 1)]}]
    t = page["type"]
    cover = page_cover(page["url"], manifest)
    image = f'{SITE_URL.rsplit("/", 1)[0]}/shared/img/{cover["file"]}' if cover else None
    base = {"@context": "https://schema.org", "name": page["h1"], "description": page["description"], "url": url,
            "inLanguage": "ru"}
    if t in ("service", "industry"):
        d = dict(base, **{"@type": "Service", "serviceType": page.get("crumb"), "provider": PERSON,
                          "areaServed": ["RU", "CN", "KZ", "BY"]})
        prices = [int(x.replace(" ", "").replace("\u00a0", "")) for c in page.get("chips") or []
                  for x in re.findall(r"(?:от|около)\s*([\d  ]+)\s*₽", c)]
        if prices:
            d["offers"] = {"@type": "Offer", "priceCurrency": "RUB", "priceSpecification": {
                "@type": "PriceSpecification", "minPrice": min(prices), "priceCurrency": "RUB"}}
        data.append(d)
    elif t == "article":
        d = dict(base, **{"@type": "BlogPosting", "headline": page["h1"], "author": PERSON,
                          "datePublished": str(page.get("date")), "dateModified": str(page.get("date")),
                          "mainEntityOfPage": url, "publisher": PERSON})
        if image:
            d["image"] = image
        data.append(d)
    elif t == "case":
        d = dict(base, **{"@type": "CreativeWork", "creator": PERSON, "genre": ", ".join(page.get("services") or [])})
        if page.get("client"):
            d["about"] = {"@type": "Organization", "name": page["client"]}
        if page.get("year"):
            d["dateCreated"] = str(page["year"])
        if image:
            d["image"] = image
        data.append(d)
    elif t == "hub":
        data.append(dict(base, **{"@type": "CollectionPage"}))
    else:
        kind = {"/about/": "AboutPage", "/contact/": "ContactPage", "/faq/": "FAQPage"}.get(page["url"], "WebPage")
        d = dict(base, **{"@type": kind})
        if kind == "AboutPage":
            d["mainEntity"] = dict(PERSON, description=page["description"])
        if kind == "FAQPage":
            d = None  # FAQPage соберётся из блока faq ниже
        if d:
            data.append(d)
    if page.get("faq"):
        data.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": strip_md(q), "acceptedAnswer": {"@type": "Answer", "text": strip_md(a)}}
            for q, a in page["faq"]]})
    return "\n".join(f'  <script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>' for d in data)


def strip_md(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return re.sub(r"[*_`#>]", "", s).replace("\n", " ").strip()


def render(page, pages, manifest):
    ctx = Ctx(page["url"])
    page["faq"] = []
    main = body_html(page, ctx, pages, manifest)  # первым: заполняет page["faq"]
    hero = hero_html(page, ctx, pages, manifest)
    cta = "" if page["url"] in ("/contact/", "/404/") or "blk--cta" in main or page["type"] == "cases" else cta_html(ctx)
    main_html = typograph(f"{hero}\n  {main}\n  {cta}")
    cover = page_cover(page["url"], manifest)
    og_img = f'{SITE_URL.rsplit("/", 1)[0]}/shared/img/{cover["file"] if cover else "hero-main.webp"}'
    is404 = page["url"] == "/404/"
    calc = "blk--calculator" in main
    head_extra = jsonld(page, ctx, pages, manifest) if not is404 else ""
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex, nofollow">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="{ctx.asset('favicon.svg')}" type="image/svg+xml">
  <title>{esc(page["title"])}</title>
  <meta name="description" content="{esc(page["description"])}">
  {"" if is404 else f'<link rel="canonical" href="{SITE_URL}{page["url"]}">'}
  <meta property="og:type" content="{"article" if page["type"] == "article" else "website"}">
  <meta property="og:title" content="{esc(page["h1"])}">
  <meta property="og:description" content="{esc(page["description"])}">
  <meta property="og:url" content="{SITE_URL}{page["url"]}">
  <meta property="og:image" content="{og_img}">
  <meta property="og:locale" content="ru_RU">
  <meta property="og:site_name" content="Вадим Паршуков">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preload" href="{ctx.asset('shared/fonts/Unbounded-SemiBold.woff')}" as="font" type="font/woff" crossorigin>
  <link rel="preload" href="{ctx.asset('shared/fonts/Montserrat-Medium.woff')}" as="font" type="font/woff" crossorigin>
  <link rel="stylesheet" href="{ctx.asset('shared/fonts/fonts.css')}">
  <link rel="stylesheet" href="{ctx.asset('shared/css/site.css')}">
  <link rel="stylesheet" href="{ctx.asset('shared/css/v2.css')}">
  <link rel="stylesheet" href="{ctx.asset('shared/css/v3.css')}">
  <link rel="stylesheet" href="{ctx.asset('shared/css/v3-pages.css')}">
{head_extra}
</head>
<body class="v2 v3 v3p v3p--{page["type"]}">

{sprite()}

{header_html(ctx, page["url"])}

<main>
  {main_html}
</main>

{footer_html(ctx)}

<script src="{ctx.asset('shared/js/site.js')}" defer></script>
<script src="{ctx.asset('shared/js/v3-pages.js')}" defer></script>
{f'<script src="{ctx.asset("shared/js/calculator.js")}" defer></script>' if calc else ""}
</body>
</html>
"""


# ---------- Главная: меню, подвал, калькулятор ----------
def update_home(pages):
    p = OUT / "index.html"
    h = p.read_text(encoding="utf-8")
    ctx = Ctx("/")
    h = re.sub(r'<header class="header" id="top">.*?</header>', lambda m: header_html(ctx, "/"), h, count=1, flags=re.S)
    h = re.sub(r'<footer class="footer">.*?</footer>', lambda m: footer_html(ctx), h, count=1, flags=re.S)
    # калькулятор вместо плашки «Калькулятор готовится»
    block = (f'<!-- calc:start -->\n  <section class="section section--light sec calc-sec" id="calculator">\n    <div class="container">\n'
             f'      {calc_head()}\n      {calc_html(ctx.rel)}\n    </div>\n  </section>\n  <!-- calc:end -->')
    if "<!-- calc:start -->" in h:
        h = re.sub(r"<!-- calc:start -->.*?<!-- calc:end -->", lambda m: block, h, count=1, flags=re.S)
    else:
        h = h.replace("  <!-- ФОРМА -->", block + "\n\n  <!-- ФОРМА -->", 1)
    brief = ('<div class="aside-card">\n          <p class="aside-card__title">Хотите описать задачу подробнее?</p>\n'
             '          <p class="aside-card__text">Заполните бриф: компания, продукт, рынки, сроки и примеры, которые нравятся. '
             'Так первая встреча пройдёт предметно.</p>\n'
             f'          <a class="btn btn--blue" href="{ctx.rel("/brief/")}">Заполнить бриф</a>\n        </div>\n')
    h = re.sub(r'<div class="aside-card">\s*<p class="aside-card__title">Хотите сначала прикинуть бюджет\?</p>.*?</div>\n',
               lambda m: brief, h, count=1, flags=re.S)
    h = h.replace('href="privacy.html"', f'href="{ctx.rel("/privacy-policy/")}"')
    if "v3-pages.css" not in h:
        h = h.replace('<link rel="stylesheet" href="../shared/css/v3.css">',
                      '<link rel="stylesheet" href="../shared/css/v3.css">\n  <link rel="stylesheet" href="../shared/css/v3-pages.css">')
    if "calculator.js" not in h:
        h = h.replace('<script src="../shared/js/site.js" defer></script>',
                      '<script src="../shared/js/site.js" defer></script>\n<script src="../shared/js/v3-pages.js" defer></script>\n'
                      '<script src="../shared/js/calculator.js" defer></script>')
    if f'<link rel="canonical"' not in h:
        h = h.replace('  <meta name="description"', f'  <link rel="canonical" href="{SITE_URL}/">\n  <meta name="description"', 1)
    p.write_text(h, encoding="utf-8")


def calc_head():
    return ('<div class="calc-head"><p class="label">Калькулятор</p><div><h2 class="h2">Хотите сначала <br>рассчитать бюджет?</h2>'
            '<p class="section-sub">Выберите необходимые услуги и параметры проекта, чтобы получить предварительную оценку '
            'стоимости и сроков реализации.</p></div></div>')


def main():
    manifest = load_manifest()
    pages = {}
    for url, slug, parent in PAGES:
        if url == "/" or url not in LIVE:
            continue
        meta = load_page(slug)
        if meta is None:
            continue
        meta["url"] = url
        pages[url] = meta
    missing = [u for u in LIVE if u != "/" and u not in pages]
    # снятые с публикации страницы: удаляем их собранные index.html и опустевшие папки
    for url, _, _ in PAGES:
        if url not in LIVE:
            f = OUT / url.strip("/") / "index.html"
            if f.exists():
                f.unlink()
    for d in sorted((p for p in OUT.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        if not any(d.iterdir()):
            d.rmdir()
    built = 0
    for url, page in pages.items():
        html_out = render(page, pages, manifest)
        if "—" in html_out:
            print(f"  ! длинное тире на {url}")
        dest = OUT / url.strip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_out, encoding="utf-8")
        built += 1
    # sitemap.xml
    urls = ["/"] + [u for u, _, _ in PAGES if u in pages and u != "/404/"]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        pr = "1.0" if u == "/" else "0.8" if BY_URL[u][2] == "/" else "0.6"
        xml.append(f"  <url><loc>{SITE_URL}{u}</loc><lastmod>{TODAY}</lastmod><priority>{pr}</priority></url>")
    xml.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")
    update_home(pages)
    print(f"собрано страниц: {built}, картинок в манифесте: {len(manifest)}")
    if missing:
        print(f"нет контента ({len(missing)}): {' '.join(missing)}")


if __name__ == "__main__":
    main()
