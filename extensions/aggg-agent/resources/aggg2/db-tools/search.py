#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Полнотекстовый поиск по содержимому проекта (база из build.py).

Примеры:
    python3 search.py виндовс
    python3 search.py -b ../db/sherpa-voice.db модель
    python3 search.py "паттерн AND агент"
    python3 search.py --substring "гнцо"            # подстрока (trigram, >= 3)
    python3 search.py -p skills "агент"             # только в skills/
    python3 search.py --json "агент"                # машинный вывод (JSON)
    python3 search.py --limit 5 фс
"""
import argparse
import contextlib
import json
import os
import re
import sqlite3
import sys

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat
from wiki_section import wiki_section as wiki_section_fn

ROOT = _compat.chulan_root()

DEFAULT_DB = os.path.join(ROOT, "db", "aggg2.db")
from log import log_search
from search_stats_cmds import cmd_empty, cmd_stats

OPS = {"AND", "OR", "NOT", "NEAR"}

# Русская морфология для 4-го фолбэка (аудит 17.08.2026, research.db
# id=785; замена наивного списка окончаний на Snowball Russian — id=786).
# Индустрия: Elasticsearch/Lucene для русского — Snowball-стеммер,
# мини-движки вендорят алгоритм (minsearch), SQLite — C-расширение
# fts5-snowball. У нас — вендоренный snowballstemmer 3.1.1 (BSD-2,
# только русский, без зависимостей) в db-tools/snowball/; стемм
# запроса + префикс «основа*» против триграм-индекса покрывает все
# падежи и глагольные формы без перестройки индекса.
_CYR = frozenset("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")

from snowball import RussianStemmer  # noqa: E402  (db-tools/snowball)

_RU_STEMMER = RussianStemmer()


def _is_cyrillic(word):
    """Слово кириллическое (морфология — только для русских слов)."""
    return bool(word) and word[0] in _CYR


def _ru_stems(word):
    """Основы слова через Snowball Russian: стемм + усечённый вариант
    (ловит чередования «настройк/настроек»). Короткие — только стемм."""
    out = []
    try:
        stem = _RU_STEMMER.stemWord(word)
    except Exception:  # noqa: S110,BLE001 — стеммер опционален для поиска
        return out
    if len(stem) >= 4 and stem not in out:
        out.append(stem)
    if len(stem) >= 5 and stem[:-1] not in out:
        out.append(stem[:-1])
    return out


def sanitize_query(query):
    """Экранирует FTS5-запрос: токены со спецсимволами (кавычки, скобки,
    дефис — известная грабля «agent-lsp», звёздочки) оборачиваются в двойные
    кавычки. Операторы AND/OR/NOT/NEAR и готовые фразы в кавычках не
    трогаем, чтобы булева логика работала."""
    out = []
    for tok in query.split():
        upper = tok.upper()
        if upper in OPS or upper.startswith("NEAR(") or \
                (tok.startswith('"') and tok.endswith('"')):
            out.append(tok)
        elif any(c in tok for c in '"-()*:^'):
            # Префиксный поиск (подмешк*) не оборачиваем: в кавычках
            # звёздочка становится литералом и префикс не работает.
            if tok.endswith("*") and not any(c in tok[:-1] for c in '"-():^'):
                out.append(tok)
            else:
                out.append('"' + tok.replace('"', '""') + '"')
        else:
            out.append(tok)
    return " ".join(out)


def _connect(db_path):
    """Открывает базу проекта (row_factory — Row для доступа по имени)."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def _out(args, data):
    """JSON-вывод по флагу --json (иначе молчит: текстовые ветки печатают сами)."""
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.



def cmd_symbol(con, args):
    """--symbol ИМЯ: где определён символ (функция/класс/раздел)."""
    rows = con.execute(
        "SELECT rel_path, name, kind, line, signature FROM symbols "
        "WHERE name LIKE ? ORDER BY rel_path, line",
        (f"%{args.symbol}%",)).fetchall()
    data = [dict(r) for r in rows]
    if args.json:
        _out(args, data)
    elif not rows:
        print(f"символ '{args.symbol}' не найден в карте проекта")
    else:
        print(f"найдено: {len(rows)}\n")
        for r in rows:
            sig = f"  {r['signature']}" if r["signature"] else ""
            print(f"{r['rel_path']}:{r['line']}  [{r['kind']}] "
                  f"{r['name']}{sig}")


