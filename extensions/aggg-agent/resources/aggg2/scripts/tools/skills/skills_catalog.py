#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Поиск скиллов по веб-каталогам (карта — docs/canon/SKILLS-WEB.md).

Когда skills_search.py НЕ смог (exit 2) или вернул «ничего не найдено»
(core.txt п.3 фоллбэк) — этот скрипт даёт СОТНИ кандидатов за секунды:
sitemap-индексы (XML-стандарт, без JS и логинов) + skillsmp REST API
(анонимно, с описаниями). Чтение содержимого найденных скиллов —
камуфокс batch_fetch (агент), кэш сутки.

Usage:
  skills_catalog.py --search "<тема>" [--limit 100] [--catalog <имя>]
  skills_catalog.py --sitemaps            # сколько URL в кэше по каталогам
  skills_catalog.py --update              # принудительное обновление кэша
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
CACHE_DIR = os.path.expanduser("~/.cache/aggg2-skills-catalog")
CACHE_DB = os.path.join(CACHE_DIR, "cache.db")
TTL = 24 * 3600  # сутки: sitemap и API (у skillsmp лимит 50 req/день)

CATALOGS = {
    "agenticskills": {
        "sitemap": "https://agenticskills.io/sitemap.xml",
        "pattern": r"/skills/",
        "note": "S-rank, авторы, платформы",
    },
    "discoveraiskills": {
        "sitemap": "https://discoveraiskills.com/sitemap.xml",
        "pattern": r"/skills/(?!collection/)",
        "note": "500+, категории",
    },
    "skillsdirectory": {
        "sitemap": "https://www.skillsdirectory.com/sitemap.xml",
        "pattern": r"/skills/[a-z0-9-]+$",
        "note": "= skillsmp.com; API с ключом",
    },
    "agentskillexchange": {
        "sitemap": "https://agentskillexchange.com/sitemap_index.xml",
        "pattern": r"/skills/[a-z0-9-]+/",
        "sub": ["skill-sitemap.xml", "skill-sitemap2.xml",
                "skill-sitemap3.xml"],
        "note": "Security Reviewed, метрики",
    },
    "agentskill.sh": {
        "sitemap": "https://agentskill.sh/sitemap_index.xml",
        "pattern": r"/@[^/]+/[^/]+",
        "sub": [f"skills-{i}.xml" for i in range(6)],
        "note": "1000 скиллов/файл, файлов 255",
    },
}
API_SKILLSMP = "https://skillsmp.com/api/v1/skills/search?q={q}&limit={n}"


def _http_get(url, timeout=20):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("каталог должен использовать HTTPS URL")
    req = urllib.request.Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected — HTTPS scheme and host are validated above
        return resp.read().decode("utf-8", errors="replace")


def _db():
    os.makedirs(CACHE_DIR, exist_ok=True)
    db = sqlite3.connect(CACHE_DB)
    db.execute("CREATE TABLE IF NOT EXISTS cache "
               "(key TEXT PRIMARY KEY, data TEXT, ts REAL)")
    return db


def _cache_get(db, key):
    row = db.execute("SELECT data, ts FROM cache WHERE key=?", (key,)).fetchone()
    if row and time.time() - row[1] < TTL:
        return row[0]
    return None


def _cache_set(db, key, data):
    db.execute("INSERT OR REPLACE INTO cache (key, data, ts) VALUES (?,?,?)",
               (key, data, time.time()))
    db.commit()


def _sitemap_urls(db, catalog, force=False):
    """Все URL из sitemap каталога (индекс — рекурсивно по под-файлам)."""
    conf = CATALOGS[catalog]
    key = f"sitemap:{catalog}"
    if not force:
        cached = _cache_get(db, key)
        if cached is not None:
            return json.loads(cached)
    urls = []
    stack = [conf["sitemap"]]
    if "sub" in conf:
        stack.extend(urllib.parse.urljoin(conf["sitemap"], s)
                     for s in conf["sub"])
    seen_files = set()
    for sm in stack[:60]:  # защита от раздувания
        if sm in seen_files:
            continue
        seen_files.add(sm)
        try:
            data = _http_get(sm)
        except Exception:  # noqa: BLE001,S112 — каталог упал, идём дальше
            continue
        try:
            root = ET.fromstring(data)  # noqa: S314 — см. комментарий выше
        except ET.ParseError:  # noqa: S110 — не XML, пропускаем
            continue
        # noqa: S314 — ET без внешних сущностей (expat не грузит DTD),
        # источник — фиксированный список каталогов docs/canon/SKILLS-WEB.md,
        # read-only; defusedxml не вводим (скрипт без зависимостей)
        for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            u = (loc.text or "").strip()
            if not u:
                continue
            if u.endswith(".xml"):
                stack.append(u)  # вложенный sitemap
            elif re.search(conf["pattern"], u):
                urls.append(u)
    urls = sorted(set(urls))
    _cache_set(db, key, json.dumps(urls))
    return urls


