---
name: ux-navigation-context
description: "Вернуться «назад» после действия, «открылся не тот экран», переработать меню/кнопки (много команд в /help), навигация ломается при повторном открытии. Не для обещаний (product-promise-contract), форматов, денег."
compatibility: боты, веб, десктоп — любой UI с навигацией и состояниями
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# UX navigation & context: состояния, возвраты, кнопки

Первоисточник: `docs/patterns/GLAV-PATTERNS.md`, блок N (1-43) + B.19-20.

## 1. Состояния и контекст (ядро)

1. **VIEW STATE SEPARATION** — fresh (результат) и history (запись) — РАЗНЫЕ состояния: свой обратный маршрут каждому («‹ К результату» vs «‹ К списку»); один маршрут = юзер внезапно в списке.
2. **CONTEXT FLAG PROPAGATION** — контекст (fresh/stale, edit/read, preview/export) флагом через ВСЕ слои: UI → actions → generators → callbacks.
3. **ROUTE NAMESPACE BY SCENARIO** — каждый сценарий возврата — свой префикс (back-to-result, back-from-edit, back-to-list); маршруты не пересекаются.
4. **NAVIGATION TARGET COMPUTED ONCE** — `backTarget = isFresh ? "fresh" : page` — одна переменная, N использований.
5. **CONTEXT PRESERVATION IN DEEP ACTIONS** — дочерние действия несут контекст родителя: `context = isFresh ? "fresh" : pageNumber`.
6. **FULL CONTEXT CHAIN THROUGH ALL ACTIONS** — кнопки действий несут полный контекст возврата, не только id.
7. **NON-DESTRUCTIVE NAVIGATION FIX** — фикс = новые маршруты + handler'ы, НЕ изменение схемы данных (не добавлять isFresh в БД ради возврата).

## 2. Структура меню и кнопки

- **COMMAND CONSOLIDATION HUB** — разрозненные команды → одна primary-кнопка → inline-меню; всё в 2 тапа.
- **TWO-TIER NAVIGATION** — keyboard = разделы (3-5), inline = действия внутри (2-6); уровни не смешивать.
- **BUTTON STYLE BY SEMANTICS** — primary=навигация, success=покупка, danger=разрушительное. Не эстетика.
- **EMOJI DISCIPLINE** — кнопки: ТОЛЬКО текст; эмодзи — в read-only контенте; callback data без эмодзи; grep по label'ам = 0.
- **CALLBACK DELEGATION, NOT DUPLICATION** — новые точки входа делегируют существующим handler'ам через adapter (<5 строк routing + adapter, бизнес-логики ноль).
- **NAME FOR FUNCTION, NOT NOVELTY** — лейбл отвечает «что внутри?»; новый юзер угадывает <3с.
- **POST-REFINEMENT LABEL AUDIT** — перед деплоем: grep по лейблам → убрать эмодзи → обновить тесты.
- **INLINE MENU GRID LAYOUT** — 4+ пунктов = сетка 2×N семантическими парами; тест: `assert [len(row) for row in markup] == [2, 2, 2]`.
- **CONSISTENT NAMING ACROSS ALL SURFACES** — один режим называется одинаково везде (настройки/результат/история/кнопка).

## 3. Контент и состояния в UI

- **ENTRY EXISTENCE GUARD** — `entry = getEntry(id); if not entry: return error(...)` до любого `entry.field`.
- **IMMEDIATE FEEDBACK + CONTENT UPDATE** — 1) подтверждение (toast/alert), 2) обновление содержимого.
- **TEMPORARY STATUS LIFECYCLE** — «загружаю…» удаляется перед финалом.
- **UI CLEANUP EXCEPTION IS SAFE** — `catch {}` допустим ТОЛЬКО для UI-cleanup, не бизнес-логики.
- **EMPTY CONTENT HIDES SECTION** — `if content:`; пустая секция без заголовка.
- **VISIBLE TRUNCATION MARKER** — обрезал → маркер «…показано не всё».
- **FIRST-VIEW vs REVISIT-VIEW** — первый показ: полные кнопки; повторный: компактный + навигация по списку (isFirstView/isFresh).
- **MUTATE IN PLACE vs CREATE NEW** — просмотр → edit in place; новая генерация/экспорт → create new.
- **EXPLICIT SOURCE LABELS** — auto-generated vs manually-requested: разные иконки; тег: auto/manual/none.
- **MODEL OUTPUT HEADER STRIP** — заголовок модели, который UI уже показывает, вырезать.
- **CONTEXT-DEPENDENT LABEL FOR SAME ACTION** — одна функция, label параметром.
- **PAGINATED OUTPUT PRESERVES CONTEXT** — каждый фрагмент (не только первый/последний) несёт back-кнопку с контекстом.
- **BEHAVIORAL TOGGLE DESCRIPTIONS** — «ВКЛ: система автоматически добавляет X», не «Режим X: ВКЛ».
- **ROUTE PATTERN CO-EVOLUTION** — контекст в маршруты → regex обновлён: `r"^action:\w+:\d+:(?:\d+|fresh)$"`.
- **TYPE WIDENING** — `page: int | string`; **SIGNATURE EVOLUTION** — новый параметр = default со старым поведением.

## 4. Регистрация и тесты

- **ROUTE REGISTRATION IN TWO PLACES** — роутер (regex → handler) + карта handler'ов (id → модуль.функция); grep имени = 2.
- **COMPLETE HANDLER REGISTRATION** — файл handler'а, роутер, карта, экспорт; grep = 3-4.
- **UI ENTRY POINT TESTS** — test_X_exists + test_X_routes_to_Y на каждое UI-добавление.
- **NAVIGATION REGRESSION TEST** — создать → fresh-back → assert контент, не список.
- **PARAMETERIZED UI TESTS** — поведение от параметра → тест на каждый значимый вариант.
- **REPLY MARKUP CAPTURE IN TEST FAKES** — FakeMessage сохраняет reply_markup → assert раскладки.

## Workflow

1. Состояния: fresh/history — разные маршруты → 2. контекст-флаг через все слои, `backTarget` один раз → 3. дочерние действия и пагинация несут back-контекст → 4. меню: hub, 2 уровня, без эмодзи, цвет по семантике → 5. делегирование (<5 строк adapter) → 6. регистрация: роутер + карта + экспорт, regex старый+новый (`(?:\d+|fresh)$`), grep 2-4 → 7. состояния UI: статусы убраны, пустые секции скрыты, маркер, entry guard → 8. тесты: presence+routing, fresh-back, раскладка.

## Чеклист ревью навигации

- [ ] fresh и history — разные обратные маршруты
- [ ] контекст-флаг не теряется ни в одном слое
- [ ] backTarget вычислен один раз
- [ ] кнопки без эмодзи; цвет по семантике
- [ ] каждый callback делегирует handler'у
- [ ] каждый фрагмент пагинации несёт back-контекст
- [ ] новый маршрут в 2+ местах + тест presence/routing
- [ ] пустые секции скрыты; обрезание с маркером
- [ ] «загружаю» удаляются перед финалом

## Этапы (handoff)

- **Вход из:** `ask-nodumb` (флоу), `product-promise-contract`
- **Дальше:** `system-feedback`, `content-delivery-format`, `testing-discipline`

## References

- Первоисточник: `docs/patterns/GLAV-PATTERNS.md` (блок N 1-43, B.19-20, ТОП-10 UX)
- Смежные: `product-promise-contract`, `content-delivery-format`, `testing-discipline`

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
