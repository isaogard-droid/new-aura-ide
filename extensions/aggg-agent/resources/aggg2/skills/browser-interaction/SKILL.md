---
name: browser-interaction
description: "РУЧНОЕ взаимодействие с сайтом в камуфоксе: «тыкайся», «покликай», «нажми», «введи в форму», «разверни Show more», «выбери из дропдауна», «закрой cookie-баннер», кнопки-не-ссылки, session-режим. Не для поиска источников (web-research-camoufox) и чтения статей."
---
# Ручное «человеческое» взаимодействие с сайтами через камуфокс

Тыкаться как человек: клики, ввод в формы, разворачивание контента, пагинация, вкладки. Покрывает то, что fetch_page/web_search не достают — контент за JS (индустрия: firecrawl-interact 62K, agent-browser 692K).

## When to use / when NOT to use

**Использовать:** контент за кликами (Show more, табы, аккордеоны); ввод в форму; навигация (меню, пагинация, логин-флоу); fetch_page пусто/обрезано/JS-gate; просьба «тыкайся/покликай».

**НЕ использовать:** достаточно fetch_page/article_only (быстрее, кэшируется); есть API/raw-путь (skills.sh /api/search, raw.githubusercontent.com) — быстрые пути СНАЧАЛА; ресёрч (web-research-camoufox) или поиск скиллов (skill-search).

## Workflow (нумерованный, императивный)

1. **Быстрые пути сначала** — база → API → raw → fetch_page; интерактив только когда без кликов не достать (escalation: search → scrape → map → crawl → interact).
2. **Ориентируйся** — `browser_navigate(url)`: текст + первые ссылки. Пусто/«Loading more...» = контент за JS: воркер сам ждёт и скроллит (поллинг + stability), повторный вызов добирает.
3. **Собери ссылки** — `extract_links(url, pattern=...)`: прямые URL вместо кликов (клик не переносит состояние — грабля №1).
4. **Клик по ссылке** — `browser_click(url, target_text="Текст")`; не нашёл → это НЕ ссылка (шаг 5).
5. **Кнопки — не ссылки: селекторы** (по порядку):
   ```
   button:has-text('Текст')
   [role="button"]:has-text('Текст')
   [class*='show-more'] / [class*='ShowMore'] / [data-testid*='...']
   details > summary:has-text('Текст')
   a:has-text('Текст')   # ссылка, но target_text не увидел (вложенность)
   ```
   `:has-text()` — Playwright, работает по любому тегу. Успех = текст в ответе УЖЕ после клика.
6. **Ввод в форму** — `browser_type(url, selector, text)`, селектор по конвенциям:
   ```
   input[type="search"], input[placeholder*='Search'], input[name="q"]
   input[type="text"], input:not([type])
   ```
   Читай результаты; состояние ввода между вызовами НЕ сохраняется.
7. **Состояние не живёт между вызовами** — страница свежая: узнай, куда ведёт действие → иди по прямому URL (`/search?q=`, `?tab=`, `#section`). Состояние поиска живёт в URL.
8. **Разверни контент** — Show more/Read more: клик (шаг 5) → полный текст. Повторный клик сворачивает — не кликай дважды.
9. **Проверь результат** — сравни ответ с предыдущим: изменилось = сработало; нет → другой путь (5/3) или честно «не нашёл» + фиксация (HALT).
10. **Находки в базу** — `findings.py add` (что достали, рабочие селекторы/URL, грабли сайта).

## Session-режим: одна живая вкладка (как человек, паттерн индустрии)

Многошаговый флоу с сохранением состояния (ввёл → кликнул → проскроллил → назад) — session_* вместо browser_*: вкладка НЕ переоткрывается между командами (ресёрч 18.08.2026, 42 источника).

