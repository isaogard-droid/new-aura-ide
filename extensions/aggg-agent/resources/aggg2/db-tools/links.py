#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""links: карта связей файла/скилла/дока — обе стороны графа.

links_for(db, file): что файл импортирует/вызывает + кто его
импортирует/вызывает + кто упоминает в доках (FTS/LIKE по содержимому).
Живая документация: данные из базы (build.py), ноль нового индекса.

refresh_section(db, file, target): вставляет/обновляет секцию «Связанные»
с маркером AUTO-GENERATED в md-файле (living docs, паттерн falconer:
staleness detection + auto-update; CodeGraph stale-docs). Маркер защищает
секцию от ручных правок — агенты обновляют только между маркерами.

Паттерн индустрии (ресёрч 18.08.2026, 50 источников): codebase-memory-mcp
(120x меньше токенов на структурные вопросы), CodeGraph (42 MCP тула,
stale docs в PR), aider repo map (PageRank). Наш граф — уже в db-tools.
"""
import os
import re
import sqlite3

# --- поиск файла в базе ---
DOC_EXTS = {".md", ".txt", ".rst", ".markdown"}

# Короткие общие имена — шум графа: callee 'main' в одном файле ≠ символ
# 'main' в другом (встроенные и частые функции). Отсекаем при
# сопоставлении «кто вызывает функции файла» (эвристика, PyCG-паттерн:
# точность важнее полноты).
_CALLER_STOP = {
    "main", "run", "init", "get", "set", "add", "new", "read", "write",
    "close", "open", "start", "stop", "print", "log", "save", "load",
    "find", "make", "next", "exec", "help", "info", "data", "test",
    "check", "clean", "build", "create", "update", "delete", "list",
    "show", "parse", "process", "execute", "fetchone", "fetchall",
    "connect", "append", "insert", "cursor", "items", "keys", "values",
}


def _db_root(con):
    try:
        row = con.execute("SELECT value FROM meta WHERE key='root'").fetchone()
        if row:
            return row[0]
    except sqlite3.Error:
        pass
    return None


def find_file(con, file):
    """Точный rel_path, при неоднозначном частичном — список кандидатов.
    Возвращает (rel_path, [кандидаты]) — кандидаты при неоднозначности.
    Базы хранят rel-пути от СВОЕГО корня (skills.db — от skills/,
    workspace.db — от корня AGGG2.0): пошагово точный → суффикс пути →
    basename (последний уровень — самый неоднозначный, только если
    первые пусты)."""
    file = file.strip().lstrip("./")
    parts = file.split("/")
    levels = [file] + (["/".join(parts[1:])] if len(parts) > 1 else []) \
        + [parts[-1]]
    for level in levels:
        if not level:
            continue
        row = con.execute("SELECT rel_path FROM files WHERE rel_path = ?",
                          (level,)).fetchone()
        if row:
            return row[0], []
        rows = con.execute(
            "SELECT rel_path FROM files WHERE rel_path LIKE ? LIMIT 20",
            (f"%{level}",)).fetchall()
        cands = sorted({r[0] for r in rows})
        if len(cands) == 1:
            return cands[0], []
        if cands:
            return None, cands[:10]
    return None, []


def _module_names(rel_path):
    """Имена модуля, под которыми файл могут импортировать."""
    base = os.path.basename(rel_path)
    stem = re.sub(r"\.(py|js|ts|rb|go|rs)$", "", base)
    return {base, stem}


def _doc_mentions(con, rel_path, limit=15):
    """Кто упоминает файл в доках (по имени файла и пути в тексте)."""
    base = os.path.basename(rel_path)
    stem = re.sub(r"\.[a-z0-9]+$", "", base)
    names = [base, stem, rel_path]
    rows = con.execute(
        "SELECT rel_path FROM files WHERE ext IN (?,?,?,?) "
        "ORDER BY rel_path", tuple(sorted(DOC_EXTS))).fetchall()
    out = []
    for (doc_path,) in rows:
        if doc_path == rel_path:
            continue
        content = con.execute("SELECT content FROM files WHERE rel_path=?",
                              (doc_path,)).fetchone()
        if not content:
            continue
        text = content[0] or ""
        for nm in names:
            if nm in text:
                out.append(doc_path)
                break
    return out[:limit]


def links_for(con, rel_path, limit=15):
    """Полная карта связей файла: импорты/вызовы обе стороны + доки."""
    out = []
    # 1) что файл импортирует
    deps_rows = con.execute(
        "SELECT module, line FROM imports WHERE rel_path=? ORDER BY line",
        (rel_path,)).fetchall()
    if deps_rows:
        out.append(f"ИМПОРТИРУЕТ ({len(deps_rows)}):")
        for r in deps_rows[:limit]:
            out.append(f"  {r[0]}  (строка {r[1]})")
        if len(deps_rows) > limit:
            out.append(f"  ... ещё {len(deps_rows) - limit}")
    # 2) кто импортирует файл (по имени модуля)
    mods = _module_names(rel_path)
    imp_rows = con.execute(
        "SELECT DISTINCT rel_path, module, line FROM imports "
        "WHERE rel_path != ? ORDER BY rel_path, line", (rel_path,)).fetchall()
    importers = []
    for r in imp_rows:
        for m in mods:
            if m in r[1]:
                importers.append((r[0], r[2]))
                break
    if importers:
        out.append(f"ИМПОРТИРУЕТСЯ ({len(importers)}):")
        for rel, line in importers[:limit]:
            out.append(f"  {rel}:{line}")
        if len(importers) > limit:
            out.append(f"  ... ещё {len(importers) - limit}")
    # 3) что файл вызывает
    call_rows = con.execute(
        "SELECT callee, line FROM calls WHERE rel_path=? ORDER BY line",
        (rel_path,)).fetchall()
    if call_rows:
        out.append(f"ВЫЗЫВАЕТ ({len(call_rows)}):")
        for r in call_rows[:limit]:
            out.append(f"  {r[0]}  (строка {r[1]})")
        if len(call_rows) > limit:
            out.append(f"  ... ещё {len(call_rows) - limit}")
    # 4) кто вызывает функции файла (символы файла → callee; kind-фильтр:
    # только function/class/method, без коротких общих имён — шум графа)
    sym_rows = con.execute(
        "SELECT DISTINCT name FROM symbols WHERE rel_path=? AND kind IN "
        "('function','class','method')", (rel_path,)).fetchall()
    if sym_rows:
        syms = [r[0] for r in sym_rows
                if r[0] not in _CALLER_STOP and len(r[0]) >= 5]
        if syms:
            ph = ",".join("?" * len(syms))
            callers = con.execute(
                f"SELECT DISTINCT rel_path FROM calls WHERE callee IN ({ph}) "
                "AND rel_path != ? ORDER BY rel_path LIMIT ?",
                (*syms, rel_path, limit)).fetchall()
            if callers:
                out.append(f"ВЫЗЫВАЕТСЯ ИЗ ({len(callers)}):")
                for r in callers:
                    out.append(f"  {r[0]}")
    # 5) кто упоминает в доках
    docs = _doc_mentions(con, rel_path, limit)
    if docs:
        out.append(f"УПОМИНАЕТСЯ В ДОКАХ ({len(docs)}):")
        for d in docs:
            out.append(f"  {d}")
    return "\n".join(out) if out else "связей не найдено (файл изолирован)"


# --- секция «Связанные» в md-файле (живая документация) ---
OPEN = "<!-- AUTO-GENERATED: doc-links -->"
CLOSE = "<!-- /AUTO-GENERATED: doc-links -->"


def _section_text(con, rel_path, limit=15):
    lines = ["## Связанные (AUTO-GENERATED)", ""]
    body = links_for(con, rel_path, limit=limit)
    for ln in body.splitlines():
        lines.append(("  " + ln) if ln.strip() and not ln[0].isspace()
                     else ln)
    lines += ["", "Правки только между маркерами — содержимое "
                   "перегенерируется `doc_links refresh`.", ""]
    return "\n".join(lines)


def check_section(con, rel_path, target_path=None, limit=15):
    """Staleness detection (falconer/CodeGraph-паттерн): свежая ли секция
    «Связанные» в md-файле — сравнение с перегенерированной БЕЗ записи.
    Возвращает вердикт: свежая / устарела / секции нет."""
    if target_path is None:
        root = _db_root(con)
        if not root:
            return "корень базы не найден — укажи target_path"
        target_path = os.path.join(root, rel_path)
    if not os.path.isfile(target_path):
        return f"файл не существует: {target_path}"
    with open(target_path, encoding="utf-8") as fh:
        raw = fh.read()
    if OPEN not in raw:
        return "секции нет (вставить: doc_links_refresh)"
    m = re.search(re.escape(OPEN) + r"(.*?)" + re.escape(CLOSE),
                  raw, flags=re.DOTALL)
    if not m:
        return "секции нет (вставить: doc_links_refresh)"
    want = "\n" + _section_text(con, rel_path, limit) + "\n"
    if m.group(1).strip() == want.strip():
        return "секция свежая"
    return "устарела: doc_links refresh"


def refresh_section(con, rel_path, target_path=None, limit=15):
    """Вставить/обновить секцию «Связанные» в md-файле. target_path —
    физический путь; None — корень базы + rel_path. Возвращает текст
    результата или ошибку-строку."""
    if not rel_path.lower().endswith(tuple(DOC_EXTS)):
        return (f"секция «Связанные» только для md/txt-файлов: {rel_path} "
                f"(у кода связи смотри тулом links)")
    if target_path is None:
        root = _db_root(con)
        if not root:
            return "корень базы не найден — укажи target_path"
        target_path = os.path.join(root, rel_path)
    if not os.path.isfile(target_path):
        return f"файл не существует: {target_path}"
    with open(target_path, encoding="utf-8") as fh:
        raw = fh.read()
    section = _section_text(con, rel_path, limit)
    n_items = len(section.splitlines())
    if OPEN in raw and CLOSE in raw:
        new = re.sub(re.escape(OPEN) + r".*?" + re.escape(CLOSE),
                     OPEN + "\n" + section + "\n" + CLOSE,
                     raw, flags=re.DOTALL)
        verb = "обновлено"
    else:
        new = raw.rstrip() + "\n\n" + OPEN + "\n" + section + "\n" + CLOSE + "\n"
        verb = "вставлено"
    with open(target_path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return f"{verb} в {target_path} ({n_items} строк)"
