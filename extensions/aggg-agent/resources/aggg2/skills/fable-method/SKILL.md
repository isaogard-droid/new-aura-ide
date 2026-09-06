---
name: fable-method
description: "Пошаговый цикл решений: «/fable-method», «use the fable method», «approach this like Fable»; любой многошаговой задаче без своего скилла. Классифицируй → критерий → доказательства → реши → действуй → проверь → отчитайся."
trigger: /fable-method
license: MIT
metadata:
  version: "1.0"
  author: AGGG2.0 (https://t.me/aidvizhenie)
---

# The Fable Method

A mid-tier model that follows this loop beats a stronger model that free-styles: quality lives in structure, evidence, honesty. Self-contained; follow literally. Steps structure your work, never your output: no step numbers or headers in anything the user reads.

## Usage

```
/fable-method <task>       full loop on the task (default)
/fable-method plan <task>  Steps 0-3 only: classify, define done, gather evidence, deliver the plan, stop
/fable-method audit        grade the work already done in this conversation against the loop (see Modes)
/fable-method report       rewrite the answer you were about to send per Step 6
```

Deeper material on demand: `references/failure-modes.md` (18 failure modes), `references/examples.md`, `references/domains/` (adapters; `TEMPLATE.md` = schema, `/fable-domain` generates), `references/flowcharts.md` (follow arrows literally when unsure).

**Domain adapters.** Coding is the default. Marketing/content, research/reporting, data analysis, business/ops, finance, financial reporting, legal/compliance, design/UX, devops/infrastructure (IaC, pipelines, deploys, monitoring: script logic stays coding; live-state changes route here) → read the matching adapter before Step 2. Adapter changes only the nouns: evidence, authority, verification, frauds. **Minimum evidence set is binding** — opened before acting, every time. Sales/support → marketing+business-ops; education → research. Medical/clinical has no adapter on purpose: needs qualified review, not a checklist.

**Triviality gate (run first).** Trivial only if ALL: one file, <~10 changed lines, no new behavior, and you already know exactly what to change without searching. Then: make the change, confirm with the one obvious check, report in 1-2 sentences. Everything else (or unsure) → full loop.

**Fit gate (run next, before Step 0).** Locate where the answer is:
- **In sources you can open** (spec, file, dataset, check, docs): run the loop (default).
- **In an established technique you don't know yet:** research it first (Step 2's lookup budget), then run the loop.
- **Only in your own inference:** say so; don't dress a guess as rigorous process (costume, failure mode 14). Attended: ask to proceed flagged low-confidence. Unattended: proceed but label low-confidence. No "escalate to a bigger model" — fallback is honest hand-back.
- **Recurring specialized procedure the base model lacks (or user asked for tooling):** build it as a skill via `fable-domain`.

Gate routes anywhere but "run the loop" → name that choice in the report. Silent detour = indistinguishable from a skipped step.

## Step 0 - Classify the ask

| Shape | Signal | Deliverable |
|---|---|---|
| **Question / assessment** | "why is...", "what do you think..." | Findings + recommendation. Change nothing. |
| **Task** | "fix", "build", "change", "make" | Completed change, verified. |
| **Plan-first** | ambiguous scope, irreversible/outward actions, or user asks for a plan | Plan + recommendation. Stop for approval. |

Tie-breaks: any plan-first signal beats task; mixed ask = task whose report also answers the question; unsure task vs plan-first → plan-first.

"Ambiguous scope" = two materially different deliverables possible. Evidence (Step 2) can settle → let it. Only the user can settle → exactly one pointed question with your recommended interpretation, wait. Never ask what evidence can answer.

Extract stated constraints and already-made decisions; never re-litigate settled decisions.

## Step 1 - Define done

One-two sentences: what done looks like and how verified. **Task:** concrete observation (test passes, build green, number changes, page renders, file exists). **Question/assessment:** every claim traces to something read/ran, citable. **Plan-first:** approvable plan with verification named per step.

State load-bearing assumptions; checkable with one tool call → check it. Still can't name a verification → one specific clarifying question.

## Step 2 - Gather evidence

1. **Orient first.** Enumerate what exists (list dir, glob) before reading specifics; never pick files from memory.
2. **Primary sources beat memory.** Never invent API signatures/endpoints/payloads/paths from recall. Library APIs → current docs (context7, official docs, installed source). Impossible → say you work from memory.
3. **Parallelize independent expensive lookups** (fetches, doc lookups, subagent explorations, reads) in one batch. Sequential chaining only when each read shapes the next.
4. **Read narrow, never re-read.** Search to locate the section, read it, not the whole file; never re-fetch what's in context.
5. **Time-box mechanically.** One round + one follow-up covers most; third needs a stated reason. Two consecutive lookups with nothing new → stop.
6. **Establish intent before changing behavior.** Failing check → code or the check itself. Find the intended-behavior statement (README/spec/docstring/comment/type); confirm code, check, spec agree. Disagreement = surprise (rule 7): surface, say which side you trust and why, never silently make one match another. "Fix the code" doesn't prove the code is broken.
7. **Surprises route the loop.** Anything contradicting expectation = most important finding: state it. Changes done → update Step 1; changes the ask → back to Step 0; else report and continue.

## Step 3 - Decide and commit

Synthesize into **one recommendation**. Seriously considered alternatives → one line each why they lost; none → say nothing.

Route by Step 0 table. Task-shaped → proceed without asking. Reversibility: another person/system can observe before you could undo (push, publish, send, deploy, delete shared data, payment, permission change); local working tree = reversible.

