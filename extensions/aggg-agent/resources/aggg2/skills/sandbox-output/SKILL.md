---
name: sandbox-output
description: "Сжатие вывода команд (100+ строк): `cmd | python3 scripts/tools/sandbox_output.py` — auto (head-tail+stats), --errors, --grep, --dedup. Паттерн: 315 KB → 5.4 KB (98%). Не для короткого вывода."
  Сжатие вывода команд — сырой вывод не в контекст. Использовать, когда
  команда возвращает 100+ строк, тесты выводят длинный лог, grep даёт
  сотни матчей, или нужно показать только ошибки/уникальные строки/статистику.
  Паттерн context-mode: 315 KB → 5.4 KB (98% reduction). Специализированные
  обработчики для git/pytest/ls/cat как в llmslim. НЕ использовать для
  короткого вывода (<100 строк) — там overhead не нужен.
---

# Sandbox output: сырой вывод не в контекст

Агент НЕ читает 1000+ строк — скрипт выводит только нужное (context-mode: 47 × Read() = 700 KB → 1 × execute() = 3.6 KB).

## Принципы (из индустрии)

- **Контекст — дефицит:** 1000 строк = 10000+ токенов, перечитываемых на каждом шаге.
- **3 категории удаления** (output filtering): (1) progress noise — download bars, spinners; (2) deduplicated repetition — одинаковые warnings ×200; (3) bulk success boilerplate — «Compiling» + verdict.
- **Token budget** — 500-1000 tokens per result. **Lost in the Middle** (Liu et al., 2023) — шум в середине окна снижает внимание.

## Workflow

1. Вывод >100 строк? → `sandbox_output.py`.
2. Режимы: Авто (default) — head-tail 20 + stats · `--errors` (error/fail/exception/traceback) · `--grep PATTERN` · `--unique` (первое вхождение) · `--dedup` (дубли ×N) · `--stats` · комбо `--no-empty --dedup --errors --top 20`.
3. Прочитай сжатый вывод + stats в конце.

## Специализированные обработчики (как в llmslim)

| Команда | Что сжимается | Экономия |
|---|---|---|
| `git status` | Только branch + file codes | 87% |
| `pytest` | Только failures + summary | 98% |
| `ls -la` | Только filenames | 83% |
| `cat huge_file.py` | Numbered head + tail с truncation | 81% |
| `cargo test` | Только failing tests + error output | 95% |
| `npm install` | Без "already satisfied", только installs/errors | 90% |

```bash
$ pytest tests/ -v 2>&1 | sandbox_output.py --errors --stats
FAILED tests/test_auth.py::test_login_timeout - TimeoutError
FAILED tests/test_api.py::test_rate_limit - AssertionError
=== 2 failed, 148 passed in 6.94s ===
--- stats: 4 строк (из 201, сжато 98%) | 156 B | 4 уникальных | 2 ошибок ---
```

## Примеры (однострочные)

```bash
python3 -c "for i in range(500): print(f'line {i}: data')" | sandbox_output.py        # авто: 500 → 41
pytest tests/ -v | sandbox_output.py --errors                                          # только ошибки
build.log | sandbox_output.py --no-empty --dedup --grep "ERROR|WARN" --top 10          # комбо
long_command | sandbox_output.py --max-lines 100 --context 20                          # budget <1000 tokens
```

## Success criteria

Вывод <100 строк (или head-tail + stats: строки/размер/уникальные/ошибки); прочитано только нужное; token budget соблюдён.

## Failure modes

- **Вывод <100 строк** — overhead не нужен, читай напрямую.
- **Нужен весь вывод** — `--file output.txt`; **сложный фильтр** — свой Python-скрипт, не regex.
- **Truncation bug** — тихое обрезание = агент врёт (partial = complete). Всегда notice.

## Gotchas

- `--stats` — только статистика; `--head-tail N` — N сверху + N снизу + stats пропущенных; `--max-lines 100` — порог авто-сжатия; `--context 20` — контекст; авто-режим только если нет других флагов.

## Truncation bug

**Решение:** notice — `[TRUNCATED: result exceeded 1000 token limit. Use --file or pagination to retrieve more.]`
**Детекция:** логируй bytes per tool call (`LARGE_RESULT_BYTES = 16_000`; `if len(result.encode()) > LARGE_RESULT_BYTES: log.warning(...)`).

## Комбо-пайплайн

Truncation (max_lines/max_chars) → Filtering (noise) → Formatting (compact).
```bash
$ pytest tests/ -v 2>&1 | sandbox_output.py --errors --dedup --stats
```

## Этапы (handoff)

- **Вход из:** любая команда с длинным выводом (pytest, build, grep, find) · **Дальше:** агент читает сжатый вывод.

## References

- Скрипт: `scripts/tools/sandbox_output.py`; паттерны: context-mode (315 KB → 5.4 KB), llmslim, Output Filtering, Tool-Result Truncation bug, Tool result budget, Lost in the Middle. AGENTS.md п.11.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
