# 2026-08-11 Обшивка баз: связи, метрики, авто-разбор сессий
aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->


## Вопрос
Реально ли мы используем базы на максимум, и что «обшить» агенту, чтобы
данные (research.db, aggg2.db, sherpa-voice.db + история сессий) работали
на полную? (Аудит — findings id=197.)

## План / под-вопросы
1. Как устроены наши базы и цикл сейчас (инвентаризация).
2. Какие паттерны deep-research в индустрии (arXiv, LangChain, fast.io).
3. Что дожимать: связи находок, метрики поисков, авто-разбор сессий,
   семантика, субагенты.

## Источники
- arXiv 2506.18096 «Deep Research Agents: A Systematic Examination And
  Roadmap» — архитектура DR-агентов: offline/online retrieval, планирование,
  мультиагентность, память.
- fast.io «How to Build an AI Agent Deep Research Workflow» — 5 стадий:
  decompose → search → store → synthesize → deliver; 3-5x tool calls;
  хранилище промежуточных артефактов обязательно.
- LangChain deepagents «Build a deep research agent» — субагенты с
  изолированным контекстом, синтез с цитатами.
- TheNewStack «6 agentic knowledge base patterns» — LinkedIn CAPT =
  плейбуки/скиллы (наш паттерн канонов), интеграционные базы знаний.
- alexgarcia.xyz / github asg017/sqlite-vec — гибрид FTS5+вектор в SQLite.

## Отсеянное и почему
- Эмбеддинг-модель (sentence-transformers + torch, ~1 ГБ) для 197 находок —
  неоправданно (YAGNI): FTS5 unicode61 уже находит по словам; порог для
  пересмотра — тысячи находок или стабильные промахи FTS.
- Отдельный scratchpad-сервис для сырья ресёрча — заменён соглашением
  «отчёт в docs/research/» (KISS, без нового сервиса).
- Авто-добавка всех кандидатов из сессий в базу без отбора — мусор в базе;
  сделано полу-авто (--add по номерам).
Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


## Выводы
Сделано (все 6 пунктов обшивки):
1. `db-tools/extract_findings.py` — авто-кандидаты из истории сессий
   (sherpa-voice history.md/txt) → research.db, полу-авто, с дедупом.
2. `findings.py`: поле source, таблица links, команды link add/list/rm,
   related, show, stats — связи находок.
3. `docs/research/` — соглашение об отчётах глубокого ресёрча (README +
   TEMPLATE), findings ссылается на отчёт через --source.
4. `db-tools/log.py` + search.py --stats + MCP db-tools — метрики поисков
   (search_log: топ запросов, пустые, по базам).
5. Семантика — замерён и отложен: sqlite-vec ставится легко, но модель
   неоправданна на текущем объёме (см. «Отсеянное»).
6. docs/canon/CAMOUFOX.md — раздел «Оркестрация большого ресёрча» (субагенты по
   под-вопросам, паттерн LangChain/fast.io).

Находки: id=197 (аудит), id=200 (итог обшивки), id=201 (spike семантики).

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
