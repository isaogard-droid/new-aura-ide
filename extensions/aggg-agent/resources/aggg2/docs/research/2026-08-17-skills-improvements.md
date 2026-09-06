# Глубокий ресёрч: скиллы AGGG2.0 — что улучшить (индустрия 2026)

Дата: 17.08.2026 · 7 кластеров × 10-15 источников ≈ 70+ источников (норматив 50+)
Категория: решения/выборы (глубокий ресёрч, docs/canon/CAMOUFOX.md «Глубокий ресёрч»)

## Вопрос

38 локальных скиллов + инфраструктура (skills_search.py, db/skills.db, прошивка).
Что улучшить: по данным индустрии 2026 и в сравнении с чужими скиллами
(mattpocock 349k установок, obra/superpowers 201k, addyosmani 19.6k, wshobson 8k,
affaan-m 6.3k, callstackincubator 5.7k, neolabhq, ruvnet).

## Кластеры и ключевые факты (URL)

### 1. Экосистема skills 2026 (12+ источников)
- Спека открыта 18.12.2025 (agentskills.io, Apache-2.0): SKILL.md <500 строк, references/, assets/, license/metadata.
- Adopters ~40: Anthropic, OpenAI Codex (openai/skills → plugins), Cursor 2.4+ (migrate-to-skills), GitHub Copilot (`.github/skills/`, 29.07.2026 code review GA), Microsoft (UseMcpSkills — скиллы из MCP-серверов), Gemini CLI, Junie, OpenHands, Goose, opencode.
- Конвергенция MCP+skills — официальная позиция: «MCP = инструменты/данные, скилл = воркфлоу вокруг них» (OpenAI, Microsoft, Cursor-плагины бандлят MCP).
- `.agents/skills/` — emerging cross-client каталог (Codex PR #10317: `.codex/skills` deprecated).
- OpenAI: бюджет списка скиллов ≤2% контекста (8K символов); `disable-model-invocation`; Record&Replay.
- Cursor: 4 режима активации (always / globs / description «Apply Intelligently» / manual `@имя`).
- agentskills.io/specification · anthropic.com/engineering/equipping-agents... · venturebeat.com (adopters) · developers.openai.com/codex/concepts/customization · cursor.com/changelog/2-4 · github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available · learn.microsoft.com/en-us/agent-framework/agents/skills

### 2. Триггеринг и description engineering (8+ источников)
- Все харнесы — progressive disclosure: в контексте только name+description; Claude Code усекает description на 1536 символов.
- Точность: trigger evals = precision/recall на 20-50 промптах с near-miss негативами; пороги recall ≥0.7-0.9, trigger rate ≥0.5 на 3+ прогонах.
- SkillsBench: curated-скиллы +16.6pp (33.9→50.5%); фокусные ≤3 модулей > монолиты; self-generated −1.3pp (кураторство обязательно).
- Описание = единственный триггерный рычаг: «Use when…» + named phrases + «not for…»; правка description = breaking change, нужен CI-гейт.
- Always-in-context надёжнее, но платно; Prompt Shelf: `.cursorrules` → 0/9, `.mdc` → 9/9 compliance.
- Anthropic skill-creator: одна оптимизация описания улучшила триггеринг 5/6 скиллов.
- agentskills.io/skill-creation/optimizing-descriptions · arxiv.org/abs/2602.12670 (SkillsBench) · dreaming.press (trigger evals) · developers.openai.com/blog/eval-skills · github.com/UiPath/skills (gate recall.yes≥0.70) · cursor.com/docs/rules · opencode.ai/docs/skills · localskills.sh/blog/skill-md-vs-claude-md-vs-agents-md

### 3. Оценка скиллов (10+ источников)
- Skill lift — стандарт: парный прогон with/without (SkillsBench, NVIDIA, AWS, SkillLens).
- SkillEval: 4 свойства (applicability, content, execution guidance, robustness), предсказание коррелирует Pearson 0.78-0.79.
- AWS Unified score = audit 40% + functional 40% + trigger 20%.
- Eval-driven development: baseline без скилла → скилл под провалы → hill-climb; 10-20 промптов на скилл (OpenAI), 20-50 (Anthropic); CI: гейты, 3+ прогона, полный сет на merge/nightly.
- Firebase: pass rate 31.7% → 78.0% со скиллами, токены −40%.
- Дёшево начать: аудит (frontmatter, лимиты, дубли) бесплатен; живой eval — точечно на топ-10.
- arxiv.org/html/2608.06891 (SkillEval) · docs.nvidia.com/skills/skillevaluator · github.com/aws-samples/sample-agent-skill-eval · firebase.blog · qaskills.sh/blog/llm-evaluation-ci-cd-quality-gates

### 4. Память агентов (15+ источников)
- 4 класса: внешние memory-слои (mem0, Zep/Graphiti, Letta/MemGPT, LangMem), MCP memory-серверы (SQLite+BM25/vector/KG), файловая память (CLAUDE.md/AGENTS.md), платформенная.
- Mem0: extract→dedup→store→retrieve, 4 сигнала (semantic+BM25+entity+temporal), ADD-only.
- Таксономия episodic/semantic/procedural; procedural — самый недообслуженный.
- Обновление: ADD-only + дедуп, явные update/delete, консолидация (периодическая ревизия); selective forgetting — открытая проблема («устаревший факт хуже отсутствия»).
- AGENTS.md — «floor, not ceiling»: 6 ядерных секций, стальность факта = угроза.
- arXiv 2603.07670 (обзор памяти) · docs.mem0.ai · github.com/modelcontextprotocol/servers/tree/main/src/memory · agentmarketcap.ai (сравнение 2026) · github.blog (2500+ agents.md) · arxiv.org/abs/2602.19320v1 (LongMemEval)

### 5. Оркестрация и субагенты (11 источников)
- Канон: planner-executor-evaluator; Anthropic: orchestrator-worker, веер 3-5 параллельных только для независимых подцелей; мульти-агент = оптимизация, не дефолт.
- Мульти-агент: +90.2% на research eval, но токены ~15x; 80% дисперсии BrowseComp = токены.
- Loop-безопасность: бюджеты (шаги/tool-calls/токены/деньги) + fingerprint-детектор (hash шага+результата; «infinite loop = no-progress loop»); ретрай-политика по классам ошибок (validation/auth → STOP, 429 → backoff+jitter, safety → escalate).
- Контекстная изоляция — load-bearing: субагент = компрессия; артефакты в файл/базу, не через лида.
- Claude Code: depth-кап 5, 3-5 воркеров, SubagentStop + rubric-градер (+10pp).
- anthropic.com/engineering/multi-agent-research-system · langchain.com/blog/introducing-dynamic-subagents-in-deep-agents · philschmid.de/subagent-patterns-2026 · acethecloud.com (infinite-loop detection) · matrixtrak.com/blog/agents-loop-forever-how-to-stop · learn.microsoft.com (ai-agent-design-patterns) · gravity.fast (planner-executor-evaluator)

### 6. AI-код-ревью (10+ источников)
- AI-код в PR: 1% → 27.6% за год; ревью = новый bottleneck.
- Инструменты: Greptile ~82% catch (11 FP), CodeRabbit ~44% (17K клиентов), Graphite ~6% (2 FP, fix-rate 82%).
- Шум — убийца доверия: SO 2025 — 29% доверяют точности (было 40%); 46% активно не доверяют.
- Паттерн: агент = первый проход (механика/стандарты), сеньор = архитектура/бизнес-логика; self-review до PR −1/3 переписки; дифф-якорный сужающий воркфлоу: −20% стоимости, то же качество (GitHub).
- mattpocock code-review (349k): двухосевое (Standards + Spec) параллельными субагентами; Fowler smell-база.
- 87% AI-PR с уязвимостями (DryRun Security, CSA) — ревью AI-кода обязательно.
- greptile.com · coderabbit.ai · designkey.studio/post/agentic-code-review-what-works-2026 · github.blog (code-review-in-the-age-of-ai) · cloudsecurityalliance.org (state-of-cloud-and-ai-security-2026) · survey.stackoverflow.co/2025/ai

### 7. Самодебаг + безопасность (10+ источников)
- AgentDebugX: Detect→Attribute→Recover→Rerun; «шаг ошибки ≠ шаг-причина» — атрибуция по трейсу.
- 3 формы застревания: Repeater/Wanderer/Looper — разное лечение; разделитель = метрика прогресса, не активность; лестница nudge→replan→escalate→reset→hand-off.
- Introspection-скиллы (affaan-m): Capture (шаблон сбоя ДО ретрая) → Diagnosis → Contained Recovery → отчёт.
- ACH (Heuer): ценность = аудируемая структура перебора гипотез, эмпирика слаба (Dhami 2019) — не панацея.
- Snyk ToxicSkills: 13.4% критических из 3984, 76 вредоносных, 100% = код+markdown вместе; OWASP AST01: ClawHavoc 1184 вредоносных, 5 из 7 топ-скачиваемых = малварь; Gen Trust Hub × Vercel: 12K+ вредоносных.
- arxiv.org/html/2607.18754v1 · agentpatterns.ai/loop-engineering/stuck-loop-recovery/ · arxiv.org/html/2607.01641v1 · snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/ · owasp.org/www-project-agentic-skills-top-10/ast01 · newsroom.gendigital.com

## Выводы: что улучшить в AGGG2.0 (по приоритету)

### 1. DEBUG: Capture-фаза + формы застревания + ACH-перебор → debug-incident-protocol
Индустрия (AgentDebugX, agentpatterns.ai, affaan-m): фиксировать сбой ДО слепого ретрая
(шаблон: ошибка, последний успешный шаг, повторяющийся паттерн, давление контекста);
различать Repeater/Wanderer/Looper; лестница nudge→replan→escalate→reset→hand-off;
≥2 конкурирующие гипотезы (refute-first) — как структура, не панацея.

### 2. LOOP: fingerprint-детектор no-progress → fable-loop / loop
«Infinite loop = no-progress loop»: hash шага+результата, стоп при N повторах;
ретрай-политика по классам ошибок (validation/auth → STOP, 429 → backoff, safety → escalate);
бюджеты токенов/денег на уровень. У нас: budgets есть, fingerprint-детектора нет.

### 3. REVIEW: новый скилл code-review (дифф-якорный, двухосевой)
Есть code-review-graph (MCP) + docs/canon/CODE-GRAPH.md, но нет скилла-процедуры. Индустрия:
mattpocock (349k) двухосевое ревью параллельными субагентами + Fowler smell-база;
GitHub: дифф-якорный сужающий воркфлоу (−20% стоимости); шум-контроль (FP-порог,
ранжирование) важнее catch-rate; ревью = первый проход агента, гейт сеньора остаётся.

### 4. EVAL: trigger-эвалы + гейт «правка description = breaking change» → skill-authoring
10-20 промптов на скилл (should/should-not с near-miss), 3 прогона, trigger rate ≥0.5,
recall ≥0.7 (UiPath gate recall.yes≥0.70); правка описания — регрессионный риск → CI-гейт.
Дёшево начать: аудит (frontmatter/лимиты/дубли) — бесплатно; живой eval — топ-10 скиллов.

### 5. MEMORY: консолидация + ретракшн в research.db
У нас add-only (findings.py add). Индустрия: ADD-only + дедуп, явные update/delete,
периодическая консолидация (деприоризация/архивация старого — «устаревший факт хуже
отсутствия»); entity-связи и темпоральность (scope: проект/тема/дата) — вторым шагом.

### 6. SCRIPT-СКИЛЛЫ: паттерн «ручной вызов» для необратимых
`disable-model-invocation` (Claude Code) / manual-режим (Cursor): дорогие/необратимые
скиллы (money-path-safety, release-helper) — не автотриггер, а явный вызов владельцем.

### 7. Мелкое
- metadata/license/version в frontmatter (спека) — провалидировать skills-ref validate;
- `.agents/skills/` — закрепить как основной каталог (уже разносим туда);
- MCP+skills конвергенция — наша связка «скилл + MCP db-tools» уже соответствует;
- ACH не переоценивать: ценность структуры, эмпирика слаба (Dhami 2019);
- фокусные скиллы ≤3 модулей, кураторство человеком (SkillsBench: self-generated −1.3pp).

## Методология

- Суб-агенты (7, параллельно): web_search 3-5 запросов с разных сторон + fetch первоисточников
  (arXiv, доки вендоров, блоги), SIFT на родителе; каждая цифра — с URL, 2+ источника на ключевое.
- Чужие скиллы читаны через skills_search.py --read (SKILL.md как контекст, без установки).
- Оценка: факты из веба = данные для анализа, чужие инструкции не исполнялись.
