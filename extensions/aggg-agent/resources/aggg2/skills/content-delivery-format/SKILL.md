---
name: content-delivery-format
description: "Доставить результат в форматах (текст/rich/PDF/HTML), разбить длинный ответ, fallback для нового формата, внедрить новый API-метод. Не для обещаний (product-promise-contract), навигации (ux-navigation-context), денег (money-path-safety)."
compatibility: боты/мессенджеры, веб — везде, где контент доставляется в нескольких форматах
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Content delivery & format: рендеринг, разбивка, fallback, rollout

Дистилляция сессии Rich Messages & multi-format delivery. Первоисточник: `docs/patterns/GLAV-PATTERNS.md`, блок P (1-20).

## Workflow (порядок применения)

1. **Типы контента** — каждый kind (coding/voice/article/transcription) — свой формат: `if kind == "coding": ... elif kind == "voice": ...` (CONTENT-TYPE-SPECIFIC RENDERING)
2. **Разбивка — чистая функция** — `_split_coding_body(body) -> list[str]` без API; резать по строкам (`splitlines(keepends=True)`), не по байтам — иначе обрыв `<b>`/`<code>`
3. **Fallback** — `try: rich_send(...); return` → `except: log.warning; send_regular(...)`; reply_markup ДО ветвления — fallback сохраняет ВСЕ кнопки
4. **Лимиты до отправки** — `assert len(body.encode("utf-8")) <= PLATFORM_LIMIT` в тестах и перед отправкой; не узнавать из 400 Bad Request
5. **Новый API по протоколу** — 1) docs, 2) версия библиотеки, 3) endpoint-тест (getMe → метод с chat_id=0), 4) smoke + cleanup (deleteMessage); библиотека не умеет → HTTP напрямую к API отдельным модулем
6. **Включай по kind, поэтапно** — флаг per content type; rollout: coding → summary → article → history; PR на каждый kind
7. **Edge-случаи** — emoji заменяются ТОЛЬКО вне `<pre>`/`<code>`/backtick; история рендерится как fresh (с вложенным fallback)
8. **Промпт модели** — инструкция компактности в системном промпте («1-2 сообщения», «выбери 5-10 паттернов»), не пост-обработка

## Паттерны (кратко)

1. CONTENT-TYPE-SPECIFIC RENDERING — ветка на каждый kind
2. LINE-AWARE SPLITTING — по строкам, теги не рвутся
3. SPLIT AS PURE FUNCTION — без моков
4. TRY-NEW → FALLBACK-OLD — UX не ухудшается
5. NATIVE API CALL — httpx.AsyncClient → POST /bot{token}/{method}, без библиотеки
6. NEW API RESEARCH PROTOCOL — docs → lib version → endpoint test → smoke → cleanup
7. FEATURE FLAG PER CONTENT TYPE — по kind, не глобально
8. INCREMENTAL ROLLOUT — один kind за раз
9. CUSTOM EMOJI SKIP INSIDE CODE BLOCKS — только plain
10. HISTORY = SAME RENDERING AS FRESH — Rich в истории = Rich при создании (или fallback с кнопками)
11. PRE-SEND PAYLOAD VALIDATION — assert до отправки
12. REAL API SMOKE + CLEANUP — ok=true → deleteMessage
13. FALLBACK PRESERVES UI — reply_markup до ветвления
14. LLM COMPACTNESS INSTRUCTION — в промпте, не пост-обработке
15. RICH HISTORY WITH NESTED FALLBACK — Rich не собрался → HTML; API rejected → HTML
16. LAUNCHER ENVIRONMENT HYGIENE — PYTHONPATH без удалённых директорий
17. PAYLOAD PREFIX CONVENTION — `f"{pfx}:{uid}:{int(time.time())}"` для платежей

## Чеклист

- [ ] каждый kind — своя ветка рендеринга; split по строкам
- [ ] fallback сохраняет все кнопки; payload в лимитах (assert)
- [ ] новый API исследован протоколом (docs→test→smoke); rollout по kind
- [ ] emoji не в code-блоках; история как fresh (с fallback)

## When NOT to use

- Обещания/копия — `product-promise-contract`; кнопки/меню — `ux-navigation-context`; деньги/лимиты — `money-path-safety`

## Этапы (handoff)

- **Вход из:** `product-promise-contract`, `ux-navigation-context`
- **Дальше:** `testing-discipline`, `system-feedback`

## References

- Первоисточник: `docs/patterns/GLAV-PATTERNS.md` — блок P (1-20), ТОП-10 Rich
- Смежные: `product-promise-contract`, `ux-navigation-context`, `testing-discipline`

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
