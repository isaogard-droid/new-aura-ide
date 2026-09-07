
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# M31-M60. ПАТТЕРНЫ ХАРДЕНИНГА И АУДИТА (часть 2)

M31-M60 из сессии hardening + merge

## M31. ORPHAN PREVENTION TEST
**Принцип:** Тест проверяет что rejected-операция не создаёт побочных записей в БД.
**Правило:** `assert not acc.user_exists(NEW + 1)` после rejected apply_referral.
**Антипаттерн:** Не проверять отсутствие side-effects при отказе.
**Признак:** В тесте отказа есть assert not user_exists.

---

## M32. RATE LIMIT UNIT TEST
**Принцип:** Тест на rate-limit делает два вызова подряд и проверяет что второй был заблокирован без внешнего API.
**Правило:** mock API → два await handler → assert len(calls) <= 1 + assert alert text.
**Антипаттерн:** Rate limit без теста — «работает, пока не сломается».
**Признак:** Для каждого rate limit есть тест с двойным вызовом.

---

## M33. PRODUCTION PROCESS PRESERVATION
**Принцип:** Никогда не останавливать production PID при операциях с CBT/тестовым окружением.
**Правило:** Stop-Process только для подтверждённых CBT PID; production PID всегда явно исключается.
**Антипаттерн:** `Get-Process python | Stop-Process` — убить всё, включая production.
**Признак:** Перед любым Stop-Process есть вывод production PID для исключения.

---

## M34. LOG TIMESTAMP FILTER AFTER RESTART
**Принцип:** После перезапуска читать только строки лога после времени старта нового процесса.
**Правило:** `Get-Content лога | Where-Object { $_ -match '2026-07-24 10:53:3' }` — проверка свежих строк.
**Антипаттерн:** Прочитать весь лог, принять старый Conflict за текущую проблему.
**Признак:** При проверке лога после рестарта есть фильтр по времени.

---

## M35. DEDICATED LAUNCHER LOG
**Принцип:** Launcher пишет stdout/stderr в отдельные файлы launcher_out.log / launcher_err.log, не пересекаясь с логами приложения.
**Правило:** `python bot.py >> launcher_out.log 2>> launcher_err.log`.
**Антипаттерн:** Перенаправление в bot_out.log / bot_err.log — конфликт с RotatingFileHandler.
**Признак:** Имена launcher-логов начинаются с launcher_.

---

## M36. COMPILEALL AS FAST SMOKE
**Принцип:** `python -m compileall -q` ловит синтаксические ошибки мгновенно, до pytest.
**Правило:** compileall сразу после Edit, до ruff и pytest.
**Антипаттерн:** Сразу запустить pytest — 5 секунд ждать ради SyntaxError на первой строке.
**Признак:** compileall в цепочке проверок до pytest.

---

## M37. METRIC TABLE: UPSERT PATTERN
**Принцип:** Таблица метрик: `name TEXT PRIMARY KEY, value INTEGER, updated REAL` + `INSERT ... ON CONFLICT DO UPDATE SET value=value+excluded.value`.
**Правило:** atomic upsert без SELECT + UPDATE race.
**Антипаттерн:** SELECT value; value += 1; UPDATE — race condition под нагрузкой.
**Признак:** SQL для метрик использует ON CONFLICT DO UPDATE.

---

## M38. METRICS SNAPSHOT FUNCTION
**Принцип:** Для отладки и /admin — функция возвращает полный снимок метрик как dict.
**Правило:** `metrics_snapshot() -> dict[str, int]` — читает все rows.
**Антипаттерн:** SELECT * FROM metrics руками в каждом месте.
**Признак:** Есть функция snapshot/metrics_snapshot с однострочным запросом.

---
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


## M39. CAP ZERO = UNLIMITED SEMANTICS
**Принцип:** Если env-переменная не задана и default=0, считать это «без ограничений», но явно.
**Правило:** `if cap and invited and int(invited["invited"]) >= cap` — cap=0 пропускает проверку.
**Антипаттерн:** `if invited >= cap` без проверки cap>0 — 0 блокирует всех.
**Признак:** Проверка cap содержит `if cap and ...`.

---

## M40. MONTHLY ROTATION KEY FOR LIMITS
**Принцип:** Месячные лимиты ключуются по YYYY-MM строке.
**Правило:** `month = datetime.now().strftime("%Y-%m")` + таблица с UNIQUE(referrer_id, month).
**Антипаттерн:** Сброс по числу месяца или cron — рассинхрон.
**Признак:** Ключ содержит YYYY-MM; таблица имеет уникальный constraint по id+month.

