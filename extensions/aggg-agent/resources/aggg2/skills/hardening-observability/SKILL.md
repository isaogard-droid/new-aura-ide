---
name: hardening-observability
description: "Ужесточить лимиты («чтобы нельзя было нафармить», rate limit), метрики/логи/алерты, «database is locked», аудит безопасности. Не для дебага инцидентов (debug-incident-protocol) и рефакторинга (agent-refactor-safety)."
compatibility: сервисы с лимитами, метриками, логами, БД, rate-limit
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Hardening & observability: лимиты, метрики, логи, процессы

Дистилляция сессии hardening & merge. Первоисточник: `docs/patterns/GLAV-PATTERNS.md`, блоки M (4-22, 25-29, 33-43, 47-59), G (51-55), F (45-50).

## 1. Лимиты и caps

- **SAFE DEFAULT ESCALATION** — default restrictive (REFERRAL_MONTHLY_CAP=20, не 0); админ поднимает через env.
- **ENV-CONFIGURABLE LIMITS WITH DEFAULTS** — `_env_int("NAME", default)` с ненулевым default; 0 = unlimited явно.
- **CAP ZERO = UNLIMITED** — `if cap and invited >= cap`; без проверки cap блокирует всех при 0.
- **PRE-CAP SIDE-EFFECT GUARD** — cap ДО _ensure()/INSERT; rejected без мусора в БД.
- **MONTHLY ROTATION KEY** — ключ YYYY-MM; `UNIQUE(referrer_id, month)`; без cron-сбросов.
- **CAP WARNING LOG** — `log.warning("... cap reached referrer=%s month=%s cap=%s")`.
- **RATE LIMIT CHEAPLY AT THE EDGE** — in-memory `dict[uid]=last_call`, N per minute, 0=off, до дорогой логики; без Redis ради одного handler'а.
- **RATE LIMIT ALERT TEXT** — reject с понятным ожиданием («Проверять можно раз в 10 секунд»), не молчаливый return.
- **monotonic() FOR RATE LIMITS** — интервалы `time.monotonic()` (time() может пойти назад); абсолютные метки — time().

## 2. Метрики

- **METRIC ON ACTUAL STATE CHANGE** — мутатор возвращает `newly_credited=True`; metric_inc только при первом изменении (иначе врёт в N раз).
- **INVOICE IDEMPOTENCY MARKER** — `out["newly_credited"]`; caller проверяет флаг.
- **METRIC TABLE: UPSERT PATTERN** — `name TEXT PRIMARY KEY, value INTEGER, updated REAL` + `ON CONFLICT DO UPDATE SET value=value+excluded.value` — атомарно, без race.
- **METRICS SNAPSHOT FUNCTION** — `metrics_snapshot() -> dict[str,int]` одним запросом.
- **METRIC AT POINT OF ACTION** — metric_inc в handler'е, в точке события, не в reporting-функции (забудут вызвать).
- **CACHE HIT METADATA** — кэш-результат логирует `cost=0; isCached=true`.

## 3. Логирование

- **THREE-TIER LOGGING** — INFO=audit (charge/invoice/referral), DEBUG=диагностика (provider), ERROR=алерты (cap, conflict).
- **CHARGE AUDIT TRAIL** — `log.info("charge uid=%s seconds=%.3f from_free=%.3f from_bonus=%.3f from_paid=%.3f")` — grep по uid = история.
- **INVOICE AUDIT LOG** — `invoice_created invoice=%s uid=%s` + `invoice_paid ... added=%s`; **REFERRAL AUDIT LOG** — `referral new=%s referrer=%s bonus=%s month=%s`.
- **PROVIDER EXCEPTION NARROWING** — except: pass → `except Exception as exc: debug-лог` с provider, key_index, error; не немой pass и не log.error (завалит прод).
- **PREMIUM CHARGE SHORT CIRCUIT** — premium ранним return с отдельным логом.
- **LOG LEVEL PER HANDLER** — явный .setLevel(): stdout=INFO, bot_err.log=ERROR.
- **TWO-PHASE ERROR LOG SETUP** — RotatingFileHandler (INFO+) + отдельный (ERROR only), разные maxBytes/backupCount.
- **LAUNCHER STDERR SEPARATION** — launcher пишет в launcher_out/err.log, НЕ в файлы кода (`>> bot.log 2>&1` при своём RotatingFileHandler = PermissionError на Windows).
- **PAYLOAD PREFIX CONVENTION** — `f"{pfx}:{uid}:{int(time.time())}"`.
- **DEBUG LOG DEGRADATION** — где был except: pass → debug-лог (видно при DEBUG, не шумит в PROD).

