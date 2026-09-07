# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Связи находок: link add/list/rm, related (соседи и граф до depth).

Вынесено из db-tools/findings.py (механическая резка god-файла, код дословно).
БД и connect() — в findings.py.
"""
import datetime
import sys

from findings import connect


def _row_links(cur, fid):
    """Связи находки в обе стороны: [(направление, связанный_id, kind, note)]."""
    out = []
    for r in cur.execute(
            "SELECT l.id link_id, l.from_id, l.to_id, l.kind, l.note, "
            "f.topic FROM links l JOIN findings f ON f.id = "
            "CASE WHEN l.from_id = ? THEN l.to_id ELSE l.from_id END "
            "WHERE l.from_id = ? OR l.to_id = ? ORDER BY l.id",
            (fid, fid, fid)).fetchall():
        direction = "->" if r["from_id"] == fid else "<-"
        out.append((r["link_id"], direction, r["kind"], r["topic"],
                    r["note"]))
    return out


def cmd_link_add(args):
    con = connect()
    cur = con.cursor()
    for fid in (args.from_id, args.to_id):
        if not cur.execute("SELECT 1 FROM findings WHERE id = ?",
                           (fid,)).fetchone():
            print(f"находки с id={fid} нет", file=sys.stderr)
            con.close()
            sys.exit(1)
    cur.execute(
        "INSERT INTO links (from_id, to_id, kind, note, created) "
        "VALUES (?,?,?,?,?)",
        (args.from_id, args.to_id, args.kind, args.note or "",
         datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")))
    con.commit()
    print(f"[✓] связь: {args.from_id} --{args.kind}--> {args.to_id} (id={cur.lastrowid})")
    con.close()


def cmd_link_list(args):
    con = connect()
    cur = con.cursor()
    if not cur.execute("SELECT 1 FROM findings WHERE id = ?",
                       (args.id,)).fetchone():
        print(f"находки с id={args.id} нет")
        con.close()
        return
    links = _row_links(cur, args.id)
    if not links:
        print(f"у находки [{args.id}] связей нет")
        con.close()
        return
    print(f"связи находки [{args.id}]:\n")
    for _link_id, direction, kind, topic, note in links:
        note_s = f"  ({note})" if note else ""
        print(f"  {direction} {kind:12} [{_link_id}] {topic}{note_s}")
    con.close()


def cmd_link_rm(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT id, from_id, to_id, kind FROM links WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"связи с id={args.id} нет")
        return
    cur.execute("DELETE FROM links WHERE id = ?", (args.id,))
    con.commit()
    print(f"[✓] связь удалена: {row['from_id']} --{row['kind']}--> {row['to_id']}")
    con.close()


def cmd_related(args):
    """Быстрый ответ на «что связано с этой находкой»: id + темы.
    --depth N — транзитивные связи (граф по links, KG-паттерн
    mcp-memory entities/relations: цепочки знаний, а не только соседи)."""
    con = connect()
    cur = con.cursor()
    if getattr(args, "depth", 0) > 0:
        _print_chain(cur, args.id, args.depth)
        con.close()
        return
    links = _row_links(cur, args.id)
    if not links:
        print(f"у находки [{args.id}] связей нет")
        con.close()
        return
    print(f"связано с [{args.id}]:\n")
    for _link_id, direction, kind, topic, note in links:
        note_s = f"  ({note})" if note else ""
        print(f"  {direction} {kind:12} {topic}{note_s}")
    con.close()


def _print_chain(cur, fid, depth):
    """Граф связей до глубины depth: recursive CTE по links."""
    rows = cur.execute(
        "WITH RECURSIVE chain(id, d, path) AS ("
        "  SELECT ?, 0, '' "
        "  UNION "
        "  SELECT CASE WHEN l.from_id = chain.id THEN l.to_id "
        "              ELSE l.from_id END,"
        "         chain.d + 1,"
        "         chain.path || ' >' || l.kind || '> '"
        "  FROM links l JOIN chain "
        "  ON (l.from_id = chain.id OR l.to_id = chain.id) "
        "  AND chain.d < ?"
        ") SELECT DISTINCT c.id, MIN(c.d) AS d, "
        "  (SELECT path FROM chain c2 WHERE c2.id = c.id "
        "   ORDER BY c2.d LIMIT 1) AS path, "
        "  (SELECT topic FROM findings f WHERE f.id = c.id) AS topic "
        "FROM chain c WHERE c.id != ? GROUP BY c.id ORDER BY d",
        (fid, depth, fid)).fetchall()
    if not rows:
        print(f"у находки [{fid}] связей нет")
        return
    print(f"граф связей [{fid}] (глубина {depth}):\n")
    for r in rows:
        print(f"  [{r['id']}] d={r['d']}  {r['topic']}")
        if r["path"]:
            print(f"       путь: {r['path'].strip()}")
