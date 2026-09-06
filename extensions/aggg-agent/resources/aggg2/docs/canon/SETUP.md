# Установка / обновление / перенос AGGG2.0

AGGG2.0 — самодостаточный воркспейс (канон-доки, скиллы, db-tools, MCP-серверы, базы, установщики). Корень в коде не захардкожен — авто-определяется, работает из любого места на любой ОС.

## Как находится корень воркспейса

Порядок (`scripts/_compat.py: chulan_root()`):
1. **`$AGGG2_ROOT`** — явный оверрайд (абсолютный путь), когда авто-детект не работает.
2. **Авто-детект по маркерам** — подъём вверх от `scripts/`; корень — при ЛЮБЫХ ДВУХ из `VERSION` / `db-tools/` / `scripts/_compat.py`. Потеря одного маркера (напр. `VERSION` в старых версиях) поиск не ломает.
3. **`__file__`-based** — scripts/ на один уровень ниже корня.

Маркеров меньше двух — честная ошибка с подсказкой.

```bash
export AGGG2_ROOT=/path/to/AGGG2.0   # оверрайд (любая ОС)
python3 scripts/setup.py             # корень найдётся сам
```

## Что копировать, а что нет

Доки (AGENTS.md, CLAUDE.md, CYCLE.md, docs/canon/*.md) живут в корне — копировать не нужно. `AGENTS.md` — единственный общий файл правил, дополнительно разносится по харнессам. Разноски требуют только:
- `AGENTS.md` — глобальный (`~/.config/opencode/AGENTS.md` и аналоги); в харнесы Google (Antigravity/agy/Gemini CLI) — монолит в `~/.gemini/GEMINI.md`, в Hermes — в `~/.hermes/SOUL.md` (слот #1)
- скиллы канона — по каталогам харнесов + общий `~/.agents/skills/`
- MCP-серверы — в конфиги харнесов (пути каждого харнеса и детали — SETUP-HARNESSES.md; ставит `install_mcp.py`)
- `vpnctl` — симлинк `~/.local/bin/vpnctl` → `scripts/vpnctl`

Всё делает кроссплатформенный `scripts/setup.py`.

---

## Установка: харнесы, требования, зависимости, Windows — вынесены в `docs/canon/SETUP-HARNESSES.md` (резка god-файла, FILE-SIZE.md)

Харнесы **опциональны, не навязываются**: `setup.py` не ставит новые CLI, только настраивает уже установленные (opt-in):

```bash
python3 scripts/install/install_harnesses.py --list       # что доступно и команды
python3 scripts/install/install_harnesses.py opencode     # поставить один
python3 scripts/setup.py --with-harnesses                 # или все сразу
```

## Диагностика чулана

```bash
python3 scripts/doctor/doctor.py        # весь чек-лист (зеркала, venv, MCP, agent-lsp, тесты)
python3 scripts/doctor/doctor.py --json # машинный вывод (CI)
python3 scripts/tools/audit/harness_status.py            # таблица 16 харнесов
python3 scripts/tools/ctx_probe.py --all           # токены контекста каждого харнеса
python3 scripts/tools/audit/harness_snapshot.py backup   # снапшот конфигов (~/.aggg2/snapshots/)
python3 scripts/tools/audit/harness_snapshot.py restore <имя>   # откат после правки
```

Camoufox (версия, окружение, Windows-баги):

```bash
python3 scripts/install/update_camoufox.py --check           # диагностика (ничего не меняет)
python3 scripts/install/update_camoufox.py --check --json    # CI
python3 scripts/install/update_camoufox.py                   # проверить + обновить пакет и браузер
```

Windows — та же команда из venv проекта (баги MS Store Python, VC++ Redistributable — в базе знаний):

```powershell
venv\Scripts\python.exe scripts\tools\update_camoufox.py --check
```

LSP-серверы (идемпотентно):

```bash
python3 scripts/install/install_lsp_servers.py --check      # план: что есть/нет
python3 scripts/install/install_lsp_servers.py --doctor     # установить + agent-lsp doctor
python3 scripts/install/install_lsp_servers.py --only-config  # пересоздать config.json
```

MCP-доставка (идемпотентно):

```bash
python3 scripts/install/install_mcp.py --list                          # план: какие серверы и куда
python3 scripts/install/install_mcp.py --server agent-lsp db-tools       # только эти серверы
python3 scripts/install/install_mcp.py --harness claude codex          # только эти харнесы
python3 scripts/install/install_mcp.py                                 # полная установка
```

Конфиги правятся ТОЧЕЧНО (jsonc-parser от Microsoft): меняется только секция MCP — комментарии, чужие записи, форматирование сохраняются. Hermes (YAML) — то же построчно, без парсера. Полная установка (без `--server`) чистит устаревшее; частичная — только доставляет выбранные. Серверы агентов (`agent/<имя>/mcp/*.py|*.sh`) — автоматически; allow-list — `agent/<имя>/mcp/manifest.json` (по умолчанию только opencode). Пример: `agent/<имя>/scripts/setup_mcp.sh`.

Харнесы с выбором:

```bash
python3 scripts/install/install_harnesses.py --list                     # команды
python3 scripts/install/install_harnesses.py deepcode omp               # только эти
python3 scripts/install/install_harnesses.py --exclude deepcode omp     # все, кроме
python3 scripts/install/install_harnesses.py --force deepcode           # переустановить
```

## Обновление

```bash
git pull                     # если из репозитория
python3 scripts/setup.py     # пересборка баз + разноска + vpnctl (идемпотентно)
./projects/sherpa-voice/run_tests.sh --mirrors   # зеркала AGENTS.md
```

Camoufox — отдельно от setup.py (большой бинарь, зависит от ОС): `python3 scripts/install/update_camoufox.py`. Windows — из venv, после обновления `--check`.

Без git (архив) — «по месту»: снапшот → сверка манифестов → чистка устаревшего в бэкап → наложение нового с .old-копиями:

```bash
python3 scripts/install/aggg_upgrade.py aggg2-<версия>.tar.gz --dry-run  # план: +/~/- файлов
python3 scripts/install/aggg_upgrade.py aggg2-<версия>.tar.gz             # обновление ядра
python3 scripts/setup.py --check && python3 scripts/setup.py            # официальная установка
python3 scripts/doctor/doctor.py                                        # здоровье: 0 новых ошибок
```

Режим «две папки» (пути любые):

```bash
python3 scripts/install/aggg_upgrade.py /tmp/aggg2-2.8 --root /data/AGGG2.0 --dry-run
python3 scripts/install/aggg_upgrade.py /tmp/aggg2-2.8 --root /data/AGGG2.0 --clean-junk
```

`--root` на пустую папку — install-режим (файлы манифеста источника + `manifest.txt` в корень). Старые версии без манифеста (2.4 и раньше) — полная замена `--full` (ядро строится обходом файлов); данные, `.env`, личные вики-посты защищены.

**Где манифест.** `manifest.txt` в корне архива (клал `make_archive.sh`; паттерн sdist SOURCES.txt / dpkg .list). Читается: `manifest.txt` → `make_archive.sh --list` (рабочая копия) → все файлы (только новая сторона). У получателя `make_archive.sh` нет — он в архив не входит.

Чистка — dpkg-семантика: удаляется только то, чем владела старая версия и чего нет в новой; вычищенное — в `~/aggg-backups/pruned-<TS>/` (не уничтожается). `--clean-junk` — следы ВНЕ манифеста в `~/aggg-backups/junk-<TS>/`. Что НЕ трогается никогда — ЕДИНЫЙ список исключений `scripts/aggg_excludes.txt` (SSOT: его же читает `make_archive.sh`; `db/`, `venv/`, `models/`, `.git/`, `projects/`, внутренний `CHANGELOG/`).

Откат: `tar -xzf ~/aggg-backups/aggg2-backup-<TS>.tar.gz -C <папка>/..` (вычищенное: `cp -r ~/aggg-backups/pruned-<TS>/ <папка>/`).

Вручную (posix): снапшот tar → `rsync -a --backup --suffix=.old <новое>/ <папка>/` → `setup.py --check` → `setup.py`. rsync устаревшее НЕ удаляет — только инструмент (или `diff -rq` по `make_archive.sh --list`).

Грабли:
- setup.py пишет и в харнесы — конфиги снимаются `harness_snapshot.py backup` (откат `restore <имя>`).
- После обновления ядра, если менялись AGENTS.md/скиллы: `install_agents.py --all` + `./projects/sherpa-voice/run_tests.sh --mirrors`.
- `VERSION` — маркер корня: не удалять, в проекты не копировать.
- Windows: tar есть (Win10+); инструмент кроссплатформенный (без rsync), установка — из venv (SETUP-HARNESSES.md).

## Перенос / сборка архива

```bash
./make_archive.sh                  # aggg2-<дата>.tar.gz рядом с корнем
./make_archive.sh --list           # что попадёт в архив
```

Не попадают секреты и пересобираемое: `db/`, `venv/`, `.env`, `models/`, `.git/`, `.github/`, `.reasonix/`, вложенные репозитории, а также `agent/reverser` (внутренний — переносится отдельной копией; install_agents/install_mcp найдут его при наличии). Полный список — в `make_archive.sh`. Перед сборкой — проверка на секреты.

## Инструменты воркспейса

Зависимости всех инструментов — общий venv `~/.venvs/aggg2` (создаётся
`scripts/setup.py`; `mcp/requirements.txt` + `projects/sherpa-voice/requirements.txt`).

**MCP-серверы** — ставит `install_mcp.py` (см. выше), core-список:
`agent-lsp`, `camoufox`, `code-review-graph`, `db-tools`, `battle`,
`semble`. Проверка: `opencode mcp list` (или аналог харнеса).

**Батл-раннеры** (`scripts/tools/battle/`, скилл `battle-test`):
стресс-тесты с цифрами — CLI/API/web/perf/fuzz/visual/gui-поверхности
(`cli_battle.py`, `api_battle.py`, `web_battle.py`, `perf_battle.py`,
`fuzz_battle.py`, `visual_battle.py`, `gui_battle.py`, `battle_core.py`).
Требуют в venv: playwright (web/visual), hypothesis (fuzz), PIL.
Интерактивный GUI-батл — через MCP-сервер `battle`
(`mcp/gui_battle_mcp.py`).

**Мультимодельное судейство** (`scripts/tools/judge/`, скилл
`multimodel-judge`): `multimodel_judge.py --diff/--file` (3+ ревьюера
на разных моделях + судья), `multiorch.py` — оркестрация субагентов.

**Поиск скиллов** (`scripts/tools/skills/skills_search/`, скилл
`skill-search`): `skills_search.py "<тема>" --top/--read/--tree` —
локальная база + внешний skills.sh за ~1с.

**Аудит** (`scripts/tools/audit/`): `check_file_sizes.py` (лимиты
файлов), `harness_status.py` (таблица харнесов), `harness_snapshot.py`
(снапшот/откат конфигов).

## Проверка здоровья после установки

```bash
vpnctl status                      # если sing-box туннель нужен
opencode mcp list                  # MCP-серверы подключены
python3 db-tools/search.py "тест"  # поиск по базе работает
./projects/sherpa-voice/run_tests.sh   # тесты sherpa-voice
```

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
