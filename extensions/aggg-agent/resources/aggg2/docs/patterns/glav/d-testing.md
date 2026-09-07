
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# D. ТЕСТИРОВАНИЕ

изоляция от prod, domain-first, тесты-спека (31-37)

# D. ТЕСТИРОВАНИЕ

---

## 31. NEVER TOUCH PROD STORE IN TESTS
**Принцип:** Тесты на throwaway storage.
**Правило:** env path override + temp file + fresh module import.
**Антипаттерн:** pytest пишет в data/users.db.
**Проверка:** После suite prod row count неизменен.

---

## 32. FRESH IMPORT FOR MODULE-LEVEL SIDE EFFECTS
**Принцип:** import-time connect/migrate ломает изоляцию тестов.
**Правило:** sys.modules.pop + importlib на каждый тест/фикстуру.
**Антипаттерн:** import access once at collection time.
**Проверка:** Два теста с разными DB path не видят данные друг друга.

---

## 33. UNIT DOMAIN FIRST, HANDLER WIRING SECOND
**Принцип:** Бизнес-правила без фреймворка; хендлеры — тонкий клей.
**Правило:** test_access (domain) + test_handlers (fakes for I/O).
**Антипаттерн:** Только e2e через реальный Telegram.
**Проверка:** Domain suite зелёный offline за <2s.

---

## 34. FAKE THE EDGES, NOT THE CORE
**Принцип:** Мокай Telegram/HTTP; не мокай свою бухгалтерскую логику «для удобства».
**Правило:** Real access + fake Update/Context.
**Антипаттерн:** mock grant_minutes → тест зелёный, prod пустой.
**Проверка:** Handler test меняет реальную temp DB.

---

## 35. TEST NAMES ARE THE SPEC
**Принцип:** Имя теста = правило продукта/системы.
**Правило:** test_referral_no_self, test_crypto_idempotent…
**Антипаттерн:** test_1, test_works.
**Проверка:** pytest --collect-only читается как чеклист.

---

## 36. ASSERT THE BOUNDARY CASES
**Принцип:** Баги живут на границах bucket/лимит/0/overflow.
**Правило:** free→0, paid edge, self-ref, double credit, empty username.
**Антипаттерн:** Только happy path.
**Проверка:** Минимум: happy + один edge + один abuse.

---

## 37. DEFINITION OF DONE = PARSE + IMPORT + TEST + ONE PROCESS
**Принцип:** «Закоммитил» ≠ «работает в рантайме».
**Правило:** ast/syntax → import module → pytest → single instance up → log ok.
**Антипаттерн:** Edit → «должно работать» без прогона.
**Проверка:** Чеклист из 4 пунктов перед «готово».

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
