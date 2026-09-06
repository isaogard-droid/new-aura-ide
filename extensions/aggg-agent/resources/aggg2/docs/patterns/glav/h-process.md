
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# H. ПРОЦЕСС РАЗРАБОТКИ И ПОРЯДОК ФИЧ

порядок фич, процесс разработки

# H. ПРОЦЕСС РАЗРАБОТКИ И ПОРЯДОК ФИЧ

---

## 56. VALUE SLICE ORDER: CORE → MONEY CORRECT → HISTORY → POWER → GROWTH
**Принцип:** Сначала работает и честно списывает; потом удобство; потом growth loops.
**Правило:** pipeline → billing correctness → retention UX → admin → referral.
**Антипаттерн:** Referral day 1 при broken charge.
**Проверка:** Можно выключить growth — core money path жив.

---

## 57. FIX MONEY BUGS BEFORE FEATURES
**Принцип:** Неправильный charge важнее новой кнопки.
**Правило:** P0 billing; P1 UX; P2 nice-to-have.
**Антипаттерн:** «Потом спишем, давай рилсы».
**Проверка:** Backlog: money items выше cosmetic.

---

## 58. SMALLEST DIFF THAT FIXES ROOT
**Принцип:** Ленивый старший: минимум кода в правильном месте.
**Правило:** Одна guard в shared function > 10 патчей в callers.
**Антипаттерн:** Костыль только на voice, audio всё ещё free.
**Проверка:** Diff short; all media kinds covered by one path.

---

## 59. DOCUMENT GAPS EXPLICITLY
**Принцип:** Известный долг (нет webhook) лучше скрытого.
**Правило:** Запись в session/README: gap + MVP workaround + next step.
**Антипаттерн:** Притворяемся real-time payment, а там кнопка «Проверить».
**Проверка:** Новый человек не удивится поведению кассы.

---

## 60. OPERATOR DOCS = /admin HELP = LIVING SPEC
**Принцип:** Если команда есть — она в шпаргалке оператора.
**Правило:** ADMIN_HELP обновляется вместе с командой.
**Антипаттерн:** 8 команд, help про 3.
**Проверка:** /admin и код 1:1.

---

## 61. SMOKE STEP IN THE HANDOFF
**Принцип:** «Готово» без «нажми X» = недоделано.
**Правило:** После фикса — 1-3 конкретных шага проверки юзером.
**Антипаттерн:** «Вроде ок, потести».
**Проверка:** Последняя строка ответа = actionable smoke.

---

## 62. PREFER MEASUREMENT OVER ARGUMENT
**Принцип:** Лог charged secs=61 закрывает спор быстрее мнений.
**Правило:** Добавь метрику/лог, воспроизведи, покажи число.
**Антипаттерн:** Час теории без одной строки evidence.
**Проверка:** Решение принято по артефакту (log/DB/test).

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
