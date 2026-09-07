#!/usr/bin/env python3

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub

# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Метрики использования поиска: --stats и --empty.

Вынесено из search.py (механическая резка god-файла, docs/canon/FILE-SIZE.md):
код перенесён дословно, данные — из log.py (research.db search_log).
"""
from log import empty_queries, search_stats


def cmd_stats(args):
    """--stats: метрики использования поиска (research.db search_log)."""
    s = search_stats()
    print(f"поисков всего: {s['total']}  (пустых: {s['empty']}, "
          f"{round(100 * s['empty'] / s['total'], 1) if s['total'] else 0}%)")
    if s["by_db"]:
        print("по базам: " + ", ".join(
            f"{r['db_name']} — {r['n']}" for r in s["by_db"]))
    print("\nтоп запросов (запрос | раз | найдено | пусто):")
    for r in s["top"]:
        print(f"  {r['query'][:60]:60} | {r['n']:3} | {r['found']:4} | {r['miss']}")
    print("\nпоследние:")
    for r in s["last"][:10]:
        print(f"  {r['ts']} [{r['tool']}] {r['db_name']}: "
              f"{r['query'][:60]} -> {r['hits']}")


def cmd_empty(args):
    """--empty: майнинг пустых запросов — темы, которые ищут и не находят.
    Кандидаты в доки/wiki (знание, которого нет в базах; аудит 14.08.2026,
    research.db id=489)."""
    rows = empty_queries(limit=args.limit)
    if not rows:
        print("стабильно пустых запросов нет — темы покрыты")
        return
    print(f"тем, которые ищут и не находят (>=2 пустых прогона): {len(rows)}\n")
    for r in rows:
        print(f"  {r['n']:2}× {r['query'][:70]:70} [{r['db_name']}]")
    print("\nчто делать: тема реально нужна → оформить в docs/ или Wiki/"
          "(скилл wiki-karpathy); обрубок/миссматч языка → ничего не делать.")
