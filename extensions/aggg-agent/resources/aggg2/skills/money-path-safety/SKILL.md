---
name: money-path-safety
description: "Деньги: оплатить/купить/подписаться, бонус/промокод, баланс/лимит/квота, возврат, гейт лимита до дорогого вызова, логика списаний — даже если деньги не названы («дай ещё минут»). Не для схем БД и дебага."
compatibility: любые языки/стеки, где есть балансы, квоты, промокоды, лимиты
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
disable-model-invocation: true
---

# Money path safety: деньги и ценность — особый класс кода

## 0. Ручной вызов для необратимых операций

Скилл помечен `disable-model-invocation` (opencode флаг игнорирует — соблюдать вручную):
- **Вопросы** («как устроено списание») — скилл можно не грузить: чтение не меняет балансы.
- **ЛЮБОЕ действие, меняющее ценность** (списание/начисление/refund/промокод/квоты/лимиты) ИЛИ дорогой вызов (LLM/API) — скилл ОБЯЗАТЕЛЬНО: гейт перед действием.
- Автономно, в середине другой задачи, деньги-путь не трогать: предложить шаг и спросить владельца.

Первоисточник: `docs/patterns/GLAV-PATTERNS.md` (блоки A, O, I, H.56-57).

## 1. Деньги: железные правила

1. **MONEY PATH IS SACRED** — lock/транзакция + идемпотентность + лог + тест double-submit (дважды «оплатить» → +X, не +2X).
2. **IDEMPOTENCY BY DEFAULT** — ключ операции (invoice_id, event_id) + флаг credited + early return.
3. **SEPARATE BUCKETS** — trial/promo/purchase/subscription — разные сущности, не одно поле `balance`; порядок списания: free → bonus → paid.
4. **HARD GATE BEFORE EXPENSIVE WORK** — проверка права/лимита/денег ДО внешнего вызова (CPU/API/LLM); нулевой баланс → API не вызывается.
5. **CHARGE AFTER SUCCESS** — успех → debit; ошибка → no debit (+ log).
6. **LOG EVERY MUTATION** — одна строка на credit/debit/grant/refund: `charge uid=%s seconds=%.3f from_free=%.3f from_bonus=%.3f from_paid=%.3f`; grep по user_id восстанавливает историю.
7. **NO SILENT EXCEPT ON SIDE EFFECTS** — except: pass допустим на cleanup, НЕДОПУСТИМ на money/auth/data-loss.
8. **READ-MODIFY-WRITE UNDER LOCK** — RMW без блокировки = lost update; mutex/транзакция на весь RMW.
9. **ONE SOURCE OF TRUTH** — UI/кэш/лог — производные; истина — хранилище; инцидент начинается с чтения storage.

## 2. Атомарность в SQL

- **Atomic check-and-increment**: `UPDATE ... SET used = used + 1 WHERE used < max` — один запрос, rowcount 0 = лимит исчерпан. НЕ SELECT → IF → UPDATE.
- **Compound PK как идемпотентность**: `PRIMARY KEY (code, user_id)` — повтор блокируется на уровне БД.
- **SQLite**: `connect(timeout=30.0)` + `PRAGMA busy_timeout=30000` + `journal_mode=WAL` — три вместе.
- **Metric upsert**: `INSERT ... ON CONFLICT DO UPDATE SET value=value+excluded.value`.

## 3. Промокоды и value-операции

- **SOFT DELETE** — никогда DELETE бизнес-строки: `UPDATE status='finished'`.
- **INPUT NORMALIZATION AT BOUNDARY** — каноническая форма один раз на входе (upper/strip/charset).
- **STRUCTURED FAILURE** — `(ok, reason_code, value)`: "not_found"/"already_used"/"exhausted"; UI мапит код. НЕ просто False.
- **CREATOR-SCOPED ADMIN QUERIES** — `WHERE created_by=?` во всех admin-запросах.
- **SINGLE CONSTANT DRIVES ALL SURFACES** — REFERRAL_BONUS=30 в БД, UI, share, тестах.
- **PRE-CAP SIDE-EFFECT GUARD** — проверка cap ДО `_ensure()`/INSERT: отказ → return без мутаций.
- **MODAL INPUT WITH CANCEL** — флаг awaiting_X + кнопка «Отмена» + проверка в on_text.

## 4. Рефералки и abuse

- **REWARD ONCE PER UNIQUE RELATION** — claimed / unique (referrer, referred); **NO SELF-DEAL** — `new_uid != referrer_uid` до credit.
- **ONLY NEW ACCOUNTS** — бонус на first-seen ИЛИ first-purchase, выбрать явно; **ABUSE BUDGET** — max loss на фейк × стоимость, записать tradeoff.
- **UI TEXT FROM CONFIG** — текст лимита из той же функции, что и enforcement.

## Workflow

Grep по handler'ам (charge, debit, credit, grant, refund, invoice, balance, promo, referral, quota, limit) → для каждого пути проверь по правилам выше и чеклисту. Тесты: double-submit, error-no-debit, reject-no-side-effects, cap edge, abuse case — имена = спека.

## Чеклист ревью money-кода

- [ ] double-submit → баланс не изменился дважды (тест); ошибка провайдера → списания нет (тест)
- [ ] каждая мутация логируется с id субъекта и amount; нет except: pass на money path
- [ ] RMW под lock/транзакцией; порядок списания — один алгоритм в одном месте
- [ ] лимиты: env-переменная с ненулевым default (cap=0 = unlimited явно), `if cap and ...`
- [ ] rejected-операция не создала строк (`assert not user_exists(...)`); месяц ключуется YYYY-MM, UNIQUE по (id, month)
- [ ] у каждого лимита warning-лог при достижении

## When NOT to use

- Обычный CRUD без балансов/квот/промокодов — избыточно; чистый UI без value-операций — `ux-navigation-context`; инцидент/дебаг — `debug-incident-protocol`.

## Этапы (handoff)

- **Вход из:** `ask-nodumb`, любая задача с деньгами/лимитами · **Дальше:** `hardening-observability`, `testing-discipline`

## References

- `docs/patterns/GLAV-PATTERNS.md` — блоки A (1-10), O (1-15), I (63-66), H (56-57), K (71-90), ТОП-20; сессии биллинга (research.db)

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