---

## M41. CAP WARNING LOG
**Принцип:** При достижении cap писать warning-лог с контекстом.
**Правило:** `log.warning("referral cap reached referrer=%s month=%s cap=%s", ...)`.
**Антипаттерн:** Молча отказывать — админ не знает что лимит душит рост.
**Признак:** Рядом с return False по cap есть log.warning.

---

## M42. METRIC AT POINT OF ACTION
**Принцип:** metric_inc вызывается прямо в handler'е, в точке действия, не в отдельной reporting-функции.
**Правило:** metric_inc("buy_page_opened") в cmd_buy и on_go_buy.
**Антипаттерн:** Одна функция report_buy_page_opened() которую забыли вызвать.
**Признак:** metric_inc разбросаны по handler'ам в точках событий.

---

## M43. PAYLOAD PREFIX CONVENTION
**Принцип:** Invoice payload содержит структурированный префикс для маршрутизации.
**Правило:** `f"{pfx}:{uid}:{int(time.time())}"` — префикс, uid, timestamp.
**Антипаттерн:** payload = str(uid) — при нескольких типах платежей не отличить.
**Признак:** payload содержит префикс (bundle5, sub, etc.) и uid.

---

## M44. MERGE SAFETY: SKIP PRODUCTION-SPECIFIC FILES
**Принцип:** При мерже НЕ копировать файлы, которые в production расходятся с CBT по production-специфике (конфиги, токены, кастомные фичи).
**Правило:** Составить список exclude; перед копированием сверить diff.
**Антипаттерн:** `Copy-Item *` — затёрли production-конфиг.
**Признак:** Явный exclude-список или белый список файлов для копирования.

---

## M45. DIFF SIZE ESTIMATE BEFORE SURGERY
**Принцип:** Перед мержем оценить размер изменений: diff --stat показывает строки.
**Правило:** `git diff --no-index --stat` -> оценка scope (76 insertions, 6 deletions).
**Антипаттерн:** Начать мерж без понимания объёма изменений.
**Признак:** Перед мержем есть diff --stat или сводка изменений по файлам.

---

## M46. PARALLEL DIFF COMPUTATION
**Принцип:** Diff по нескольким файлам запускать параллельно для ускорения.
**Правило:** Цикл по файлам с diff --no-index, результаты в одном выводе.
**Антипаттерн:** Запускать diff по одному файлу, ждать, потом следующий.
**Признак:** В одном Execute несколько diff-команд.

---

## M47. ENV OVERRIDE WITH NON-ZERO DEFAULT
**Принцип:** Функция чтения env должна позволять default != 0 и != None.
**Правило:** `_env_int("NAME", 20)` — 20 это реальный дефолт, не заглушка.
**Антипаттерн:** Все default'ы = 0 или "" — неясно, задано или нет.
**Признак:** Вызовы _env_int имеют разумные ненулевые default'ы.

---

## M48. UPGRADE PATH: CONNECTION TIMEOUT + BUSY TIMEOUT
**Принцип:** При hardening БД: connect timeout + PRAGMA busy_timeout + PRAGMA journal_mode=WAL — три настройки вместе.
**Правило:** timeout=30.0 в connect(); busy_timeout=30000; journal_mode=WAL.
**Антипаттерн:** Только WAL без busy_timeout; или busy_timeout без connect timeout.
**Признак:** Инициализация БД содержит три строки: timeout, busy_timeout, journal_mode.

---

## M49. PROVIDER DEBUG LOG WITH KEY INDEX
**Принцип:** Debug-лог ошибки провайдера содержит provider name + key index (i+1) + error.
**Правило:** `logging.getLogger(...).debug("... provider=%s key_index=%s error=%s", provider, i+1, exc)`.
**Антипаттерн:** Просто `pass` или `print(e)` без контекста.
**Признак:** Каждый debug-лог в voice.py содержит provider и key_index.

---

## M50. FACADE EXPORT FOR NEW SYMBOLS
**Принцип:** Любая новая публичная функция из access.py добавляется в import-список bot.py.
**Правило:** Добавил def metric_inc -> добавил metric_inc в `from access import (..., metric_inc, ...)`.
**Антипаттерн:** Функция есть в access, но не экспортирована в bot -> handlers не видят.
**Признак:** Grep имени функции в bot.py находит её в import-списке.

