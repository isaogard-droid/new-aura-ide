
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# ТОП-20 / ТОП-10 «ЕСЛИ ПОМНИТЬ ТОЛЬКО ИХ»

краткие сводки по всем блокам

# ТОП-20 «ЕСЛИ ПОМНИТЬ ТОЛЬКО ИХ» (универсальные)

1. Money path: atomic, idempotent, logged, tested
2. Separate buckets for different value semantics
3. Hard gate before expensive work
4. No silent except on side effects
5. Facts (DB/log/PID) before theories
6. Symptom ≠ root; fix once in shared place
7. Never test on prod storage
8. Product rules as named tests
9. Promise only what code does
10. One render/escape path for all surfaces
11. YAGNI until second need
12. Config/secrets outside; defaults in code
13. Schema evolves without wipe
14. Single consumer for exclusive streams + restart ritual
15. Domain tests first, handler fakes second
16. DoD: parse + import + test + one live process
17. Cache expensive; rebuild cheap views
18. Identity: flexible input, stable id storage
19. Growth with abuse cases from day one
20. Handoff ends with concrete smoke steps

---

# ТОП-10 «ЕСЛИ ПОМНИТЬ ТОЛЬКО ИХ» (поведение ИИ)

1. Map before cut — сначала карта кода, потом Edit
2. Import-and-lint loop — после каждого Edit проверка ruff/compileall
3. Facts-first, then theory — PID/log/DB до гипотез
4. PID trace chain + lineage audit — ParentProcessId + CreationDate = кто кого и когда запустил
5. Stop-all-then-start-one — убить старые процессы перед запуском
6. Token isolation by launcher — каждый бот свой токен, launcher чистит env
7. Compatibility facade — старые имена сохраняются через адаптеры
8. _LOCAL_NAMES guard + pre-cap side-effect guard — bind() не затирает; _ensure() после проверок
9. Three-step verification — ruff -> compileall -> pytest
10. Definition of Done — parse + import + test + one live process + log verification window

---

# ТОП-10 «ЕСЛИ ПОМНИТЬ ТОЛЬКО ИХ» (hardening & merge)

1. Diff before copy — хэш + diff stat перед любым копированием между проектами
2. Metric on actual state change — newly_credited флаг, metric_inc только при первом зачислении
3. Safe default escalation — лимиты по умолчанию restrictive (20, не 0)
4. Busy_timeout + WAL combo — SQLite: timeout=30 + busy_timeout=30000 + journal_mode=WAL
5. Provider except narrowing — except: pass → except as exc: debug-лог с контекстом
6. Pre-cap side-effect guard — проверка cap ДО _ensure() / INSERT
7. Launcher stderr separation — launcher_err.log отдельно от RotatingFileHandler
8. Post-restart log timestamp filter — проверять только строки после времени старта
9. Merge scope: architectural only — не копировать production-специфичные файлы
10. Hardening retrospective audit — после сессии grep-аудит: что реально закрыто, что осталось

---

# ТОП-10 «ЕСЛИ ПОМНИТЬ ТОЛЬКО ИХ» (promo & value ops)

1. Soft delete / soft finish — UPDATE status, никогда не DELETE бизнес-строки
2. Compound PK as idempotency guard — (code, user_id) блокирует повтор на уровне БД
3. Atomic check-and-increment in SQL — UPDATE...SET x=x+1 WHERE x<max, один запрос
4. Input normalization at boundary — каноническая форма один раз на входе
5. Structured failure reasons — (ok, reason_code, value) вместо True/False
6. Creator-scoped admin queries — WHERE created_by=? во всех admin-запросах
7. Single constant drives all surfaces — REFERRAL_BONUS в БД, UI, share, тестах
8. User-facing copy as regression tests — assert на ключевые обещания в тексте
9. Dual registration: handler + command menu — handler в bot_app + BotCommand в post_init
10. Modal input with cancel — awaiting_X флаг + cancel button + проверка в on_text

---

# ТОП-10 «ЕСЛИ ПОМНИТЬ ТОЛЬКО ИХ» (Rich & multi-format delivery)

1. Content-type-specific rendering — разная доставка для coding/voice/article
2. Line-aware splitting — резать по строкам, не рвать HTML-теги
3. Try-new → fallback-old — Rich → HTML при любой ошибке
4. Native API call when library lacks support — HTTP напрямую к Bot API
5. New API research protocol — docs → lib check → endpoint test → real smoke
6. Feature flag per content type — Rich включается по kind, не глобально
7. Incremental rollout — coding → summary → article → transcription по одному
8. Custom emoji skip inside code blocks — замена только вне <pre>/<code>
9. History view uses same rendering as fresh — Rich в истории = Rich при создании
10. Inline menu grid layout — 2×N сетка с семантическими парами

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
