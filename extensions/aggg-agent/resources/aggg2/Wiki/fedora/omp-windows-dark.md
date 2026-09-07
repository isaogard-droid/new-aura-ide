---
type: Howto
title: omp-windows-dark
description: "Use when the user wants a dark Windows-style theme in the omp CLI (Oh My Pi TUI): 'поменяй тему в omp cli', 'тёмная тема как на виндовсе', 'windows terminal', 'One Half Dark', 'omp"
date: 2026-08-16
tags: [skill-notes, fedora, omp, theme, cli]
source: skills/omp-windows-dark/ (перенесено 16.08.2026)
status: stable
---

# omp-windows-dark — скилл-на-полке (Howto)

Перенесено из `skills/omp-windows-dark/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже — дословно.

Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->


# omp CLI: тёмная тема в стиле Windows (One Half Dark)

## Что делает
Ставит omp (Oh My Pi coding agent TUI) на тёмную тему One Half Dark — штатную тёмную схему Windows Terminal: фон `#282C34`, текст `#DCDFE4`. Создаёт кастомную тему, включает её в конфиге omp, чинит `omp: команда не найдена`.

## Когда использовать
- «Поменяй тему в omp cli», «тёмная тема как на виндовсе / windows terminal», «One Half Dark».
- omp запускается со стандартной тёмной темой `titanium`, хочется Windows-стиль.
- `bash: omp: команда не найдена` при том, что бинарь есть (`~/.bun/bin/omp`).

НЕ использовать: для темы самого терминала Konsole (это отдельный скилл `konsole-windows-theme`), для светлой темы omp (меняется `theme.light` аналогично).

## Workflow
1. **Конфиг omp**: `~/.omp/agent/config.yml` (директория может переопределяться `PI_CODING_AGENT_DIR`). Ключи: `theme.dark` (дефолт `titanium`), `theme.light` (дефолт `light`), `symbolPreset`, `colorBlindMode`. Тёмный слот активен, когда терминал тёмный (определяется по OSC 11 / COLORFGBG).
2. **Создать тему**: файл `~/.omp/agent/themes/<name>.json`. Обязательны `name` и ВСЕ токены `colors` (полный список — `references/theme-schema.md`); `vars`, `export`, `symbols` — опционально. Готовую windows-dark ставит `skills/omp-windows-dark/scripts/apply-windows-dark.py` (содержит тему целиком).
3. **Включить**: `omp config set theme.dark windows-dark` (официальный путь) или правка config.yml: в блоке `theme:` строка `  dark: windows-dark`. Скрипт делает это сам (редактирует YAML напрямую — не зависит от PATH).
4. **Применить**: рестарт omp, либо в запущенном TUI: Settings → Appearance → Dark Theme → windows-dark (live-превью без рестарта). Кастомная тема перезагружается на лету watcher'ом, если она ТЕКУЩАЯ.
5. **Проверить**: `omp config get theme.dark` → `windows-dark`; JSON темы валиден и содержит все обязательные токены (скрипт проверки в `references/theme-schema.md`); свежий шелл: `command -v omp`.
6. **PATH (если `omp: команда не найдена`)**: бинарь omp живёт в `~/.bun/bin/omp`, а bun ставит утилиты в `~/.bun/bin`, который часто не в PATH. Добавить в `~/.bashrc`:
   ```bash
   if ! [[ "$PATH" =~ "$HOME/.bun/bin:" ]]; then
       PATH="$HOME/.bun/bin:$PATH"
   fi
   ```
   Применить: `source ~/.bashrc` или новая вкладка терминала.
Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


## Палитра Windows (One Half Dark, из iTerm2-Color-Schemes)
| Роль | Hex | Назначение в теме omp |
|---|---|---|
| фон | `#282C34` | userMessageBg, mdCodeBlockBorder окрестности |
| текст | `#DCDFE4` | text, syntaxVariable |
| текст приглуш. | `#ABB2BF` | thinkingText, toolOutput, punctuation |
| комментарий | `#5C6370` / muted `#5D637A` | syntaxComment, muted, dim |
| рамки | `#3E4452` | border, selectedBg |
| синий | `#61AFEF` | accent, mdHeading, syntaxFunction, statusLinePath |
| зелёный | `#98C379` | success, syntaxString, diffAdded |
| жёлтый | `#E5C07B` | warning, syntaxType |
| красный | `#E06C75` | error, syntaxKeyword-соседи, diffRemoved |
| пурпурный | `#C678DD` | syntaxKeyword, pythonMode, statusLineModel |
| циан | `#56B6C2` | syntaxOperator, bashMode |
| оранжевый | `#D19A66` | syntaxNumber, statusLineCost |