def cmd_imports(con, args):
    """--imports МОДУЛЬ: кто импортирует модуль (файл + строка)."""
    rows = con.execute(
        "SELECT rel_path, line FROM imports WHERE module = ? "
        "ORDER BY rel_path, line", (args.imports,)).fetchall()
    data = [dict(r) for r in rows]
    if args.json:
        _out(args, data)
    elif not rows:
        print(f"модуль '{args.imports}' никто не импортирует")
    else:
        print(f"импортируют '{args.imports}': {len(rows)}\n")
        for r in rows:
            print(f"{r['rel_path']}:{r['line']}")


def cmd_calls(con, args):
    """--calls ФУНКЦИЯ: кто вызывает функцию (файл + строка)."""
    rows = con.execute(
        "SELECT rel_path, line FROM calls WHERE callee = ? "
        "ORDER BY rel_path, line", (args.calls,)).fetchall()
    data = [dict(r) for r in rows]
    if args.json:
        _out(args, data)
    elif not rows:
        print(f"функцию '{args.calls}' никто не вызывает")
    else:
        print(f"вызывают '{args.calls}': {len(rows)}\n")
        for r in rows:
            print(f"{r['rel_path']}:{r['line']}")


def cmd_deps(con, args):
    """--deps ФАЙЛ: какие модули импортирует файл."""
    rows = con.execute(
        "SELECT module, line FROM imports WHERE rel_path = ? "
        "ORDER BY line", (args.deps,)).fetchall()
    data = [dict(r) for r in rows]
    if args.json:
        _out(args, data)
    elif not rows:
        print(f"файл '{args.deps}' ничего не импортирует (или нет в базе)")
    else:
        print(f"зависимости '{args.deps}': {len(rows)}\n")
        for r in rows:
            print(f"  {r['module']}  (строка {r['line']})")


def cmd_inherits(con, args):
    """--inherits КЛАСС: кто наследует от класса; с =Х — от кого наследует Х."""
    if args.inherits.startswith("="):
        child = args.inherits[1:]
        rows = con.execute(
            "SELECT rel_path, base, line FROM inherits "
            "WHERE child = ? ORDER BY rel_path, line",
            (child,)).fetchall()
        data = [{"rel_path": r["rel_path"], "child": child,
                 "base": r["base"], "line": r["line"]} for r in rows]
        if args.json:
            _out(args, data)
        elif not rows:
            print(f"класс '{child}' ничего не наследует (или нет в базе)")
        else:
            print(f"наследует '{child}': {len(rows)}\n")
            for r in rows:
                print(f"{r['rel_path']}:{r['line']}  {child} -> {r['base']}")
        return
    rows = con.execute(
        "SELECT rel_path, child, line FROM inherits "
        "WHERE base = ? ORDER BY rel_path, line",
        (args.inherits,)).fetchall()
    data = [{"rel_path": r["rel_path"], "child": r["child"],
             "base": args.inherits, "line": r["line"]} for r in rows]
    if args.json:
        _out(args, data)
    elif not rows:
        print(f"от класса '{args.inherits}' никто не наследует "
              f"(или нет в базе)")
    else:
        print(f"наследуют от '{args.inherits}': {len(rows)}\n")
        for r in rows:
            print(f"{r['rel_path']}:{r['line']}  {r['child']} -> "
                  f"{args.inherits}")


def _search_rows(con, idx, query, path, limit, no_snippet):
    """FTS-выборка по индексу idx (files_fts или files_fts_trigram)."""
    path_cond = "AND f.rel_path LIKE ?" if path else ""
    params = [query]
    if path:
        params.append(f"%{path}%")
    cols = "f.rel_path, f.size_bytes"
    if not no_snippet:
        cols += f", snippet({idx}, 1, '<<', '>>', '…', 12) AS snip"
    sql = f"""
    SELECT {cols}
    FROM {idx}
    JOIN files f ON f.id = {idx}.rowid
    WHERE {idx} MATCH ? {path_cond}
    ORDER BY bm25({idx}, 10.0, 1.0)
    LIMIT ?
    """
    params.append(limit)
    # idx/cols — внутренние константы, значения — только prepared-параметры.
    return con.execute(sql, params).fetchall()  # nosemgrep: sqlalchemy-execute-raw-query


