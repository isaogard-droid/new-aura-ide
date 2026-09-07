
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# G. ПРОИЗВОДИТЕЛЬНОСТЬ И НАДЁЖНОСТЬ I/O

I/O, производительность, надёжность

# G. ПРОИЗВОДИТЕЛЬНОСТЬ И НАДЁЖНОСТЬ I/O

---

## 51. DON'T BLOCK THE EVENT LOOP
**Принцип:** Async framework + sync HTTP/CPU = latency для всех.
**Правило:** to_thread / worker для blocking; async клиенты где уместно.
**Антипаттерн:** requests.get в async handler на 30s STT.
**Проверка:** Под нагрузкой ping/health не встаёт колом на одном job.

---

## 52. TEMP ARTIFACTS DIE IN FINALLY
**Принцип:** Скачал — обработал — удалил. Всегда.
**Правило:** try/finally unlink; missing_ok.
**Антипаттерн:** tmp/ растёт гигабайтами.
**Проверка:** После 100 jobs tmp ~ empty.

---

## 53. RATE LIMIT CHEAPLY AT THE EDGE
**Принцип:** Простой per-user window отсекает тупой flood до дорогой логики.
**Правило:** N per minute; 0 = off; message «подожди».
**Антипаттерн:** Сразу в LLM на 100 msg/sec от одного uid.
**Проверка:** Burst → reject without provider calls.

---

## 54. PAGINATE LISTS; CARRY BACK CONTEXT
**Принцип:** Длинные списки без страниц — смерть UX и лимитов сообщения.
**Правило:** page size fixed; numbered or next/prev; back_page in deeper views.
**Антипаттерн:** Вывести 500 записей одним message.
**Проверка:** Open item → Back → same page.

---

## 55. SPLIT OUTPUT AT PLATFORM LIMITS SAFELY
**Принцип:** Лимит длины сообщения/пакета — факт платформы.
**Правило:** chunk by lines/paragraphs; mark truncated; don't break escape mid-tag if avoidable.
**Антипаттерн:** send 20k chars → API error «message too long».
**Проверка:** Long fixture splits without crash.

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
