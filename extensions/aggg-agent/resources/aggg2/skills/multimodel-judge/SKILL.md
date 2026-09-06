---
name: multimodel-judge
description: "Мультимодельное судейство дорогих проверок: 3+ ревьюера РАЗНЫХ моделей + судья. Большой рефакторинг, спорный дифф, ответ наружу, аудит безопасности, «проверь вторым мнением». НЕ для рутины."
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Мультимодельное судейство (multimodel-judge)

Паттерн Rejudge: `scripts/tools/judge/multimodel_judge.py` (opencode CLI, free-модели — бесплатно). 3+ РАЗНЫХ модели-ревьюера в изолированных сессиях (fan-out), судья получает ТОЛЬКО их отчёты: (1) уточняющие вопросы по расхождениям (ask_panel), (2) ответы с контекстом первого отчёта, (3) финальный вердикт.

## Когда использовать

- большой рефакторинг / спорный дифф перед коммитом; ответ наружу; аудит безопасности; «проверь вторым мнением».
- НЕ для рутины: мелкие правки — как обычно (get_diagnostics → ruff → semgrep → тесты → CRG). Страховка от слепой зоны ОДНОЙ модели.

## Запуск

```bash
python3 scripts/tools/judge/multimodel_judge.py --diff /tmp/change.diff --query "review this change"
git diff | python3 scripts/tools/judge/multimodel_judge.py --diff - --query "review this change"
python3 scripts/tools/judge/multimodel_judge.py --file scripts/_compat.py --out /tmp/verdict.md
```
**Оркестратор задач:** `scripts/tools/judge/multiorch.py --task "..."` — планер → воркеры параллельно → синтезатор (hard cap `--cap 5`). Путь: `$AGGG2_ROOT/scripts/tools/judge/multimodel_judge.py`.

## Модели: конфиг-файл, НЕ правка кода

Приоритет: `--reviewers/--judge` > `--config <файл>` > `./.multimodel-judge.json` > `~/.config/aggg2/multimodel-judge.json` > дефолты.

```json
{
  "reviewers": ["opencode/mimo-v2.5-free", "opencode/hy3-free", "opencode/nemotron-3-ultra-free"],
  "judge": "deepseek/deepseek-v4-pro"
}
```
Судья — САМЫЙ СИЛЬНЫЙ фронтир и НЕ из семейки ревьюеров (family bias); deepseek в ревьюерах не ставить, если судья deepseek. Bias-контроль: перемешивание порядка отчётов (position bias), запрет оценки по длине (length bias). Минимум 2 ревьюера + судья. Список: `opencode models`.

## Харнессы

Нужны: Python, `opencode` в PATH, сеть, auth.json (общий). claude/codewhale/omp/deepcode работают (bash может спросить подтверждение); codex — с настройкой sandbox/approval; reasonix — sandbox режет СЕТЬ (`--unshare-net`) и bash-таймаут 120с: `~/.reasonix/config.toml` → `[sandbox] bash = "off"` (или фоновым job).

**Ключи — ТОЛЬКО плейсхолдеры (`YOUR_API_KEY`).**

| Харнес | Где ключ | Формат модели | Статус |
|---|---|---|---|
| opencode | `~/.local/share/opencode/auth.json` (`opencode auth login` / `providers.<id>.key`) | `provider/model` | ✅ живой |
| reasonix | `~/.reasonix/.env` → `DEEPSEEK_API_KEY=...` | `deepseek-pro`, `deepseek-flash` | ✅ живой |
| omp | `~/.omp/agent/models.yml` → `providers.<id>.apiKey` | `provider/model` | ✅ живой |
| codewhale | `~/.codewhale/config.toml` → `api_key` (или env) | одна из конфига (`default_text_model`) | ✅ живой |
| claude | env `ANTHROPIC_API_KEY` | `--model` (напр. `claude-sonnet-4-5`) | ⚠️ авторизация |
| codex | env `OPENAI_API_KEY` | `-c model=...` (напр. `gpt-5.4-mini`) | ⚠️ OpenAI-ключ |
| deepcode | `~/.deepcode/settings.json` | TTY-only — не работает | ❌ |

omp deepseek-провайдер: полный шаблон с compat-полями (без них 400 на тулах) — api-docs.deepseek.com/quick_start/agent_integrations/oh_my_pi/ (`providers.deepseek: {baseUrl: https://api.deepseek.com, api: openai-completions, apiKey: YOUR_API_KEY, authHeader: true, models: [{id: deepseek-v4-pro, reasoning: true, thinking: {minLevel: high, maxLevel: xhigh, mode: effort}, contextWindow: 1000000, maxTokens: 384000, compat: {supportsDeveloperRole: false, supportsReasoningEffort: true, maxTokensField: max_tokens, reasoningEffortMap: {high: high, xhigh: max}, supportsToolChoice: false, requiresReasoningContentForToolCalls: true, requiresAssistantContentForToolCalls: true, extraBody: {thinking: {type: enabled}}}}]}`).
codewhale: `codewhale config set provider deepseek` / `set default_text_model deepseek-v4-pro` / `set api_key YOUR_API_KEY`.
reasonix: `echo 'DEEPSEEK_API_KEY=YOUR_API_KEY' >> ~/.reasonix/.env`.
Проверка: `opencode models` / `omp -p --model <модель> "ок"` / `codewhale exec "ок"` / `reasonix run --model <модель> "ок"` / `claude -p "ок"` / `codex exec "ок"`.

## Аргументы

| Флаг | Что |
|---|---|
| `--file <путь>` | проверить файл (ревьюеры читают сами) |
| `--diff <путь\|'-'>` | дифф из файла или stdin (обрезка 30K) |
| `--query` | задача для ревьюеров |
| `--reviewers` / `--judge` | модели через запятую / судья |
| `--config` | явный конфиг-файл |
| `--harness` | `opencode` (дефолт)/`reasonix`/`codex`/`claude`/`codewhale`/`omp`/`deepcode`; или в конфиге. opencode/reasonix проверены; codewhale/omp/claude — авторизация харнесса; codex — OpenAI-ключ; deepcode — TTY-only |
| `--out <файл>` | полный протокол (отчёты + вердикт) в md |
| `--timeout` | таймаут (дефолт 240с, для файлов 300+) |

## Грабли (проверено живьём)

- **groq падает на 128 тулов**: глобальный конфиг opencode даёт ~330 MCP-тулов, `OPENCODE_CONFIG` их НЕ отключает, `--pure` не помогает. Не использовать groq в `--reviewers`, пока не ограничишь тулы (permissions deny + `tools: {"mcp__*": false}`). Free-модели opencode-go работают.
- **deepseek платный**: нулевой баланс → 402 Insufficient Balance. **mimo-v2.5-free** медленный: файловые ревью — `--timeout 300+`.
- Вызовы из временного каталога (не из корня воркспейса) — иначе подхватится корневой opencode.jsonc с MCP.

## Ссылки / Этапы (handoff)

- Wiki: `Wiki/ai/rejudge.md`; оригинал: github.com/syabro/rejudge (MIT).
- **Вход из:** `code-review` (спорный дифф), `fable-judge` (второе мнение) · **Дальше:** `fable-judge`, `changelog-discipline`

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
