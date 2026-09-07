---
name: agent-refactor-safety
description: "Рефакторинг/разбиение монолита, вынос модулей, мерж версий, удаление импортов, перенос правок между проектами; «пропала строка/фича» после правки. Не для дебага инцидентов (debug-incident-protocol) и тестов (testing-discipline)."
compatibility: любой язык; рефакторинг, merge, моно-разбиение
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Agent refactor safety: как безопасно править и мержить код

Дистилляция сессии рефакторинга монолита + hardening & merge. Первоисточник: `docs/patterns/GLAV-PATTERNS.md` (блоки L, M.1-3/23-24/44-46/60), `UNIVERSAL-PATTERNS.md`.

## 1. Перед правкой: карта и план

- **MAP BEFORE CUT** — карта (функции/классы/импорты/тесты) до Edit; первые 5-10 действий — чтение, 0 Edit, иначе циклические импорты
- **GREP FIRST, READ SECOND** — Grep «^(async )?def » → Read нужных строк, не 2500 строк ради 5 функций
- **AST BEFORE SURGERY** — ast.parse + FunctionDef/ClassDef = карта модуля до Edit
- **PARALLEL CALLS** — Read+Grep пакетами в одном ответе
- **TOKEN BUDGET** — большие файлы — offset/limit, не целиком

## 2. Порядок рефакторинга (безопасный)

- **SAFE LAYER FIRST** — выносить от наименее зависимого: runtime/конфиг/утилиты (чистые) → handlers с I/O
- **IMPORT-AND-LINT LOOP** — Edit → ruff/compileall → fix → repeat; 2-3 итерации на модуль, не 500 строк разом
- **THREE-STEP VERIFICATION** — ruff → compileall → pytest, порядок не менять
- **ONE SYMBOL AT A TIME** — импорт: удалил → ruff → ошибка → вернул
- **TEST-PRESERVING** — pytest после каждого крупного шага; падает → чинить wiring, не функциональность
- **TWO-PHASE IMPORT CLEANUP** — очевидно лишние → ruff → остаток F401 → убрать → ruff
- **VALUE SLICE ORDER** — core → money → UX → growth (pipeline → billing → history → admin → referrals)
- **LAZY ARCHITECTURE (YAGNI)** — без абстракций до второго потребителя
- **SHARED ROOT > COPY-PASTE** — одна guard в shared функции > 10 патчей в callers
- **ROLLBACK ON FAILURE** — фикс не помог → откат Edit → другой подход
- **RETRY WITH SIMPLIFICATION** — команда упала на синтаксисе → упрости (убери пайплайн, разбей шаги)

## 3. Разбивка монолита: паттерны совместимости

- **COMPATIBILITY FACADE** — старые публичные имена живут: bot.py — точка сборки (re-export'ы, адаптеры); тесты/импорты целы
- **ALIAS RENAMING** — `from bot_ui import edit_html as _edit_html`
- **BIND NAMESPACE** — общий namespace через bind() — нет циклических импортов
- **_LOCAL_NAMES GUARD** — `_LOCAL_NAMES = set(globals())`; bind() пишет только отсутствующее — чужие имена не затирают
- **EXPLICIT WIRING** — `namespace.update({"cmd_history": ...})` явным словарём, не globals().update вслепую
- **STATE ALIAS** — `media._pending = _pending` — ссылка, НЕ копия (state расходится)
- **IDENTITY CHECK** — `bot._pending is media._pending`
- **hasattr GUARD** — тестовый FakeCtx без user_data → `if hasattr(ctx, "user_data")`
- **FACADE EXPORT** — новый публичный символ → import-список facade → namespace; NameError = разрыв цепочки
- **COMPAT OVER PURITY** — facade-функции остаются, даже делегируя, — тесты их monkeypatch'ят
- **TWO-WAY MERGE** — переносить архитектурные модули, не production-специфику (access/voice/generators)

## 4. Merge: diff before copy

- **DIFF BEFORE COPY** — hash-сравнение → diff stat → выборочный copy, не вслепую
- **NON-GIT MERGE PROTOCOL** — 1) hash одноимённых 2) diff различающихся 3) перенос нужного 4) пропуск prod-специфики
- **HARDENING MARKERS** — grep по маркерам (charge log, metric, debug) в CBT ↔ production, перенести отсутствующие
- **HASH FIRST** — Get-FileHash → сравнить → diff только различающихся
- **DIFF SIZE ESTIMATE** — `diff --stat` до мержа
- **PARALLEL DIFF** — diff нескольких файлов одним запуском
- **MERGE SCOPE** — Copy-Item конкретными именами, не `*.*`; exclude конфиги/токены/кастомные фичи
- **POST-MERGE CHECK** — compileall → ruff → pytest в production venv
- **STAGING FIRST** — staging → тесты зелёные → diff → перенос → prod-тесты
- **FULL FLEET RESTART** — перезапуск ВСЕХ экземпляров, не одного

