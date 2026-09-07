# CODE-GRAPH — ревью изменений через граф кода

MCP-сервер `code-review-graph` (tirth8205, 29.5k★, MIT; tree-sitter граф) подключён в живой конфиг opencode — opencode.json/.jsonc. Отвечает на вопрос **«что сломает эта правка из N файлов»** — impact/blast radius по ДИФФУ, dead-code, communities, flows. 30 MCP-инструментов + CLI-команды.
**Порядок:** (ядро: core.txt п.2). ПЕРЕД КОММИТОМ — ОБЯЗАТЕЛЬНО ревью диффа: сначала `get_diagnostics` (agent-lsp), затем CRG (`detect_changes`/`get_impact_radius`); граф пересобирается инкрементально (`build_or_update_graph_tool`) — данные устарели = ложный анализ. Пропущенное ревью = правка не готова. CRG дополняет, не заменяет.

## Когда использовать
| Задача | Инструмент |
|---|---|
| ревью изменений (дифф → риск → приоритеты) | `detect_changes` (risk-скор, пробелы в тестах) |
| blast radius правки из N файлов | `get_impact_radius`, `get_review_context` |
| затронутые execution-пути (пользовательские флоу) | `get_affected_flows`, `list_flows` |
| мёртвый код | `refactor_tool(mode="dead_code")` |
| архитектура: «кто хаб/мост/связан неожиданно» | `get_hub_nodes`, `get_bridge_nodes`, `get_surprising_connections`, `get_architecture_overview` |
| слабые места (изолированные узлы, тонкие коммьюнити) | `get_knowledge_gaps`, `get_suggested_questions` |
| сообщества кода | `list_communities`, `get_community` |
| переименование с предпросмотром | `refactor_tool(mode="rename")` → `apply_refactor_tool` |

## Грабли (проверено замером 08.2026, подробности в research.db)
- **repo_root — от CWD процесса харнесса, не от проекта**: env `CRG_REPO_ROOT` → git-root от cwd → cwd (issue #155). Харнес из HOME (не git-репо) молча читает ПУСТУЮ базу `~/.code-review-graph/` — тулы отдают нули. Лечится `CRG_REPO_ROOT=<корень>` в конфиге MCP-сервера (`install_mcp.py` прописывает сам). Ключ конфига — `environment` (не `env` — silently игнорируется, opencode #26332/#39135).
- **dead-code даёт ложные срабатывания** (callback-паттерны, `Thread(target=...)`) — проверять через agent-lsp (`find_references`), не удалять вслепую.
- **search CRG без эмбеддингов слабее нашей базы** (голый FTS) — поиск по коду через `search.py`/db-tools, CRG — для структурного анализа.
- граф строится инкрементально: `build_or_update_graph_tool` (после правок — пересобрать). Первый build большого проекта не мгновенный.

## Как проверить подключение
```bash
opencode mcp list        # code-review-graph должен быть connected
code-review-graph mcp    # запуск сервера (CLI)
```

## Подробнее
Установка/подключение: `scripts/install/install_mcp.py`, `mcp/README.md`. Глубина по коду (типы/ссылки/rename): AGENT-LSP.md.

Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
