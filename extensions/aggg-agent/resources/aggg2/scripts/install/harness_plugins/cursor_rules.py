#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""cursor_rules — установка AGGG2.0 в Cursor: глобальные правила + команды.

Офф-механизмы Cursor (cursor.com/docs/rules, forum.cursor.com):
- User Rules (глобальные) — Settings → Rules (в новых версиях — облако);
  файловый путь меняется по версиям; ~/.cursor/rules/*.mdc читается в
  ряде версий (desastre/форум) — кладём как основной канал;
- ~/.cursor/commands/*.md — глобальные команды (подтверждённый
  файловый механизм, ⌘⇧J) — надёжный канал для команд канона.

Кладём: правило ядра (alwaysApply) + команды /findings, /bro, /canon
(те же промпты, что у claude-плагина — один источник текстов).

Использование:
    python3 scripts/install/harness_plugins/cursor_rules.py [--check]
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))  # корень чулана
ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
HOME = Path.home()
RULES_DIR = HOME / ".cursor" / "rules"
CMDS_DIR = HOME / ".cursor" / "commands"

CORE_RULE = """---
description: AGGG2.0 — ядро правил воркспейса
globs: []
alwaysApply: true
---
Правила AGGG2.0 (t.me/aidvizhenie), жёсткие:
1. ВЕБ-РЕСЁРЧ ПЕРВЫМ — первое действие задачи с выбором/неизвестностью:
   веб-поиск, первоисточники, 2+ независимых источника на факт.
2. БАЗА ДО КОДА — вопросы по содержимому воркспейса AGGG2.0: сначала
   база (db-tools/search.py, findings.py search), потом чтение файлов.
3. НЕ ОТВЕЧАТЬ С ГОЛОВЫ — факт без проверки = гипотеза, помечай
   «проверить».
4. НАХОДКИ В БАЗУ — после ресёрча/эксперимента:
   python3 db-tools/findings.py add (research.db).
5. СЕКРЕТЫ — только плейсхолдеры (YOUR_API_KEY).
6. `pkill -f` — всегда скобочный трюк: pkill -f "[х]...".
7. QA после правок кода: линтер → semgrep → тесты.
8. КАТАЛОГИ: ≤ 15 файлов-братьев в папке — больше: дели по доменам
   (docs/canon/ARCHITECTURE.md). Процедура деления — там же.
Детали — в корне AGGG2.0 (маркер VERSION или $AGGG2_ROOT):
AGENTS.md, CLAUDE.md, CYCLE.md, docs/canon/CAMOUFOX.md, docs/canon/DB-FIRST.md,
docs/canon/ARCHITECTURE.md.
"""

COMMANDS = {
    "findings.md": """---
description: Поиск находок и выводов ресёрча в research.db
argument-hint: запрос (2-4 слова)
---
Найди в базе знаний AGGG2.0 выводы по теме «$ARGUMENTS»:
`python3 db-tools/findings.py search "$ARGUMENTS"` (корень — маркер
VERSION или $AGGG2_ROOT). Если пусто — попробуй короче/другими словами.
Дай ответ: id, дата, тема, суть. Не нашлось — честно скажи.
""",
    "bro.md": """---
description: Перескажи последнее сообщение простыми словами, без жаргона
argument-hint: (необязательно — что пересказать)
---
Перескажи последнее сообщение (или $ARGUMENTS) простыми словами, как
человек человеку: те же факты, без жаргона, короче. Сначала — суть
одной фразой.
""",
    "canon.md": """---
description: Канон-чек: прочитать канон AGGG2.0 и выдать таблицу
argument-hint: (необязательно — тип задачи)
---
Прочитай канон AGGG2.0 (корень — маркер VERSION или $AGGG2_ROOT):
Tier A всегда (AGENTS.md, CYCLE.md, CLAUDE.md), Tier B по типу задачи.
Выдай канон-чек: таблица «файл → прочитан → 1 главное правило».
""",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry-run")
    args = ap.parse_args()
    plan = [
        (RULES_DIR / "aggg2.mdc", CORE_RULE),
    ] + [(CMDS_DIR / name, text) for name, text in COMMANDS.items()]
    if args.check:
        for p, _ in plan:
            print(f"план: {p}")
        return 0
    for p, text in plan:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_file() and p.read_text(encoding="utf-8") == text:
            print(f"[=] уже актуален: {p}")
            continue
        shutil.copy2(p, str(p) + ".bak") if p.is_file() else None
        p.write_text(text, encoding="utf-8")
        print(f"[✓] записан: {p}")
    print("[/] User Rules в Settings → Rules (облако в новых версиях) — "
          "заведи вручную, если ~/.cursor/rules не читается твоей версией.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
