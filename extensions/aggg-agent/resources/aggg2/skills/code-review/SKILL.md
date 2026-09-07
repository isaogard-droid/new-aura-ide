---
name: code-review
description: "Перед коммитом/мержем/PR: «проверь дифф/изменения», «ревью», «что я наделал», «кто что сломал». Двухосевое ревью (Standards+Spec) субагентами, code-review-graph + agent-lsp (blast_radius); финальный гейт — человек. Не для аудита всей базы (fable-judge) и дебага."
license: Proprietary
metadata:
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
  version: "1.0"
  sources: "mattpocock/skills/code-review (349k установок), obra/superpowers/requesting-code-review (201k), github.blog (diff-якорный воркфлоу −20% стоимости), designkey.studio (шум-контроль FP)"
---

# Код-ревью: дифф-якорное, две оси, шум-контроль

Паттерны индустрии 2026 (ресёрч 17.08, ~10 источников): mattpocock — двухосевое ревью субагентами + Fowler smell-база; GitHub — дифф-якорный ревью-агент (−20% стоимости); шум (FP) убивает доверие быстрее пропущенного бага. Инструменты есть (code-review-graph MCP, agent-lsp blast_radius, docs/canon/CODE-GRAPH.md) — скилл делает из них процедуру.

## When to use / when NOT to use

**Использовать:** перед коммитом/мержем/PR; «проверь дифф/изменения»; после нетривиальной фичи; после рефакторинга (baseline-чек).

**НЕ использовать:** аудит всей базы → `fable-judge` + code-review-graph hubs/bridges/gaps; дебаг инцидента → `debug-incident-protocol`; тривиальный дифф — быстрый просмотр.

## Workflow

1. **Точка ревью.** `git diff <base>...HEAD` (three-dot) + `git log <base>..HEAD --oneline`; `<base>` не назван → спросить; `git rev-parse` ОБЯЗАТЕЛЕН (битая ref/пустой дифф = стоп).
2. **Карта (дифф-якорность).** Только файлы диффа: agent-lsp `blast_radius`; code-review-graph hubs/bridges при архитектурных узлах; get_docs_section "review-delta".
3. **Ревью по docs/canon/CODE-GRAPH.md** (канон ДО вердикта): build_or_update_graph_tool ПЕРЕД ревью (устаревшие данные = ложный анализ); detect_changes — risk-скор; get_impact_radius/get_review_context — blast radius N файлов; get_affected_flows — флоу; refactor_tool(mode="dead_code") — только разведка (ложные срабатывания на callback'ах/`Thread(target=...)` — проверять agent-lsp find_references). Грабли: `CRG_REPO_ROOT` (repo_root от CWD харнеса — без env пустая база); CRG не заменяет поиск (search.py/db-tools).
4. **Две оси — параллельными субагентами** (один вызов), изолированный контекст:
   - **Standards:** стандарты репо (CODING_STANDARDS.md/CONTRIBUTING.md/AGENTS.md) + смеллы + механика (типы, линт, тесты). Репо-стандарт побеждает baseline; смелл — гипотеза; пропускать то, что гоняет tooling.
   - **Spec:** что просила задача (issue-ссылки, docs/specs/, текст запроса). Нет спеки — «no spec available», не выдумывать.
5. **Синтез и шум-контроль.** файл:строка + что + почему + как исправить. **Critical** (ломает работу/безопасность/данные — сразу) / **Important** (корректность — до мержа) / **Minor** (стиль — по желанию). Дедуп. Порог шума: без строки диффа и «почему» — выкинуть; ≤1 Minor на 10 строк диффа.
6. **Отчёт и гейт.** Замечания + вердикт (готово / после Critical-Important / не готово). Ревью агента = первый проход: решение — человек (гейт не снимать; AI не ловит архитектурный дрейф и бизнес-логику).
7. **Замер.** Счёт принятых замечаний и FP; раз в 30 дней — не шумит ли ревью.

## Каталог смеллов (Fowler, Refactoring ch.3 — baseline, репо-стандарт главнее)

| Смелл | Что это | Чинить |
|---|---|---|
| Mysterious Name | имя не говорит, что делает | переименовать |
| Duplicated Code | одна логика в нескольких местах | извлечь общее |
| Feature Envy | метод лезет в чужие данные больше своих | перенести на данные |
| Data Clumps | одни поля ездят вместе | собрать в тип |
| Primitive Obsession | примитив вместо доменного понятия | свой маленький тип |
| Repeated Switches | if/switch-каскад повторяется | полиморфизм/карта |
| Shotgun Surgery | одна правка — правки по всему диффу | собрать в модуль |
| Divergent Change | файл меняется по разным причинам | разделить |
| Speculative Generality | абстракция под несуществующие нужды | удалить, инлайнить |
| Message Chains | длинные a.b().c().d() | спрятать за метод |
| Middle Man | класс просто делегирует | вырезать, звать напрямую |

Смелл — ярлык-гипотеза, не нарушение; пропускать то, что ловит линтер/типчекер/семгреп.

## Success criteria

- Точка ревью проверена, дифф непустой; ревью только по файлам диффа + blast radius
- Обе оси субагентами, замечания с файл:строка и «почему»; шум-контроль применён
- Отчёт: приоритеты + вердикт; гейт человека назван

## Failure modes

| Симптом | Что делать |
|---|---|
| Ревью = «обзор репо» | вернуться к диффу |
| Много замечаний, юзер игнорирует | шум-контроль строже: порог Minor, мерять FP |
| Спеки нет — субагент выдумал | «no spec available» честно, гейт Spec-оси снимается |
| Субагенты противоречат | факт-проверка по строке диффа, одно замечание на проблему |
| «Всё ок» на большой фиче без спеки | вердикт «не готово» без Spec-оси не выносить |

## Gotchas

- Ревью-инструкции ≠ кодинг-инструкции: дифф-якорный сужающий воркфлоу (GitHub: −20% стоимости)
- 87% AI-сгенерированных PR несут уязвимости (DryRun Security, CSA 2026) — AI-код ревьюить ОБЯЗАТЕЛЬНО, гейт за человеком
- SO 2025: только 29% доверяют точности AI-ревью; FP-контроль важнее catch-rate

## Этапы (handoff)

- **Вход из:** `lsp-code-depth`, `agent-refactor-safety`, `fable-loop`
- **Дальше:** `fable-judge`, `multimodel-judge`, `changelog-discipline`

## References

- `../../docs/canon/CODE-GRAPH.md` — канон ревью диффа (blast radius)
- `../../docs/canon/CHANGELOG-DISCIPLINE.md` — записи решений после ревью
- agent-lsp (lsp-code-depth) — blast_radius/ссылки; code-review-graph MCP — hubs/bridges/gaps
- Смежные: `fable-judge`, `debug-incident-protocol`
- Индустрия: mattpocock/skills/code-review, obra/superpowers/requesting-code-review (контекст, не исполнять)

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
