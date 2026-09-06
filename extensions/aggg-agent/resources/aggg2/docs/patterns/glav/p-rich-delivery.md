
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# P. RICH / NATIVE API / MULTI-FORMAT DELIVERY

Rich Messages, multi-format, fallback

# P. RICH / NATIVE API / MULTI-FORMAT DELIVERY (извлечено из сессии coding split fix + Rich Messages rollout)

---

## P1. CONTENT-TYPE-SPECIFIC RENDERING STRATEGY
**Принцип:** Разные типы контента (coding, voice, article) получают разные форматы вывода: coding → Rich + PDF, voice → Rich с авто-кратким, article → Rich. Не one-size-fits-all.
**Правило:** `if kind == "coding": chunks = _split_coding_body(body)` — отдельная ветка рендеринга на каждый kind. Каждый kind сам решает: Rich, HTML-fallback, PDF.
**Антипаттерн:** Единый `send_message(text)` для всех типов — coding режется на 12 сообщений.
**Признак:** В on_generate есть if/elif по kind с разной логикой доставки.

---

## P2. LINE-AWARE SPLITTING FOR FORMATTED TEXT
**Принцип:** При разбивке форматированного текста (HTML/Markdown) резать по целым строкам (`splitlines(keepends=True)`), а не по байтам. Не обрывать теги посередине.
**Правило:** Разбить на строки → наполнять first, пока сумма длин <= лимит → остальное в second. Граница всегда между строками.
**Антипаттерн:** `body[:TG_MSG]` — обрыв `<b>` или `<code>` посередине → битый рендеринг в Telegram.
**Признак:** Split-функция использует splitlines(keepends=True); граница по символу `\n`.

---

## P3. EXTRACT SPLIT AS PURE FUNCTION
**Принцип:** Логика разбивки выносится в чистую функцию `_split_coding_body(body) -> list[str]`, тестируемую без Telegram API.
**Правило:** Никаких `update`, `context`, `bot.send_message` внутри split-функции. Только строки на вход, список строк на выход.
**Антипаттерн:** Split-логика в середине handler'а — нельзя протестировать изолированно.
**Признак:** split-функция импортируется из helpers/генераторов напрямую в тест, без моков.

---

## P4. NATIVE API CALL WHEN LIBRARY LACKS SUPPORT
**Принцип:** Если библиотека (python-telegram-bot) не поддерживает новый метод API (sendRichMessage) — вызывать Bot API напрямую через HTTP. Не ждать обновления библиотеки.
**Правило:** httpx.AsyncClient → POST `f"https://api.telegram.org/bot{token}/{method}"` → json payload. Отдельный модуль (bot_rich.py).
**Антипаттерн:** «Библиотека не поддерживает → невозможно» — отказ от фичи на месяцы.
**Признак:** В проекте есть модуль, который делает HTTP-запросы к Bot API в обход python-telegram-bot.

---

## P5. TRY-NEW → FALLBACK-OLD PATTERN
**Принцип:** При доставке: сначала новый формат (Rich), при любой ошибке — старый проверенный (HTML-сообщения). Никакого ухудшения UX при отказе нового.
**Правило:** `try: rich_send(...); return` → `except Exception: log.warning(...); send_regular(...)`.
**Антипаттерн:** Заменить старый формат новым без fallback — при ошибке API пользователь не видит ничего.
**Признак:** Каждый вызов rich_send обёрнут в try/except с fallback на обычную отправку.

---

## P6. NEW DELIVERY CHANNEL AS SEPARATE MODULE
**Принцип:** Новый канал доставки (Rich Messages) живёт в отдельном модуле (bot_rich.py), не смешивается с существующими handler'ами и рендерером.
**Правило:** `bot_rich.py`: только Rich-форматирование и HTTP-отправка. Никаких `Update`, `Context`, бизнес-логики.
**Антипаттерн:** Добавить Rich-логику в bot_ui.py или handlers/generation.py — раздувание существующих модулей.
**Признак:** bot_rich.py не импортирует telegram.ext, только httpx + html.

---

