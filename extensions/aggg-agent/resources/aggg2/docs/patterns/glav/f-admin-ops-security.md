
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# F. ADMIN, OPS, БЕЗОПАСНОСТЬ

админ, эксплуатация, безопасность

# F. ADMIN, OPS, БЕЗОПАСНОСТЬ

---

## 45. ADMIN POWER WITH LEAST SURPRISE
**Принцип:** Админ-команды мощные → явный resolve, push юзеру, отчёт delivered.
**Правило:** /give id|@user; notify target; reply admin status.
**Антипаттерн:** Тихий grant без уведомления и без audit.
**Проверка:** Юзер узнал о начислении без скрина от админа.

---

## 46. RESOLVE IDENTITY FLEXIBLY, STORE CANONICALLY
**Принцип:** Ввод: id или @name. Хранение: stable numeric id.
**Правило:** find_user(token); deep-links by id (username меняется).
**Антипаттерн:** Referral link by @username only.
**Проверка:** Смена username не ломает старые ссылки/гранты.

---

## 47. SCOPED CAPABILITIES (WHAT USER SEES)
**Принцип:** Не светить admin surface всем.
**Правило:** Command menu scope / RBAC / feature flags per role.
**Антипаттерн:** /broadcast в общем меню «ну его не найдут».
**Проверка:** Обычный юзер не видит admin commands.

---

## 48. BROADCAST/BULK WITH THROTTLE + REPORT
**Принцип:** Массовая отправка = rate limits + partial failure normal.
**Правило:** segment query; throttle; sent/failed counters.
**Антипаттерн:** for user in all: send без sleep и без отчёта.
**Проверка:** 100 recipients → отчёт и нет ban/flood immediate.

---

## 49. DENY QUIETLY OR SHORT; NEVER LEAK INTERNALS
**Принцип:** Non-admin не должен получать карту системы.
**Правило:** silent return or «нет доступа»; без списка id/env.
**Антипаттерн:** «You are not in TELEGRAM_ADMIN_IDS=…».
**Проверка:** Ответ deny не содержит инфраструктуры.

---

## 50. SECRETS NEVER IN GIT, NEVER IN USER MESSAGES
**Принцип:** Ключи живут в env/secret store.
**Правило:** load at start; redact logs; no token in exceptions to client.
**Антипаттерн:** .env committed; bot token in screenshot docs in repo root.
**Проверка:** git grep token/password пуст в tracked files.

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