Альтернатива — Campbell (дефолт Windows Terminal): фон `#0C0C0C`, текст `#CCCCCC`.
Источник палитры: `https://github.com/mbadolato/iTerm2-Color-Schemes` → `konsole/One Half Dark.colorscheme` (цвета в формате R,G,B десятичные).

## Gotchas
- **Все токены `colors` обязательны** (кроме `thinkingMax`, фолбэк на `thinkingXhigh`). Пропуск любого → ошибка валидации → тема падает на built-in `dark` с `{success:false}`.
- Значения цвета: hex `"#RRGGBB"`, 256-индекс (`0..255`), ссылка на `vars` (поддерживаются вложенные), `""` = дефолт терминала.
- **Имя кастомной темы не должно совпадать с built-in** (`titanium`, `dark`, `light`, `defaults/*`) — built-in имеет приоритет, кастомный файл проигнорируется.
- Имя в JSON (`"name"`) должно совпадать с именем файла (`<name>.json`) — lookup по имени.
- `theme.dark` — только тёмный слот; авто-выбор слота по яркости терминала; в светлом терминале тёмная тема не применится сама (нужно `theme.light` или принудительно).
- Watcher перезагружает файл темы на лету только если она текущая и watcher включён (интерактивный режим/settings). Изменение `theme.dark` в config.yml применяется при старте.
- **Не убивать живую сессию omp** — тема применится на следующем запуске или через Settings (live preview). Сессия агента может висеть в той же Konsole (проверять `ps --ppid $(pgrep -x konsole)` перед kill).
- Для консистентности: Konsole должен быть тёмным (схема One Half Dark в `~/.config/konsolerc` → `ColorScheme=One Half Dark`, файлы в `~/.local/share/konsole/*.colorscheme`).

## Available scripts
- `skills/omp-windows-dark/scripts/apply-windows-dark.py` — ставит тему windows-dark: пишет `~/.omp/agent/themes/windows-dark.json` (тема целиком внутри) и включает `theme.dark` в `~/.omp/agent/config.yml` (создаёт блок `theme:` при отсутствии).
  Usage: `python3 skills/omp-windows-dark/scripts/apply-windows-dark.py [--name NAME] [--dry-run] [--agent-dir PATH]`
  `--dry-run` — показать изменения без записи; `--name` — имя темы (по умолчанию `windows-dark`). Коды: 0 = ok, 1 = ошибка, 2 = usage.
  Идемпотентен: повторный запуск = no-op. Рестарт omp не делает (и не убивает живые сессии).

## References
- `references/theme-schema.md` — полная схема темы omp: все обязательные токены по группам, правила значений, поведение фолбэков, скрипт-валидатор. Читай при создании своей темы.
- Канонический источник механики (только внутри omp-харнесса): `omp://theme.md` — schema, загрузка, watcher, цветовые режимы.




---

*Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.***

Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

## Скрипт `apply-windows-dark.py`

Применяется по инструкции выше (перенесено дословно).

