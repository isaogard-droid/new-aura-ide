---
name: fable-loop
description: "Многошаговая задача с оркестрацией: «/fable-loop», «параллельные субагенты», «выполни как Fable», «run the fable loop», «многошаговая задача». План + воркеры + intent gate + adversarial-проверка + отчёт результат-первым. Для правил — fable-method; для цикла — task-cycle."
license: MIT
metadata:
  version: "1.0"
  author: AGGG2.0 (https://t.me/aidvizhenie)
---

# The Fable Loop

Orchestrates the fable-method: read its SKILL.md first; its rules govern every stage. It is installed alongside this skill (in this plugin's `skills/fable-method/`, or `~/.claude/skills/fable-method/` for manual installs). Method says WHAT to check; loop says WHO does the work (main thread vs subagents) and what gets attacked before delivery.

**Gate first.** Trivial per the method's triviality gate: just do it, verify with the one obvious check, report in two sentences. Everything else runs the four stages below.

## Stage 1 - PLAN (the first bookend)

1. Method Steps 0-3: classify, define done with a named verification, load-bearing assumptions.
2. **Evidence fan-out.** Gatherers as parallel subagents in ONE message, never sequentially: Explore agent per distinct codebase area; research agent for library/fact questions. Each returns distilled findings with citations, never raw dumps. One batch + one follow-up is the budget; a third needs a stated reason.
3. **Plan artifact:** classification; done + verification; evidence (cited); ONE approach (alternatives dismissed in a line each); scope (exact files/surfaces); risks/assumptions; execution checklist.
4. **Decision gate.** Task-shaped and reversible → proceed without asking. Plan-first (ambiguous scope, irreversible/outward actions, or user asked for a plan) → present plan and STOP.

## Этапы (handoff)

- **Вход из:** `task-cycle` (нетривиальное многошаговое), `nodumb`
- **Дальше:** `fable-judge` (adversarial-проверка)

## Stage 2 - EXECUTE

1. Checklist in the **main thread** (todo tool if present; tick as completed). Deciding/editing stay in main thread; only searching/verifying fan out.
2. Every edit per method Step 4: intent gate, recall gate, smallest correct change, precise edits, never destroy without looking.
3. Independent mechanical items (same change across many files, isolated generation) may fan out in one message, worktree isolation if same files possible.
4. Surprise mid-execution: say it, update the plan or back to Stage 1; never force the plan through a surprise.
5. Mid-item ignorance = pause, not guess: edit would carry a fact from memory → stop that item, fan out one research subagent (recall gate), resume when it returns.
6. Outward-facing items obey the authorization gate: no quoted user authorization, no action; the item becomes a proposed next step in the report.

## Stage 3 - VERIFY (adversarially)

1. Run the named verification yourself, both halves: done criterion observed (ran, rendered, counted) + surrounding system healthy (build, tests, lint).
2. **For consequential changes, spawn attackers.** 1-3 parallel subagents, each told to REFUTE from a distinct lens: "prove the change wrong/incomplete", "find an input that breaks it", "check claims against spec", "prove something outside the declared scope changed". Distinct lenses beat identical reviewers.
3. A finding that survives your own check goes back to Stage 2. Hard bound: 3 failed fix-verify cycles on the same issue, or any blocker outside your control → stop and hand back with the output and your hypothesis.

## Stage 4 - AUDIT and REPORT (the second bookend)

1. Self-audit per fable-method audit mode: each step followed, skipped, or faked. Fix what one pass can fix (usually an unverified claim: verify it now or relabel it a caveat).
2. Deliver per method Step 6: outcome in the first sentence, verification evidence shown, honest caveats, follow-ups only if they emerged from the work. No stage names or step numbers; the INTENT and AUTH lines are the only method artifacts a report may contain.

## Loop safety (бюджеты, детектор отсутствия прогресса, ретрай-политика)

Индустрия 2026 (acethecloud, matrixtrak, Azure; ресёрч 17.08): бесконечный цикл = цикл без прогресса, не «много итераций». Три механизма:

1. **No-progress fingerprint.** Хэш (шаг + результат) каждого витка; N одинаковых подряд (дефолт 3) = стоп → НОВАЯ информация (ресёрч/док/субагент) или hand back с отчётом. Прогресс — по продвижению к done, не по числу вызовов.
2. **Ретрай-политика по классам ошибок:**
   | Класс ошибки | Действие |
   |---|---|
   | validation / auth / перманентные | STOP — классифицировать и сообщить |
   | 429 / rate-limit / timeout | ретрай 2-3 с backoff + jitter |
   | safety / необратимое | escalate к владельцу, не ретраить |
   | остальное | 1 ретрай, потом по таблице |
3. **Бюджеты на уровень** (токены/деньги/витки на этап): выход за бюджет = стоп с отчётом (что сделано, что осталось), не молчаливое продолжение.

## When NOT to use this loop

- Trivial tasks (the gate handles them); pure questions without multi-step work: plain fable-method.
- Inside an already-orchestrated GSD phase: GSD owns the stages; apply fable-method rules within, no nested loops.

## Model economy

Model-agnostic. Evidence and attacker subagents are cheap-model-friendly; keep the main thread (deciding, editing) on the strongest model available, and give attackers higher effort than gatherers when a choice exists.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
