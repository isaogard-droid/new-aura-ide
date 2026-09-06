# AGENT-LSP — глубина по коду

MCP-сервер `agent-lsp` (мост LSP → MCP, `/usr/local/bin/agent-lsp`, в живом конфиге
opencode) — для вопросов по коду: **типы, скоуп, все ссылки, безопасный rename,
диагностика**. 65 инструментов.

**Языковые серверы** (`mcp/agent-lsp/config.json`, формат `extensions → command`):

| Язык | Сервер | Как ставится |
|---|---|---|
| Python | `pyright-langserver` | `npm i -g pyright` (fallback: pipx, `pip --user`) |
| Go | `gopls` | `go install golang.org/x/tools/gopls@latest` → `~/go/bin` |
| Rust | `rust-analyzer` | `rustup component add rust-analyzer` |
| JS/TS | `typescript-language-server` | `npm i -g typescript-language-server typescript@5` |
| C/C++ | `clangd` | пакет ОС (`dnf/apt install clang-tools-extra/clangd`) |
| bash | `bash-language-server` | `npm i -g bash-language-server` |
| JSON | `vscode-json-languageserver` | `npm i -g vscode-json-languageserver` (бинарь БЕЗ второй «s») |
| YAML | `yaml-language-server` | `npm i -g yaml-language-server` |
| Dockerfile | `docker-langserver` | `npm i -g dockerfile-language-server-nodejs` |
| Lua | `lua-language-server` | GitHub release LuaLS (tar без корневой папки — в свою директорию) |

**Установка:** `scripts/install/install_lsp_servers.py` (кроссплатформенно, идемпотентный;
перегенерирует `config.json`; `--doctor` — проверка, `--check` — план, `--only-config` —
конфиг; на CI пропускает clangd/lua). Шаг `scripts/setup.py`, тест в
`.github/workflows/setup-test.yml` (3 ОС). После — перезапустить opencode.

**Харнессы:** `scripts/install/install_mcp.py` разносит по всем с MCP: opencode, claude,
codex, deepcode (opencode.json/.jsonc, .claude.json, .codex/config.toml,
.deepcode/settings.json). Серверы — общие для всех.

**Без хардкода путей:** симлинки бинарей в `~/.local/bin` — авто-детект без `--config`
(язык по расширению; новый проект без правки конфигов). `config.json` всё равно
генерится (явные пути надёжнее + pyright/tsserver нужен `--stdio`).

Проверка: `agent-lsp doctor`. Грабля: `npm i -g typescript` = TS7 (Go-порт), нет
`lib/tsserver.js` — падает; нужен `typescript@5` + симлинк (детали в базе знаний).
Не ставятся (JVM/native): jdtls, kotlin-language-server, intelephense, solargraph,
csharp-ls, swift/zig.

База — быстрый статический слой (где символ, кто вызывает, FTS). **Порядок: сначала
база (ядро: core.txt п.2) → не хватило → agent-lsp.**

## Когда использовать agent-lsp вместо грепа/чтения/базы

| Задача | Инструмент |
|---|---|
| типы и их связи | `find_symbol` (`detail_level: "hover"` — сигнатура и тип), `type_hierarchy`, `go_to_type_definition` |
| скоуп и тень («этот foo — другой») | только LSP |
| ВСЕ ссылки на символ (импорты, тернарные вызовы) | `find_references` (база `--calls` — только прямые `имя(...)`) |
| безопасное переименование с предпросмотром | `prepare_rename` → предпросмотр → `rename_symbol` (не трогает комментарии и чужие переменные) |
| диагностика (типы, неиспользуемое) | `get_diagnostics` (база видит только SyntaxError) |
| кто вызывает функцию перед удалением/правкой | `blast_radius` (callers: тест/не-тест), `find_callers` |
| структура файла | `list_symbols` (outline) |

## Порядок работы с кодом

1. **База** — `search.py --symbol/--calls/--inherits`.
2. Не хватило (типы/скоуп/все ссылки/rename) — **agent-lsp**.
3. После ЛЮБЫХ правок — **ОБЯЗАТЕЛЬНО** `get_diagnostics` (0 ошибок = готово к QA;
   есть — чинить ДО ruff/semgrep/тестов). Пропуск = незавершённая правка (грабля
   08.2026: install_proshivka.py правился 3 раза без неё).
4. ПЕРЕД КОММИТОМ — **ОБЯЗАТЕЛЬНО** ревью диффа через code-review-graph
   (`detect_changes`/`get_impact_radius`, граф пересобран `build_or_update_graph_tool`).
   Детали — CODE-GRAPH.md.

## Грабли (проверено замером 08.2026, подробности в research.db)

- `start_lsp` **обязателен** перед инструментами: `root_dir`, `language_id` — не `file_path`.
- `find_references`/`rename_symbol` — по **позиции** (`file_path` + `line` + `column`, 1-indexed).
- **`position_pattern` (@@...@@) хрупкий:** «not found in file» = «паттерн не совпал»,
  сервер жив (12.08.2026). Надёжно: `find_symbol` → `find_references` по line/column
  или `blast_radius`.
- Первая индексация ~**30с**, дальше тёплый runtime; 0.3s таймаут = «нет ответа».
- Конфиг: `mcp/agent-lsp/config.json`; запуск — авто-детект или `--config`.
- Проверка: `opencode mcp list` (agent-lsp должен быть connected).

## Подробнее

Установка/подключение: `scripts/install/install_mcp.py`, `mcp/README.md`;
«Карта проекта» (база) — DB-FIRST.md.

Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->
