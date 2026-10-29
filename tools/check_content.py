#!/usr/bin/env python3
"""Проверка файлов content/v3/*.md по правилам _FORMAT.md.

python3 tools/check_content.py                  # все файлы
python3 tools/check_content.py about.md faq.md  # выборочно
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "v3"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pages import URLS  # noqa: E402

TYPES = {"service", "hub", "case", "industry", "article", "page"}
BLOCKS = {"cards", "steps", "prices", "facts", "faq", "links", "note", "cta", "gallery", "calculator", "form", "sitemap"}
FORBIDDEN = [
    r"\bмы\b", r"\bнаш[аеиу]?\b", r"\bнашей\b", r"\bнашим\b", r"\bнаших\b", r"\bкоманд[аеуыо]й?\b",
    r"\bстуди[яиюей]\b", r"\bагентств[оаеу]\b", r"агентск", r"без посредник", r"без наценок",
    r"напрямую от исполнител", r"без менеджер", r"гарантир", r"\bлучш(ий|ая|ее|ие)\b", r"уникальн",
    r"Добро пожаловать", r"В современном мире", r"Не секрет", r"Важно отметить", r"verify", r"TODO",
    r"нужно от Вадима", r"Батуми",
]
ALLOWED_PRICES = {"30 000", "50 000", "60 000", "80 000", "100 000", "150 000"}
PRICE_RE = re.compile(r"(\d{2,3}[\s ]000)\s*(₽|руб)")
PRICE_K_RE = re.compile(r"(\d{2,3})\s*(тыс)")


def check(path):
    errs, warns = [], []
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return ["нет YAML front matter"], warns
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"YAML: {e}"], warns
    body = m.group(2)
    for f in ("url", "type", "title", "description", "h1", "crumb", "lead"):
        if not meta.get(f):
            errs.append(f"нет поля {f}")
    if meta.get("url") not in URLS:
        errs.append(f"url {meta.get('url')} не из списка")
    if meta.get("type") not in TYPES:
        errs.append(f"type {meta.get('type')} неизвестен")
    t, d = meta.get("title", ""), meta.get("description", "")
    if not 30 <= len(t) <= 70:
        warns.append(f"title {len(t)} знаков")
    if not 110 <= len(d) <= 175:
        warns.append(f"description {len(d)} знаков")
    for u in meta.get("related") or []:
        if u not in URLS:
            errs.append(f"related {u} не из списка")
    if "—" in text:
        errs.append(f"длинное тире: {text.count('—')} шт.")
    for pat in FORBIDDEN:
        for mm in re.finditer(pat, text, re.I):
            ctx = text[max(0, mm.start() - 30): mm.end() + 30].replace("\n", " ")
            if pat == r"\bмы\b" and "мы с вами" in ctx.lower():
                continue
            errs.append(f"запрещено «{mm.group(0)}»: …{ctx}…")
    for mm in re.finditer(r"\]\(([^)\s]+)\)", body):
        u = mm.group(1)
        if u.startswith("/"):
            if u.split("#")[0] not in URLS:
                errs.append(f"ссылка на несуществующий URL {u}")
        else:
            errs.append(f"внешняя ссылка {u}")
    opened = None
    for i, line in enumerate(body.split("\n"), 1):
        s = line.strip()
        if s.startswith(":::"):
            name = s[3:].split()[0] if len(s) > 3 else ""
            if name:
                if opened:
                    errs.append(f"строка {i}: блок {name} внутри незакрытого {opened}")
                if name not in BLOCKS:
                    errs.append(f"строка {i}: неизвестный блок {name}")
                opened = name
            else:
                if not opened:
                    errs.append(f"строка {i}: лишнее закрытие :::")
                opened = None
        if s.startswith("# ") or s.startswith("#### "):
            errs.append(f"строка {i}: заголовок уровня {s.split()[0]} запрещён")
    if opened:
        errs.append(f"блок {opened} не закрыт")
    if body.count(":::faq") > 1:
        errs.append("больше одного блока faq")
    for mm in PRICE_RE.finditer(text):
        if mm.group(1).replace(" ", " ") not in ALLOWED_PRICES:
            warns.append(f"цена {mm.group(0)} не из списка")
    for mm in PRICE_K_RE.finditer(text):
        if mm.group(1) + " 000" not in ALLOWED_PRICES:
            warns.append(f"цена {mm.group(0)} не из списка")
    words = len(re.findall(r"[А-Яа-яЁёA-Za-z]{2,}", body))
    lim = {"service": (900, 1700), "hub": (500, 1200), "industry": (650, 1300), "case": (400, 1000),
           "article": (1500, 2900), "page": (200, 1000)}.get(meta.get("type"), (0, 99999))
    if not lim[0] <= words <= lim[1]:
        warns.append(f"объём {words} слов, ожидается {lim[0]}–{lim[1]}")
    if meta.get("type") in ("service", "industry"):
        for b in ("faq", "cta"):
            if f":::{b}" not in body:
                errs.append(f"нет блока {b}")
        if "/calculator/" not in body:
            warns.append("нет ссылки на /calculator/")
    return errs, warns


def main():
    files = [CONTENT / a for a in sys.argv[1:]] or sorted(p for p in CONTENT.glob("*.md") if not p.name.startswith("_"))
    bad = 0
    for p in files:
        errs, warns = check(p)
        if errs or warns:
            print(f"\n{p.name}")
            for e in errs:
                print(f"  ОШИБКА {e}")
            for w in warns:
                print(f"  внимание {w}")
        bad += bool(errs)
    print(f"\nфайлов: {len(files)}, с ошибками: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
