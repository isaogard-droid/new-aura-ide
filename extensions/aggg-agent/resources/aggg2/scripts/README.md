# scripts/ — управление воркспейсом (CLI-инструменты, не MCP)

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

Слой логики воркспейса: установка, прошивка правил, диагностика, eval.
MCP-серверы — в `mcp/`; движок баз — в `db-tools/`; ядро прошивки — в
`harness/`. Каталог поделён по доменам (паттерн Go cmd/: группа команд = папка;
Python CLI — группировка по назначению): `install/` (установка и её
модули), `doctor/` (диагностика), `eval/` (оценка скиллов/доков),
`tools/` (переключатели, судьи, кирпичи). В корне scripts/ — только
общие кирпичи (`_compat.py`, `jsonc_edit.py`), `setup.py` и `tests/`.
Ссылки на них зашиты в канон-доки и CI — при переносе файла обновлять
все упоминания (grep по базе: files_fts MATCH '<имя>').

## Группы

| Префикс/файл | Что делает |
|---|---|
| `setup.py` (корень scripts/) | полная установка/обновление воркспейса (идемпотентно) |
| `install_*.py` | разноска слоёв: `install/install_agents` (правила/скиллы/субагенты), `install_mcp` (MCP-серверы в конфиги), `install_proshivka` (ядро+хуки), `install_lsp_servers` (LSP для agent-lsp), `install_harnesses` (харнесы) |
| `toggle_*.py` | переключатели: `tools/toggle_proshivka` (вкл/выкл AGGG2.0 по харнесам) + `tools/toggle_config_ops` (общие операции) |
| `proshivka_*.py` | модули прошивки: helpers/hooks/hermes/permissions (механическая резка install_proshivka) |
| `doctor*.py` | диагностика: `doctor/doctor` (CLI) + `doctor_checks_core/ops` (пакеты проверок) |
| `eval/eval_*_triggers.py` + `eval/*_queries.json` | trigger/doc-eval скиллов и доков (результаты — `docs/eval/`) |
| `tools/multimodel_judge.py` | мультимодельный судья для дорогих диффов |
| `tools/multiorch.py` | оркестрация: планер → воркеры → синтез |
| `eval/quality_eval.py` | оценка качества |
| `_compat.py`, `jsonc_edit.py` (корень), `tools/doc_deps.py`, `tools/check_file_sizes.py`, `tools/update_camoufox.py`, `install/harness_map.py`, `install/skills_sync.py` | кирпичи: хирургия JSONC, хелперы, карта связей доков, лимиты файлов |

## Тесты

`scripts/tests/` — unittest-пакеты (запуск из корня):
`python3 -m unittest discover -s scripts/tests -t scripts/tests`

Правило: новый скрипт — сначала посмотри, есть ли аналог здесь (KISS),
или кирпич в `db-tools/`/`mcp/`.
