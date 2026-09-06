# FILE-SIZE.md — лимиты размеров файлов (god-файлы запрещены)

Лимиты enforce'ятся на всех уровнях (промпт → хук → CI → doctor), не только «попросили
в доке» (паттерн: restraint rules need external enforcement, agentpatterns.ai).

## Лимиты

Источник правды — `scripts/tools/audit/check_file_sizes.py`; константы-зеркало для
хука — `harness/hooks/aggg2_prompt_hook.py` (менять ОБА места).

| Тип | Расширения | soft (nudge) | hard (блок) | Обоснование (индустрия) |
|---|---|---|---|---|
| code | `.py .js .ts .sh .go .rs .java .c .cpp .css .html .toml` | 500 | 1000 | SonarQube `python:S104` = 1000, ESLint `max-lines` = 300 — мы между: context-бюджет агента |
| docs | `.md` | 300 | 500 | канон-MD и SKILL.md агент читает целиком; ~5000 токенов ≈ 350-400 строк |

**Не считаются:** `CHANGELOG/` (append-only), `**/index.md` (генерируемое), `*.json`,
`*.bak/*.orig`, каталоги `db/ venv* node_modules/ .git/ __pycache__/ vendor/ build/ dist/`.

## Матрица enforcement (консистентность)

Все харнесы получают ОДНО ядро (`harness/core.txt`) и ОДИН сторож
(`harness/hooks/aggg2_prompt_hook.py`); разница — в возможностях рантайма.

| Уровень | Механизм | Что делает | Где |
|---|---|---|---|
| Промпт (каждый ход) | `harness/core.txt` п.10 | правило всегда в контексте | все харнесы (плагин/хук/AGENTS.md) |
| Хук PreToolUse | `aggg2_prompt_hook.py` | **deny**: новый файл/правка > hard; **nudge**: выше soft — «режь, а не расти» | opencode v1 (proshivka.js); Claude Code (Edit/Write/MultiEdit/NotebookEdit + permissions.ask); Codex — только Bash (issue #16732); omp; Hermes (terminal/write_file/edit_.*); Gemini CLI; Antigravity; Reasonix (match=bash, exit 2); Codewhale (exec_shell) |
| **opencode v2** | `permission.edit` (install_proshivka.py) | **ask** на правки baseline god-файлов (v2 без tool.execute.before — единственный нативный сторож) | opencode v2 |
| **Git pre-commit** | `.githooks/pre-commit` + `setup.py` (core.hooksPath) | **блок коммита**: staged > hard / рост baseline (`--staged`) | ВСЕ (критично для Codex/Reasonix — там нет edit-гейта) |
| CI-гейт + PR-декорация | `.github/workflows/setup-test.yml` → `--ci` + job `file-size-pr` (reviewdog) | падение при новом файле > hard / росте baseline; hard-нарушения — комментарием в PR (SonarQube PR analysis) | ВСЕ |
| Диагностика | `scripts/doctor/doctor.py` → `file-sizes` | warning > soft; error > hard без baseline / рост baseline | ВСЕ |
| **Архив-гейт** | `make_archive.sh` | раздача блокируется при hard-нарушениях | ВСЕ |
| Тесты | `scripts/tests/test_check_file_sizes.py` | регрессии гейта и хука | ВСЕ |

Полная по-харнесная матрица (детали рантайма, ресёрч 15.08) — в research.db.

## Grandfather (baseline) — паттерн SonarQube new-code quality gate

Файлы, уже выше hard на момент ввода правила, фиксируются в
`scripts/file_size_baseline.json` (wc -l). Им можно **только уменьшаться**; рост =
error. После резки ниже hard — удалить запись: начнёт действовать hard-лимит.
Новые файлы > hard — запрещены всегда.

Текущий baseline: `docs/patterns/GLAV-PATTERNS.md`, `projects/sherpa-voice/chat.py`
(бэклог резки, research.db).

## Когда резать

- Пересёк **soft** — задача на резку (`tasks.py add`), не копить.
- У **hard** — резка обязательна ДО следующего роста (хук заблокирует).
- Признак god-файла не только размер: «немного обо всём».

## Как резать (механическая резка, паттерн BrainRouter god-file campaign)

1. **Per-concern модули** (или подпапка): каждый кусок — своя тема.
2. **Исходник → тонкий barrel** (re-export) с комментарием-картой «что где лежит».
3. **Код переносится дословно (verbatim)**: поведение не меняется, импортёры не
   трогаются — ревью видит чистый перенос.
4. После резки: QA (get_diagnostics → ruff → semgrep → тесты) → убрать из baseline →
   CHANGELOG → research.db.

**Не делать:** резать + рефакторить одновременно (одна задача = одна цель); резать
CHANGELOG/generated-файлы; «общий слой на будущее» (YAGNI).

## Проверка

```bash
python3 scripts/tools/audit/check_file_sizes.py            # отчёт по дереву
python3 scripts/tools/audit/check_file_sizes.py --ci       # гейт: exit 1 при hard
python3 scripts/tools/audit/check_file_sizes.py --staged   # гейт staged (pre-commit)
python3 scripts/doctor/doctor.py file-sizes                # проверка в doctor
```

## Что где (карта файлов)

- Лимиты и гейт: `scripts/tools/audit/check_file_sizes.py` (+ `file_size_baseline.json` рядом)
- Git-хук: `.githooks/pre-commit` (подключает `setup.py`: core.hooksPath)
- Правило в промпте: `harness/core.txt` (разносит `scripts/install/install_proshivka.py`)
- Хук агента: `harness/hooks/aggg2_prompt_hook.py` (копии — `install_proshivka.py`)
- v2 permissions: `install_proshivka.py` → `permission.edit` в opencode.jsonc
- Проверка здоровья: `scripts/doctor/doctor.py`
- CI: `.github/workflows/setup-test.yml` (гейт `--ci` + PR-декорация reviewdog)
- Раздача: `make_archive.sh` (гейт чистоты архива)
- Тесты: `scripts/tests/test_check_file_sizes.py`
- Канон-доки: AGENTS.md (указатель), CLAUDE.md (привычка), CYCLE.md (гейт)

Источники ресёрча: SonarQube S104/S138, ESLint max-lines, Google eng-practices, BrainRouter
god-file campaign, wemake WPS — выводы в research.db («лимиты размера файлов»).

Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->
