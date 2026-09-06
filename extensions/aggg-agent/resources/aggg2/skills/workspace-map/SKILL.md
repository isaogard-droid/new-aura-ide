---
name: workspace-map
description: "Устройство AGGG2.0: карта каталогов, прошивка и ядро по харнесам, разноска/зеркала, процедура правки AGENTS.md; «а где у нас X?». Обязательно перед изменением структуры воркспейса. Не для установки (workspace-setup), цикла, поиска."
compatibility: AGGG2.0
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Workspace map: устройство AGGG2.0

Первоисточник: `AGENTS.md` + канон-доки.

## Карта каталогов

| Путь | Что это |
|---|---|
| `AGENTS.md` | указатель; зеркала: `~/.config/opencode/AGENTS.md`, `projects/sherpa-voice/AGENTS.md` |
| `CLAUDE.md` / `CYCLE.md` | персона + веб-ресёрч + продакшен-первым / рабочий цикл (9 фаз) |
| `docs/canon/` | CAMOUFOX.md (веб), DB-FIRST.md (база), AGENT-LSP.md (код), CODE-GRAPH.md (ревью), SETUP.md (установка), WIKI.md, FILE-SIZE.md, ARCHITECTURE.md, SEMBLE.md, skills.sh.md |
| `skills/` | канон скиллов (Agent Skills стандарт) |
| `db-tools/` / `db/` | build.py, search.py, findings.py / базы (aggg2.db, sherpa-voice.db, research.db) |
| `harness/` | прошивка: `core.txt`, `opencode/prompts/build.txt`, `opencode/plugins/proshivka.js`, `hooks/aggg2_prompt_hook.py`, `monolith.md` |
| `agent/<имя>/` | агенты: AGENT.md + персона + skills/ (reverser, semble-search) |
| `mcp/` | MCP-серверы: camoufox_research.py, db_tools_mcp.py, semble_mcp.py, agent-lsp config |
| `scripts/` | setup.py, install/, doctor/, tools/, _compat.py, jsonc_edit.py |
| `projects/` / `docs/` | sherpa-voice, video-zoom / patterns/, research/ |

## Прошивка правил (ядро → агенты)

- **Источник правды — `harness/core.txt`.**
- **opencode:** плагин `proshivka.js` инжектит ядро в системный промпт на КАЖДЫЙ ход (`experimental.chat.system.transform`) и при компакции; build-агент — `opencode/prompts/build.txt`.
- **Claude Code / Codex:** хук `aggg2_prompt_hook.py` — ядро как additionalContext (UserPromptSubmit).
- **Google (Antigravity/agy/Gemini CLI) / Hermes / Amp:** файл правил разносится `install_agents.py`: монолит в `~/.gemini/GEMINI.md`, `~/.hermes/SOUL.md`, указатель в `~/.config/amp/AGENTS.md` (ядро НЕ хук-инъекцией — уже в промпте).
- **Сторож запретов (все харнесы с хуками):** `aggg2_prompt_hook.py` — ветки: Claude/Codex (hookSpecificOutput), Reasonix (exit 2 + stderr), Codewhale (env DEEPSEEK_*), omp (AGGG2_HOOK_MODE=omp), Hermes (`{"action":"block"}`), Gemini CLI (`{"decision":"deny"}`), Antigravity/agy (hooks.json PreToolUse). Запреты (pkill-трюк, rm -rf, git reset --hard) — в ОДНОМ месте (BLOCK_RULES).
- **Установка:** `scripts/install/install_proshivka.py` (шаг `setup.py`). Грабля: core.txt берётся из `harness/core.txt`, НЕ из подпапки плагинов.

## Зеркала и разноска

- AGENTS.md в 3 местах (корень, sherpa-voice, ~/.config/opencode) — править ВСЕ одинаково; расхождение ловит `./run_tests.sh --mirrors`.
- После правки AGENTS.md: 1) зеркала, 2) `python3 scripts/install/install_agents.py --all` (только скиллы — `--skills`, агентские — `--agent-skills`, только AGENTS.md — без флага; бэкап `.bak`), 3) `./projects/sherpa-voice/run_tests.sh --mirrors`.
- Скиллы — в каталоги харнесов (opencode/claude/codex/reasonix/codewhale/deepcode/omp/antigravity/agy/hermes/amp) + `~/.agents/skills/` (gemini-cli читает алиас).
- Корневые доки читаются из корня; копируются вручную, если харнес не видит корень (`~/AGENTS.md` — монолит, обновляется копией CLAUDE.md).

## Обязательные чтения перед работой

AGENTS.md, CLAUDE.md, CYCLE.md, docs/canon/CAMOUFOX.md, DB-FIRST.md, AGENT-LSP.md, CODE-GRAPH.md, SETUP.md (ядро: core.txt п.8). ⚠️ Пути примерные: корень на монтируемом диске, mount point может смениться.

## Чеклист перед изменением структуры

- [ ] нашёл, что уже есть (scripts/, db-tools/, skills/, findings)
- [ ] понял, куда класть правило (база — DB-FIRST/AGENTS/CLAUDE, веб — CAMOUFOX)
- [ ] после правки AGENTS.md — зеркала + install_agents.py --all + run_tests --mirrors
- [ ] удалил скилл из канона → почистил харнесы вручную (install_agents.py не удаляет)

## Этапы (handoff)

- **Вход из:** `workspace-setup` (после установки), любая задача по устройству
- **Дальше:** `task-cycle`, `aggg2-mandatory-reads`

## References

- Первоисточник: `AGENTS.md`, канон-доки; смежные: `workspace-setup`, `task-cycle`, `aggg2-mandatory-reads`

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
