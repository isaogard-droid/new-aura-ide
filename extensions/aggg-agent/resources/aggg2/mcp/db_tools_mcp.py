#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.




# Авторство и разработка: https://t.me/aidvizhenie · https://t.me/hilartem. Версия уникальна — и это не предел.
"""MCP-сервер базы данных чулана: поиск, карта символов, граф кода.

Обёртка над db-tools: FTS-поиск по содержимому, символы (функции/классы/
разделы с сигнатурами), граф (imports/calls/deps). Тулы синхронные —
по опыту camoufox, async-тулы в FastMCP дедлочат.

Подключение (через scripts/install/install_mcp.py) в opencode/claude/codex/deepcode.
"""
import contextlib
import os
import pathlib
import sqlite3
import subprocess
import sys

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass

from mcp.server.fastmcp import FastMCP

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Лог поисков (метрики использования) — модуль db-tools, research.db
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "db-tools"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))
import _compat
from _compat import db_connect
from log import log_search
from repomap import map_file, map_project
from search import _did_you_mean
from search_all import search_all as _search_all
from wiki_section import wiki_section as wiki_section_fn

mcp = FastMCP("db-tools")

# Базы чулана — db/ корня воркспейса (определяется автоматически по
# маркерам, без хардкода пути: mount point/ОС могут быть любыми).
DB_DIR = os.path.join(_compat.chulan_root(), "db")
ROOT = _compat.chulan_root()

def _ensure_fresh(db: str) -> bool:
    """Делегирует универсальному сторожу fresh.py (одна реализация для
    MCP/CLI/doctor): рассинхрон → инкрементальная пересборка. Штатный
    случай — walk по корню за миллисекунды, спавн ТОЛЬКО при рассинхроне."""
    with contextlib.suppress(Exception):
        from fresh import ensure as _fresh_ensure
        return _fresh_ensure(db) in ("ok", "rebuilt")
    return False


def _dbs():
    """Автообнаружение баз: каждая <имя>.db в db/ чулана становится
    доступной MCP-тулам без правки кода."""
    dbs = {}
    if os.path.isdir(DB_DIR):
        for fn in sorted(os.listdir(DB_DIR)):
            if fn.endswith(".db"):
                dbs[fn[:-3]] = os.path.join(DB_DIR, fn)
    return dbs


@contextlib.contextmanager
def _connect(db):
    """Контекстный менеджер коннекта: close в finally — в долгоживущем
    процессе MCP-сервера исключение между connect и close НЕ должно
    оставлять открытый дескриптор (ресёрч sqlite close-дисциплины,
    research.db id=689)."""
    dbs = _dbs()
    path = dbs.get(db, db)
    if not os.path.isfile(path):
        raise ValueError(
            f"база не найдена: {path} (доступны: {', '.join(dbs) or '—'}). "
            f"Проиндексируй проект: python3 db-tools/build.py -r <корень> "
            f"-o db/{db}.db — или MCP-тулом index_project(path, name)"
        )
    with db_connect(path, sqlite3.Row) as con:
        yield con


@mcp.tool()
def index_project(path: str, name: str, timeout_s: int = 180) -> str:
    """Проиндексировать проект в СВОЮ базу (lazy): любой каталог (в т.ч.
    сторонний) → db/<name>.db, дальше поиск через search/symbol с db=name.
    timeout_s — лимит на сборку (по умолчанию 180с); для больших
    каталогов передай больше, иначе сборка будет убита по таймауту
    (база при этом остаётся в прошлом согласованном состоянии — откат).

    Пример: index_project(path="/home/user/my-app", name="my-app")
    """
    root = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
    cmd = [sys.executable, str(root / "db-tools" / "build.py"),
           "-r", path, "-o", os.path.join(DB_DIR, f"{name}.db")]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired:
        return (f"таймаут индексации {path} ({timeout_s}с) — каталог "
                f"слишком большой? Повтори с timeout_s больше (база "
                f"не повреждена: SQLite откатил незавершённое).")
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode == 0:
        return f"индексация {name} готова: {out.splitlines()[-1] if out else 'ok'}"
    return f"ошибка индексации {name} (rc={proc.returncode}): {err or out[:500]}"