```py
#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Install the Windows-dark (One Half Dark) theme for the omp CLI.

Writes ~/.omp/agent/themes/<name>.json (full theme embedded) and sets
theme.dark=<name> in ~/.omp/agent/config.yml (creates the theme: block if absent).

Idempotent; does NOT restart omp (never kills live sessions).

Exit codes: 0 = ok, 1 = error, 2 = usage error.
"""
import argparse
import json
import os
import sys

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


THEME = {
    "name": "windows-dark",
    "vars": {
        "bg": "#282c34", "fg": "#dcdfe4", "fgDim": "#abb2bf",
        "comment": "#5c6370", "muted": "#5d637a", "border": "#3e4452",
        "blue": "#61afef", "green": "#98c379", "yellow": "#e5c07b",
        "red": "#e06c75", "magenta": "#c678dd", "cyan": "#56b6c2",
        "orange": "#d19a66",
    },
    "colors": {
        "accent": "blue", "border": "border", "borderAccent": "blue",
        "borderMuted": "muted", "success": "green", "error": "red",
        "warning": "yellow", "muted": "muted", "dim": "#4b5263",
        "text": "fg", "thinkingText": "fgDim",
        "selectedBg": "border", "userMessageBg": "bg", "userMessageText": "fg",
        "customMessageBg": "#2c323c", "customMessageText": "fg",
        "customMessageLabel": "blue", "toolPendingBg": "#23272f",
        "toolSuccessBg": "#23272f", "toolErrorBg": "#23272f",
        "toolTitle": "fg", "toolOutput": "fgDim",
        "mdHeading": "blue", "mdLink": "blue", "mdLinkUrl": "muted",
        "mdCode": "fg", "mdCodeBlock": "fgDim", "mdCodeBlockBorder": "border",
        "mdQuote": "fgDim", "mdQuoteBorder": "border", "mdHr": "muted",
        "mdListBullet": "blue",
        "toolDiffAdded": "green", "toolDiffRemoved": "red", "toolDiffContext": "muted",
        "syntaxComment": "comment", "syntaxKeyword": "magenta",
        "syntaxFunction": "blue", "syntaxVariable": "fg", "syntaxString": "green",
        "syntaxNumber": "orange", "syntaxType": "yellow", "syntaxOperator": "cyan",
        "syntaxPunctuation": "fgDim",
        "thinkingOff": "muted", "thinkingMinimal": "fgDim", "thinkingLow": "blue",
        "thinkingMedium": "cyan", "thinkingHigh": "magenta", "thinkingXhigh": "red",
        "thinkingMax": "orange",
        "bashMode": "cyan", "pythonMode": "magenta",
        "statusLineBg": "#21252b", "statusLineSep": "muted",
        "statusLineModel": "magenta", "statusLinePath": "blue",
        "statusLineGitClean": "green", "statusLineGitDirty": "yellow",
        "statusLineContext": "cyan", "statusLineSpend": "blue",
        "statusLineStaged": "green", "statusLineDirty": "yellow",
        "statusLineUntracked": "red", "statusLineOutput": "fgDim",
        "statusLineCost": "orange", "statusLineSubagents": "magenta",
    },
    "export": {"pageBg": "#282c34", "cardBg": "#21252b", "infoBg": "#23272f"},
}


def set_dark_theme(cfg_path, name):
    """Return new config.yml content with theme.dark=<name> set."""
    with open(cfg_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)

    theme_idx = next((i for i, ln in enumerate(lines) if ln.strip() == "theme:"), None)
    if theme_idx is None:
        out = list(lines)
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(f"\ntheme:\n  dark: {name}\n")
        return "".join(out)

    end = len(lines)
    for i in range(theme_idx + 1, len(lines)):
        if lines[i].strip() and not lines[i].startswith(" "):
            end = i
            break
    block = lines[theme_idx + 1 : end]
    new_block, replaced = [], False
    for ln in block:
        if ln.startswith("  dark:"):
            new_block.append(f"  dark: {name}\n")
            replaced = True
        else:
            new_block.append(ln)
    if not replaced:
        new_block.insert(0, f"  dark: {name}\n")
    return "".join(lines[: theme_idx + 1] + new_block + lines[end:])




# Создано и поддерживается: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая новая версия — уникальная и лучшая.
def main():
    ap = argparse.ArgumentParser(
        prog="apply-windows-dark.py",
        description="Install the Windows-dark (One Half Dark) theme for the omp CLI.",
    )
    ap.add_argument("--name", default="windows-dark",
                    help="theme name (default: windows-dark)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would change without writing")
    ap.add_argument("--agent-dir", default=os.path.expanduser("~/.omp/agent"),
                    help="omp agent dir (default: ~/.omp/agent)")
    args = ap.parse_args()

    theme = dict(THEME)
    theme["name"] = args.name
    themes_dir = os.path.join(args.agent_dir, "themes")
    theme_path = os.path.join(themes_dir, f"{args.name}.json")
    cfg_path = os.path.join(args.agent_dir, "config.yml")

    try:
        os.makedirs(themes_dir, exist_ok=True)
    except OSError as e:
        print(f"error: cannot create {themes_dir}: {e}", file=sys.stderr)
        return 1

    new_theme = json.dumps(theme, indent=2) + "\n"
    if os.path.isfile(theme_path):
        with open(theme_path, encoding="utf-8") as f:
            theme_changed = f.read() != new_theme
    else:
        theme_changed = True  # файла нет — тема изменится (будет записана)

    if os.path.isfile(cfg_path):
        new_cfg = set_dark_theme(cfg_path, args.name)
        with open(cfg_path, encoding="utf-8") as f:
            cfg_changed = f.read() != new_cfg
    else:
        new_cfg = f"theme:\n  dark: {args.name}\n"
        cfg_changed = True

    if args.dry_run:
        print(f"would write theme: {theme_path}" + (" (changed)" if theme_changed else " (unchanged)"))
        print(f"would set theme.dark={args.name} in: {cfg_path}" + (" (changed)" if cfg_changed else " (unchanged)"))
        if theme_changed:
            print("--- theme json ---")
            print(new_theme, end="")
        if cfg_changed:
            print("--- config.yml ---")
            print(new_cfg, end="")
        return 0

    if theme_changed:
        with open(theme_path, "w", encoding="utf-8") as f:
            f.write(new_theme)
        print(f"wrote theme: {theme_path}")
    if cfg_changed:
        tmp = cfg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new_cfg)
        os.replace(tmp, cfg_path)
        print(f"set theme.dark={args.name} in {cfg_path}")

    if not theme_changed and not cfg_changed:
        print("no changes (already applied)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
```