def _api_search(db, query, limit=50, force=False):
    """skillsmp REST API (анонимно): JSON с описаниями. Кэш — сутки
    (у API лимит 50 req/день — кэшировать обязательно)."""
    key = f"api:{query.lower()}"
    if not force:
        cached = _cache_get(db, key)
        if cached is not None:
            return json.loads(cached)
    url = API_SKILLSMP.format(q=urllib.parse.quote(query), n=min(limit, 100))
    try:
        data = json.loads(_http_get(url))
    except Exception:  # noqa: BLE001 — API упал, вернём пусто
        return []
    skills = (data.get("data") or {}).get("skills") or []
    _cache_set(db, key, json.dumps(skills))
    return skills


def _slug_filter(urls, words):
    """Фильтр URL-слага по всем словам темы (дешёвый recall-первый)."""
    if not words:
        return urls
    return [u for u in urls
            if all(w in u.lower() for w in words)]


def main():
    ap = argparse.ArgumentParser(description="Поиск скиллов по веб-каталогам "
                                             "(docs/canon/SKILLS-WEB.md, фоллбэк без GitHub)")
    ap.add_argument("--search", metavar="ТЕМА", help="поиск скиллов по теме")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--catalog", choices=list(CATALOGS) + ["api", "all"],
                    default="all", help="только один источник (по умолчанию все)")
    ap.add_argument("--sitemaps", action="store_true",
                    help="сколько URL в кэше по каталогам")
    ap.add_argument("--update", action="store_true", help="обновить кэш")
    args = ap.parse_args()

    db = _db()
    if args.sitemaps or args.search is None:
        print("sitemap-индексы (кэш сутки):")
        for name in CATALOGS:
            urls = _sitemap_urls(db, name, force=args.update)
            print(f"  {name:20s} {len(urls):5d} URL  ({CATALOGS[name]['note']})")
        if args.sitemaps:
            return 0

    words = re.findall(r"[a-z0-9а-яё-]{2,}", (args.search or "").lower())
    found = []  # (name, source, url, description)

    if args.catalog in ("all", "api"):
        for s in _api_search(db, args.search, force=args.update):
            name = s.get("name") or s.get("id") or "?"
            desc = (s.get("description") or "")[:120]
            found.append((name, "skillsmp-api", s.get("id") or "",
                          f"https://skillsmp.com/{s.get('id', '')}"))

    if args.catalog in ("all",) + tuple(CATALOGS):
        for name in CATALOGS:
            if args.catalog != "all" and args.catalog != name:
                continue
            urls = _sitemap_urls(db, name, force=args.update)
            for u in _slug_filter(urls, words):
                slug = u.rstrip("/").split("/")[-1].replace("-", " ")
                found.append((slug, name, u, ""))

    seen, out = set(), []
    for item in found:
        key = item[2]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    out = out[: args.limit]

    if not out:
        print(f"ничего не найдено по «{args.search}» (источники: "
              f"{args.catalog}) — следующий шаг: камуфокс-ресёрч скиллов "
              f"(web_search 3-5 запросов, docs/canon/SKILLS-WEB.md)")
        return 0
    print(f"скиллы ({len(out)}; кэш: сутки):")
    for i, (name, src, url, desc) in enumerate(out, 1):
        print(f"[{i}] {name} — {src}\n    {url}"
              + (f"\n    {desc}" if desc else ""))
    print("\nчтение содержимого: batch_fetch этих URL камуфоксом "
      "(mcp/camoufox_rpc.py --tool batch_fetch)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