def cmd_errors(con, args):
    """--errors: файлы с синтаксическими ошибками (не парсятся)."""
    rows = con.execute(
        "SELECT rel_path, line, message FROM errors "
        "ORDER BY rel_path, line").fetchall()
    data = [dict(r) for r in rows]
    if args.json:
        _out(args, data)
    elif not rows:
        print("синтаксических ошибок нет — все .py парсятся")
    else:
        print(f"синтаксических ошибок: {len(rows)}\n")
        for r in rows:
            loc = f":{r['line']}" if r["line"] else ""
            print(f"{r['rel_path']}{loc}  {r['message']}")


def _post_filter(rows, args):
    """Пост-фильтры выдачи (паттерн Veles): --file-sat — не складывать
    результаты из одного файла (file saturation); --demote-tests —
    тестовые файлы в конец выдачи (path penalties)."""
    if getattr(args, "file_sat", 0):
        seen: dict[str, int] = {}
        capped = []
        for r in rows:
            p = r["rel_path"]
            if seen.get(p, 0) >= args.file_sat:
                continue
            seen[p] = seen.get(p, 0) + 1
            capped.append(r)
        rows = capped
    if getattr(args, "demote_tests", False):
        pat = re.compile(r"(^|/)(tests?|spec|__tests__)/|(^|/|_)test[_.]|_test\.")
        tests = [r for r in rows if pat.search(r["rel_path"])]
        rest = [r for r in rows if not pat.search(r["rel_path"])]
        rows = rest + tests
    return rows


