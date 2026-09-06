# Мультимодельный судья (scripts/tools/judge/multimodel_judge.py)

Независимая проверка кода связкой «несколько моделей + судья» (Rejudge / Multiagent Debate / LLM-as-a-Judge). Проверено живьём.

## Когда использовать / когда НЕ
| Использовать (дорогие случаи) | НЕ использовать |
|---|---|
| большой рефакторинг, спорный дифф перед коммитом | мелкие правки — обычный QA (get_diagnostics → ruff → semgrep → тесты) |
| ответ наружу (публикация, отчёт) | рутина, «проверил сам и уверен» |
| аудит безопасности, критичный код | срочный фикс — быстрее руками |
| «проверь вторым мнением» после fable-judge | — |

## Как работает (4 фазы)
1. **Панель**: ревьюеры ПАРАЛЛЕЛЬНО, изолированные read-only сессии (не видят друг друга); сбой одного не роняет панель.
2. **Вопросы судьи (ask_panel)**: судья получает ТОЛЬКО отчёты, ищет расхождения, задаёт уточняющие вопросы (JSON).
3. **Ответы ревьюеров** (с контекстом своего отчёта) → судья сводит всё в один итоговый. Вопросов нет — раунд пропускается (adaptive).

## Быстрый старт
```bash
# проверить дифф (файл или stdin)
python3 scripts/tools/judge/multimodel_judge.py --diff /tmp/change.diff --query "review this change"
git diff | python3 scripts/tools/judge/multimodel_judge.py --diff - --query "review this change"
# проверить файл (ревьюеры прочитают сами)
python3 scripts/tools/judge/multimodel_judge.py --file scripts/_compat.py --out /tmp/verdict.md
# полный протокол (все отчёты + вопросы + ответы + вердикт)
python3 scripts/tools/judge/multimodel_judge.py --diff /tmp/x.diff --out /tmp/verdict.md
```
Флаги: `--file` / `--diff`, `--query`, `--reviewers` / `--judge`, `--config`, `--harness`, `--out`, `--timeout` (для файлов 300+).

## Модели: правило силы и семейки (важно!)
- **Судья = самый сильный доступный фронтир** (сейчас `deepseek/deepseek-v4-pro`).
- **Судья НЕ из той же семейки, что ревьюеры** (family bias). Судья deepseek → deepseek в ревьюерах не ставить.
- Ревьюеры — разнообразные, дешёвые: `opencode/mimo-v2.5-free`, `opencode/hy3-free`, `opencode/nemotron-3-ultra-free`.
Менять модели — конфигом, не кодом. Приоритет: `--reviewers/--judge` (CLI) > `--config <файл>` > проектный `./.multimodel-judge.json` > глобальный `~/.config/aggg2/multimodel-judge.json` > дефолты.
```json
{ "reviewers": ["opencode/mimo-v2.5-free", "opencode/hy3-free", "opencode/nemotron-3-ultra-free"],
  "judge": "deepseek/deepseek-v4-pro" }
```
Bias-контроль: порядок отчётов судье перемешивается (position bias), промпт запрещает оценку по длине (length bias).

## Бэкенды (харнессы)
| Бэкенд | Статус | Модель из CLI |
|---|---|---|
| opencode | ✅ живой (дефолт) | да |
| reasonix | ✅ живой | да |
| codewhale | ✅ живой | нет (одна из конфига) |
| omp | ✅ живой | да |
| claude | ⚠️ нужна авторизация | да |
| codex | ⚠️ нужен OpenAI-ключ | да |
| deepcode | ❌ TTY-only | нет |
Выбор: `--harness reasonix` или `"harness": "reasonix"` в конфиге. Настройка провайдеров — в скилле `multimodel-judge` (ядро: core.txt п.6).

## Грабли (все проверены живьём)
- **groq падает на лимите 128 тулов** (~330 MCP-тулов в opencode; `OPENCODE_CONFIG`/`--pure` не помогают) — не ставить, нужен permissions deny + `tools: {"mcp__*": false}`.
- **deepseek 402** — БАЛАНС аккаунта: `GET api.deepseek.com/user/balance`.
- **reasonix**: ключ в `~/.reasonix/.env` (`DEEPSEEK_API_KEY`); sandbox режет СЕТЬ — для судьи `[sandbox] bash = "off"`.
- **JSON-ответы**: модели вставляют `{}`-примеры — парсер балансный (`extract_json_object`), срез по `rfind('}')` режет JSON.
- **Таймауты**: файловые ревью — `--timeout 300+`. **deepseek-chat/reasoner мертвы** с 24.07.2026 — v4-flash/v4-pro.
- Судья обязан быть сильнее и другой семейки — иначе результат обесценен.

## Связки
CYCLE.md фаза 5 — проверка дорогих диффов; скилл `multimodel-judge` — полная инструкция; ORCHESTRATION.md / `multiorch.py` — судья для ПРОВЕРКИ, оркестратор для РАБОТЫ; fable-judge — «готово», судья — второе мнение; оригинал паттерна: github.com/syabro/rejudge (MIT).

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->