## 5. Защита от регрессий (UNIVERSAL-PATTERNS)

1. **Правка ≠ готово** — после каждой замены перечитай ВСЮ функцию целиком; сверь баланс строк (N → N + added − removed). Пропавшая строка — самый частый регресс.
2. **Правки едят соседнюю строку** — после ЛЮБОЙ SWAP-замены перечитай весь файл (dataset.theme, docstring, basicConfig — трижды за сессию).
3. **Верификация ПОСЛЕ последней правки** — правящий шаг между «проверил» и «готово» = недействительная проверка.
4. **Сценарий пользователя — дословно**, синхронно, без reload/restore/fallback (они маскируют баги).
5. **Аномалия = баг, пока не доказано обратное** — синхронно, чистое storage, curl отданных байт.
6. **Одно состояние — одно место** — инлайн+атрибут+localStorage+класс = расхождение → рефактори.
7. **Минимальная правка + дифф интента** — «должно было измениться» = «изменилось»; лишняя строка = ошибка.
8. **Тесты ≠ запуск** — py_compile/юнит зелёные, запуск падает → smoke реального entrypoint + hasattr-тест.
9. **Мёртвая переменная = потерянная фича** — значение читается и выбрасывается → grep-аудит + e2e.
10. **Одноразовые проверки = вечные блокировки** — «навсегда»-флаг при импорте = вечный бан → lazy-перепроверка по действию.

## Workflow (порядок применения)

Карта → вынос от наименее зависимого (facade с re-export'ами, явный wiring, bind + guard) → цикл Edit→ruff→pytest на каждый шаг → merge diff-before-copy (4 шага, architectural only) → после каждой правки ре-читай весь файл, верификация ПОСЛЕ последней → smoke реального entrypoint + post-merge integrity (compileall+ruff+pytest в prod venv) + перезапуск ВСЕХ экземпляров.

## Чеклист перед коммитом

- [ ] карта (символы + callers + тесты); каждый шаг: ruff → compileall → pytest
- [ ] facade-имена сохранены; bind с _LOCAL_NAMES guard
- [ ] файл перечитан целиком; баланс строк сошёлся; верификация ПОСЛЕ последней правки
- [ ] дифф содержит только заказанное
- [ ] merge: diff before copy; prod-специфика не тронута; после мержа — compileall+ruff+pytest в проде

## Этапы (handoff)

- **Вход из:** `debug-incident-protocol` (после разбора инцидента), `code-review` (проблема в диффе)
- **Дальше:** `code-review` (ревью после переноса), `testing-discipline` (тесты после правок), `fable-judge` (проверка «готово»)

## References

- Первоисточник: `docs/patterns/GLAV-PATTERNS.md` — блоки L (1-54), M.1-3/23-24/44-46/60, ТОП-10 ИИ
- `UNIVERSAL-PATTERNS.md` — «Защита от регрессий», «Оконный режим и редактирование»
- Смежные: `debug-incident-protocol`, `testing-discipline`

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