## 4. SQLite

- **BUSY_TIMEOUT + WAL COMBO** — `connect(timeout=30.0)` + `busy_timeout=30000` + `journal_mode=WAL` — три вместе.
- **ATOMIC CHECK-AND-INCREMENT** — `UPDATE ... SET used=used+1 WHERE used < max`; rowcount 0 = исчерпан.
- **COMPOUND PK AS IDEMPOTENCY GUARD** — `PRIMARY KEY (code, user_id)`.

## 5. Производительность I/O

- **DON'T BLOCK THE EVENT LOOP** — to_thread/worker для sync HTTP/CPU; async-клиенты где уместно (requests.get в async handler на 30s STT = кол).
- **TEMP ARTIFACTS DIE IN FINALLY** — try/finally unlink, missing_ok.
- **CACHE BY STABLE KEY, REBUILD VIEWS** — дорогое (LLM) по PK (entity_id, kind); дешёвое (PDF) пересобирать; второй клик generate = 0 external calls.
- **PAGINATE LISTS; CARRY BACK CONTEXT** — page size fixed; numbered/next-prev; back_page в глубоких видах.
- **SPLIT OUTPUT AT PLATFORM LIMITS SAFELY** — chunk по строкам/абзацам; mark truncated; не рвать escape/tag.

## 6. Безопасность и админ

- **SECRETS NEVER IN GIT / USER MESSAGES** — env/secret store; redact logs; git grep token/password пуст.
- **TOKEN FINGERPRINT WITHOUT SECRET** — первые 12 символов хэша; полный токен никуда.
- **DENY QUIETLY OR SHORT; NEVER LEAK INTERNALS** — non-admin не получает карту системы: silent return или «нет доступа».
- **ADMIN POWER WITH LEAST SURPRISE** — /give id|@user; уведомить цель; статус админу. Тихий grant без audit = плохо.
- **SCOPED CAPABILITIES** — admin surface не светить всем: menu scope / RBAC / feature flags per role.
- **BROADCAST/BULK WITH THROTTLE + REPORT** — segment query; throttle; sent/failed counters. `for user in all: send` без sleep и отчёта = ban.
- **RESOLVE IDENTITY FLEXIBLY, STORE CANONICALLY** — ввод id|@name; хранение stable numeric id (смена username не ломает ссылки).
- **FAIL CLOSED ON AUTH** — auth-отказ закрыт; fail open только на опциональном UX (с notify).

## Workflow (порядок применения)

1. **Лимиты/пороги** (grep констант 20/50/100) → `_env_int("NAME", 20)`, 0=unlimited, default restrictive; cap ДО _ensure()/INSERT, отказ без мутаций + warning-лог.
2. **Rate-limit на границе:** in-memory per-user, monotonic, alert-текст; без Redis. **Метрики:** только на первый change; ON CONFLICT DO UPDATE; metrics_snapshot(); в точке действия.
3. **Логи:** три уровня; except с debug-логом контекста; launcher-логи отдельно. **SQLite:** timeout+busy_timeout+WAL вместе; инкременты одним SQL с WHERE; compound PK.
4. **Производительность:** to_thread для sync; temp в finally; дорогое кэш по стабильному ключу. **Безопасность:** git grep пуст; fingerprint; deny коротко; RBAC/menu scope; bulk с throttle+отчётом.
5. **Retrospective audit:** по каждому пункту — grep-верификация в коде: закрыто/реально открыто, не «всё сделали».

## Чеклист харденинга

- [ ] лимиты env-конфигурируемые, default ненулевой; cap до создания записей; метрики на первый реальный change
- [ ] audit-логи: charge/invoice/referral с id; SQLite: timeout + busy_timeout + WAL; rate-limit на границе, monotonic
- [ ] launcher-логи отдельно; секреты: git grep пуст, fingerprint; retrofit-аудит по каждому пункту плана

## Этапы (handoff)

- **Вход из:** `money-path-safety` (деньги/лимиты), `debug-incident-protocol` (метрика flat), `architecture-simplicity`
- **Дальше:** `testing-discipline` (лимиты/отказы), `code-review`

## References

- Первоисточник: `docs/patterns/GLAV-PATTERNS.md` — M (4-22, 25-29, 33-43, 47-59), G (51-55), F (45-50), ТОП-10 hardening
- Смежные: `money-path-safety` (деньги/лимиты), `debug-incident-protocol` (метрика flat = silent failure)

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
