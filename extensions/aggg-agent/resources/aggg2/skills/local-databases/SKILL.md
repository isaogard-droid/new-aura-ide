---
name: local-databases
description: "ГЕЙТ перед вебом: сначала skill-knowledge.db (--knowledge) и context-internet.db (--internet); ответ уже есть — НЕ ходи в веб. «Мы это читали», «что агент уже знает», «статистика баз», FTS5. Не для db/skills.db (db-first-search) и веб-поиска."
license: Proprietary
metadata:
  version: "1.2"
  author: AGGG2.0 (https://t.me/aidvizhenie)
  created: "2026-08-18"
  updated: "2026-08-18"
---

# local-databases

Поиск по локальным базам знаний — "локальному интернету" агента. Две SQLite базы с FTS5 (полнотекстовый поиск), которые растут с каждым использованием.

## Когда использовать

**Загружать скилл, когда:**
- Нужно найти информацию в уже прочитанных скиллах (`--knowledge`)
- Нужно найти информацию в уже прочитанных веб-страницах (`--internet`)
- Хочешь посмотреть статистику баз (`--stats`)
- Фраза владельца: «мы это читали», «что мы знаем о X», «поищи в базе знаний»

**НЕ загружать, когда:**
- Поиск в локальных скиллах AGGG2.0 (`db/skills.db`) → `db-first-search`
- Веб-поиск через Camoufox → `web-research-camoufox`
- Чтение конкретного скилла по id → `skills_search.py --read`

## Архитектура

```
db/
├── skill-knowledge.db      # База знаний скиллов (прочитанные через --read/--read-top)
└── context-internet.db     # База интернет-контекста (прочитанные через Camoufox)
```

SQLite + FTS5 с триггерами для синхронизации индекса.

## Workflow

### 1. Поиск по скиллам (skill-knowledge.db)

```bash
python3 scripts/tools/skills/skills_search.py --knowledge "debugging strategies"
python3 scripts/tools/skills/skills_search.py --stats
```

**Что искать:** паттерны из прочитанных скиллов, примеры кода, рекомендации по инструментам, воркфлоу и best practices.

### 2. Поиск по веб-контексту (context-internet.db)

```bash
python3 scripts/tools/skills/skills_search.py --internet "SQLite FTS5"
python3 scripts/tools/skills/skills_search.py --stats
```

**Что искать:** документацию, которую уже читал, статьи и туториалы, паттерны индустрии, решения из блогов и форумов.

### 3. Пополнение баз

- **skill-knowledge.db** — автоматически при `skills_search.py --read owner/repo/skill`, `--read-top N "query"`.
- **context-internet.db** — автоматически при `camoufox_worker.py fetch_page(url)`, `camoufox_fetch.py batch_fetch(urls)`.

### 4. Комбинированный поиск

```bash
python3 scripts/tools/skills/skills_search.py --knowledge "testing"
python3 scripts/tools/skills/skills_search.py --internet "testing"
# не найдено → web-research-camoufox
```

## Порядок поиска (иерархия)

1. **Локальные скиллы AGGG2.0** (`db/skills.db`) → `db-first-search`
2. **skill-knowledge.db** (прочитанные внешние скиллы) → `--knowledge`
3. **context-internet.db** (прочитанный веб-ресёрч) → `--internet`
4. **Wiki/** (библиотека знаний) → `db-tools search db=wiki`
5. **Веб-поиск** (новый ресёрч) → `web-research-camoufox`

Локальные базы (2-3) — быстрее и дешевле, чем веб-поиск (5). Используй их первыми.

## Примеры использования

### Пример 1: Повторное использование прочитанного

```bash
# Вчера читал скиллы по тестированию — сегодня ищем конкретное
python3 scripts/tools/skills/skills_search.py --read-top 10 "testing"
python3 scripts/tools/skills/skills_search.py --knowledge "test coverage"
```

### Пример 2: Поиск в веб-контексте

```bash
# Делал ресёрч по SQLite — ищем по уже прочитанному
python3 mcp/camoufox_research.py web_search "Python SQLite FTS5"
python3 mcp/camoufox_fetch.py fetch_page "https://docs.python.org/3/library/sqlite3.html"
python3 scripts/tools/skills/skills_search.py --internet "SQLite"
```

### Пример 3: Комбинированный поиск

```bash
python3 scripts/tools/skills/skills_search.py --knowledge "debugging"
python3 scripts/tools/skills/skills_search.py --internet "debugging"
# не найдено → web_search "systematic debugging patterns"
```

## Преимущества локальных баз

- **Быстро** — FTS5 за миллисекунды (vs секунды веба); **оффлайн** — без интернета
- **Дёшево** — не тратит токены на повторные загрузки; **история** — что и когда читалось
- **Семантика** — поиск по содержимому, не только по URL

## Ограничения

- **Размер** — растёт с использованием (скилл ~10-50KB, страница ~5-20KB)
- **FTS5 vs векторы** — keyword-поиск, не семантический (нужен sqlite-vec)
- **Нет дедупликации** — один URL может быть сохранён несколько раз; **нет версионирования** — перезапись при повторном чтении

## Связанные скиллы

- `db-first-search` — поиск в db/skills.db (локальные скиллы AGGG2.0)
- `web-research-camoufox` — веб-поиск через Camoufox
- `wiki-karpathy` — поиск в Wiki/ библиотеке
- `skill-search` — поиск внешних скиллов (skills.sh)

## Документация

Полное описание архитектуры — `docs/canon/LOCAL_DATABASES.md` в корне AGGG2.0.

## Этапы (handoff)

- **Вход из:** `db-first-search` (пусто в db/skills.db), `web-research-camoufox` (уже читал)
- **Дальше:** если пусто — `web-research-camoufox` (новый ресёрч)

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
