# Аудит, улучшения, agent-lsp (вынесено из DB-FIRST.md)

Механическая резка god-файла `DB-FIRST.md` (FILE-SIZE.md, доки soft 300). Код перенесён дословно. Правила поиска — в `DB-FIRST.md`.

## Аудит и улучшения через индексацию
База — не только поиск, но и ИЗМЕРЕНИЯ: данные для решений (паттерн SonarQube/CodeScene/DORA — «улучшение без данных = догадка»). Инструменты уже есть: метрики в sqlite, CRG, линтеры.
```bash
# метрики: топ файлов по строкам, ошибки
sqlite3 db/aggg2.db "SELECT rel_path, lines FROM files ORDER BY lines DESC LIMIT 10;"
python3 db-tools/search.py --errors      # файлы, которые не парсятся
python3 db-tools/search.py --stats       # как используются базы
# граф кода (CRG): get_hub_nodes — хотспоты; refactor (dead_code) — мёртвые символы
#   get_knowledge_gaps — untested hotspots; find_large_functions — функции > N строк
```
1. **Улучшение без данных = догадка**: сначала метрики (база/CRG/линтеры), потом «что улучшать и почему».
2. **Крупный рефакторинг — со сверкой:** кандидаты из данных → план → правки → QA (тесты зелёные).
3. **Ложные срабатывания CRG** (argparse-dispatch, addEventListener, Thread) — проверять agent-lsp, не удалять вслепую.
4. **После аудита — выводы в research.db** (что нашли/сделали/в бэклог, с id). (ядро: core.txt п.5)
5. **Health-check — ритуал:** refresh → метрики → CRG → бэклог улучшений.

## agent-lsp (глубина по коду)
База — быстрый статический слой (где символ, кто вызывает, FTS). Когда ответ НЕ очевиден из базы — agent-lsp: MCP-сервер (LSP → MCP), `/usr/local/bin/agent-lsp`, в `opencode.jsonc`. Для Python — pyright. 65 инструментов.
- типы и связи: `find_symbol` (`detail_level: "hover"`), `type_hierarchy`, `go_to_type_definition`
- скоуп и тень («этот foo — другой»), ВСЕ ссылки (импорты, тернарные): `find_references` — база `--calls` ловит только прямые `имя(...)`
- безопасный rename: `prepare_rename` → предпросмотр → `rename_symbol`
- диагностика: `get_diagnostics` (pyright: типы, неиспользуемое — база видит только SyntaxError)
Порядок: сначала база (`search.py --symbol/--calls/--inherits`); не хватило — agent-lsp. Не начинать с грепа, если вопрос про символы. (ядро: core.txt п.2)
Грабли, конфиг, проверка — **AGENT-LSP.md**. Ревью диффов — **CODE-GRAPH.md**.

---

## Журнал задач и история файлов (вынесено из DB-FIRST.md, 18.08)

## Журнал задач (tasks в research.db)
Дополнение к находкам: находки = «что знаем», журнал = «что делали, когда и чем кончилось». Append-only. Завести задачу и закрыть по итогу — CYCLE.md фазы 0 и 8.
```bash
python3 db-tools/tasks.py add "Что делаем, одной строкой" --tags "тема"
python3 db-tools/tasks.py list                    # открытые
python3 db-tools/tasks.py list --status all       # вся история
python3 db-tools/tasks.py close 5 --result "итог одной-двумя строками"
python3 db-tools/tasks.py block 5 --reason "что мешает"   # заблокирована
python3 db-tools/tasks.py abort 5 --reason "почему"        # отменена
python3 db-tools/tasks.py search прошивка         # FTS по задачам и итогам
python3 db-tools/tasks.py stats
```
«Что мы делали N недель назад / что открыто» → сначала `tasks.py`.

## История файлов (git → research.db)
«Кто менял файл, когда, как часто» — history-aware поиск из базы (паттерн Sourcegraph/zoekt). Замер 13.08.2026: `git log` по AGGG2.0 — 0.00с, 7.6 МБ пик RAM, база +428 КБ.
```bash
python3 db-tools/githist.py refresh                # перечитать (идемпотентно)
python3 db-tools/githist.py file scripts/doctor/doctor.py # кто менял файл, когда
python3 db-tools/githist.py hotspots --top 10      # файлы-лидеры по правкам
python3 db-tools/githist.py commits --since 2026-08-01
```
Свежесть ловит `doctor.py` (db-freshness). Отклонено замером: SCIP-индекс (70 МБ + 410 МБ RAM, дублирует agent-lsp), RRF-гибрид (эффект ≈0; вернуться с эмбеддингами на пороге ~2–5к находок).
**Метрики баз**: `python3 db-tools/search.py --stats` — топ запросов, пустые результаты (search_log пишется при каждом поиске).

Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
