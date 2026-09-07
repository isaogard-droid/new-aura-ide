---
name: semble
description: "Найти код по СМЫСЛУ: «найди код, который валидирует», «как обрабатываются ошибки» — MCP semble.search/find_related (терминами дока). НЕ для точного имени (сразу agent-lsp) и коротких keyword (db-tools FTS). Грабли: первый запрос — индексация."
---
# Semble — семантический поиск по коду (MCP)

Эмбеддинги (potion-code-16M) + BM25 + code-aware reranking; релевантные чанки с путём и строкой — 98% меньше токенов, чем grep+read. Первоисточник: docs/canon/SEMBLE.md, github.com/MinishLab/semble.

## When to use / when NOT to use

Используй, когда вопрос про СМЫСЛ и имени символа не знаешь. **НЕ используй:** точное имя → `agent-lsp find_symbol/find_references` (5-34x меньше токенов; 92-99% grep-хитов — false positives); структура («кто импортирует») → db-tools; короткий keyword («auth flow») → db-tools FTS (CoREB 05.2026: nDCG@10 ≈ 0); «мы это разбирали?» → findings.py, wiki.

## Workflow

1. Запрос — описательно, коротко, терминами дока + англ. термины: «как считается лимит токенов», «обработка ошибок error handling retry». Длинные русские фразы размывают вектор.
2. `tools.semble.search({ query, repo: <корень>, top_k: 5, max_snippet_lines: 10 })`. repo — путь или https:// URL (кэш на сессию).
3. Не подтвердил сниппетом → `max_snippet_lines: None` или больше `top_k`.
4. Нашёл файл → по лестнице: db-tools (кто вызывает) → agent-lsp (типы/ссылки) — `code-search-ladder`.
5. Похожий код рядом с известной локацией → `find_related({ file_path, line, repo })`.

## Success criteria

Ответ с путём и строкой; файл в топ-5; ни одного grep/read вслепую после вызова. Цифры (19.08): 23/23 доступность, 13/13 качество, avg 43ms (p50 28ms) на тёплом индексе.

## Failure modes

- **Нерелевантен** → запрос — бытовой пересказ, не термины дока («toggle enabled mcp opencode»); переформулируй или → db-tools.
- **Нет файла в топ-5, хотя он есть** → `.txt/.json/.jsonc` вне индекса (core.txt, opencode.jsonc) — read напрямую.
- **Первый запрос ~400ms+** → индексация репо; дальше из кэша. **«Unknown tool» после перезапуска MCP** → повторить; не помогло — переподключить сервер (SEMBLE.md «Переподключение»).

## Gotchas

- Запрос — НЕ текст ошибки и НЕ имя файла: описание поведения/назначения.
- **Терминами дока, не пересказом** (19.08: термины 23/23 и 15/15, перефразы 0-1/10 и 2/15): Model2Vec ловит редкие термины (raw, tree, fuzzy, quarantine, toggle).
- **Не знаешь терминов — возьми из db-tools** (двухшаговая схема, 19.08): db-tools FTS ловит 40% перефразов — из его выдачи возьми термины и повтори semble: 100% (15/15). Стемминг/multi-query не помогают.
- Короткий запрос + англ. термин бьёт длинный пересказ (модель англоязычная): «судья ревьюеров вердикт» → multimodel_judge.py, пересказ — нет.
- `max_snippet_lines: 0` — только путь+строка (для карты). Один поиск на вопрос: иди к файлу, не повторяй.

## Этапы (handoff)

- **Вход из:** `code-search-ladder`, `task-cycle` (база не дала ответа), `debug-incident-protocol` · **Дальше:** `db-first-search`, `lsp-code-depth`, `code-search-ladder`

## References

- docs/canon/SEMBLE.md; github.com/MinishLab/semble

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
