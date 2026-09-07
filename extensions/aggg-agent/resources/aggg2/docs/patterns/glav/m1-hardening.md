
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# M1-M30. ПАТТЕРНЫ ХАРДЕНИНГА И АУДИТА (часть 1)

M1-M30 из сессии hardening + merge

# M. ПАТТЕРНЫ ХАРДЕНИНГА И АУДИТА (извлечено из сессии hardening + merge)

---

## M1. DIFF BEFORE COPY
**Принцип:** Перед переносом изменений между проектами — сравни содержимое файлов, не перезаписывай вслепую.
**Правило:** hash-сравнение -> diff stat -> выборочный copy. Не Copy-Item без проверки.
**Антипаттерн:** Скопировать CBT-файлы поверх production без diff — потерять production-специфику.
**Признак:** Перед любым Copy-Item есть вывод diff --no-index или сравнение хэшей.

---

## M2. NON-GIT MERGE PROTOCOL
**Принцип:** Когда репозитории не под git, мерж делается файловым сравнением с явным скоупом.
**Правило:** 1) хэш-сравнение одноимённых файлов, 2) diff по различающимся, 3) выборочный перенос только hardening-изменений, 4) пропуск production-специфичных файлов.
**Антипаттерн:** Пытаться сделать git merge в не-git папке; копировать всё подряд.
**Признак:** Чеклист из 4 шагов перед первым копированием.

---

## M3. HARDENING MARKER TRACKING
**Принцип:** При hardening-сессии изменения группируются по маркерам (charge log, metric, provider debug), чтобы при мерже не потерять ни одно.
**Правило:** Grep по ключевым маркерам изменений (log.info, metric_inc, debug log) в CBT; сопоставить с production; перенести отсутствующие.
**Антипаттерн:** «Там вроде всё то же самое» без построчного сравнения.
**Признак:** Перед мержем есть список hardening-маркеров с номерами строк.

---

## M4. SAFE DEFAULT ESCALATION
**Принцип:** Значение по умолчанию для лимита/ограничения должно быть restrictive, не permissive.
**Правило:** Cap по умолчанию != 0 (unlimited). REFERRAL_MONTHLY_CAP default = 20, не 0. Админ может поднять через env.
**Антипаттерн:** Cap=0 как дефолт -> «ой, а мы думали там лимит есть».
**Признак:** Каждый env-управляемый лимит имеет ненулевой разумный default.

---

## M5. METRIC ON ACTUAL STATE CHANGE
**Принцип:** Метрика инкрементится только при первом реальном изменении состояния, не при повторной проверке.
**Правило:** Возвращать флаг newly_credited=True из функции зачисления; metric_inc только если newly_credited.
**Антипаттерн:** metric_inc("invoice_paid") на каждый check_invoice — метрика врёт в N раз.
**Признак:** Функции-мутаторы возвращают признак «было ли изменение» для метрик.

---

## M6. STDERR/STDOUT SEPARATION IN LAUNCHER
**Принцип:** Launcher (cmd) перенаправляет stderr в отдельный файл, не в тот же, что открыт RotatingFileHandler внутри Python.
**Правило:** launcher_err.log для stderr launcher'а; bot_err.log для RotatingFileHandler из кода. Никогда не пересекать.
**Антипаттерн:** `python bot.py >> bot.log 2>&1` когда bot.py сам пишет в bot.log через RotatingFileHandler — PermissionError на Windows.
**Признак:** Launcher пишет stdout и stderr в файлы с префиксом launcher_.

---

## M7. PROVIDER EXCEPTION NARROWING
**Принцип:** except Exception: pass вокруг provider-бухгалтерии заменяется на except Exception as exc: debug-лог с контекстом.
**Правило:** debug-лог содержит provider, key_index, error. pass допустим, но не немой.
**Антипаттерн:** except Exception: pass — инцидент с ключами невидим.
**Признак:** Каждый except в provider-коде пишет хотя бы debug-лог.

---

## M8. ENV-CONFIGURABLE LIMITS WITH DEFAULTS
**Принцип:** Любой лимит/порог — env-переменная с разумным default в коде.
**Правило:** `_env_int("NAME", default)` с осмысленным default; 0 = unlimited (явная семантика).
**Антипаттерн:** Хардкод 20 в коде «потому что так надо»; или default None который ломает.
**Признак:** Каждый лимит читается через _env_int / _env_float с явным default.

---

## M9. CROSS-MODULE METRIC SURFACE
**Принцип:** Метрики (metric_inc, metrics_snapshot) экспортируются через facade (bot.py) чтобы handlers видели их через bind().
**Правило:** Добавил функцию в access.py -> добавил в import-список bot.py -> handlers используют через namespace.
**Антипаттерн:** Вызвать metric_inc в handler'е без экспорта — NameError в runtime.
**Признак:** Grep metric_inc в bot.py показывает export; grep в handlers показывает использование.

