# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Команды базы находок: add/del/edit/search/list/show/stats/supersede/consolidate.

Вынесено из db-tools/findings.py (механическая резка god-файла, код дословно).
БД и connect() — в findings.py (DB переопределяется тестами на модуле).
"""
import datetime
import re
import sqlite3
import sys

from findings import connect, sanitize_query
from findings_links import _row_links


def cmd_add(args):
    con = connect()
    cur = con.cursor()
    if not args.source:
        print("[~] подсказка: --source не указан; для веб-фактов указывай "
              "URL/путь (верификация, research.db id=367)", file=sys.stderr)
    dup = cur.execute(
        "SELECT id, topic FROM findings WHERE topic = ? LIMIT 1",
        (args.topic,)).fetchone()
    if dup:
        print(f"[!] уже есть находка с такой темой: id={dup['id']} "
              f"«{dup['topic']}» — добавляю дубликат", file=sys.stderr)
    cur.execute(
        "INSERT INTO findings (created, topic, text, tags, source) "
        "VALUES (?,?,?,?,?)",
        (datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
         args.topic, args.text, args.tags, args.source or ""))
    new_id = cur.lastrowid
    for rel in _parse_ids(args.related):
        if rel != new_id:
            cur.execute(
                "INSERT INTO links (from_id, to_id, kind, note, created) "
                "VALUES (?,?,?,?,?)",
                (new_id, rel, "related", "",
                 datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")))
    con.commit()
    print(f"[✓] добавлено: {args.topic} (id={new_id})")
    if args.related:
        print(f"    связан с: {args.related}")
    con.close()


def _parse_ids(s):
    """'1,2, 3' -> [1, 2, 3]; мусор пропускаем."""
    out = []
    for part in (s or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def cmd_del(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT topic FROM findings WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"находки с id={args.id} нет")
        return
    cur.execute("DELETE FROM findings WHERE id = ?", (args.id,))
    n_links = cur.execute(
        "DELETE FROM links WHERE from_id = ? OR to_id = ?",
        (args.id, args.id)).rowcount
    con.commit()
    print(f"[✓] удалено: id={args.id} «{row['topic']}»"
          + (f" (связей удалено: {n_links})" if n_links else ""))
    con.close()


def _status_filter(choice):
    """'live'/'active'/'superseded'/'archived'/'all' -> SQL-условие (или '').

    live = только активные: superseded и archived снимаются с выдачи
    по умолчанию, видны через --status superseded/archived/all."""
    if choice == "all":
        return ""
    if choice == "live":
        return "f.status = 'active'"
    return f"f.status = '{choice}'"


def cmd_supersede(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT topic FROM findings WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"находки с id={args.id} нет")
        con.close()
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    topic = row["topic"]
    if args.note:
        suffix = f"\n\n[устарело {now}] {args.note}"
        cur.execute(
            "UPDATE findings SET status = 'superseded', updated = ?, "
            "text = text || ? WHERE id = ?", (now, suffix, args.id))
    else:
        cur.execute(
            "UPDATE findings SET status = 'superseded', updated = ? WHERE id = ?",
            (now, args.id))
    con.commit()
    print(f"[✓] superseded: id={args.id} «{topic}»"
          + (f" — {args.note}" if args.note else ""))
    print("    выдача по умолчанию (live) её больше не показывает")
    con.close()


def _cmd_dupes(con, args):
    """Почти-дубликаты активных находок (difflib по нормализованным темам).
    --apply архивирует старшие дубликаты (младший id остаётся жить)."""
    import difflib
    rows = con.execute(
        "SELECT id, topic FROM findings WHERE status='active' ORDER BY id"
    ).fetchall()

    def norm(s):
        return re.sub(r"\s+", " ", str(s).strip().lower())

    topics = {r["id"]: norm(r["topic"]) for r in rows}
    ids = sorted(topics)
    pairs = []
    for i in range(len(ids)):
        a = topics[ids[i]]
        for j in range(i + 1, len(ids)):
            b = topics[ids[j]]
            if abs(len(a) - len(b)) > max(4, len(a) // 3):
                continue
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio >= 0.82:
                pairs.append((ids[i], ids[j], round(ratio, 2)))
    if not pairs:
        print("почти-дубликатов не найдено")
        return
    print(f"почти-дубликаты (темы совпадают на >=82%): {len(pairs)} пар\n")
    for a, b, r in pairs:
        print(f"  [{a}] <-> [{b}]  ({r})  {topics[a][:80]}")
    if not args.apply:
        print("\nпросмотр: без архивации. Архив старших дубликатов: --apply")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    dupes = sorted({b for _, b, _ in pairs})
    for did in dupes:
        con.execute("UPDATE findings SET status='archived', updated=? "
                    "WHERE id=?", (now, did))
    con.commit()
    print(f"[✓] заархивировано дубликатов: {len(dupes)} "
          f"(id: {', '.join(map(str, dupes))})")


def cmd_consolidate(args):
    con = connect()
    cur = con.cursor()
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    if getattr(args, "dupes", False):
        _cmd_dupes(con, args)
        con.close()
        return
    if args.id:
        if not args.apply:
            print("--id работает только вместе с --apply", file=sys.stderr)
            con.close()
            return
        placeholders = ",".join("?" * len(args.id))
        rows = cur.execute(
            f"SELECT id, created, topic FROM findings "
            f"WHERE id IN ({placeholders}) AND status != 'archived' "
            f"ORDER BY id", args.id).fetchall()  # noqa: S608 — id из CLI, int
        for r in rows:
            cur.execute(
                "UPDATE findings SET status = 'archived', updated = ? WHERE id = ?",
                (now, r["id"]))
        con.commit()
        for r in rows:
            print(f"[✓] archived: id={r['id']} «{r['topic']}»")
        print(f"итого заархивировано: {len(rows)}")
        con.close()
        return
    cutoff = (datetime.datetime.now().astimezone() -
              datetime.timedelta(days=args.days)).strftime("%Y-%m-%d %H:%M")
    rows = cur.execute(
        "SELECT f.id, f.created, f.topic, "
        "(SELECT COUNT(*) FROM links l WHERE l.from_id = f.id "
        "   OR l.to_id = f.id) AS nl "
        "FROM findings f "
        "WHERE f.status = 'active' AND f.created < ? "
        "  AND (f.updated = '' OR f.updated < ?) "
        "ORDER BY f.id", (cutoff, cutoff)).fetchall()
    if not rows:
        print(f"кандидатов на архив нет (старше {args.days} дней, без обновлений)")
        con.close()
        return
    print(f"кандидаты на архив (старше {args.days} дн., без обновлений, "
          f"всего {len(rows)}):")
    for r in rows:
        links = f", связей: {r['nl']}" if r["nl"] else ""
        print(f"  [{r['id']}] {r['created']}  {r['topic']}{links}")
    if not args.apply:
        print("\nпросмотр: показать без архивации. Архив: --apply; "
              "точечно: consolidate --id 1 2 --apply")
    else:
        cur.executemany(
            "UPDATE findings SET status = 'archived', updated = ? WHERE id = ?",
            [(now, r["id"]) for r in rows])
        con.commit()
        print(f"[✓] заархивировано: {len(rows)}")
    con.close()


def cmd_edit(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM findings WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"находки с id={args.id} нет")
        return
    sets, params = [], []
    for col, val in (("topic", args.topic), ("text", args.text),
                     ("tags", args.tags), ("source", args.source)):
        if val is not None:
            sets.append(f"{col} = ?")
            params.append(val)
    if not sets:
        print("нечего менять: укажите --topic/--text/--tags")
        return
    params.append(args.id)
    # Колонки — фиксированный список выше (topic/text/tags/source),
    # значения — только параметры: инъекции нет.
    cur.execute(f"UPDATE findings SET {', '.join(sets)} WHERE id = ?", params)  # noqa: S608 — колонки whitelist, значения params; nosemgrep
    con.commit()
    print(f"[✓] обновлено: id={args.id} «{row['topic']}»")
    con.close()


def cmd_search(args):
    con = connect()
    cur = con.cursor()
    sql = ("SELECT f.id, f.created, f.topic, f.tags, "
           "snippet(findings_fts, 1, '[', ']', '…', 12) AS snip "
           "FROM findings_fts JOIN findings f ON f.id = findings_fts.rowid "
           "WHERE findings_fts MATCH ?")
    params = [sanitize_query(args.query)]
    source = getattr(args, "source", "")
    tag = getattr(args, "tag", "")
    if source:
        sql += " AND f.source LIKE ?"
        params.append(f"%{source}%")
    if tag:
        sql += " AND ' '||f.tags||' ' LIKE ?"
        params.append(f"% {tag} %")
    status = getattr(args, "status", "live")
    if status:
        cond = _status_filter(status)
        if cond:
            sql += f" AND {cond}"
    sql += " ORDER BY f.id DESC LIMIT ?"
    params.append(args.limit)
    try:
        rows = cur.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        print(f"неверный запрос: {e}", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print(f"ничего не найдено по «{args.query}»"
              + (f" (source ~ «{source}»)" if source else "")
              + (f" (тег «{tag}»)" if tag else ""))
        print("подсказка: короче (2-3 слова, без склонений); ЗНАНИЯ (посты,"
              " инструкции, разборы инструментов) — search.py -b db/wiki.db"
              " (или MCP search, db: wiki); «где лежит» по всем базам —"
              " search_all.py")
        return
    print(f"найдено: {len(rows)}\n")
    for r in rows:
        print(f"[{r['id']}] {r['created']}  {r['topic']}  ({r['tags']})")
        print(f"  …{r['snip']}")
        print()
    con.close()


def cmd_list(args):
    con = connect()
    cur = con.cursor()
    status = getattr(args, "status", "live")
    cond = _status_filter(status)
    base = "SELECT id, created, topic, tags, status FROM findings f"
    where, params = [], []
    if args.tags:
        where.append("' '||f.tags||' ' LIKE ?")
        params.append(f"% {args.tags} %")
    if cond:
        where.append(cond)
    sql = base + ((" WHERE " + " AND ".join(where)) if where else "") + \
        " ORDER BY id DESC LIMIT ?"
    params.append(args.limit)
    rows = cur.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query — SQL fragments are fixed allowlisted predicates; all user values are bound params
        sql, params).fetchall()
    if not rows:
        print("пока пусто — добавьте первую находку: findings.py add «тема»")
        return
    print(f"всего: {len(rows)}\n")
    for r in rows:
        badge = "" if r["status"] == "active" else f" [{r['status']}]"
        print(f"[{r['id']}] {r['created']}  {r['topic']}  ({r['tags']}){badge}")
    con.close()


def cmd_show(args):
    con = connect()
    cur = con.cursor()
    r = cur.execute("SELECT * FROM findings WHERE id = ?",
                    (args.id,)).fetchone()
    if not r:
        print(f"находки с id={args.id} нет")
        con.close()
        return
    print(f"[{r['id']}] {r['created']}  {r['topic']}"
          + (f"  [{r['status']}]" if r["status"] != "active" else ""))
    if r["tags"]:
        print(f"теги: {r['tags']}")
    if r["source"]:
        print(f"источник: {r['source']}")
    if r["updated"]:
        print(f"обновлено: {r['updated']}")
    print()
    print(r["text"])
    links = _row_links(cur, args.id)
    if links:
        print("\nсвязи:")
        for _link_id, direction, kind, topic, note in links:
            note_s = f"  ({note})" if note else ""
            print(f"  {direction} {kind:12} {topic}{note_s}")
    con.close()


def cmd_stats(args):
    con = connect()
    cur = con.cursor()
    total = cur.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
    week_ago = (datetime.datetime.now().astimezone() -
                datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    last7 = cur.execute("SELECT COUNT(*) FROM findings WHERE created >= ?",
                        (week_ago,)).fetchone()[0]
    nlinks = cur.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    print(f"находок: {total}  (за 7 дней: {last7})  связей: {nlinks}")
    by_status = cur.execute(
        "SELECT status, COUNT(*) n FROM findings GROUP BY status").fetchall()
    if by_status:
        parts = [f"{r['status']}: {r['n']}" for r in by_status]
        print("по статусам: " + ", ".join(parts))
    tags = cur.execute(
        "SELECT tags, COUNT(*) n FROM findings GROUP BY tags "
        "ORDER BY n DESC LIMIT 10").fetchall()
    if tags and any(r["tags"] for r in tags):
        print("\nтоп тегов (набор | сколько):")
        for r in tags:
            if r["tags"]:
                print(f"  {r['tags']:40} | {r['n']}")
    con.close()
