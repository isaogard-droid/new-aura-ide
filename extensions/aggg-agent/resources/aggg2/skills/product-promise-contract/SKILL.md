---
name: product-promise-contract
description: "Условия продукта («сколько даёте?», «а если скидка?»), маркетинговые тексты/обещания, кнопка или скрыть команду в /help, UI не обещает больше кода. Не для навигации (ux-navigation-context) и денег (money-path-safety)."
compatibility: боты, веб, десктоп — любой UI с пользовательским текстом
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Product promise contract: обещания, копия, безопасный вывод, коммуникация

Дистилляция из боевых сессий (UX fix, promo & value ops). Первоисточник: `docs/patterns/GLAV-PATTERNS.md`, блоки B (11-20), J (67-70).

## Workflow (8 шагов → паттерны ниже)

1. **Собери обещания продукта** из UI/маркетинга («скидка 50%», «мгновенно», «бесплатно») — каждое обязано иметь код + тест; нет кода → убрать или реализовать (п.1).
2. **Правила продукта — в именованные тесты** (`test_free_spent_first`). Спека живёт в тестах, не в чате (п.2).
3. **Математика:** формула сказана вслух в UI/доке один раз; нет «бонус минут» без renew/bucket/expiry (п.3).
4. **Воронка:** promo не скрывает Buy; can_buy после promo == true; trust-гейты (username/email/KYC) в начале handler'ов (п.4-5).
5. **Вывод:** один render-путь на все поверхности; user-ввод escape'ится ДО своего markup (п.6-7).
6. **Сообщения:** юзеру коротко («Не вышло»), себе stack/ids/provider; статусы «гружу…» удаляются перед финалом; 2-4 primary кнопки (п.8-10).
7. **Копия:** пользовательские тексты покрыты тестами (`assert "..." in WELCOME`); длины ≤ лимитов до деплоя (п.11-12).
8. **Ответ юзеру:** первая строка = что сделано, последняя = что нажать; один уточняющий вопрос на развилке денег/абуза (J).

## Паттерны (кратко)

1. **PROMISE ONLY WHAT CODE DOES** — нет «скидка 50%» без coupon engine.
2. **PRODUCT RULES AS NAMED TESTS** — спека в test_*.py; тесты = понимание продукта.
3. **EXPLICIT PRODUCT MATH** — формула вслух: «30+50=80 первый день; дальше 30/мес».
4. **SEPARATE PROMO FROM PURCHASE IN UX** — can_buy после promo == true.
5. **TRUST BOUNDARY GATES EARLY** — require_X() в начале handler'ов; без X нет side-effects в storage.
6. **ONE RENDER PATH FOR ALL SURFACES** — один конвертер: raw → escape → format → send.
7. **ESCAPE USER INPUT, THEN ADD YOUR MARKUP** — никогда HTML mode на сыром user text.
8. **MINIMAL USER ERRORS, RICH INTERNAL LOGS** — prod UI без имён вендоров/путей/токенов.
9. **STATUS LIFECYCLE** — «гружу…»: создал → обновил → УДАЛИЛ → финал.
10. **KEYBOARD/PRIMARY ACTIONS > HIDDEN COMMANDS** — 2-4 primary buttons.
11. **USER-FACING COPY AS REGRESSION TESTS** — изменение копии = breaking change в CI.
12. **PRE-DEPLOY CONTENT VALIDATION** — `len(WELCOME)` ≤ лимиты платформы, сбой при превышении.
13. **OBSERVABILITY IS PART OF THE FEATURE** — лог/метрика с фичей в том же PR.

## Коммуникация с пользователем (J)

- **LEAD WITH ACTION, END WITH NEXT ACTION** — первая строка = что сделано, последняя = что нажать.
- **ONE CRITICAL QUESTION BEATS WRONG BUILD** — развилка денег/абуза → один вопрос, не угадывать.
- **SMOKE STEP IN THE HANDOFF** — «готово» заканчивается 1-3 шагами проверки юзером.
- **KEEP A PASSPORT OF THE SYSTEM** — секреты, admin ids, product rules, paths — в одном известном месте.
- **CODE/COMMITS CLEAN; CHAT CAN BE ROUGH** — в git профессионально, в чате по-человечески.

## Чеклист

- [ ] каждое число/обещание в UI имеет код + тест; продукт-правила — именованные тесты
- [ ] user-ввод escape'ится до своего markup; статус-сообщения удаляются перед финалом
- [ ] форматтер один на все поверхности; копия покрыта тестами; тексты в лимитах
- [ ] ответ заканчивается actionable next step

## When NOT to use

- Навигация/возвраты/кнопки/меню — `ux-navigation-context`; доставка контента (Rich/PDF/fallback) — `content-delivery-format`; балансы/промокоды/лимиты — `money-path-safety`.

## Этапы (handoff)

- **Вход из:** `ask-nodumb`, `system-feedback` · **Дальше:** `ux-navigation-context`, `content-delivery-format`, `testing-discipline`

## References

- `docs/patterns/GLAV-PATTERNS.md` — блоки B (11-20), J (67-70), ТОП-20

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
