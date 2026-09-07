---
name: subagent-authoring
description: "Создание/правка субагентов: «сделай субагента», «вынеси в специалиста», «по канону ли субагент». Структура agent/<имя>/ (AGENT.md + персональный md + agents/), frontmatter (mode: subagent), install_agents.py --subagents. Не для создания скиллов (skill-authoring) и оркестрации (fable-loop)."
---
# Создание субагентов по канону

Субагент — изолированный работник: берёт задачу, возвращает ОДИН компактный результат; шум умирает с его контекстом. Эталон — `agent/reverser/`.

## When to use / NOT

| Сценарий | Пример |
|---|---|
| **Context pollution** — тонны файлов в контекст супервизора | поиск по коду (semble-search) |
| **Parallelizable** — независимые пути параллельно | N ревью разных аспектов |
| **Specialization** — >15-20 тулов / конфликтующие режимы | реверс-инженер (ghidra) |

**НЕ создавай:** точечная правка (спавн дороже), роль ради роли. Ключ: **split by context boundaries, not by roles** (Anthropic: «most teams don't need multi-agent systems»).

## Структура (канон)

```
agent/<имя>/
├── AGENT.md            # конфиг: что внутри, когда делегировать
├── <ПЕРСОНА>.md        # личность и полные правила
├── skills/ references/ # по надобности
└── agents/
    ├── <имя>.md                # ОБЩИЙ: все .md-харнесы (opencode, claude, omp, antigravity, gemini)
    └── <имя>.<харнес>.md/.toml # специфичный: харнес = ПОСЛЕДНИЙ сегмент имени
```

## Frontmatter

.md (opencode/claude):
```yaml
name: <имя>                    # строго = имя файла без расширения
description: "..."             # триггер автоделегирования: ЧТО + КОГДА; в кавычках (двоеточие-пробел ломает YAML)
mode: subagent                 # обязателен
permission:
  edit: deny                   # read-only по умолчанию
```
TOML (codex, ~/.codex/agents/):
```toml
name = "<имя>"
description = "..."
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
nickname_candidates = ["<Русский ник>"]
```

## Тело субагента

1. «Полные правила — `$AGGG2_ROOT/agent/<имя>/<ПЕРСОНА>.md`, прочитай: `cat ...`» (канон не виден автоматически).
2. Краткая суть правил (5-8 буллетов) — на случай сбоя чтения.
3. Строгий формат ответа (ФАЙЛ/СУТЬ/ДОПОЛНИТЕЛЬНО — semble-search) + границы (что НЕ делать) + шапка AGGG.

## Workflow

1. Классифицируй по таблице; не попал — НЕ создавай. Паттерны — Camoufox первым (ядро: core.txt п.1).
2. `<ПЕРСОНА>.md` → `AGENT.md` → `agents/<имя>.md` (общий, с frontmatter) → специфичные.
3. Read-only: «delegate the gathering, keep the deciding» — решение у супервизора.
4. **Внеси в канон-указатели** (грабля 19.08): AGENTS.md «Агенты» + `agent/README.md`; после правки AGENTS.md — зеркала + `install_agents.py --all` + `run_tests.sh --mirrors`.
5. Разнеси: `python3 scripts/install/install_agents.py --subagents`.
6. Проверь: `ls ~/.config/opencode/agents/ ~/.claude/agents/ ~/.omp/agent/agents/ ~/.gemini/agents/ ~/.copilot/agents/`; reasonix — `~/.reasonix/skills/<имя>`, codex/codewhale — `.toml`, `[~] пропущен` без него — норма (как semble-search).
7. Спавн-чек: виден после ПЕРЕЗАПУСКА харнеса (claude-code issue #5738).

## Success criteria

- Frontmatter: name=файл, mode: subagent, edit: deny / sandbox read-only, description в кавычках с триггерами.
- Общий файл во ВСЕ .md-харнесы; специфичные — по расширению.
- **Упомянут: AGENTS.md «Агенты» + agent/README.md; зеркала идентичны (--mirrors).**
- Ответ — один компактный блок; сценарий — один из трёх.

## Failure modes / Gotchas

- Нет mode/permission → субагент может редактировать: deny обязателен.
- Имя файла ≠ name → не подхватится (codex: строго).
- `.opencode.md` вместо общего → только один харнес.
- Спавн дороже задачи → не окупается без изоляции/параллелизма (Anthropic: overhead).
- Описание без триггеров → нет автоделегирования.
- ЧИСТЫЙ контекст: без истории и скиллов — всё нужное в его файле.
- Разноска не удаляет старые — чистить вручную; `.agent.md` для copilot — тот же контент.
- **Новый агент виден после рестарта** (#5738, 19.08): сессия до создания `agents/` не увидит файл — рестарт, не баг.
- Русские триггеры в description скилла субагента обязательны (батл 19.08: 0/4 → 4/4).

## Этапы (handoff)

- **Вход из:** `skill-authoring`, `task-cycle` (нужен узкий специалист), `semble` (готовый пример)
- **Дальше:** `battle-test` (спавн-проверка), `changelog-discipline`, `workspace-map`

## References

- Эталон: `agent/reverser/`; opencode.ai/docs/agents; claude.com/blog/subagents-in-claude-code; subagent-best-practices (dianyike/claude-code-insights); issue #5738; smartscope.blog «Distributing Agent Skills»; jmlopezdona/ai-coding-agents-fundamentals

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