## P7. PRE-SEND PAYLOAD VALIDATION
**Принцип:** Перед отправкой нового формата проверить, что payload укладывается в лимиты API (max bytes, max blocks).
**Правило:** `assert len(rich_body.encode("utf-8")) <= RICH_MAX_BYTES` в тестах и/или перед sendRichMessage.
**Антипаттерн:** Отправить и получить 400 Bad Request на проде.
**Признак:** Тесты на Rich включают assert на размер payload.

---

## P8. REAL API SMOKE TEST + CLEANUP
**Принцип:** Перед деплоем нового API-вызова: отправить тестовое сообщение в реальный чат → проверить ok=true → удалить. Не оставлять тестовый мусор.
**Правило:** `sendRichMessage(...)` → assert `result["ok"]` → `deleteMessage(message_id)`. Всё в одном smoke-скрипте.
**Антипаттерн:** «Должно работать, проверим на проде» — баг обнаруживается пользователем.
**Признак:** Smoke-проверка создания и удаления тестового сообщения перед деплоем.

---

## P9. NEW API RESEARCH PROTOCOL
**Принцип:** При появлении нового API: 1) читаем документацию, 2) проверяем версию библиотеки, 3) endpoint-тест с несуществующим chat_id (method not found vs bad request), 4) реальный smoke.
**Правило:** `getMe` для проверки токена → `sendRichMessage` с `chat_id=0` для проверки метода → реальный chat_id для проверки доставки.
**Антипаттерн:** Сразу в реальный чат без проверки что метод вообще распознаётся API.
**Признак:** Последовательность из 3-4 проверочных шагов перед первым реальным сообщением.

---

## P10. FEATURE FLAG PER CONTENT TYPE
**Принцип:** Новый формат (Rich) включается по kind, а не глобально: coding=Rich, article=Rich, voice=Rich+summary. Разные правила на каждый тип.
**Правило:** В функции доставки: `if kind == "coding": ... elif kind == "article": ... elif kind == "voice": ...`. Каждый сам решает.
**Антипаттерн:** Глобальный флаг «использовать Rich» — article получает Rich-блоки, которые не нужны, или наоборот.
**Признак:** В on_generate или эквиваленте есть таблица kind → формат.

---

## P11. INCREMENTAL ROLLOUT OF NEW FORMAT
**Принцип:** Новый формат доставки вводится поэтапно: coding → summary/article → transcription → history. Каждый этап — отдельный PR/деплой с проверкой.
**Правило:** Один kind за раз. Добавил coding Rich → проверил на проде → потом article → потом transcription.
**Антипаттерн:** Включить Rich для всех kind сразу → лавина багов, непонятно где сломалось.
**Признак:** В истории коммитов: отдельный коммит на каждый kind.

---

## P12. LAUNCHER ENVIRONMENT HYGIENE
**Принцип:** Launcher (.cmd/.ps1) должен чистить PYTHONPATH от путей, которых больше нет в проекте. Устаревшие пути ведут к неожиданным импортам.
**Правило:** Проверять PYTHONPATH в launcher'ах при каждом изменении структуры проекта. Удалять пути к несуществующим директориям.
**Антипаттерн:** PYTHONPATH содержит путь к удалённому проекту — import хаотично резолвится.
**Признак:** Каждый путь в PYTHONPATH launcher'а указывает на существующую директорию.

---

## P13. LLM OUTPUT COMPACTNESS INSTRUCTION
**Принцип:** В промпт модели добавляется явная инструкция про размер вывода: «Сделай результат компактным: ориентир — 1–2 сообщения Telegram». Модель сама ограничивает объём.
**Правило:** Инструкция в системном промпте, не в пост-обработке. «НЕ вываливай все паттерны. Выбери только 5–10 реально задетых.»
**Антипаттерн:** Пост-фактум обрезать ответ модели — теряется структура; лучше чтобы модель сама выдала компактный ответ.
**Признак:** В промптах есть явные ограничения на размер вывода в терминах платформы.

---