---

## M10. INVOICE IDEMPOTENCY MARKER
**Принцип:** Функция зачисления invoice возвращает признак «первый раз или повтор», чтобы caller не считал дважды.
**Правило:** out["newly_credited"] = True при первом зачислении; False при повторе. Caller проверяет флаг.
**Антипаттерн:** metric_inc по факту credited=True — срабатывает при каждой проверке.
**Признак:** Возвращаемый dict содержит newly_credited; caller проверяет `if credited.get("newly_credited")`.

---

## M11. LAUNCHER STDOUT CAPTURE
**Принцип:** Launcher перенаправляет stdout процесса в лог-файл для диагностики.
**Правило:** `python bot.py >> launcher_out.log 2>> launcher_err.log`.
**Антипаттерн:** Запуск без перенаправления — вывод теряется, не видно traceback при краше.
**Признак:** В run_*.cmd есть >> для stdout и 2>> для stderr.

---

## M12. CONFLICT RESOLUTION BY COMMAND LINE MATCH
**Принцип:** При поиске дубликатов процессов фильтровать по содержимому CommandLine (путь проекта), не только по имени exe.
**Правило:** `Where-Object CommandLine -match 'project-name'`.
**Антипаттерн:** `Get-Process python` — находит все Python-процессы в системе.
**Признак:** Фильтр процессов всегда содержит путь или имя проекта.

---

## M13. TOKEN FINGERPRINT WITHOUT SECRET
**Принцип:** Идентифицировать токен по первым 12 символам хэша, никогда не выводить полный ключ.
**Правило:** `(Get-FileHash token).Hash.Substring(0, 12)` — fingerprint для сопоставления.
**Антипаттерн:** Вывести полный токен в лог/консоль «чтобы проверить».
**Признак:** Все упоминания токенов — fingerprint, не содержимое.

---

## M14. PROCESS LINEAGE AUDIT
**Принцип:** Понимать кто кого запустил: ParentProcessId + CreationDate строят дерево процессов.
**Правило:** Для каждого Python-процесса вывести ParentProcessId; если parent — cmd.exe, это launcher.
**Антипаттерн:** Смотреть только на PID, не понимая что это за процесс.
**Признак:** Вывод процессов содержит столбцы Id, ParentProcessId, CreationDate, CommandLine.

---

## M15. DRY-RUN SMOKE WITH TEMP LOCK
**Принцип:** Запускать тестовый экземпляр с временным lock-файлом, чтобы не мешать production.
**Правило:** `$env:BOT_LOCK_PATH = "$env:TEMP\bot_test.lock"` перед smoke-запуском.
**Антипаттерн:** Запустить второй экземпляр на том же lock — Conflict, production сломается.
**Признак:** У каждого smoke-запуска уникальный lock-файл.

---

## M16. TWO-PHASE ERROR LOG SETUP
**Принцип:** Два handler'а: RotatingFileHandler для всех уровней + отдельный RotatingFileHandler только для ERROR.
**Правило:** bot_out.log = INFO+; bot_err.log = ERROR only. Разные maxBytes/backupCount.
**Антипаттерн:** Один файл для всего — ошибки тонут в INFO.
**Признак:** Два RotatingFileHandler в logging.getLogger().handlers; один с .setLevel(ERROR).

---

## M17. BUSY_TIMEOUT + WAL COMBO
**Принцип:** SQLite WAL без busy_timeout = риск database is locked при конкурентном доступе.
**Правило:** `connect(..., timeout=30.0)` + `PRAGMA busy_timeout=30000` вместе с WAL.
**Антипаттерн:** Только WAL, без busy_timeout — при блокировке immediate fail вместо ожидания.
**Признак:** В коде инициализации БД есть и timeout=, и PRAGMA busy_timeout.

---

## M18. LOG LEVEL PER HANDLER
**Принцип:** Разные handler'ы могут иметь разный уровень: stdout=INFO, bot_err.log=ERROR.
**Правило:** После добавления handler'а явно установить .setLevel() если не default.
**Антипаттерн:** Все handler'ы на одном уровне — error-лог забивается INFO.
**Признак:** Для каждого handler'а есть вызов .setLevel() или аргумент level=.

---

## M19. PRE-CAP SIDE-EFFECT GUARD
**Принцип:** Проверка cap/лимита должна быть ДО _ensure() / создания записи, иначе rejected-пользователи оставляют мусор в БД.
**Правило:** check cap -> if rejected return False -> only then _ensure().
**Антипаттерн:** _ensure(new_uid) перед проверкой cap — пустые строки rejected пользователей.
**Признак:** _ensure() вызывается после всех проверок на отказ.

---

