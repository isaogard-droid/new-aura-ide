
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# I. РЕФЕРАЛКИ, РОСТ, ABUSE

рефералки, рост, защита от абуза

# I. РЕФЕРАЛКИ, РОСТ, ABUSE (универсально)

---

## 63. REWARD ONCE PER UNIQUE RELATION
**Принцип:** Один приглашённый = один бонус паре, не на каждый /start.
**Правило:** claimed flag / unique (referrer, referred) constraint.
**Антипаттерн:** Каждый re-start капает минуты.
**Проверка:** Повтор deep-link → no second credit.

---

## 64. NO SELF-DEAL
**Принцип:** Нельзя быть реферером самому себе.
**Правило:** new_uid != referrer_uid до credit.
**Антипаттерн:** Своя ссылка в другом клиенте без проверки id.
**Проверка:** self ref → false, balances unchanged.

---

## 65. ONLY NEW ACCOUNTS (OR ONLY AFTER QUALIFYING ACTION)
**Принцип:** Либо bonus on first seen, либо on first purchase — выбрать явно.
**Правило:** exists-before-track check ИЛИ pay-event trigger; не оба размыто.
**Антипаттерн:** Старый юзер открыл чужую ссылку → обоим +50.
**Проверка:** Existing user + ref link → no credit.

---

## 66. ABUSE BUDGET IS A PRODUCT DECISION
**Принцип:** +50/+50 on start = дешёвый farm; on purchase = меньше farm, меньше viral.
**Правило:** Записать tradeoff; лимиты/username gate/quality action.
**Антипаттерн:** «Потом антифрод» при публичной раздаче минут.
**Проверка:** Оценка: max loss per fake account × cost of minute.

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
