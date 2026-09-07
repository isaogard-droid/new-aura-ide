---
name: workspace-setup
description: "Установка/обновление/перенос AGGG2.0: bootstrap/setup.py, что копировать, требования, venv, Windows UTF-8, doctor.py, make_archive.sh. Не для ежедневных задач (task-cycle) и устройства воркспейса (workspace-map)."
compatibility: AGGG2.0; Linux/macOS/Windows
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Workspace setup: установка, обновление, перенос

Первоисточник: `docs/canon/SETUP.md`. Корень в коде не захардкожен — определяется автоматически (маркер `VERSION`) или через `$AGGG2_ROOT`.

## Workflow (порядок применения)

1. **Что копировать.** Канон-доки (AGENTS/CLAUDE/CAMOUFOX/DB-FIRST/AGENT-LSP/CODE-GRAPH) живут В КОРНЕ — не копировать. Разносятся: AGENTS.md, скиллы (по харнесам + `~/.agents/skills/`), MCP-серверы (конфиг opencode), `vpnctl` (симлинк). Всё — `scripts/setup.py`.
2. **Требования.** python3, node+npm, bun (omp), curl (opencode), git. setup.py ничего системного не ставит — честно диагностирует.
3. **Новое железо с нуля (даже без python).** Паттерн — mise (без sudo): `./scripts/bootstrap.sh` (Linux/macOS) / `.\scripts\bootstrap.ps1` (Windows: winget → mise → runtime'ы → setup.py). `--check` — план без установки. Shims mise в КОНЕЦ PATH.
4. **Python уже есть.** `python3 scripts/setup.py` (Windows: `python scripts/setup.py` — нет python3). Флаги: `--check`, `--skip-mcp`, `--skip-harnesses`, `--skip-lsp`, `--skip-db`, `--skip-doctor`. Идемпотентно.
5. **Что делает setup.py.** venv (`~/.venvs/aggg2`), зависимости MCP, браузер Camoufox (~150MB; неудача — предупреждение + `venv/bin/python -m camoufox fetch` позже), разноска (`install_agents.py --all`), MCP (`install_mcp.py`), LSP (`install_lsp_servers.py`), харнесы (`install_harnesses.py`), базы (`build.py`), симлинк `vpnctl`.
6. **Два набора зависимостей (один venv).** `mcp/requirements.txt` (MCP) + `projects/sherpa-voice/requirements.txt` (проект); setup.py ставит MCP-набор, проект — `./run.sh`. Windows: `venv\Scripts\python.exe -m pip install ...`.
7. **Windows: UTF-8.** Консоль cp1251 ломает юникод-вывод: `[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")` + рестарт консоли (детали — `windows-encoding-fixes`).
8. **Диагностика.** `python3 scripts/doctor/doctor.py` (`--json` — CI); LSP: `install_lsp_servers.py --check/--doctor/--only-config`; харнесы: `install_harnesses.py --list`, `deepcode omp`, `--exclude`, `--force`.
9. **Обновление.** `git pull` → `python3 scripts/setup.py` → `./projects/sherpa-voice/run_tests.sh --mirrors`. Без git: архив поверх корня + setup.py.
10. **Архив для шаринга.** `./make_archive.sh` (aggg2-<версия>.tar.gz рядом с корнем), `--list`, `--zip-password ПАРОЛЬ`. Не попадают: db/, venv/, .env, models/, .git/, .github/, .reasonix/, вложенные репозитории; перед сборкой — проверка на секреты.
11. **Проверка здоровья.** `vpnctl status`, `opencode mcp list` (connected), `python3 db-tools/search.py "тест"`, `./projects/sherpa-voice/run_tests.sh`.

## Грабли

- Mount point диска может смениться — пути примерные, подставлять реальные.
- `install_lsp_servers.py` на CI (`CI=true`) пропускает тяжёлые загрузки (clangd/lua) — норма.
- `install_agents.py` не удаляет осиротевшие скиллы — чистить харнесы вручную.
- Windows: winget может отсутствовать — LSP-скрипт делает fallback scoop/choco.

## Этапы (handoff)

- **Вход из:** новая машина / обновление
- **Дальше:** `workspace-map`, `aggg2-mandatory-reads`, `task-cycle`

## References

- Первоисточник: `docs/canon/SETUP.md`; смежные: `windows-encoding-fixes`, `task-cycle`

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
