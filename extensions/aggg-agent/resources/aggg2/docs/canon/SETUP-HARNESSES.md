# Установка: харнесы и зависимости (вынесено из SETUP.md)

Механическая резка god-файла `SETUP.md` (FILE-SIZE.md, доки soft 300). Полный цикл — в `SETUP.md`.

### Харнесы Google (Antigravity / agy / Gemini CLI), Hermes, Amp и др.

Прошиваются тем же `install_agents.py --all`, но пути свои (проверено по офиц. докам, 08.2026):

| Харнес | Файл правил (глоб.) | Скиллы (глоб.) | Субагенты (глоб.) |
|---|---|---|---|
| Antigravity 2.0 (IDE) | `~/.gemini/GEMINI.md` | `~/.gemini/config/skills/` | `~/.gemini/config/agents/` |
| agy (Antigravity CLI) | `~/.gemini/GEMINI.md` | `~/.gemini/antigravity-cli/skills/` + `config/skills/` | `~/.gemini/config/agents/` |
| gemini-cli | `~/.gemini/GEMINI.md` | `~/.agents/skills/` (общий алиас, приоритетнее своего) | `~/.gemini/agents/` |
| Hermes (CLI + Desktop) | `~/.hermes/SOUL.md` (слот #1) | `~/.hermes/skills/` | — (динамические, delegate_task) |
| Amp (Sourcegraph) | `~/.config/amp/AGENTS.md` | `~/.config/agents/skills/` | — (не задокументированы) |
| Windsurf | `~/.codeium/windsurf/memories/global_rules.md` (лимит 6000 симв., монолит влезает) | — | — |
| Copilot CLI | `~/.copilot/copilot-instructions.md` | — | `~/.copilot/agents/*.agent.md` |
| Kiro (Amazon) | — (MCP только) | — | — |

- У семьи Google файл правил — `GEMINI.md`, туда пишется **монолит** (`harness/monolith.md`), не полный CLAUDE.md и не указатель: GEMINI.md впрыскивается в КАЖДЫЙ промпт — указатель бесполезен (нет доступа к воркспейсу), полный CLAUDE.md — перегруз always-on. `AGENTS.md` читается из корня проекта (Antigravity — с v1.20.3; gemini-cli — по умолчанию, PR #28240). Глобальный `~/.gemini/AGENTS.md` у Antigravity — 1 источник, не автоматизировано (проверить при аудите).
- agy: скиллы в ОБА каталога (`config/skills/` и `antigravity-cli/skills/` — доки разнятся).
- Установка CLI: `install_harnesses.py agy gemini` (agy — `curl -fsSL https://antigravity.google/cli/install.sh | bash`; gemini — `npm install -g @google/gemini-cli`). Antigravity 2.0 — GUI, вручную (установщик честно пропускает).
- ⚠️ С 18.06.2026 Google переводит индивид. пользователей Gemini CLI на agy (developers.googleblog.com); gemini-cli остаётся для Enterprise и OSS.
- MCP: antigravity/agy — `~/.gemini/config/mcp_config.json` (`mcpServers`, command/args/env, antigravity.google/docs/mcp); gemini-cli — `~/.gemini/settings.json` (top-level `mcpServers`, geminicli.com/docs/tools/mcp-server). Доставляет `install_mcp.py`.
- Сторож (install_proshivka.py, общий `aggg2_prompt_hook.py`): gemini-cli — `hooks.BeforeTool` в `~/.gemini/settings.json` (matcher `run_shell_command`, `{"decision":"deny"}` + exit 2, env AGGG2_HOOK_MODE=gemini; включить: `/hooks enable aggg2-storozh`); antigravity/agy — `~/.gemini/config/hooks.json` (`PreToolUse`, matcher `run_command`, гейт `{"decision":"deny"}`).
- **Amp**: `~/.config/amp/AGENTS.md` всегда включается (ampcode.com/manual); скиллы — `~/.config/agents/skills/` (ampcode.com/news/agent-skills; читает и `~/.claude/skills/`). MCP/субагенты не задокументированы — пропущены. Установка: `install_harnesses.py amp` (`curl -fsSL https://ampcode.com/install.sh | bash`).
- **Cursor CLI**: глобального AGENTS.md нет — читает `AGENTS.md`/`CLAUDE.md` из корня + `.cursor/rules/` (cursor.com/docs/cli/using); запись только для установки/карты. MCP — `install_mcp.py` (`~/.cursor/mcp.json`). Хуки шлют не все события (известный баг) — сторож не ставим. Установка: `install_harnesses.py cursor` (`curl https://cursor.com/install -fsS | bash`).
- **Windsurf**: монолит — `~/.codeium/windsurf/memories/global_rules.md` (лимит 6000 симв., монолит 4КБ влезает); MCP — `~/.codeium/windsurf/mcp_config.json`. Скиллы/субагенты не задокументированы. Установка — с windsurf.com.
- **Copilot CLI**: монолит — `~/.copilot/copilot-instructions.md`; субагенты — `~/.copilot/agents/*.agent.md` (.md конвертится расширением, контент тот же); AGENTS.md/CLAUDE.md/GEMINI.md читает из репо сам. MCP/скиллы не задокументированы. Установка: `install_harnesses.py copilot` (`npm install -g @github/copilot`).
- **Kiro (Amazon)**: MCP — `~/.kiro/settings/mcp.json` (kiro.dev/docs/mcp/configuration); правила/агенты — пути не подтверждены — не прошиваем. Crush (charm): ключ `mcp` есть, схема не подтверждена — пропущен (проверить при аудите).
- **Hermes** (Nous Research): CLI + Desktop — один агент-ядро, конфиг `~/.hermes/` (HERMES_HOME). Монолит — `~/.hermes/SOUL.md` (слот #1). Глобального AGENTS.md нет — читает из корня (git-root → cwd; first-match: `.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`). Субагенты динамические (`delegate_task`) — разноска пропущена. Скиллы — стандарт agentskills.io. Установка: `install_harnesses.py hermes` (`curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`); Desktop — `hermes desktop` или установщик. MCP — `install_mcp.py` в `mcp_servers:` `~/.hermes/config.yaml` (схема `command`+`args`+`env`, docs/reference/mcp-config-reference). Сторож — `install_proshivka.py`: shell hook `pre_tool_call` (общий `aggg2_prompt_hook.py`, ветка hermes по wire-протоколу agent/shell_hooks.py: stdout `{"action":"block"}` + exit 2); согласие — `hooks_auto_accept: true`; проверка: `hermes hooks list`.

## Требования к системе

`setup.py` ничего системного не ставит (забота менеджера пакетов ОС) — но честно диагностирует в начале:

| Инструмент | Зачем | Если нет |
|---|---|---|
| python3 | сам установщик | обязательно (setup.py не запустится) |
| node + npm | npm-харнесы (claude, codex, reasonix, codewhale, deepcode, gemini) | харнесы не поставятся — предупреждение |
| bun | omp-харнес | omp пропустится с подсказкой |
| curl | opencode, agy, hermes (posix) | opencode/agy/hermes не поставятся |
| git | обновление через pull | обновление только архивом |

## Новое железо с нуля (даже без python) — одна команда

Runtime'ы сначала; паттерн — **mise** (замена nvm/pyenv/asdf, без sudo):

```bash
# Linux/macOS
./scripts/bootstrap.sh                # всё: runtime'ы → setup.py
./scripts/bootstrap.sh --check        # план, ничего не ставя

# Windows (PowerShell)
.\scripts\bootstrap.ps1               # winget: mise → runtime'ы → setup.py
.\scripts\bootstrap.ps1 --check
```

Есть python/node/bun/go/rust — ничего не ставит, просто запускает `setup.py` (аргументы передаются дальше). Иначе — mise (`curl https://mise.run | sh` / `winget install jdx.mise`) + `mise use --global` недостающие runtime'ы. Shims mise — в КОНЕЦ PATH: системные версии не перебиваются.

## Установка на новую машину (python уже есть)

```bash
python3 scripts/setup.py        # Linux/macOS
python scripts/setup.py         # Windows (там нет python3 — только python)
python3 scripts/setup.py --check     # показать план, ничего не делать
python3 scripts/setup.py --skip-mcp  # выборочно (см. --help)
```

---

`setup.py` сам: venv + MCP-зависимости (`mcp/requirements.txt`), браузер Camoufox (разово ~150MB; при неудаче докачать: `venv/bin/python -m camoufox fetch`), разноска (`install_agents.py --all`: AGENTS.md по корням агентов, Google — `~/.gemini/GEMINI.md`; скиллы канона по харнесам + `~/.agents/skills/`; скиллы агентов `agent/*/skills/` НЕ разносим — читаются субагентом напрямую (изоляция); отдельно: `--skills`, `--agent-skills`, или только файл правил), MCP (`install_mcp.py`), LSP (`install_lsp_servers.py`: Go/JS/TS/Rust/C/bash/JSON/YAML/Docker/Lua, на CI пропускает тяжёлое), харнесы (`install_harnesses.py`), базы (`build.py`), `vpnctl`. Всё идемпотентно. Требуется только Python 3.

## Расширения харнесов (офф-механизмы, после setup.py)

```bash
# Gemini CLI (agy/antigravity): extension «aggg2» — контекст + MCP пакетом
python3 scripts/install/harness_plugins/extensions_gemini.py --check
python3 scripts/install/harness_plugins/extensions_gemini.py      # link в ~/.gemini/extensions/

# Claude Code: плагин (команды /bro, /findings, /canon) — нужен claude /login
python3 scripts/install/harness_plugins/claude_plugin.py          # сам проверит login и поставит

# Cursor: глобальное правило ядра + команды (~/.cursor/rules, ~/.cursor/commands)
python3 scripts/install/harness_plugins/cursor_rules.py
```

MCP-серверы реверсера (ghidra/reverser) в харнесы НЕ доставляются (манифест `agent/reverser/mcp/manifest.json`: `"harnesses": []` — изоляция); субагент @reverser зовёт их из shell: `agent/reverser/scripts/mcp_call.sh reverser|ghidra list|call` (сервер поднимается на время вызова). Глобально — явно: харнес в манифесте + `setup_mcp.sh`.

Базы: карта кода (`db-tools/repomap.py project|file`, MCP `repo_map`), поиск по всем базам (`db-tools/search_all.py`, MCP `search_all`), граф находок (`findings.py related <id> --depth 2`).

## Два набора зависимостей (один venv)

| Файл | Что даёт |
|---|---|
| `mcp/requirements.txt` | MCP-слой: mcp, camoufox, code-review-graph |
| `projects/sherpa-voice/requirements.txt` | проект: sherpa-onnx, sounddevice, soxr, reportlab |

```bash
venv/bin/python -m pip install -r mcp/requirements.txt \
    -r projects/sherpa-voice/requirements.txt
# Windows:
venv\Scripts\python.exe -m pip install -r mcp\requirements.txt \
    -r projects\sherpa-voice\requirements.txt
```

`setup.py` ставит только MCP-набор (проект ставится его `./run.sh`).

## Windows: UTF-8 для консоли

Консоль по умолчанию cp1251 — вывод с юникодом (✓/✗, кириллица) падает с `UnicodeEncodeError`. Скрипты чулана переключают stdout сами, для сторонних утилит — системное:

```powershell
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
# перезапустить консоль
```

Или разово: `$env:PYTHONUTF8=1` перед запуском python.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
