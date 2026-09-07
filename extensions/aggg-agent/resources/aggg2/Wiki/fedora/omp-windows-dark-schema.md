---
type: Reference
title: "omp-windows-dark: схема темы"
description: "Дополнение к скиллу-на-полке omp-windows-dark: references/theme-schema.md"
date: 2026-08-16
tags: [skill-notes, fedora]
source: skills/omp-windows-dark/references/theme-schema.md (перенесено 16.08.2026)
status: stable
---

# omp-windows-dark: схема темы

Дополнение к Howto-посту `omp-windows-dark.md` (вынесено из-за лимита 300 строк).

---

*Источник: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия — новая и ещё лучше.***
# Схема темы omp (Oh My Pi TUI)

Источник: внутренняя документация omp (`omp://theme.md`, v17). Файл темы — JSON, валидируется рантаймом
(`themeJsonSchema` в `src/modes/theme/theme.ts`).

## Файлы и настройки
- Кастомные темы: `~/.omp/agent/themes/<name>.json` (директория переопределяется `PI_CODING_AGENT_DIR/themes`).
- Настройки: `~/.omp/agent/config.yml` → `theme.dark` (дефолт `titanium`), `theme.light` (дефолт `light`),
  `symbolPreset` (дефолт `unicode`), `colorBlindMode`.
- CLI: `omp config get|set <key> <value>` (например `omp config set theme.dark windows-dark`).
- Built-in темы: `dark`, `light`, `defaults/*` — имеют приоритет над кастомными с тем же именем.

## Топ-левел поля JSON
- `name` (обязателен) — должен совпадать с именем файла.
- `colors` (обязателен) — все токены ниже.
- `vars` (опционально) — переменные цвета, значения: hex / 256-индекс / ссылка на другую var.
- `export` (опционально) — `pageBg`, `cardBg`, `infoBg` для HTML-экспорта.
- `symbols` (опционально) — `preset: unicode|nerd|ascii`, `overrides`, `spinnerFrames`.

## Обязательные токены colors (66 + 1 опциональный)

### Core text и рамки (11)
`accent`, `border`, `borderAccent`, `borderMuted`, `success`, `error`, `warning`, `muted`, `dim`, `text`, `thinkingText`

### Фоновые блоки (7)
`selectedBg`, `userMessageBg`, `customMessageBg`, `toolPendingBg`, `toolSuccessBg`, `toolErrorBg`, `statusLineBg`

### Текст сообщений/инструментов (5)
`userMessageText`, `customMessageText`, `customMessageLabel`, `toolTitle`, `toolOutput`

### Markdown (10)
`mdHeading`, `mdLink`, `mdLinkUrl`, `mdCode`, `mdCodeBlock`, `mdCodeBlockBorder`, `mdQuote`, `mdQuoteBorder`, `mdHr`, `mdListBullet`

### Diff + синтаксис (12)
`toolDiffAdded`, `toolDiffRemoved`, `toolDiffContext`,
`syntaxComment`, `syntaxKeyword`, `syntaxFunction`, `syntaxVariable`, `syntaxString`, `syntaxNumber`, `syntaxType`, `syntaxOperator`, `syntaxPunctuation`

### Режимы/thinking (8 + 1 опциональный)
`thinkingOff`, `thinkingMinimal`, `thinkingLow`, `thinkingMedium`, `thinkingHigh`, `thinkingXhigh`,
`thinkingMax` (опционально, фолбэк на `thinkingXhigh`),
`bashMode`, `pythonMode`

### Статус-лайн (13)
`statusLineSep`, `statusLineModel`, `statusLinePath`, `statusLineGitClean`, `statusLineGitDirty`,
`statusLineContext`, `statusLineSpend`, `statusLineStaged`, `statusLineDirty`, `statusLineUntracked`,
`statusLineOutput`, `statusLineCost`, `statusLineSubagents`
aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


## Значения цветов
- hex: `"#RRGGBB"`
- 256-индекс: `0..255` (конвертируется в `38;5`/`48;5`)
- ссылка на `vars`: `"myvar"` — резолвится рекурсивно; циклические ссылки = ошибка
- пустая строка `""` — дефолт терминала (`\x1b[39m` fg / `\x1b[49m` bg)

## Поведение при ошибках
- Пропущенный обязательный токен / плохой тип / неизвестная переменная → ошибка валидации с путём JSON.
- `setTheme` при ошибке фолбэчится на built-in `dark` (возвращает `{success:false, error}`).
- `previewTheme` (live-превью в Settings) при ошибке НЕ заменяет текущую тему.
- Неизвестное имя темы: `Theme not found: <name>`.
- Watcher: следит только за файлом ТЕКУЩЕЙ кастомной темы; ошибки релоада держат последнюю удачную.

## Валидатор (python3, без зависимостей)
```python
import json, sys
required = """accent border borderAccent borderMuted success error warning muted dim text thinkingText
selectedBg userMessageBg customMessageBg toolPendingBg toolSuccessBg toolErrorBg statusLineBg
userMessageText customMessageText customMessageLabel toolTitle toolOutput
mdHeading mdLink mdLinkUrl mdCode mdCodeBlock mdCodeBlockBorder mdQuote mdQuoteBorder mdHr mdListBullet
toolDiffAdded toolDiffRemoved toolDiffContext
syntaxComment syntaxKeyword syntaxFunction syntaxVariable syntaxString syntaxNumber syntaxType syntaxOperator syntaxPunctuation
thinkingOff thinkingMinimal thinkingLow thinkingMedium thinkingHigh thinkingXhigh bashMode pythonMode
statusLineSep statusLineModel statusLinePath statusLineGitClean statusLineGitDirty statusLineContext statusLineSpend statusLineStaged statusLineDirty statusLineUntracked statusLineOutput statusLineCost statusLineSubagents""".split()
t = json.load(open(sys.argv[1]))
missing = [k for k in required if k not in t.get("colors", {})]
print("missing:", missing or "NONE")
print("name:", t.get("name"))
```

Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
