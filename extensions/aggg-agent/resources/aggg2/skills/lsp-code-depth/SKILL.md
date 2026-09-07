---
name: lsp-code-depth
description: "Вопросы по коду: типы, скоуп/тень, ВСЕ ссылки, безопасный rename, диагностика; перед правкой функции (кто вызывает); после правок — get_diagnostics. Не для поиска по содержимому — база сначала (db-first-search)."
compatibility: AGGG2.0 (MCP agent-lsp, 65 инструментов, 10 LSP-серверов)
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# LSP depth: типы, ссылки, rename, диагностика

Первоисточник: `docs/canon/AGENT-LSP.md`. MCP agent-lsp — для вопросов, где нужны типы, скоуп, ВСЕ ссылки, безопасный rename, диагностика. Порядок: база (дёшево) → не хватило → agent-lsp.

## Workflow

1. **Начни с базы:** `search.py --symbol/--calls/--inherits` (где определён символ, кто вызывает напрямую, FTS).
2. **Подключай agent-lsp, когда базы не хватает:** типы и связи, скоуп/тень, ВСЕ ссылки (база ловит только прямые `имя(...)`), rename, диагностика, структура файла. Не начинать с грепа/чтения, если вопрос про символы.
3. **Выбери инструмент** (таблица ниже).
4. **После ЛЮБЫХ правок кода — ОБЯЗАТЕЛЬНО `get_diagnostics`** (0 ошибок = готово к QA; чинить ДО ruff/semgrep/тестов).
5. **ПЕРЕД КОММИТОМ — ревью диффа** через code-review-graph (`code-graph-review`).

## Таблица: задача → инструмент

| Задача | Инструмент |
|---|---|
| типы и их связи | `find_symbol` (detail_level: "hover"), `type_hierarchy`, `go_to_type_definition` |
| скоуп и тень | только LSP |
| ВСЕ ссылки (импорты, тернарные вызовы) | `find_references` |
| безопасный rename с предпросмотром | `prepare_rename` → предпросмотр → `rename_symbol` |
| диагностика (типы, неиспользуемое) | `get_diagnostics` |
| кто вызывает перед удалением/правкой | `blast_radius` (callers: тест/не-тест), `find_callers` |
| структура файла | `list_symbols` (outline) |

## Грабли (проверено замером 08.2026)

- `start_lsp` ОБЯЗАТЕЛЕН перед инструментами; аргументы: `root_dir`, `language_id` — не `file_path`.
- `find_references`/`rename_symbol` — по ПОЗИЦИИ (`file_path`+`line`+`column`, 1-indexed), не по имени.
- Первая индексация ~30с, дальше тёплый runtime (0.3s таймаут = «нет ответа»).
- Конфиг: `mcp/agent-lsp/config.json`; проверка: `opencode mcp list` (connected).
- `npm i -g typescript` ставит TS7 (Go-порт) — нет `lib/tsserver.js`, tsserver падает; нужен `typescript@5` + симлинк.
- Установка LSP-серверов: `scripts/install/install_lsp_servers.py` (идемпотентный, `--doctor`/`--check`/`--only-config`).

## Этапы (handoff)

- **Вход из:** `db-first-search` (база СНАЧАЛА) · **Дальше:** `code-review`, `windows-encoding-fixes`

## References

- `docs/canon/AGENT-LSP.md`; смежные: `db-first-search`, `code-graph-review`, `windows-encoding-fixes`.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