@mcp.tool()
def list_dbs() -> str:
    """Список доступных баз (из db/ чулана) с числом файлов в каждой."""
    out = []
    for name, path in _dbs().items():
        try:
            con = sqlite3.connect(path)
            has_files = con.execute(
                "SELECT 1 FROM sqlite_master WHERE name='files'").fetchone()
            if has_files:
                n = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
                out.append(f"{name}: {n} файлов")
            else:
                tabs = [r[0] for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")]
                out.append(f"{name}: другая схема (таблицы: "
                           f"{', '.join(tabs[:4])})")
            con.close()
        except sqlite3.Error as e:
            out.append(f"{name}: ошибка чтения ({e})")
    return "\n".join(out) if out else "баз нет — соберите через db-tools/build.py"


def _fts_safe(query: str) -> str:
    """Санитизация запроса FTS5: дефисы/спецсимволы в токенах FTS5 читает
    как операторы (NOT/колонки) → 'no such column'. Каждый токен берём в
    кавычки, кроме явных кавычек-фраз. Паттерн: hermes-agent #14024."""
    import re
    tokens = re.findall(r'"[^"]+"|\S+', query)
    out = []
    for t in tokens:
        if t.startswith('"') and t.endswith('"'):
            out.append(t)
        elif t.endswith("*") and not any(c in t[:-1] for c in '"-():^'):
            out.append(t)  # префиксный поиск: звёздочка в кавычках — литерал
        else:
            out.append(f'"{t}"')
    return " ".join(out)


@mcp.tool()
def search(query: str, db: str = "aggg2", limit: int = 10) -> str:
    """Полнотекстовый поиск по содержимому базы (aggg2 или sherpa-voice).
    Возвращает файлы со сниппетами. При пустом результате — авто-фолбэк
    на триграм-подстроку (спайк 12.08.2026). База с известным корнем
    (wiki/aggg2/sherpa-voice/...) авто-пересобирается при рассинхроне —
    устаревший индекс невозможен."""
    _ensure_fresh(db)
    try:
        with _connect(db) as con:
            rows = con.execute(
                "SELECT f.rel_path, snippet(files_fts, 1, '[', ']', '…', 12) s "
                "FROM files_fts JOIN files f ON f.id = files_fts.rowid "
                "WHERE files_fts MATCH ? ORDER BY rank LIMIT ?",
                (_fts_safe(query), limit)).fetchall()
            fallback = False
            if not rows and len(query) >= 3:
                rows = con.execute(
                    "SELECT f.rel_path, snippet(files_fts_trigram, 1, '[', ']', '…', 12) s "
                    "FROM files_fts_trigram JOIN files f ON f.id = files_fts_trigram.rowid "
                    "WHERE files_fts_trigram MATCH ? ORDER BY rank LIMIT ?",
                    (query, limit)).fetchall()
                fallback = bool(rows)
    except sqlite3.OperationalError as e:
        return f"ошибка запроса: {e}"
    log_search("mcp", db, query, len(rows))
    wiki_section = (wiki_section_fn(query, _fts_safe(query), db,
                                     {r["rel_path"] for r in rows})
                    if db != "wiki" else "")
    if not rows:
        return ("ничего не найдено" + wiki_section +
                ("\n" + dym if (dym := _did_you_mean(query, db)) else ""))
    label = " (по подстроке, авто-фолбэк)" if fallback else ""
    out = f"найдено{label}: {len(rows)}\n" + \
        "\n".join(f"{r['rel_path']}\n  …{r['s']}" for r in rows)
    if wiki_section:
        out += wiki_section
    return out


@mcp.tool()
def symbol(name: str, db: str = "aggg2") -> str:
    """Где определён символ (функция/класс/раздел): файл, строка, сигнатура."""
    with _connect(db) as con:
        rows = con.execute(
            "SELECT rel_path, name, kind, line, signature FROM symbols "
            "WHERE name LIKE ? ORDER BY rel_path, line LIMIT 20",
            (f"%{name}%",)).fetchall()
    if not rows:
        return f"символ '{name}' не найден"
    out = []
    for r in rows:
        sig = f"  {r['signature']}" if r["signature"] else ""
        out.append(f"{r['rel_path']}:{r['line']} [{r['kind']}] "
                   f"{r['name']}{sig}")
    return "\n".join(out)


@mcp.tool()
def imports(module: str, db: str = "sherpa-voice") -> str:
    """Граф: кто импортирует модуль (файл + строка)."""
    with _connect(db) as con:
        rows = con.execute(
            "SELECT rel_path, line FROM imports WHERE module = ? "
            "ORDER BY rel_path, line", (module,)).fetchall()
    if not rows:
        return f"модуль '{module}' никто не импортирует"
    return "\n".join(f"{r['rel_path']}:{r['line']}" for r in rows)


@mcp.tool()
def calls(func: str, db: str = "sherpa-voice") -> str:
    """Граф: кто вызывает функцию (файл + строка)."""
    with _connect(db) as con:
        rows = con.execute(
            "SELECT rel_path, line FROM calls WHERE callee = ? "
            "ORDER BY rel_path, line", (func,)).fetchall()
    if not rows:
        return f"функцию '{func}' никто не вызывает"
    return "\n".join(f"{r['rel_path']}:{r['line']}" for r in rows)


@mcp.tool()
def deps(file: str, db: str = "sherpa-voice") -> str:
    """Граф: какие модули импортирует файл."""
    with _connect(db) as con:
        rows = con.execute(
            "SELECT module, line FROM imports WHERE rel_path = ? ORDER BY line",
            (file,)).fetchall()
    if not rows:
        return f"файл '{file}' ничего не импортирует (или нет в базе)"
    return "\n".join(f"  {r['module']}  (строка {r['line']})" for r in rows)


def _resolve_auto(file):
    """db='auto': файл ищется по ВСЕМ базам db/ (приоритет workspace,
    skills — SQLite ATTACH-паттерн федерации, у нас дешевле: lookup по
    rel_path). Возвращает (db, rel) или (None, None)."""
    from links import find_file  # noqa: PLC0415
    found = []
    for name in sorted(_dbs()):
        try:
            with _connect(name) as con:
                rel, _ = find_file(con, file)
                if rel:
                    found.append((name, rel))
        except Exception:  # noqa: BLE001 — одна битая база не роняет поиск
            pass
    if not found:
        return None, None
    for pref in ("aggg2", "skills"):
        for name, rel in found:
            if name == pref:
                return name, rel
    return found[0]


def _resolve(file, db):
    """Общий резолвер: db='auto' — по всем базам, иначе в указанной."""
    if db == "auto":
        return _resolve_auto(file)
    with _connect(db) as con:
        from links import find_file  # noqa: PLC0415
        rel, cands = find_file(con, file)
        if rel is None and cands:
            return db, f"НЕОДНОЗНАЧНО:{'; '.join(cands)}"
        return db, rel


@mcp.tool()
def links(file: str, db: str = "auto", limit: int = 15) -> str:
    """Карта связей ЛЮБОГО файла/скилла/дока — обе стороны графа:
    что импортирует/вызывает + кто импортирует/вызывает (по символам,
    kind-фильтр, без коротких общих имён) + кто упоминает в доках.
    db='auto' (по умолчанию) — файл сам ищется по всем базам
    (workspace — корень AGGG2.0, skills — скиллы, vpn-gui/sherpa-voice —
    проекты); db='workspace' — только в ней. Живые данные, fresh.py
    пересобирает при рассинхроне."""
    from links import links_for  # noqa: PLC0415
    name, rel = _resolve(file, db)
    if rel is None:
        return (f"файл '{file}' не найден ни в одной базе. Базу: "
                f"index_project(path, name) / build.py -r <корень>")
    if isinstance(rel, str) and rel.startswith("НЕОДНОЗНАЧНО:"):
        return f"неоднозначно '{file}': {rel.split(':', 1)[1]} — уточни путь"
    with _connect(name) as con:
        return links_for(con, rel, limit=limit)


@mcp.tool()
def doc_links_check(file: str, db: str = "auto", target: str = "") -> str:
    """Staleness detection: свежая ли секция «Связанные» (маркер
    AUTO-GENERATED) в md-файле — сравнение с базой БЕЗ записи. Ответ:
    свежая / устарела (что делать) / секции нет. Для аудита перед
    раздачей и после правок канона."""
    from links import check_section  # noqa: PLC0415
    name, rel = _resolve(file, db)
    if rel is None:
        return f"файл '{file}' не найден ни в одной базе"
    with _connect(name) as con:
        return check_section(con, rel, target_path=target or None)


@mcp.tool()
def doc_links_refresh(file: str, db: str = "auto",
                      target: str = "", limit: int = 15) -> str:
    """Живая документация: вставляет/обновляет секцию «Связанные»
    (маркер AUTO-GENERATED) в md-файле — связи из базы, ручной контент
    не трогается. db='auto' — файл ищется по всем базам. Только
    md/txt-файлы. Пример: doc_links_refresh('CYCLE.md')"""
    from links import refresh_section  # noqa: PLC0415
    name, rel = _resolve(file, db)
    if rel is None:
        return f"файл '{file}' не найден ни в одной базе"
    with _connect(name) as con:
        return refresh_section(con, rel, target_path=target or None,
                               limit=limit)


@mcp.tool()
def db_stats(db: str = "aggg2") -> str:
    """Сколько файлов, символов, рёбер в базе."""
    with _connect(db) as con:
        n = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        s = con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        try:
            i = con.execute("SELECT COUNT(*) FROM imports").fetchone()[0]
            c = con.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        except sqlite3.Error:
            i = c = 0
    return (f"файлов: {n}, символов: {s}, импортов: {i}, вызовов: {c}")


@mcp.tool()
def repo_map(db: str = "aggg2", path: str = "", tokens: int = 1500) -> str:
    """Карта для промпта агента (паттерн repo-map): path='' — карта всего
    проекта (PageRank по импорт-графу, топ-файлы с символами в
    токен-бюджете); path=<файл> — карта одного файла (символы + кто его
    зовёт + кого он зовёт). Ориентация в коде без чтения файлов."""
    with _connect(db) as con:
        if path:
            return map_file(con, path, tokens=tokens)
        return map_project(con, tokens=tokens)


@mcp.tool()
def search_all(query: str, limit: int = 5, substring: bool = False) -> str:
    """Поиск по ВСЕМ базам воркспейса сразу (multi-DB, паттерн srclight
    ATTACH+UNION): «где это лежит» одним запросом. substring=True —
    триграм-подстрока (находит склонения: «настройк» → настройка/
    настройки)."""
    rows = _search_all(query, limit=limit, substring=substring,
                       db_dir=DB_DIR)
    if not rows:
        return "ничего не найдено ни в одной базе"
    out = []
    for name, rel_path, snip in rows:
        out.append(f"[{name}] {rel_path}\n  {snip}")
    bases = {n for n, _, _ in rows}
    return "\n".join(out) + f"\n\nитого: {len(rows)} в {len(bases)} базах"


if __name__ == "__main__":
    mcp.run()

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