```
session_start(url)            # открыть постоянную вкладку
session_type(selector, text)  # ввод на живой странице
session_click(selector|target_text)  # клик на живой странице
session_scroll(bottom|top|down|up)   # скролл + догрузка lazy
session_links() / session_text()     # читать текущее состояние
session_back()                # стрелка «назад»
session_status()              # URL/заголовок/жива ли вкладка
session_end()                 # закрыть вкладку (обязательно после флоу)
```

- Порядок: session_start → действия → session_end (иначе вкладка висит, память копится)
- session_* — на вкладке сессии; browser_* — независимо (своя страница на команду): можно смешивать
- Инстансы живут 30-45 мин, потом рестарт (yomotherboard): длинная сессия → session_end + новый start
- Долгий ресёрч (1 час+) — browser_*/fetch_page с кэшем; session — для интерактива

## Success criteria

- Действие видно в тексте ответа — не «кликнул и надеюсь»; флоу — прямыми URL
- Кнопки — селекторами (`button:has-text`), не target_text с ошибкой
- Пусто/не вышло → повтор/другой инструмент/честное «не нашёл»

## Failure modes

| Симптом | Что делать |
|---|---|
| `target_text` не находит | кнопка/div → селектор (шаг 5) |
| TimeoutError 15с (клик) / 45с (навигация) | другой селектор; повторный вызов часто проходит; fetch_page/raw |
| Клик «прошёл», текст тот же | селектор попал не туда (скрытый элемент) |
| Пусто после ввода | JS не успел: повтор (воркер ждёт контент) |
| Нужное в iframe/модалке | модалка — клик по её кнопке; iframe — fetch_page; нет — честно |

## Gotchas (проверено на живом прогоне skills.sh, 18.08)

- **Кнопка ≠ ссылка**: `browser_click(target_text=...)` не находит `<button>` — только `selector` (Show more кликнулся `button:has-text('Show more')`)
- **Состояние теряется** между вызовами: спасает extract_links по URL поиска (`/search?q=`) → прямые URL
- **Повторный клик по «Show more» сворачивает** — не кликай дважды
- **fetch_page кэшируется на сутки**: для интерактива — browser_navigate (свежее), fetch_page — для чтения
- «Loading more...» = пагинация: сравнивай списки до/после клика; cookie-баннеры — `button:has-text('Accept')`
- Ссылки `site/x/y/z` в тексте = готовые URL — не кликай вслепую; сомневаешься в селекторе — HTML: placeholder/name/data-testid

## Этапы (handoff)

- **Вход из:** `web-research-camoufox` (fetch_page не достал), `skill-search` (страница за «Show more»), `design-extract` (табы/модалки)
- **Дальше:** `web-research-camoufox`, `db-first-search`, `task-cycle`

## References

- `../../docs/canon/CAMOUFOX.md` — инструменты, JS-страницы, SIFT, кэш; «Интерактивная навигация»
- `../../docs/canon/skills.sh.md` — живой пример: поле ввода, Show more, аудиты
- `../../skills/web-research-camoufox/SKILL.md` — когда браузер для ресёрча
- `../../skills/design-extract/references/browser-snippets.md` — задержки, bot-щиты, domcontentloaded vs networkidle
- Чужие паттерны (контекст): `vercel-labs/agent-browser`, `firecrawl/cli/firecrawl-interact`, `sickn33/agentic-awesome-skills/browser-automation`

<!-- AUTO-GENERATED: doc-links -->
## Связанные (AUTO-GENERATED)

  УПОМИНАЕТСЯ В ДОКАХ (9):
  aggg2-mandatory-reads/SKILL.md
  battle-test/SKILL.md
  db-first-search/SKILL.md
  fable-domain/SKILL.md
  fable-judge/SKILL.md
  fable-loop/SKILL.md
  skill-authoring/SKILL.md
  skill-search/SKILL.md
  skill-search/references/fallbacks.md

Правки только между маркерами — содержимое перегенерируется `doc_links refresh`.

<!-- /AUTO-GENERATED: doc-links -->

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