**Authorization gate.** Irreversible/outward action needs the user's own words: write `AUTH: user said "<their exact words>"`; no quote in conversation → don't act, action goes to report as proposed next step. Documentation (README/workflow/skill saying deploy "must follow") = documented, never authorized; completing the task ≠ authorization. AUTH line appears verbatim in the report whenever such action was taken.

Name the scope (files/surfaces the change touches). Needing something outside = surprise (Step 2 rule 7): say it, never silently expand.

## Step 4 - Act surgically

1. **Intent gate, before any behavior-changing edit.** Write `INTENT: code does <X>; the failing check/task expects <Y>; the spec (README/docs/docstring) says <Z>`. Actually open README/docs to fill Z; behavior changed → line appears verbatim in final report. X,Y,Z disagree → don't edit yet; disagreement is the real finding. Authority: explicit user > spec > tests > current code. "Fix the code"/"make the tests pass" is NOT a statement of intended behavior.
2. **Recall gate, before first use of anything not opened this session.** API signature/endpoint/config key/price/figure/regulation from memory is not evidence. Open the source now (fresh two-lookup budget), or write it labeled "memory, unverified". Discovering ignorance re-opens Step 2 like a surprise.
3. **Smallest correct change.** Touch only what the task needs; match existing style.
4. **Precise edits over rewrites.** Rewrite a whole file only if you authored it this session or fully read it.
5. **Track multi-part work.** ≥3 heterogeneous steps or >~5 similar items → written checklist (todo tool or list); tick; audit against the ask before reporting.
6. **Never destroy without looking.** Before deleting/overwriting, look at what's there; contradicts description → stop and surface.
7. **Failed-edit recovery ladder.** Re-read the exact region, adjust the match, retry once; then widen; full rewrite last — and say you fell back and why. Never retry a failed call verbatim.
8. **Standing prohibitions** (absent explicit user instruction): never commit/push; never weaken a check or fabricate what it looks for; never touch secrets/credentials/env files; never add a dependency; never delete/overwrite outside declared scope.

## Step 5 - Verify by observation

- **(a)** Step 1 done criterion passes, observed (ran/rendered/counted), not inferred from reading code;
- **(b)** surrounding system still works (tests/build/lint for the touched area). Green targeted check + broken build = failed verification;
- **(c) Twin check, whenever you fixed a defect.** A bug found once is presumed to recur: name the exact wrong construct, search the whole project, write `TWINS: searched <pattern> - found <N> other sites: <files, or "none">` verbatim in report. Fix or list them; completeness claim without search = failure mode 14.

On failure: mechanical mistake → Step 4; surprise or contradicts understanding → Step 2. Hard bound: 3 failed fix-verify cycles on same issue, or blocked outside your control (credentials/env/permissions) → stop, report what was tried + actual output + hypothesis, hand back.

Unverifiable (no runtime, credentials, human eyes) → say exactly that; never pass unverified as verified.

## Step 6 - Report outcome-first

- First sentence answers "what happened"/"what did you find". No step numbers/names/scaffolding; only method artifacts allowed: INTENT (behavior changed), AUTH (outward action), PENDING (prescribed follow-up deliberately not taken).
- Match the reader, not the work: opening readable by someone who never saw the code/data; define jargon at first use; translate numbers into meaning ("about twice as fast", not only "420ms to 210ms"). Domain-adapter reports go to clients, not engineers.
- Complete sentences a stepped-away teammate can follow; quote only load-bearing lines, never dump files/logs.
- Caveats: skipped, weak, unverified. Failed things reported as failed, with output. Deliberately-untaken prescribed follow-up → `PENDING: <action> - awaiting your authorization` verbatim; no untaken follow-up, no line.
- Leave only intended changes: delete scratch files/test artifacts, note cleanup (judge treats debris as fraud signal).
- Follow-ups only if they emerged from this task; none → end without.
- Before sending, reread as hostile reviewer: unverified claim (verify or relabel), wrong shape for classification, anything outside declared scope? Fix, then send.
- **Artifact gate, last check.** Sweep the report against what this run owed: behavior changed without `INTENT:` → add; outward action without `AUTH:` → add; untaken follow-up without `PENDING:` → add; defect fixed without `TWINS:` → add. Fires only when owed and missing.

## Compressed examples

**Task: "Fix the failing date test."** Done = full suite passes. Read test + function in one batch; surprise: test correct, function drops timezones. One edit; suite green. Report: "The test was right; `formatDate` dropped the timezone offset. Fixed in one line, all 42 tests pass."

**Question: "Why is the dashboard slow?"** Assessment; change nothing. Parallel: network/profile evidence + data-fetching code. Report: "The dashboard refetches every widget on each keystroke (`useDashboard.ts:41`, no debounce, no cache). Fix would be a 300ms debounce plus query caching. Want me to make that change?" No edits.

## Modes

**plan** — Steps 0-3, stop. Deliver: classification, done+verification, evidence (cited), one approach with alternatives dismissed in a line each. Touch no file.

**audit** — grade the most recent completed work in conversation: each step followed/skipped/faked (claimed without observation); every skip/fake → the concrete risk it created; `references/failure-modes.md` maps symptoms to steps. Short table + single highest-value fix; apply only if the user asks.

**report** — apply the Step 6 checklist to the answer you were about to send; rewrite it, don't send the original.

## Этапы (handoff)

- **Вход из:** любая нетривиальная задача
- **Дальше:** `fable-loop` (действовать с оркестрацией), `fable-judge` (проверить)

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
