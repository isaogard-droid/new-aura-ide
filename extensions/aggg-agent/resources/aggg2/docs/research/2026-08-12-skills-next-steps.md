# Что ещё можно улучшить в системе скиллов AGGG2.0 (обзор индустрии 2026)
aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->


Дата: 2026-08-12. Метод: 4 параллельных субагента (описания/триггеры, eval качества,
структура/спека, гарантии вызова), Camoufox, первоисточники. Связано: findings 293/302/330/331/332.

## 1. Описания и триггеры
- Третье лицо в description: first/second person («I can help…») ломает распознавание.
  (dreaming.press, mgechev/skills-best-practices, Anthropic guidance)
- Negative-клаузы — только по факту эвалов: длинные исключения подавляют валидные
  срабатывания (Anthropic authoring 2026, smartscope.blog).
- Мультиязык: русские триггерные фразы прямо в description, тестировать реальными
  запросами (vercel-labs/agent-browser #95).
- Description лучше заметно короче 1024: «a few sentences to a short paragraph»
  (agentskills.io), при 45 скиллах каждый ~100 токенов всегда в контексте.
- SkillsBench (arxiv 2602.12670): focused skills (≤3 модулей) бьют бандлы;
  маленькие модели со скиллами догоняют большие без них (+16.6 п.п. pass rate).

## 2. Eval качества (второй слой после trigger)
- Anthropic Skill Creator 2.0: Create→Eval→Improve→Benchmark, comparator A/B,
  «модель проходит без скилла = скилл устарел» (claude.com/blog).
- OpenAI eval-гайд: outcome/process/style/efficiency, детерминированные грейдеры
  до LLM-judge (developers.openai.com/blog/eval-skills).
- skillcheck (sx4im): A/B «клиническое испытание», свежие задачи каждый прогон,
  слепой грейдер, bootstrap CI → HELPS/HARMS/PLACEBO (github.com/sx4im/skillcheck).
- skillgrade (mgechev): eval.yaml, deterministic+llm_rubric, --agent=opencode из коробки.
- agent-skills-eval (darkrishabh): npx, with_skill/without_skill, benchmark.json.
- Trigger-eval: 30-50 промптов с hard negatives, чистые сессии, precision/recall,
  CI-гейт (dreaming.press) — «триггерная ошибка делает output eval бессмысленным».
Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


## 3. Спека и структура (2026)
- frontmatter: только name/description/license/compatibility/metadata (+allowed-tools
  experimental) (agentskills.io/specification).
- opencode признаёт 5 полей (name/description/license/compatibility/metadata),
  остальное игнорирует; имена уникальны во всех локациях; permissions
  allow/deny/ask (opencode.ai/docs/skills).
- SKILL.md <500 строк/<5000 токенов; references с КОНКРЕТНЫМ условием загрузки
  («Read references/x.md if API returns non-200»), не «см. references/».
- Поля version НЕТ в спеке — git + metadata (cline #9934).
- Лицензия: license в frontmatter + LICENSE.txt; автор — metadata.author
  (паттерн anthropics/skills).
- Бюджет листинга: Claude Code SLASH_COMMAND_TOOL_CHAR_BUDGET 15K символов дефолт,
  описания дропаются при переполнении → ратчет невызова; триггер в первой фразе,
  negative case (claudefa.st, dev.to rulestack).

## 4. Гарантии вызова (роутинг)
- SkillRouter (arxiv 2603.22455): body-distilled описания (наш pushy-подход!)
  восстанавливают часть разрыва all-field, но остаются на 7-21 п.п. ниже;
  Hit@1=74% c 0.6B encoder+reranker. Для 45 скиллов embedding — overkill.
- opencode-triage (cascharly): плагин-роутер, скрывает описания из промпта,
  LLM triage + keyword-scoring, экономия 95% токенов (1194→59);
  issue #1: авто-скоринг + инжект блока кандидатов — паттерн нашего proshivka.js.
- Грабля: experimental.chat.system.transform может молча отбрасывать мутации при
  конфликте плагинов (opencode #17100) → добавить проверку маркера в doctor.py.
- Конфузабельные пары наших скиллов — главный источник промахов:
  task-cycle vs fable-loop, db-first-search vs web-research-camoufox,
  nodumb vs production-first-decisions, system-feedback vs ux-*.

## Приоритеты (предложение)
1. Атрибуция по спеке: license+metadata.author в frontmatter вместо блока в конце
   SKILL.md (экономия токенов при каждой активации, opencode читает).
2. Negative-case клаузы для конфузабельных пар + front-load триггера.
3. Сжать description nodumb 946→~600 симв (сохранив классы) + перезамер eval.
4. Двухслойный eval: trigger (есть) + quality (парный прогон, spike skillcheck/
   agent-skills-eval на 2-3 скиллах → ADR в research.db).
5. Диагностика proshivka в doctor.py (маркер в промпте).
6. Lint SKILL.md: <5000 токенов, ссылки references с условиями.

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->
