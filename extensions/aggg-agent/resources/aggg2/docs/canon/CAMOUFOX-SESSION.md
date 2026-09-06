# Camoufox session — одна живая вкладка «как человек»

Session-режим камуфокс-воркера: непрерывная работа в одной вкладке — ввод, клики, скролл живут между командами. Отличие от `browser_*` тулов (каждая команда переоткрывает страницу): состояние НЕ теряется.
Реализация: `mcp/camoufox_worker.py` (actions `session_*`) + `mcp/camoufox_research.py` (MCP-тулы). Через живой воркер `--serve`.

## Когда использовать
- многошаговые флоу: ввёл → кликнул → развернул → назад → проскроллил (логин, поиск, пагинация, каталоги);
- контент за JS-взаимодействием, где следующий шаг зависит от состояния;
- «поработай как человек в браузере».
**НЕ использовать** для массового чтения (fetch_page/batch_fetch с кэшем быстрее) и разовых кликов (browser_click — дешевле).

## Тулы (10)
| Тул | Что делает |
|---|---|
| `session_start(url="")` | открыть постоянную вкладку (пустую или URL) |
| `session_navigate(url)` | перейти на URL в ТЕКУЩЕЙ вкладке |
| `session_click(selector\|target_text)` | клик (кнопка: `button:has-text('...')`; ссылка: текст) |
| `session_type(selector, text)` | ввод в поле |
| `session_scroll(bottom\|top\|down\|up)` | скролл + догрузка lazy-контента |
| `session_links(max_links=20)` | ссылки текущей страницы |
| `session_text(max_chars=6000)` | текст текущей страницы |
| `session_back()` | «назад» по истории вкладки |
| `session_status()` | URL / заголовок / жива ли вкладка |
| `session_end()` | закрыть вкладку, сбросить состояние |
Все возвращают текст страницы ПОСЛЕ действия (изменилось = сработало).

## Воркфлоу (как человек)
```text
session_start("https://www.skills.sh/")      # открыли сайт
session_type("input[placeholder*='Search']", "sing-box")   # ввели запрос
session_status()                              # URL стал ?q=sing-box — ввод прошёл
session_click(selector="a:has-text('singbox-config')")     # кликнули результат
session_click(selector="button:has-text('Show more')")     # развернули SKILL.md
session_scroll(direction="bottom")            # дочитали до конца
session_back()                                # назад к результатам
session_end()                                 # закрыли вкладку — ОБЯЗАТЕЛЬНО
```
Смешивание с обычными тулами допустимо: `browser_*`/`fetch_page` работают независимо.

## Паттерны индустрии (ресёрч 18.08.2026, 42 источника)
Боевое крещение (18.08.2026): serve-воркер держал браузер **1 час — 60/60 = 100% успех**, медиана 6.4с/команда, RSS без дрейфа (~950–1270 MB), 0 падений (findings id=921).
- **agent-browser (Vercel, 692K):** daemon держит браузер; сессии default (память) / named (изоляция) / persistent (`--session-name` — автосейв cookies+localStorage+sessionStorage, AES-256-GCM); CDP к живому браузеру, tab pinning по target id, `tab_gone` — не действовать на чужую вкладку.
- **Playwright MCP (microsoft):** persistent (default, userDataDir: логин живёт между сессиями) / isolated / extension; `browser_storage_state` save/restore.
- **browser-use (100K+):** BrowserSession + CDPSession + Target, agent-focus, авто-recovery фокуса при детаче; снимки DOM/accessibility tree.
- **Skyvern:** session persistence −70% runtime, −85% auth-фейлов, headless −60% ресурсов.
- **Боевой опыт (сеithx, 24ч):** storage_state.json для auth; CSRF-токены умирают — рефреш 25-35 мин с джиттером; периодические рефреши страниц убивали сессии — отключены.
- **arXiv 2511.19477 (FillApp):** архитектура важнее модели: accessibility tree + селективное зрение; безопасность границами в коде, не рассуждениями LLM.

## Грабли
- **Не забывай `session_end()`** — вкладка висит, память копится.
- **Инстансы живут 30-45 мин**, потом kill+restart (yomotherboard) — разбивай: session_end → session_start, или рестарт воркера.
- **Нужен живой воркер** (`--serve`): из CLI-разового запуска session_* вернёт ошибку.
- **Вкладка может упасть** — `session_status()` покажет `closed: true`; восстановление: session_start заново.
- **Скролл не всегда добирает контент** — после `session_scroll(bottom)` проверь текст; не вырос — «Load more»/«Показать ещё».
- **session_type не жмёт Enter** — часть сайтов ищет по кнопке → session_click.
- **Повторный клик по «Show more» сворачивает** — не кликай дважды.

## Связи
Скилл `skills/browser-interaction/SKILL.md` («Session-режим»); `CAMOUFOX.md` — инструменты, SIFT, кэш; `skills.sh.md` — пример каталога с интерактивом.

*Авторство и разработка: https://t.me/aidvizhenie · https://t.me/hilartem. Версия уникальна — и это не предел.***