## M20. REFERRAL UI TRANSPARENCY
**Принцип:** UI рефералки показывает актуальный лимит из той же функции, что используется для enforcement.
**Правило:** `f"Лимит: до {referral_monthly_cap()} приглашённых в месяц."` — функция одна.
**Антипаттерн:** Хардкод «Приглашай сколько угодно» при наличии cap.
**Признак:** Текст в UI читает лимит из Config-функции, не из константы.

---

## M21. RATE LIMIT WITH IN-MEMORY DICT
**Принцип:** Простейший per-user rate limit — dict[uid] = last_call_time + сравнение с now.
**Правило:** `_invoice_checks: dict[int, float] = {}`; `if now - last < window: reject`.
**Антипаттерн:** Для rate-limit тащить Redis/внешнее хранилище ради одного handler'а.
**Признак:** Модульный dict для rate-limit с monotonic().

---

## M22. monotonic() FOR RATE LIMITS
**Принцип:** Для измерения интервалов использовать time.monotonic(), не time.time().
**Правило:** `now = time.monotonic()` в rate-limit; time.time() — для абсолютных меток.
**Антипаттерн:** time.time() для интервалов — может пойти назад при коррекции часов.
**Признак:** rate-limit использует monotonic(); логи/БД — time().

---

## M23. MERGE SCOPE: ARCHITECTURAL ONLY
**Принцип:** При мерже CBT -> production переносятся архитектурные модули (bot_runtime, bot_ui, bot_pipeline, handlers), но не трогаются production-специфичные (access, voice, generators — если они уже hardening-расходятся).
**Правило:** Выборочный список файлов для Copy-Item; остальные — ручной diff + merge.
**Антипаттерн:** Копировать всю папку CBT поверх production.
**Признак:** Copy-Item с конкретными именами, не *.*.

---

## M24. HASH COMPARISON BEFORE EXPENSIVE DIFF
**Принцип:** Перед построчным diff сделать быстрый хэш-сравнение: равные файлы пропустить.
**Правило:** `Get-FileHash` -> сравнить -> diff только для различающихся.
**Антипаттерн:** `git diff --no-index` по 10 файлам, из которых 8 одинаковы.
**Признак:** Перед diff есть вывод same named source file hashes.

---

## M25. DEBUG LOG DEGRADATION
**Принцип:** Там где был except: pass, ставим except as exc: debug log. Не меняем поведение, но оставляем след.
**Правило:** `logging.getLogger(...).debug("... %s", exc)` — видно при DEBUG, не шумит в PROD.
**Антипаттерн:** Заменить pass на log.error — завалить продакшн-лог на безобидных сбоях bookkeeping.
**Признак:** Каждый бывший except: pass имеет debug-лог.

---

## M26. CHARGE AUDIT TRAIL
**Принцип:** Каждое списание логируется с разбивкой по корзинам: from_free, from_bonus, from_paid.
**Правило:** `log.info("charge uid=%s seconds=%.3f from_free=%.3f from_bonus=%.3f from_paid=%.3f", ...)`.
**Антипаттерн:** Списание без лога — support не может ответить «куда делись минуты».
**Признак:** Grep 'charge uid=' в логе восстанавливает историю списаний.

---

## M27. PREMIUM CHARGE SHORT CIRCUIT
**Принцип:** Premium-пользователи не проходят математику корзин — отдельная ветка с отдельным логом.
**Правило:** `if is_premium: UPDATE used_seconds; log.info("charge ... premium=%s")`.
**Антипаттерн:** Premium идёт через общую математику с нулевыми корзинами — лог неотличим.
**Признак:** В charge_seconds есть ранний return для premium с отдельным log.

---

## M28. INVOICE AUDIT LOG
**Принцип:** Создание счёта и оплата — отдельные audit-логи с invoice_id, uid, amount.
**Правило:** `log.info("invoice_created invoice=%s uid=%s", ...)`; `log.info("invoice_paid invoice=%s uid=%s added=%s", ...)`.
**Антипаттерн:** Только UI-ответ, в логах тишина.
**Признак:** grep invoice_ создаёт полную историю платежей.

---

## M29. REFERRAL AUDIT LOG
**Принцип:** Каждое реферальное начисление логируется с месяцем: кто, кого, месяц, бонус.
**Правило:** `log.info("referral new=%s referrer=%s bonus=%s month=%s", ...)`.
**Антипаттерн:** Без лога — при жалобе «почему не начислилось» нечего смотреть.
**Признак:** grep referral в логе даёт полную историю.

---

## M30. TEST-DRIVEN CAP BEHAVIOR
**Принцип:** Перед реализацией cap/лимита пишется тест на enforced поведение, включая edge: cap исчерпан -> False, юзер не создан.
**Правило:** test_referral_monthly_cap_limits_farming с monkeypatch на env.
**Антипаттерн:** Реализовать cap без теста; «вроде работает».
**Признак:** Для каждого нового лимита есть тест с monkeypatch.setenv и assert False.

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
