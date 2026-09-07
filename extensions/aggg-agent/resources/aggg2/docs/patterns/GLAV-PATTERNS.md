
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# GLAV — ГЛАВНЫЙ ПРОМТ

## ОБЯЗАТЕЛЬНОЕ ПРАВИЛО

Перед каждым ответом (каждым сообщением) перечисляй паттерны которые применяешь в этом шаге.

Применяй ВСЕ паттерны в своей работе — они обязательны к исполнению.

---

# УНИВЕРСАЛЬНЫЕ ПАТТЕРНЫ, ПРАВИЛА И ПРИНЦИПЫ РАЗРАБОТКИ + ПАТТЕРНЫ ПОВЕДЕНИЯ ИИ
283+ штук. Без привязки к стеку. Для кода, продукта, дебага, тестов, деплоя, работы с ИИ.
Источник дистилляции: боевые сессии (боты, биллинг, API, UI, инциденты) + сессия рефакторинга tg-voice-bot (разбивка монолита на модули, дебаг процессов, мердж в production) + сессия hardening & merge (аудит, метрики, cap, rate limit, provider debug) + сессия UX fix (view state separation, navigation context, content labels) + сессия UX consolidation (command hub, two-tier navigation, button semantics, emoji discipline, callback delegation) + сессия promo & value ops (soft delete, compound PK, atomic SQL, input normalization, structured failures, creator scoping, single constant, copy tests, dual registration, content validation, modal input) + сессия Rich Messages & multi-format delivery (content-type rendering, line-aware split, native API fallback, incremental rollout, custom emoji isolation, history Rich parity, grid layout, smoke-test protocol).
Дата: 2026-07-24

---

## КАК ЧИТАТЬ
  Имя
  Принцип (1-2 строки)
  Правило (что делать)
  Антипаттерн (что ломает)
  Проверка/Признак (как понять, что соблюдён)

---

---

# КАРТА ФАЙЛА

Паттерны разнесены по темам (механическая резка 15.08.2026 — гейт god-файлов, docs/canon/FILE-SIZE.md). Файл-индекс, полное содержимое — ниже.

| Блок | Файл | Тема |
|---|---|---|
| A (1-10) | `glav/a-money.md` | Истина и деньги: биллинг, side-effects |
| B (11-20) | `glav/b-product-ux.md` | Продукт и UX-контракт |
| C (21-30) | `glav/c-architecture.md` | Архитектура и простота |
| D (31-37) | `glav/d-testing.md` | Тестирование |
| E | `glav/e-debug-incidents.md` | Дебаг и инциденты |
| F | `glav/f-admin-ops-security.md` | Admin, ops, безопасность |
| G | `glav/g-performance-io.md` | Производительность и надёжность I/O |
| H | `glav/h-process.md` | Процесс разработки, порядок фич |
| I | `glav/i-referrals-growth-abuse.md` | Рефералки, рост, abuse |
| J | `glav/j-communication.md` | Коммуникация, работа в паре |
| K | `glav/k-meta.md` | Мета-принципы (короткие законы) |
| L (L1-L54+) | `glav/l-ai-behavior.md` | Паттерны поведения ИИ |
| M (M1-M30) | `glav/m1-hardening.md` | Харденинг и аудит, часть 1 |
| M (M31-M60) | `glav/m2-hardening.md` | Харденинг и аудит, часть 2 |
| N (N1-N43+) | `glav/n-ux-navigation.md` | UX-навигация, контекст |
| O | `glav/o-promo-value.md` | Промо, активации, value-операции |
| P | `glav/p-rich-delivery.md` | Rich / native API / multi-format |
| ТОПы | `glav/tops.md` | ТОП-20/ТОП-10 «если помнить только их» |

---

# КАК ПРИМЕНЯТЬ ЭТОТ ФАЙЛ

- Перед фичей: пробежать топ-20 — что задеваем?
- На ревью: money/auth/render/tests чеклист
- На инциденте: блок E (debug) + L9-L15 (AI debug patterns)
- На росте/рефералке: блок I
- При hardening/аудите: блок M (hardening & merge patterns) + M57 (retrospective audit)
- При UX-навигации/контексте: блок N (navigation & context) + N1-N8 (view state separation, context propagation)
- При UI-консолидации/редизайне кнопок: N36-N43 (command hub, two-tier nav, button semantics, emoji discipline, callback delegation)
- При промо/активациях/value-операциях: блок O (soft delete, compound PK, atomic SQL, structured failures, creator scoping, single constant, copy tests, dual registration, modal input)
- При смене/добавлении формата доставки: блок P (content-type rendering, line-aware split, native API fallback, incremental rollout, custom emoji isolation, history parity, grid layout, smoke protocol)
- При работе с ИИ: блок L (AI behavior patterns) — понимать как агент принимает решения
- При слиянии проектов (staging ↔ production): M1-M4, M23-M25, M44-M46, M60 + N20 (staging-first)
- Раз в спринт: вычеркнуть то, что уже «в крови» команде



---

*Разработано для https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, дальше — ещё лучше.***

Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
