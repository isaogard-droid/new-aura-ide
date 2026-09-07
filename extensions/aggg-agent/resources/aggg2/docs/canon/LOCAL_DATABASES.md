# Локальные базы данных AGGG2.0

Две SQLite базы — «локальный интернет» агента: персистентное хранилище знаний.
**ГЕЙТ ПЕРЕД ВЕБОМ:** ответ уже есть в них — НЕ ходи в веб (ядро: core.txt п.1-2).

## Архитектура

```
db/
├── skill-knowledge.db      # База знаний скиллов
└── context-internet.db     # База интернет-контекста
```

Обе — SQLite + FTS5 (полнотекстовый поиск), триггеры синхронизируют индекс.

## skill-knowledge.db

### Что это
Персистентное хранилище всех прочитанных внешних скиллов. Растёт с каждым `--read` и `--read-top`.

### Структура

```sql
skills (
    id TEXT PRIMARY KEY,        -- owner/repo/skill
    name TEXT,                  -- имя скилла
    owner TEXT,                 -- владелец репо
    repo TEXT,                  -- имя репо
    source TEXT,                -- источник (read/read_batch)
    description TEXT,           -- описание (frontmatter или первые 200 символов)
    installs INTEGER,           -- количество установок
    content TEXT,               -- полное содержимое SKILL.md
    fetched_at REAL             -- timestamp последнего чтения
)

skills_fts (FTS5 виртуальная таблица)
    -- Индексирует: name, description, content
    -- Триггеры: AFTER INSERT/UPDATE/DELETE на skills
```

### Команды

```bash
# Поиск по базе знаний
python3 scripts/tools/skills/skills_search.py --knowledge "debugging strategies"
# Статистика базы
python3 scripts/tools/skills/skills_search.py --stats
# Прочитать скилл (автоматически сохраняется в базу)
python3 scripts/tools/skills/skills_search.py --read obra/superpowers/systematic-debugging
# Пакетное чтение (тоже сохраняется)
python3 scripts/tools/skills/skills_search.py --read-top 10 "testing"
```

## context-internet.db

### Что это
Персистентное хранилище всех прочитанных через Camoufox веб-страниц. Растёт с каждым
`fetch_page` и `batch_fetch`.

### Структура

```sql
pages (
    url TEXT PRIMARY KEY,         -- URL страницы
    title TEXT,                   -- заголовок (или URL если нет)
    content TEXT,                 -- полное содержимое страницы
    query TEXT,                   -- исходный поисковый запрос
    domain TEXT,                  -- домен (из urlparse)
    fetched_at REAL               -- timestamp загрузки
)

pages_fts (FTS5 виртуальная таблица)
    -- Индексирует: title, content, query
    -- Триггеры: AFTER INSERT/UPDATE/DELETE на pages
```

### Команды

```bash
# Поиск по интернет-контексту
python3 scripts/tools/skills/skills_search.py --internet "SQLite FTS5"
# Статистика (топ-10 доменов, число страниц, дата последнего добавления)
python3 scripts/tools/skills/skills_search.py --stats
```

### Автоматическая интеграция

Пополняется автоматически при использовании Camoufox: `mcp/camoufox_worker.py`
(fetch_page) и `mcp/camoufox_fetch.py` (batch_fetch) вызывают
`save_to_internet(url, title, content, query)` — ручных действий нет.

## Почему SQLite + FTS5

- **Один файл** — легко бэкапить/переносить; **нет зависимостей** (SQLite в Python).
- **FTS5** — быстрый полнотекстовый поиск; `snippet()` подсвечивает контекст.
- **Триггеры** — автосинхронизация индекса.
- Не векторная БД: эмбеддинги не нужны, нет внешних сервисов, быстрее и проще.
- Не кэш: персистентность (без TTL), поиск по содержимому, аналитика, оффлайн.

## Паттерны индустрии

Ресёрч 20+ источников (research.db id=937, 939): Hermes Agent (3-слойная память),
OpenClaw (SQLite FTS5 для локального RAG), kbx (гибрид FTS5+векторы), sqlite-rag
(Reciprocal Rank Fusion), AWS AGENTPERF03-BP04 (multi-layer caching).

## Использование в рабочем цикле

Фаза 1 (ресёрч): `python3 scripts/tools/skills/skills_search.py "debugging" --top`,
`--read-top 5 "debugging"`, `python3 mcp/camoufox_research.py web_search "debugging patterns"`
— чтения сохраняются автоматически.
Фаза 2 (повторное использование, оффлайн) — **ГЕЙТ ПЕРЕД ВЕБОМ**:
`--knowledge "systematic debugging"`, `--internet "debugging strategies"`.
Фаза 3 (аналитика): `--stats`.

## Ограничения

- **Размер БД** — растёт (скилл ~10-50KB, страница ~5-20KB).
- **FTS5 vs векторы** — keyword-поиск, не семантический (для семантики — sqlite-vec).
- **Нет дедупликации** — один URL может сохраниться несколько раз.
- **Нет версионирования** — перезапись при повторном чтении.

## Будущие улучшения

Дедупликация URL (по хешу), гибрид FTS5+sqlite-vec, экспорт/импорт, визуализация,
фоновая индексация.

## Связанные файлы

- `scripts/tools/skills/skills_search.py` — CLI для работы с базами
- `mcp/camoufox_worker.py` — интеграция с fetch_page
- `mcp/camoufox_fetch.py` — интеграция с batch_fetch
- `db/skill-knowledge.db` — база скиллов
- `db/context-internet.db` — база интернет-контекста

**Создано:** 2026-08-18 · **Версия:** 1.0 · **Ресёрч:** 20+ источников (research.db id=937, 939)
