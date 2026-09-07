
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# O. ПРОМО, АКТИВАЦИИ И VALUE-ОПЕРАЦИИ

promo codes, referral adjustment, marketing copy

# O. ПРОМО, АКТИВАЦИИ И VALUE-ОПЕРАЦИИ (извлечено из сессии promo codes + referral adjustment + marketing copy)

---

## O1. SOFT DELETE / SOFT FINISH
**Принцип:** Никогда не DELETE строки с бизнес-значением. Меняй status: active → finished/deleted. История, audit trail и foreign keys выживают.
**Правило:** status TEXT NOT NULL DEFAULT 'active'; finish_promo() делает UPDATE status=..., не DELETE. Список по умолчанию фильтрует status='active'.
**Антипаттерн:** DELETE FROM promo_codes — история активаций теряет связь, аудит невозможен.
**Признак:** В коде нет DELETE для бизнес-сущностей; только UPDATE status.

---

## O2. COMPOUND PK AS IDEMPOTENCY GUARD
**Принцип:** Повторная активация одним пользователем блокируется на уровне БД: PRIMARY KEY (code, user_id). Не нужно проверять в коде.
**Правило:** Таблица redemption с PK (entity_id, user_id). INSERT — сработал или UNIQUE constraint violation. Никаких SELECT перед INSERT.
**Антипаттерн:** SELECT COUNT(*), потом if count==0: INSERT — race condition между проверкой и вставкой.
**Признак:** Схема содержит составной PRIMARY KEY по (бизнес-сущность, пользователь); handler не делает pre-check.

---

## O3. ATOMIC CHECK-AND-INCREMENT IN SQL
**Принцип:** `UPDATE ... SET used = used + 1 WHERE used < max` — одно атомарное SQL-выражение вместо SELECT + IF + UPDATE. Нет гонки.
**Правило:** Инкремент счётчика с WHERE-условием-ограничением в одном запросе. Проверять rowcount: 0 = лимит исчерпан.
**Антипаттерн:** SELECT used; if used < max: UPDATE used = used + 1 — между SELECT и UPDATE другой поток тоже проходит.
**Признак:** SQL для инкремента содержит WHERE-ограничение в том же UPDATE; rowcount используется для определения исчерпания.

---

## O4. INPUT NORMALIZATION AT BOUNDARY
**Принцип:** Нормализовать ввод один раз на входе: uppercase, strip whitespace, validate charset. Хранить каноническую форму. Весь downstream-код доверяет формату.
**Правило:** `_promo_code(value)` → canonical form. Одна функция нормализации. Все операции (create, redeem, finish, delete) работают с канонической формой.
**Антипаттерн:** upper() в одном месте, strip() в другом, валидация в третьем — разные пути видят разное.
**Признак:** Одна точка нормализации на входе; downstream-код не повторяет transform/validate.

---

## O5. STRUCTURED FAILURE REASONS
**Принцип:** Возвращать (ok: bool, reason: str, value: X) вместо True/False. Reason codes ("not_found", "already_used", "exhausted", "closed", "invalid") мапятся в понятные пользователю сообщения.
**Правило:** Кортеж из трёх: успех, причина-отказа (машинный код), полезная нагрузка. UI-слой мапит код в человеческое сообщение.
**Антипаттерн:** return False — пользователь видит «не вышло», админ не знает причину.
**Признак:** Функции-мутаторы возвращают (bool, str, value); есть dict маппинга reason → user_message.

---

## O6. CREATOR-SCOPED ADMIN QUERIES
**Принцип:** Админ видит только свои объекты. list_promos(created_by=admin_id) фильтрует по создателю. Мутации проверяют created_by match.
**Правило:** WHERE created_by=? во всех admin-запросах. finish/delete проверяют row["created_by"] == admin_id.
**Антипаттерн:** list_promos() возвращает все промокоды всех админов — утечка между админами.
**Признак:** Каждый admin-запрос содержит created_by фильтр или проверку.

---

## O7. SINGLE CONSTANT DRIVES ALL SURFACES
**Принцип:** Одна константа (REFERRAL_BONUS = 30) управляет: зачислением в БД, UI-текстом приглашения, share-сообщением, тестами. Изменил в одном месте — обновилось везде.
**Правило:** Константа в access.py; все упоминания значения — через неё. Ни одного хардкода числа в UI или тестах.
**Антипаттерн:** "50 минут" в UI хардкодом при REFERRAL_BONUS=30 — расходятся.
**Признак:** Grep числа бонуса в коде находит только определение константы и её использования.

