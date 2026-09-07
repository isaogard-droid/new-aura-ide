#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# -*- coding: utf-8 -*-
"""Skill-usage report: какие скиллы реально загружались агентами.

Источник данных — база сессий opencode (opencode.db, таблица part:
tool-вызовы "skill" с именем скилла и временем). Сравнивает с каноном
skills/ и показывает использованные / мёртвые скиллы.

Запуск:
    python3 scripts/skill_usage.py                  # по умолчанию
    python3 scripts/skill_usage.py --db ~/.local/share/opencode/opencode.db
    python3 scripts/skill_usage.py --top 5 --json

Мотивация (research.db id=362): observability скиллов — вручную нашли,
что fable-* загружались 1 раз за 546 сессий; скрипт автоматизирует
курацию: мёртвые скиллы -> чистка или вшивание.
"""
import json

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass


def _find_opencode_db(explicit):
    """Путь к opencode.db: явный аргумент > стандартные локации."""
    if explicit:
        return Path(explicit).expanduser()
    candidates = [
        Path.home() / ".local/share/opencode/opencode.db",   # Linux/macOS
        Path.home() / ".config/opencode/opencode.db",       # альтернатива
        Path(os.environ.get("LOCALAPPDATA", "")) / "opencode/opencode.db",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return candidates[0]


def load_usage(db_path):
    """Скилл -> (число вызовов, последний вызов unix_ms)."""
    usage = {}
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT json_extract(data,'$.state.input.name') AS sk, "
            "MAX(time_created) AS last_ts, COUNT(*) AS n "
            "FROM part "
            "WHERE json_extract(data,'$.tool')='skill' AND sk IS NOT NULL "
            "GROUP BY sk"
        ).fetchall()
        for sk, last_ts, n in rows:
            usage[sk] = (n, last_ts or 0)
    finally:
        con.close()
    return usage


def load_canon(canon_root):
    """Имена скиллов: (канон skills/, скиллы агентов agent/*/skills/).

    Раздельно: скиллы агентов (reverser и др.) вызываются в сессиях
    субагентов и 0 вызовов для них — не «мёртвый канон», а холодный
    инструмент узкого специалиста (14.08.2026: 12 reverser-скиллов
    засоряли список мёртвых).
    """
    canon, agent_skills = set(), set()
    root = Path(canon_root).expanduser()
    for sk in sorted((root / "skills").glob("*/SKILL.md")):
        canon.add(sk.parent.name)
    for sk in sorted((root / "agent").glob("*/skills/*/SKILL.md")):
        agent_skills.add(sk.parent.name)
    return canon, agent_skills


def _fmt_ts(ms):
    if not ms:
        return "никогда"
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Skill-usage report по opencode.db")
    ap.add_argument("--db", help="путь к opencode.db (по умолчанию — автопоиск)")
    ap.add_argument("--canon", default=os.environ.get("AGGG2_ROOT", "."),
                    help="корень воркспейса с skills/ (по умолчанию AGGG2_ROOT или .)")
    ap.add_argument("--top", type=int, default=10, help="топ используемых (0 = все)")
    ap.add_argument("--json", action="store_true", help="вывод в JSON")
    args = ap.parse_args()

    db_path = _find_opencode_db(args.db)
    if not db_path.is_file():
        print(f"[✗] opencode.db не найден: {db_path}", file=sys.stderr)
        print("    укажи --db <путь>", file=sys.stderr)
        sys.exit(1)

    usage = load_usage(db_path)
    canon, agent_skills = load_canon(args.canon)
    all_skills = sorted(canon | agent_skills | set(usage))
    used = {s: usage[s] for s in all_skills if s in usage}
    dead = sorted(canon - set(usage))
    dead_agent = sorted(agent_skills - set(usage))
    total_calls = sum(n for n, _ in usage.values())

    if args.json:
        print(json.dumps({
            "db": str(db_path),
            "total_skills": len(all_skills),
            "canon_skills": len(canon),
            "used_skills": len(used),
            "dead_skills": dead,
            "total_calls": total_calls,
            "top": sorted(used.items(), key=lambda kv: -kv[1][0])[:args.top],
        }, ensure_ascii=False, indent=1))
        return

    print(f"база сессий: {db_path}")
    print(f"скиллов в каноне: {len(canon)} | использовано: {len(used)} "
          f"| мёртвых: {len(dead)} | вызовов всего: {total_calls}")
    print()

    if used:
        print("используемые (топ):")
        for sk, (n, last_ts) in sorted(used.items(),
                                       key=lambda kv: -kv[1][0])[:args.top]:
            print(f"  {sk:<32} {n:>4} вызовов, последний {_fmt_ts(last_ts)}")
        if len(used) > args.top:
            print(f"  … и ещё {len(used) - args.top} (всего использовано {len(used)})")
        print()

    if dead:
        print("мёртвые канона (0 вызовов — кандидаты на чистку/вшивание):")
        for sk in dead:
            print(f"  {sk}")
    else:
        print("мёртвых в каноне нет — все скиллы канона используются")

    if dead_agent:
        print()
        print("скиллы агентов без вызовов в общих сессиях (холодные — ждут"
              " задач своего агента):")
        for sk in dead_agent:
            print(f"  {sk}")


if __name__ == "__main__":
    main()

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
