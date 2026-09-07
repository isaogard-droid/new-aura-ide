---
name: wiki-karpathy
description: "Работа с Wiki-библиотекой: пост → MD с тегами, поиск, lint, обновление index.md/log.md; создание новой библиотеки. Не для веб-ресёрча (web-research-camoufox) и вопросов по воркспейсу (db-first-search)."
compatibility: AGGG2.0 (папка Wiki, db-tools, pyyaml); паттерн универсален — переносится в любую markdown-библиотеку
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Wiki Карпатого: markdown-библиотека знаний, которую ведёт агент

Паттерн **LLM Wiki Андрея Карпатого**: человек кидает посты, агент оформляет в markdown с YAML-frontmatter, обновляет каталог и журнал, пересобирает базу. Совместим с **Open Knowledge Format (OKF)**. Основа: файл = один концепт, путь = идентичность, теги = главный механизм поиска.

## Структура библиотеки

```
Wiki/
├── README.md          # правила библиотеки (схема) — источник истины, lean
├── index.md           # каталог — ГЕНЕРИРУЕТСЯ gen_index.py, руками не править
├── log.md             # append-only журнал (append >>, ротация при >500 строк)
├── log-archive/       # архив логов (log-<YYYY-MM>.md)
├── _templates/        # шаблоны (post.md)
├── ai/ coding/ tools/ # тематические папки (новая — при 3+ постах)
└── <slug>.md          # посты
```

## Workflow

### Ingest — добавить пост (главная операция)

1. Прими текст поста как есть, не искажай. Ссылка на первоисточник (source) → проверь Camoufox (не curl), контекст — разделом «Контекст».
2. Папка по категории; имя файла — kebab-case: `tencent-worldclaw.md`.
3. Frontmatter (схема ниже): обязательно `type`, `title`, `description`, `date`, `tags`.
4. Пересобери index.md СКРИПТОМ, не руками: `python3 skills/wiki-karpathy/scripts/gen_index.py` (бэкап .bak). НЕ читай/не правь index.md целиком — сотни КБ на каждый ингест.
5. log.md — append'ом, не читая: `printf '%s\n' "- $(date '+%F %H:%M') — add — <файл> — что добавлено" >> Wiki/log.md`; >500 строк — ротация в `Wiki/log-archive/log-<YYYY-MM>.md`.
6. Пересобери базу: `python3 db-tools/build.py -r Wiki -o db/wiki.db` (инкрементальная).
7. Проверь: `python3 skills/wiki-karpathy/scripts/lint_wiki.py` — 0 ошибок.

### Query — найти

- Агенту: MCP db-tools `search`/`db: wiki` (или `search.py -b db/wiki.db`). **ТОЛЬКО через базу — греп по Wiki/ агенту запрещён** (человеку — ок).
- Человеку: `grep -ri "<тег>" Wiki/` или `index.md`. «Мы это разбирали» — сначала `findings.py search`.
- Пусто → лестница (ядро: core.txt п.2): короче → `--substring` → `search_all.py` → `findings.py search` → свежесть (`build.py`/`--refresh`); всё пусто — «не нашёл».

### Lint

`python3 skills/wiki-karpathy/scripts/lint_wiki.py` — у каждого поста: frontmatter есть, обязательные поля, теги в нижнем регистре без пробелов, имя kebab-case. Отчёт + статистика тегов. После каждого добавления (lint = eslint для знаний).

## Служебные файлы при масштабе

index.md/log.md растут (297 постов ≈ 90-130 КБ) — НЕЛЬЗЯ читать целиком («LLM Wiki at Scale», gist SurajGThakkar): index — генерируется из frontmatter, агент не читает/не правит, поиск через базу; log — append `>>`, ротация при >500; README держать lean (всегда в контексте). Потолок — не в файлах: flat + теги + FTS держат тысячи постов (кейс: 8000 заметок/64к ссылок); сигнал к разделению — домены без кросс-ссылок, не размер.

## Схема frontmatter (OKF v0.2)

```yaml
---
type: Post                    # Post | Insight | Reference | Idea | Howto (обязателен)
title: Короткое название
description: Одно предложение — о чём пост (для поиска и index.md)
date: YYYY-MM-DD
tags: [ai, 3d, tencent, agents]   # категория + 2-5 предметных
source: https://...           # первоисточник (если есть)
author: @xor_journal          # автор/канал
status: stable                # draft | stable | deprecated
---
```

По желанию OKF: `sources` (provenance), `verified` (unverified → machine-confirmed → human-reviewed), `stale_after`. См. `okf/SPEC.md` (GoogleCloudPlatform/knowledge-catalog).

## Таксономия тегов

**Нижний регистр, без пробелов** (дефис), английские. Категория (первый): `ai`, `coding`, `tools`, `3d`, `hardware`, `research`, `industry`. Предметные: технологии (`llm`, `agents`, `video`, `voice`), компании (`tencent`, `openai`), тип (`news`, `tutorial`, `opinion`, `paper`). Расширяются свободно.

## Грабли

- **Забыл index/log** — рассинхрон. Порядок строгий: файл → gen_index → log append → база.
- **Править index.md руками** — пересборка затрёт; исключить пост — `status: deprecated`, не удалять строку.
- **Пост без проверки первоисточника** — контекст может быть неверным; проверка через Camoufox (curl даёт ложные 403).
- **Дубль контента** — конвертированный черновик (`1.md`) удалить, иначе поиск находит два файла.
- **Папки заранее** — не плодить: новая тема при 3+ постах (YAGNI).
- **Теги с заглавными/пробелами** — ломают grep: `AI, 3D` → `ai, 3d`.
- **Двоеточие/спецсимволы в YAML** — `description: ...миры: планирует...` (двоеточие-пробел), `author: @xor_journal` (ведущий `@`) не парсятся: значения с `: `, `#`, `@`, кавычками — в двойные кавычки: `description: "текст: с двоеточием"`, `author: "@channel"`.
- **Секреты** — плейсхолдер `YOUR_API_KEY` (ядро: core.txt п.6).

## Чеклист ingest

- [ ] текст сохранён без искажений; первоисточник проверен (если есть)
- [ ] frontmatter: type, title, description, date, tags
- [ ] slug kebab-case, папка по категории
- [ ] index.md пересобран (gen_index.py — НЕ руками)
- [ ] log.md дописан (append >>; ротация при >500)
- [ ] база пересобрана (build.py → db/wiki.db)
- [ ] lint_wiki.py — 0 ошибок

## When NOT to use

- Поиск по коду/докам — `db-first-search`; веб-ресёрч — `web-research-camoufox`; скиллы — `skill-authoring`.

## Этапы (handoff)

- **Вход из:** `task-cycle` (фаза 6/7), findings (продукт знания)
- **Дальше:** `db-first-search`, `skill-search`

## References

- `okf/SPEC.md` — GoogleCloudPlatform/knowledge-catalog (спека v0.2)
- blog.starmorph.com/blog/karpathy-llm-wiki-knowledge-base-guide
- gist.github.com/SurajGThakkar/aaadf2b0178ba11b6288b2a181472d1a — LLM Wiki at Scale
- `Wiki/README.md` — правила конкретной библиотеки

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