---

## O8. USER-FACING COPY AS REGRESSION TESTS
**Принцип:** Маркетинговый/пользовательский текст проверяется тестами: `assert "E-transcriber" in WELCOME`, `assert "улучшает промпты" in WELCOME`. Изменение копии — breaking change.
**Правило:** test_marketing_copy_explains_core_features с assert на ключевые обещания и фичи. Запускается в CI.
**Антипаттерн:** Копия только в коде, без тестов — можно случайно удалить ключевое обещание.
**Признак:** Для каждого пользовательского текста (welcome, examples, invite) есть тест с assert на ключевые строки.

---

## O9. DUAL REGISTRATION: HANDLER + COMMAND MENU
**Принцип:** Команда должна быть зарегистрирована в двух местах: handler в bot_app.py (обработка) И BotCommand в post_init (меню команд Telegram). Одно без другого — команда невидима.
**Правило:** Добавил CommandHandler → добавил BotCommand("cmd", "описание") в список команд меню.
**Антипаттерн:** Handler есть, BotCommand нет — команда работает через /cmd но не показывается в меню.
**Признак:** Grep имени команды находит и CommandHandler, и BotCommand.

---

## O10. PRE-DEPLOY CONTENT VALIDATION
**Принцип:** Перед деплоем проверить что пользовательские тексты укладываются в платформенные лимиты (описание, welcome). Сбой при превышении.
**Правило:** `len(WELCOME)`, `len(short_description)` проверяются скриптом или тестом до деплоя. При превышении — fail.
**Антипаттерн:** Узнать о превышении лимита из ошибки API на проде.
**Признак:** В тестах или CI есть assert len(text) <= PLATFORM_LIMIT.

---

## O11. MODAL INPUT WITH CANCEL
**Принцип:** Пользователь входит в режим ввода (промокод) → user_data флаг awaiting_X = True → inline-кнопка «Отмена» → text handler проверяет флаг и либо обрабатывает ввод, либо отменяет.
**Правило:** Флаг в user_data + cancel button + проверка флага в on_text. Отмена снимает флаг и убирает клавиатуру.
**Антипаттерн:** Бесконечный режим ввода без отмены — пользователь заперт.
**Признак:** Любой режим ожидания ввода имеет cancel button и снятие флага.

---

## O12. CONTEXT-CONDITIONAL TEXT ROUTING
**Принцип:** Один on_text handler обслуживает несколько режимов через проверку флагов user_data. Не нужно плодить handlers на каждый режим.
**Правило:** `if ctx.user_data.get("awaiting_promo"): handle_promo(); return`. Проверка в начале, до общей логики.
**Антипаттерн:** Отдельный MessageHandler для каждого режима — конфликты приоритетов, дублирование.
**Признак:** В on_text есть несколько if-блоков с early return для разных awaiting_X флагов.

---

## O13. BONUS PURPOSE COMMUNICATION
**Принцип:** При начислении бонуса сообщать пользователю, на что его можно потратить. Устанавливает ожидания и снижает support-тикеты.
**Правило:** После активации: "+N бонусных минут. Минуты доступны для функций A, B, C."
**Антипаттерн:** "+30 минут" без контекста — пользователь не знает что с ними делать.
**Признак:** Каждое сообщение о начислении содержит перечень применений.

---

## O14. VALUE-PARAMETER ADJUSTMENT AS SINGLE COMMIT
**Принцип:** При изменении value-параметра (бонус 50→30): один коммит меняет константу, все тесты с новыми expected, все UI-тексты. Никакого промежуточного состояния.
**Правило:** Grep старого значения → заменить во всех местах → запустить тесты → коммит. Атомарно.
**Антипаттерн:** Константа 30, тесты ждут 50, UI пишет 50 — три источника правды.
**Признак:** Grep старого числа после изменения не находит ни одного вхождения.

---

## O15. ADMIN-COMMAND PRESENCE AUDIT
**Принцип:** После добавления admin-команды — grep-аудит: handler есть? BotCommand есть? В menu scope для admin role? В /admin help тексте?
**Правило:** Чеклист из 4 пунктов: handler, BotCommand, role scope, help text.
**Антипаттерн:** Добавил handler, забыл BotCommand — админ не видит команду в меню.
**Признак:** Grep имени команды находит 4 вхождения в коде.



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