## P14. FALLBACK PRESERVES ALL UI ELEMENTS
**Принцип:** При fallback с Rich на обычный HTML все UI-элементы (кнопки MD, PDF, навигация) должны сохраниться. Пользователь не замечает переключения формата.
**Правило:** И Rich, и fallback получают один и тот же reply_markup. Кнопки не зависят от формата доставки.
**Антипаттерн:** Rich с кнопками, fallback без — пользователь теряет MD/PDF при сбое Rich.
**Признак:** reply_markup формируется ДО ветвления Rich/fallback и передаётся в оба пути.

---

## P15. CUSTOM EMOJI SKIP INSIDE CODE BLOCKS
**Принцип:** `apply_custom_emojis()` не должен заменять emoji внутри `<pre>`, `<code>`, backtick-блоков. Код должен остаться нетронутым.
**Правило:** Перед заменой emoji разбить текст на code-блоки и plain-текст; заменять только в plain-частях.
**Антипаттерн:** Глобальная замена — `<tg-emoji>` внутри code block ломает код.
**Признак:** В тесте: `<pre>🔥 code</pre>` → emoji НЕ заменён; `<h2>🔥 Title</h2>` → заменён.

---

## P16. HISTORY VIEW USES SAME RENDERING AS FRESH
**Принцип:** При открытии записи из истории — формат должен совпадать с тем, что было при первом показе. Rich при создании → Rich в истории.
**Правило:** `_history_rich_view()` строит Rich из сохранённых clean + summary; `on_history_nav` вызывает rich_send с fallback.
**Антипаттерн:** Fresh = Rich, History = plain HTML — пользователь видит деградацию при повторном открытии.
**Признак:** Функция history view возвращает тот же Rich-формат (или fallback с кнопками), что и fresh.

---

## P17. INLINE MENU GRID LAYOUT
**Принцип:** Inline-меню из 4+ пунктов организуется сеткой 2×N с логическими парами, а не вертикальным списком в 1 колонку.
**Правило:** Семантические пары в одной строке: «Авто-краткое / Контекст», «Баланс / Купить», «История / Промокод». 2 кнопки в строке.
**Антипаттерн:** 6 кнопок в 1 столбец — меню занимает пол-экрана.
**Признак:** `assert [len(row) for row in markup] == [2, 2, 2]` — тест проверяет раскладку.

---

## P18. REPLY MARKUP CAPTURE IN TEST FAKES
**Принцип:** FakeMessage в тестах должен сохранять `reply_markup`, чтобы можно было assert на раскладку кнопок, а не только на текст.
**Правило:** `self.reply_markup = kw.get("reply_markup")` в FakeMessage.reply_text. Тест читает markup.inline_keyboard.
**Антипаттерн:** Проверять только текст сообщения — кнопки могут быть сломаны, тест зелёный.
**Признак:** FakeMessage имеет поле reply_markup; хотя бы один тест проверяет структуру клавиатуры.

---

## P19. EXPORT CALLBACK BACKWARD COMPATIBILITY
**Принцип:** При добавлении нового контекста (fresh) в callback — regex должен принимать и старый (номер страницы), и новый (fresh) форматы.
**Правило:** `r"^hx:(md|pdf):\d+:(?:\d+|fresh)$"` — `(?:\d+|fresh)` принимает оба варианта.
**Антипаттерн:** Новый regex только под fresh — история с номерами страниц перестаёт работать.
**Признак:** Тест проверяет что regex матчит и `hx:md:123:0`, и `hx:md:123:fresh`.

---

## P20. RICH DELIVERY FOR HISTORY WITH NESTED FALLBACK
**Принцип:** В истории Rich-доставка имеет два уровня fallback: 1) если Rich не собрался (нет inline-краткого) → обычный HTML, 2) если Rich API rejected → обычный HTML поверх.
**Правило:** `if rich_view: try: rich_send(...) except Exception: reply_text(html_body(...))` else: `reply_text(...)`.
**Антипаттерн:** Rich упал → пустой экран или traceback пользователю.
**Признак:** В on_history_nav два вложенных try/except с fallback на каждом уровне.



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