def cmd_search(con, args):
    """FTS-поиск по содержимому (или trigram-подстрока с --substring)."""
    if args.substring and len(args.query) < 3:
        print("--substring требует запрос не короче 3 символов",
              file=sys.stderr)
        sys.exit(1)

    idx = "files_fts_trigram" if args.substring else "files_fts"
    query = sanitize_query(args.query)

    try:
        rows = _search_rows(con, idx, query, args.path, args.limit,
                            args.no_snippet)
    except sqlite3.OperationalError as e:
        print(f"неверный запрос: {e}", file=sys.stderr)
        sys.exit(1)

    fallback = False
    if not rows and not args.substring and len(args.query) >= 3:
        # Авто-фолбэк при пустом результате: триграм-индекс (подстрока).
        # Спайк 12.08.2026 (research.db id=348): 33% запросов пустые;
        # «удал»/«настройк»/«delete file» в обычном FTS дают 0, в trigram —
        # десятки результатов. В trigram нет булевых операторов — берём
        # сырой запрос как литеральную подстроку.
        try:
            rows = _search_rows(con, "files_fts_trigram", args.query,
                                args.path, args.limit, args.no_snippet)
            fallback = bool(rows)
        except sqlite3.OperationalError:
            pass
    fallback_or = False
    if not rows and not args.substring and " " in args.query:
        # OR-релаксация многословного запроса (аудит 15.08.2026,
        # research.db id=662): «продуктовая стратегия» пусто 9 раз подряд —
        # целая фраза как подстрока не встречается, а слова порознь есть.
        # FTS5 trigram поддерживает OR: «продуктовая OR стратегия» -> 8.
        words = [w for w in args.query.split()
                 if len(w) >= 4 and w.upper() not in OPS
                 and not w.startswith('"') and not w.startswith("NEAR(")]
        if words:
            try:
                rows = _search_rows(con, "files_fts_trigram",
                                    " OR ".join(words), args.path,
                                    args.limit, args.no_snippet)
                fallback_or = bool(rows)
            except sqlite3.OperationalError:
                pass

    fallback_stem = False
    if not rows and not args.substring:
        # 4-й фолбэк — русская морфология (аудит 17.08.2026, id=785).
        # Кирпич-запросы в склонениях («продуктовой стратегии») не
        # ловятся ни триграм-подстрокой, ни OR целых слов. Основы с
        # префиксом против триграм-индекса покрывают все падежи.
        terms = []
        for w in args.query.split():
            wl = w.lower()
            if not wl or wl.upper() in OPS or wl.startswith('"'):
                continue
            if _is_cyrillic(wl) and len(wl) >= 5:
                terms.extend(f"{s}*" for s in _ru_stems(wl)[:2])
            elif len(wl) >= 3:
                terms.append(wl)
        if terms:
            try:
                rows = _search_rows(con, "files_fts_trigram",
                                    " OR ".join(terms[:8]), args.path,
                                    args.limit, args.no_snippet)
                fallback_stem = bool(rows)
            except sqlite3.OperationalError:
                pass

    if not args.no_log:
        log_search("search.py", os.path.basename(args.db).replace(".db", ""),
                   args.query, len(rows))

    rows = _post_filter(rows, args)

    if args.json:
        data = [dict(r) for r in rows]
        _out(args, data)
        return

    wiki_section = wiki_section_fn(args.query, sanitize_query(args.query),
                                    args.db,
                                    {r["rel_path"] for r in rows})

    if not rows:
        print("ничего не найдено")
        print("подсказка: короче (2-3 слова, без AND-цепочек) и без склонений;"
              " содержимое базы — на РУССКОМ, имена файлов — латиницей"
              " (вместо «delete file» → «удалить файл»); другая база:"
              " -b db/aggg2.db; ЗНАНИЯ (посты/инструкции) — -b db/wiki.db;"
              " research.db — findings.py search;"
              " СМЫСЛОВОЙ вопрос («найди код, который…») — MCP semble.search"
              " (запрос терминами дока, скилл code-search-ladder)")
        if wiki_section:
            print(wiki_section)
        dym = _did_you_mean(args.query,
                            os.path.basename(args.db).replace(".db", ""))
        if dym:
            print(dym)
        return

    label = ("найдено по корням слов (морфология)" if fallback_stem else
             "найдено по словам (OR-релаксация)" if fallback_or else
             "найдено по подстроке (авто-фолбэк)" if fallback else "найдено")
    print(f"{label}: {len(rows)}\n")
    for r in rows:
        print(f"{r['rel_path']}  ({r['size_bytes']} б)")
        if not args.no_snippet:
            print(f"  …{r['snip']}")
        print()
    if wiki_section:
        print(wiki_section)


def _did_you_mean(query, db_name):
    """Пустой результат → похожие НЕпустые запросы из search_log (research.db):
    совпадение по общему токену >=3 символов, топ-2 по числу результатов.
    Паттерн «did you mean» из индустрии (search UX); данные — свои (30.7%
    пустых запросов, аудит 15.08, research.db id=540)."""
    if len(query) < 3:
        return ""
    rd = os.path.join(ROOT, "db", "research.db")
    if not os.path.isfile(rd):
        return ""
    toks = {t.lower() for t in query.split() if len(t) >= 3}
    if not toks:
        return ""
    try:
        con = sqlite3.connect(rd)
        try:
            rows = con.execute(
                "SELECT query, MAX(hits) FROM search_log WHERE hits > 0 "
                "GROUP BY query ORDER BY MAX(hits) DESC LIMIT 200").fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        return ""
    best = []
    for q, h in rows:
        ql = q.lower()
        if ql == query.lower() or ql == db_name:
            continue
        score = sum(1 for t in toks if t in ql)
        if score:
            best.append((score, h, q))
    best.sort(key=lambda x: (-x[0], -x[1]))
    out = [f"«{q}» ({h} рез.)" for _, h, q in best[:2]]
    if out:
        return "искали похожее: " + ", ".join(out)
    return ""


