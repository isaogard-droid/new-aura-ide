---
name: testing-discipline
description: "Добавить/починить тесты, «что покрыто», «готово ли», воспроизвести баг тестом, лимиты/rate-limit/отказы, тесты в реальную БД/сеть. Не для стратегии дебага (debug-incident-protocol) и рефакторинга."
compatibility: pytest, jest и аналоги; применимо к любому языку
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Testing discipline: тесты как спека и определение «готово»

Первоисточники: `docs/patterns/GLAV-PATTERNS.md` (блоки D 31-37, O.8, M.30-32, N.22-23, P.7/18), `UNIVERSAL-PATTERNS.md`.

## 1. Изоляция и структура

1. **NEVER TOUCH PROD STORE IN TESTS** — throwaway storage: env path override + temp file + fresh import. После suite prod row count неизменен.
2. **FRESH IMPORT FOR MODULE-LEVEL SIDE EFFECTS** — import-time connect/migrate ломает изоляцию: `sys.modules.pop` + importlib на каждый тест.
3. **UNIT DOMAIN FIRST, HANDLER WIRING SECOND** — бизнес-правила без фреймворка; хендлеры — тонкий клей с fakes. Domain suite зелёный offline за <2s.
4. **FAKE THE EDGES, NOT THE CORE** — мокай Telegram/HTTP/API; НЕ мокай свою бизнес-логику (mock grant_minutes → тест зелёный, prod пустой).

## 2. Имена и границы

- **TEST NAMES ARE THE SPEC** — `test_referral_no_self`, `test_crypto_idempotent` — имя = правило; `pytest --collect-only` = чеклист продукта. НЕ test_1.
- **ASSERT THE BOUNDARY CASES** — на каждую функцию: happy + edge + abuse (free→0, paid edge, self-ref, double credit, empty username, overflow).
- **WRITE THE ABUSE CASE WITH THE GROWTH CASE** — рефералка/промо — с анти-фрод тестом в том же PR.

## 3. Специфичные тесты

- **MONEY PATH**: double-submit → +X не +2X; ошибка провайдера → баланс не меняется; reject → `assert not user_exists(...)`.
- **LIMITS (cap)**: тест до реализации: cap исчерпан → False; `monkeypatch.setenv`; `assert cap and invited >= cap`.
- **RATE LIMIT**: два вызова → второй заблокирован без внешнего API: mock API → `assert len(calls) <= 1`.
- **UI: PRESENCE + ROUTING** — test_X_exists + test_X_routes_to_Y; FakeMessage сохраняет reply_markup → assert раскладки.
- **USER-FACING COPY AS REGRESSION** — `assert "E-transcriber" in WELCOME`: изменение копии = breaking change в CI.
- **PAYLOAD VALIDATION** — `assert len(body.encode("utf-8")) <= PLATFORM_LIMIT` до деплоя.
- **NAVIGATION REGRESSION** — fresh-back возвращает на контент, не в список.
- **ENV DEFAULTS** — monkeypatch env; константы бонуса/лимита проверяются во всех поверхностях (БД/UI/share).

## 4. DoD — «готово» (4 пункта)

1. **Parse** — `python -m compileall -q` (SyntaxError мгновенно)
2. **Import** — модуль импортируется без ошибок
3. **Test** — pytest зелёный (домен offline; интеграция с fakes)
4. **One live process** — реальный запуск entrypoint, лог OK, единственный инстанс

Три-шаговая верификация: **ruff → compileall → pytest** (не пропуская). Ошибки: import (F401/F821) → syntax (ParserError) → runtime (NameError).

## Workflow

1. Изолируй хранилище → 2. определи слой (domain юнит / handler клей) → 3. тесты от правил продукта (имя = спека) → 4. границы happy+edge+abuse → 5. специфичные (money/limits/rate-limit/UI/копия/payload) → 6. ruff → compileall → pytest → 7. DoD: parse → import → test → live.

## Чеклист

- [ ] тесты не пишут в prod storage (temp path + fresh import)
- [ ] domain-логика без фреймворка
- [ ] на каждое правило именованный тест (имя = спека)
- [ ] границы: happy + edge + abuse
- [ ] money: double-submit, error-no-debit, no-side-effects-on-reject
- [ ] лимиты и rate-limit покрыты (monkeypatch, двойной вызов)
- [ ] UI: presence + routing; копия: assert на обещания
- [ ] DoD: parse + import + test + live process

## When NOT to use

- Инцидент/дебаг — `debug-incident-protocol`. Деньги/лимиты глубже — `money-path-safety`, `hardening-observability`.

## Этапы (handoff)

- **Вход из:** `lsp-code-depth`/`agent-refactor-safety`, `hardening-observability`, `task-cycle` (фаза 5)
- **Дальше:** `code-review`, `fable-judge`

## References

- `docs/patterns/GLAV-PATTERNS.md` (блоки D/O/M/N/P, ТОП-20); `UNIVERSAL-PATTERNS.md` («Тесты ≠ запуск»)
- Смежные: `money-path-safety`, `ux-navigation-context`

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