---

## M51. HANDLER BIND REQUIRES FACADE EXPORT
**Принцип:** Handlers получают функции через bind(namespace), а namespace заполняется из bot.py.
**Правило:** Если handler вызывает metric_inc, проверь что: 1) она в access.py, 2) в import bot.py, 3) в namespace.
**Антипаттерн:** Вызов metric_inc в handler'е без проверки цепочки access -> bot -> bind.
**Признак:** NameError в handler = разрыв в цепочке access -> bot -> bind.

---

## M52. SKILL ACTIVATION FOR MERGE/SURGERY
**Принцип:** Перед сложным мержем активировать skill ponytail для минималистичного подхода.
**Правило:** Skill ponytail в начале мерж-сессии.
**Антипаттерн:** Начать копировать файлы без стратегии.
**Признак:** В начале сессии есть Skill ponytail activated.

---

## M53. REJECT CREATES NO SIDE EFFECTS
**Принцип:** Если операция вернула False/отказ — в БД не должно появиться новых строк.
**Правило:** _ensure() и INSERT только после всех проверок. Отказ -> return без мутаций.
**Антипаттерн:** _ensure() до проверки cap — юзер создан, но бонус не начислен.
**Признак:** Тест проверяет not user_exists после отказа.

---

## M54. UI TEXT FROM CONFIG, NOT CONSTANT
**Принцип:** Текст в UI должен читать лимит из той же функции, что и enforcement, чтобы не расходиться.
**Правило:** `f"Лимит: до {referral_monthly_cap()} ..."` — вызов функции, не хардкод.
**Антипаттерн:** «Приглашай сколько угодно» в UI + cap=20 в коде.
**Признак:** UI-текст формируется с вызовом config-функции.

---

## M55. PROCESS FILTER BY PROJECT PATH
**Принцип:** При поиске процесса фильтровать CommandLine по подстроке пути проекта.
**Правило:** `Where-Object CommandLine -match 'tg-voice-bot'` а не `-match 'python'`.
**Антипаттерн:** Get-Process python* — сотни процессов, неясно какой наш.
**Признак:** Фильтр процессов содержит имя папки проекта.

---

## M56. RESTART WITH VERIFICATION WINDOW
**Принцип:** После перезапуска процесса — выждать Start-Sleep, проверить лог на Application started И на отсутствие Conflict/ERROR.
**Правило:** Start-Sleep 12-15s; проверить свежие строки лога; убедиться что нет Conflict.
**Антипаттерн:** Запустил и пошёл дальше — не знаешь жив ли.
**Признак:** После Start-Process есть Sleep + проверка лога.

---

## M57. HARDENING RETROSPECTIVE AUDIT
**Принцип:** После hardening-сессии прогнать аудит: какие пункты реально закрыты, какие остались.
**Правило:** Пройти по каждому пункту исходного плана; grep по коду для верификации; отметить закрыто/открыто.
**Антипаттерн:** «Всё сделали» без построчной проверки.
**Признак:** В конце сессии есть список «закрыто / реально открыто».

---

## M58. THREE-TIER LOGGING: INFO/AUDIT, DEBUG/DIAG, ERROR/ALERT
**Принцип:** Три уровня: INFO для audit trail (charge, invoice, referral), DEBUG для диагностики (provider bookkeeping), ERROR для алертов (cap reached, conflict).
**Правило:** log.info — бизнес-события; log.debug — техническая диагностика; log.warning/log.error — проблемы.
**Антипаттерн:** Всё в INFO или всё в ERROR — нет градации.
**Признак:** В коде есть info, debug и warning на разных типах событий.

---

## M59. RATE LIMIT ALERT TEXT
**Принцип:** При срабатывании rate limit показывать пользователю понятное сообщение с временем ожидания.
**Правило:** `await q.answer("Проверять можно раз в 10 секунд.", show_alert=True)`.
**Антипаттерн:** Молчаливый return — юзер думает что кнопка не работает.
**Признак:** rate-limit reject содержит user-visible alert/text.

---

## M60. POST-MERGE INTEGRITY CHECK
**Принцип:** После мержа прогнать compileall + ruff + pytest на production-копии.
**Правило:** merge -> compileall -> ruff -> pytest в production venv.
**Антипаттерн:** Скопировал файлы -> «работает наверное».
**Признак:** После мержа три зелёных проверки в production venv.


---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