def main():
    ap = argparse.ArgumentParser(description="Поиск по содержимому базы проекта")
    ap.add_argument("query", nargs="?", help="FTS5-запрос, например: виндовс или 'токен AND шкала'")
    ap.add_argument("-b", "--db", default=DEFAULT_DB, help="путь к базе (по умолчанию aggg2.db)")
    ap.add_argument("--limit", type=int, default=10, help="сколько результатов (по умолчанию 10)")
    ap.add_argument("--no-snippet", action="store_true", help="не показывать сниппеты")
    ap.add_argument("--symbol", metavar="ИМЯ", help="где определён символ: файл + строка + сигнатура")
    ap.add_argument("--imports", metavar="МОДУЛЬ", help="граф: кто импортирует модуль")
    ap.add_argument("--calls", metavar="ФУНКЦИЯ", help="граф: кто вызывает функцию")
    ap.add_argument("--deps", metavar="ФАЙЛ", help="граф: какие модули импортирует файл")
    ap.add_argument("--inherits", metavar="КЛАСС", help="граф: наследования (с =Х — от кого)")
    ap.add_argument("--errors", action="store_true", help="файлы с синтаксическими ошибками")
    ap.add_argument("--substring", action="store_true",
                    help="поиск подстроки через trigram-индекс (запрос >= 3 символа)")
    ap.add_argument("--file-sat", type=int, default=0, metavar="N",
                    help="не более N результатов из одного файла "
                         "(file saturation, паттерн Veles; 0 = выкл)")
    ap.add_argument("--demote-tests", action="store_true",
                    help="тестовые файлы (test_*/tests/) в конец выдачи "
                         "(path penalties, паттерн Veles)")
    ap.add_argument("-p", "--path", metavar="ПОДСТРОКА",
                    help="искать только в файлах, чей путь содержит подстроку")
    ap.add_argument("--json", action="store_true", help="вывод в JSON (машиночитаемо)")
    ap.add_argument("--stats", action="store_true",
                    help="метрики использования поиска (research.db search_log): "
                         "топ запросов, пустые, последние")
    ap.add_argument("--empty", action="store_true",
                    help="майнинг пустых запросов: темы, которые ищут и не "
                         "находят — кандидаты в доки/wiki")
    ap.add_argument("--no-log", action="store_true",
                    help="не писать этот поиск в search_log (по умолчанию пишется)")
    ap.add_argument("--refresh", action="store_true",
                    help="пересобрать базу перед поиском (-r/--root, --extra-files)")
    ap.add_argument("-r", "--root", default=str(ROOT),
                    help="корень проекта для --refresh (по умолчанию AGGG2.0)")
    ap.add_argument("--extra-files", nargs="*", default=[],
                    help="внешние файлы вне root для --refresh (например ~/.cache/sherpa-voice/history.md)")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    # Универсальная свежесть (fresh.py): при рассинхроне — инкрементальная
    # пересборка; штатно — walk за миллисекунды, спавн не поднимается.
    with contextlib.suppress(Exception):
        from fresh import ensure as _ensure_fresh
        _ensure_fresh(os.path.basename(db_path).replace(".db", ""))
    if args.stats:
        cmd_stats(args)
        return
    if args.empty:
        cmd_empty(args)
        return
    if args.refresh:
        import subprocess
        build_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build.py")
        cmd = [sys.executable, build_py, "-r", os.path.abspath(args.root),
               "-o", db_path]
        if args.extra_files:
            cmd += ["--extra-files"] + args.extra_files
        subprocess.run(cmd, check=True)
    if not os.path.exists(db_path):
        print(f"базы нет: {db_path}\nСначала запусти: python3 build.py -o {db_path}", file=sys.stderr)
        sys.exit(1)

    con = _connect(db_path)
    try:
        for flag, fn in ((args.symbol, cmd_symbol), (args.imports, cmd_imports),
                         (args.calls, cmd_calls), (args.deps, cmd_deps),
                         (args.inherits, cmd_inherits), (args.errors, cmd_errors)):
            if flag:
                fn(con, args)
                return

        if not args.query:
            print("задайте запрос или одну из команд: --symbol, --imports, "
                  "--calls, --deps, --inherits, --errors, --substring",
                  file=sys.stderr)
            sys.exit(1)

        cmd_search(con, args)
    finally:
        con.close()


if __name__ == "__main__":
    main()


# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
