
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# E. ДЕБАГ И ИНЦИДЕНТЫ

факты до теорий, симптом ≠ корень (38-…)

# E. ДЕБАГ И ИНЦИДЕНТЫ

---

## 38. FACTS BEFORE THEORIES
**Принцип:** Сначала storage + logs + process list, потом гипотезы.
**Правило:** 1) config flags 2) DB row 3) log lines 4) only then code guess.
**Антипаттерн:** «Наверное кэш, переустанови».
**Проверка:** Первое сообщение в инциденте содержит факт, не мнение.

---

## 39. SYMPTOM ≠ ROOT CAUSE
**Принцип:** «Минуты не списываются» — симптом; silent except + wrong parser — корень.
**Правило:** Трассируй call path до side-effect; чини корень один раз.
**Антипаттерн:** Патч в каждом caller вместо shared charge().
**Проверка:** Один фикс закрывает все поверхности (voice/audio/note).

---

## 40. IF METRIC FLAT WHILE FEATURE «WORKS» — SILENT FAILURE
**Принцип:** UX успех + нулевая метрика = глотание ошибки.
**Правило:** Ищи except/early return на path метрики.
**Антипаттерн:** «Ну юзеру же ответило».
**Проверка:** Корреляция success UX ↔ counter increment.

---

## 41. SINGLE CONSUMER FOR EXCLUSIVE STREAMS
**Принцип:** long-poll / queue consumer / lock file — один владелец.
**Правило:** kill duplicates before start; health = exactly one PID.
**Антипаттерн:** Два bot.py → Conflict, «рандомные» пропуски update.
**Проверка:** process list count == 1 после restart ritual.

---

## 42. RESTART RITUAL IS PART OF THE FIX
**Принцип:** Код на диске ≠ код в памяти.
**Правило:** После фикса runtime-процесса: stop all → start one → verify log.
**Антипаттерн:** Починил файл, старый PID живёт час.
**Проверка:** PID creation time > edit time.

---

## 43. ENCODING OF CONSOLE ≠ ENCODING OF PRODUCT
**Принцип:** Кракозябры в Windows console не значат битые данные.
**Правило:** Проверяй UTF-8 в клиенте/файле; не «исправляй» данные из-за cp1251.
**Антипаттерн:** Перекодировали БД «чтобы в консоли красиво».
**Проверка:** Файл/Telegram ок при кривой консоли.

---

## 44. INCIDENT CHECKLIST TEMPLATE
**Принцип:** Повторяемые инциденты → чеклист, не героизм.
**Правило:** flags? storage? logs? single instance? money path except? duration source?
**Антипаттерн:** Каждый раз с нуля.
**Проверка:** Чеклист лежит рядом с runbook/паспортом.

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
