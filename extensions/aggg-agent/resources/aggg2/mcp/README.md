
Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# mcp — Model Context Protocol серверы

Инструменты-серверы для агентов (opencode и другие), подключённые через MCP.
Папка хранит: серверы, воркеры, конфиги подключения, заметки.

## Сейчас подключено

| Сервер | Что даёт | Инструментов |
|---|---|---|
| `camoufox_research.py` | веб-ресёрч через анти-детект браузер: поиск, чтение страниц, батч-чтение, клики, ввод; **скиллы: skills_search (по каталогам: skills.sh/skillsmp API + sitemap-индексы, браузер-fallback), skill_read (raw GitHub SKILL.md / страница каталога)** | 11 (research, web_search, fetch_page, batch_fetch, extract_links, browser_navigate, browser_click, browser_type, skills_search, skill_read, ping) |
| `db_tools_mcp.py` | поиск по базе чулана: FTS-поиск, символы, граф (imports/calls/deps), статистика, multi-DB, карта кода | 10 (list_dbs, search, symbol, imports, calls, deps, db_stats, index_project, search_all, repo_map) |
| `agent-lsp` (blackwell-systems, MIT) | мост LSP→MCP: диагностика (pyright), find_symbol, find_references, rename preview, type_hierarchy, blast_radius | 65 |
| `code-review-graph` (tirth8205, 29.5k★, MIT) | структурный граф кода (tree-sitter): blast radius по ДИФФУ (impact), dead-code, communities, flows | 30 (MCP) + CLI-команды |

Подключение всех серверов — через `scripts/install/install_mcp.py` (кроссплатформенный,
Linux/macOS/Windows). Он сам выбирает живой конфиг opencode (`opencode.json`
при наличии, иначе `opencode.jsonc`), вычисляет пути от корня чулана и чистит
устаревшие записи при повторных запусках.

## Зависимости (обязательно перед подключением)

MCP-серверы запускаются интерпретатором общего venv воркспейса
(`~/.venvs/aggg2`). Пакеты в `mcp/requirements.txt`:

```
mcp          # FastMCP для обоих python-серверов
camoufox     # анти-детект браузер (ресёрч)
code-review-graph  # граф кода
```

Установка:

```bash
# Linux/macOS
venv/bin/pip install -r mcp/requirements.txt
venv/bin/python -m camoufox fetch        # скачать браузер (один раз)

# Windows (cmd)
venv\Scripts\pip install -r mcp\requirements.txt
venv\Scripts\python -m camoufox fetch
```

`install_mcp.py` перед записью конфигов проверяет зависимости и честно
подсказывает команду, если их нет (серверы без них не стартовали бы).

## Спека MCP 2026-07-28 (stateless) — план миграции

28.07.2026 вышла новая ревизия спеки MCP: stateless-ядро — убраны
handshake/`initialize`, `Mcp-Session-Id`, протокольный `ping`,
`logging/setLevel`, `notifications/roots`; добавлены `_meta`
(protocolVersion/capabilities на каждый запрос), `server/discover`,
`subscriptions/listen`, MRTR, cache-hints у list-ответов. Старая спека
(2025-11-25) работает, окно депрекейшна — минимум 12 месяцев (по плану).

**Аудит наших серверов (14.08.2026, research.db id=490):**

- patchwright-grep (`Mcp-Session-Id`, `notifications/initialized`,
  `initialize`, `logging/setLevel`) по `mcp/*.py` — пусто: мы не
  реализуем протокол руками, всё через SDK. Миграция придёт апгрейдом SDK.
- PyPI: Python SDK **v2 — стабильная ветка** (поддерживает 2026-07-28
  и все прежние ревизии); `pip install mcp` теперь ставит 2.x. В v2
  API переименован: `MCPServer` вместо `mcp.server.fastmcp.FastMCP`.
- Наш пин `mcp==1.29.0` (v1-ветка) — безопасен: точный пин не даёт
  pip подтянуть 2.x случайно; v1.x получает критик-фиксы и живёт на
  ветке v1.x. Официальная рекомендация для остающихся — верхняя граница
  `mcp>=1.28,<2`; наш `==1.29.0` эквивалентен по защите.
- Матрица совместимости спеки: modern-клиент + legacy-сервер = FAIL.
  Наши серверы — локальные stdio, клиент (харнес) обновляется вместе
  с SDK, поэтому сегодня разрыва нет.

**Когда мигрировать на v2:** (1) выйдет харнес/SDK, требующий
2026-07-28 (или клиент перестанет понимать v1); (2) заходим в
stateless-фичи (заголовки-маршрутизация, cache-hints). Не раньше — v1
поддерживается, миграция трогает все 4 сервера (camoufox, db-tools,
agent-lsp-мост, CRG) разом. **Порядок миграции:** поднять пин до
`mcp>=2,<3` в venv → заменить `FastMCP` → `MCPServer` (migration guide:
py.sdk.modelcontextprotocol.io) → прогнать doctor + живой прогон MCP.
Помнить ложный конфликт semgrep `mcp==1.23.3` (при v2 конфликт снимется).

## Как это устроено

1. Сервер: `camoufox_research.py` (FastMCP, stdio).
2. Браузер живёт в отдельном процессе: `camoufox_worker.py` (sync Camoufox,
   headless=True) — вызывается через subprocess из тулов.
3. Подключение пишет `scripts/install/install_mcp.py` в живой конфиг opencode:
   `~/.config/opencode/opencode.json` (Windows) или `opencode.jsonc` (Linux) —
   пути абсолютные, от корня чулана, без хардкода имени пользователя.
   Интерпретатор — общий venv воркспейса `~/.venvs/aggg2`
   (вынесенный из папки, чтобы проект шерился чисто):

```json
{
  "mcp": {
    "camoufox": {
      "type": "local",
      "command": ["/путь/до/venv/bin/python",
                  "/путь/до/чулана/mcp/camoufox_research.py"],
      "enabled": true
    }
  }
}
```

4. Проверка: `opencode mcp list` → сервер должен быть `connected`.

## Грабли, собранные при сборке (проверено экспериментами)
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


- **Готовый `camoufox-mcp` (PyPI) не подошёл**: `headless=False` жёстко в
  конфиге, без дисплея браузер виснет без ошибок.
- **Async-тулы FastMCP + subprocess дедлочат**: в связке mcp 1.x + python
  3.14 любой subprocess внутри async-тула не отвечает (event loop
  блокируется). Проверено: ping/echo без subprocess работают, с subprocess —
  нет.
- **Решение**: тулы СИНХРОННЫЕ (FastMCP сам выполняет их в thread pool) +
  subprocess.run. Работает стабильно.
- **Батч-отправка JSON в stdio путает FastMCP**: запросы надо слать по
  одному, дожидаясь ответа (иначе pydantic ловит `json_invalid, '\n'`).
- Воркер запускается медленно при первом вызове (старт браузера ~2-5с);
  каждый вызов — новый процесс браузера.
- **Глубокий ресёрч (30-50 источников)**: `batch_fetch(urls=[...])` —
  один старт браузера на все URL + кэш страниц (SQLite
  `~/.cache/aggg2-camoufox/cache.db`, TTL сутки) + retry с backoff +
  rate limit 0.4с между переходами. Батч ≥8 URL — параллельно (пул
  потоков, свой браузер на поток — sync API не потокобезопасен):
  10 URL за ~19с вместо ~45с (замер 17.08). Повторный вызов из кэша —
  0.5с.
- **Адаптивный параллелизм по железу** (паттерн Crawlee AutoscaledPool):
  число воркеров `_auto_workers()` — по CPU и свободной RAM
  (~1GB на браузер, резерв 1.5GB): слабый ПК (2-4 ядра, 4-8GB) — 1-2
  воркера, мощный (16+ ядер, 32+GB) — до 8, кап 8. Явный лимит —
  `max_parallel`. Кроссплатформенно (stdlib): Linux — `/proc/meminfo`
  (MemAvailable); Windows — `GlobalMemoryStatusEx` (ullAvailPhys);
  macOS — `vm_stat` (SC_PHYS_PAGES = ВСЯ память, только fallback /2).
- **Per-host bounded concurrency**: сколько бы ни было воркеров, на ОДИН
  домен — не больше 2 параллельных запросов (паттерн proxiesapi/Crawlee
  session limits) + rate limit 0.4с: мощная машина не словит капчу
  собственным рвением; разные домены — до `workers` штук параллельно.
- **Блокировка тяжёлых ресурсов**: при загрузке страниц обрезаются
  image/font/media/stylesheet (паттерн scrapingcentral «block
  unnecessary resources») — тексту не нужны: меньше трафика, памяти
  и времени загрузки.
- **`research(queries=[...])` — норматив «10 источников» одним вызовом**:
  агент планирует 2-5 формулировок запроса, сервер ищет по каждой
  (DDG), дедуплицирует URL и возвращает список со сниппетами (отбор без
  fetch); `fetch_top>0` — сразу читает топ-N. Замер: 10 источников за
  11.6с, повторно из кэша 0.57с. Паттерн gpt-researcher quick_search.
- **Кэш поиска**: результаты `web_search`/`research` кэшируются на сутки
  (таблица searches в cache.db) — повторные запросы мгновенно (паттерн
  Firecrawl, +500%).
- **Живой воркер (`--serve`)**: браузер держится между вызовами —
  сервер запускает воркер один раз и общается с ним по stdin/stdout;
  разовый режим остался как фолбэк при сбое. Замер: fetch_page
  1.34с/0.0с (было ~5-7с), web_search 5.98с (было ~8с).
  Грабля: select + TextIOWrapper дедлочит (буфер вычитал данные, select
  на pipe молчит) — чтение через поток-читатель + queue.Queue.
- **Пагинация DDG** (`web_search(pages=N)`)**: собирает результаты с N
  страниц через submit формы Next. Грабля: GET `&s=` игнорируется DDG,
  работает только POST формы (поля q/s/vqd/dc/kl) — проверено 08.2026
  .
- **Текст статьи** (`fetch_page/batch_fetch(article_only=True)`)**:
  Trafilatura 2.2.0 (стандарт индустрии для LLM-пайплайнов, F1 0.958 по
  ScrapingHub benchmark) — без меню/баннеров; fallback на весь body.
  Опциональная зависимость: `pip install trafilatura`.

## Camoufox на Windows (баги и решения, ресёрч 08.2026)

Проверено по issues daijro/camoufox. У нас Linux — всё ок, на Windows
возможны 3 класса проблем:

| Баг | Симптом | Решение |
|---|---|---|
| Python из MS Store (#282) | fetch «успешен», но exe не найден: Store сандбоксит AppData\Local | Python с **python.org**, не из MS Store |
| headless падает (#614) | exit 0x80000003 (STATUS_BREAKPOINT) на части билдов | **воркер сам пробует fallback**: headless → headed + `windows_hide=True` (окно скрыто) |
| SxS mozglue / нет CRT (#624/#650) | «side-by-side configuration is incorrect» / spawn UNKNOWN на чистых системах | VC++ Redistributable (x64) + установка вне AppData\Local (`CAMOUFOX_INSTALL_DIR`), обновление до v152+ |

**Обновление/диагностика — скрипт `scripts/install/update_camoufox.py`**:
проверяет всё выше (Python-источник, VC++ redist, путь установки) и
обновляет пакет + браузер. На Windows запускать из venv проекта
(`venv\Scripts\python.exe scripts\tools\update_camoufox.py`).
- **Воркер обязан стартовать тем же интерпретатором, что и сервер**
  (`sys.executable`): хардкод `python3` брал системный Python без пакета


---

*Проект каналов https://t.me/aidvizhenie и https://t.me/hilartem. Каждая версия — новая и неповторимая.***
  camoufox, а на Windows его нет и вовсе.
- **Клики**: Playwright click ждёт actionability — на страницах с оверлеями
  (DDG) виснет, а первый матч по тексту может оказаться скрытой рекламой
  (y.js-ссылки). Решение: JS-клик через page.evaluate по настоящей ссылке
  (startsWith http, без y.js).

## Добавить новый MCP-сервер

1. Установи пакет или напиши сервер в этой папке.
2. Допиши команду в `SERVERS` (scripts/install/install_mcp.py) — пути от корня
   чулана, платформенные venv-разрешения.
3. `python3 scripts/install/install_mcp.py` — перезапишет конфиги харнесов.
4. `opencode mcp list` — проверить.

## agent-lsp (LSP → MCP, для кода)

Мост LSP→MCP: диагностика (pyright), find_symbol, find_references, rename
preview, type_hierarchy, blast_radius. 65 инструментов.

### Установка

- **Linux/macOS**: официальный скрипт ставит в `/usr/local/bin/agent-lsp`
  (v0.17.0).
- **Windows**: скрипт установки — только darwin/linux, но релизы GitHub
  содержат `agent-lsp_windows_amd64.zip` и `_arm64.zip` — Windows официально
  поддерживается (issue «fix(windows): daemon mode» закрыт). Скачать из
  Releases, распаковать в `mcp/agent-lsp/`, оттуда его находит
  `install_mcp.py` (или положить на PATH).

Для Python нужен `pyright-langserver` — он ставится ГЛОБАЛЬНО на машину
(`npm i -g pyright`, fallback: pipx / `pip --user`; legacy: venv проекта),
бинарь попадает в PATH и подхватывается конфигом `mcp/agent-lsp/config.json`
(см. ниже). На PEP 668-системах (Ubuntu 24.04+, Fedora) системный pip
заблокирован — поэтому npm/pipx, а не pip в систему.

### Конфиг (формат v0.17.0)

Формат — `{"servers": [{"extensions": [...], "command": [...]}]}` (старый
`{"languages": ...}` исходником не читается). Пример `mcp/agent-lsp/config.json`:

```json
{
  "servers": [
    {
      "extensions": ["py"],
      "command": ["/путь/до/pyright-langserver", "--stdio"]
    }
  ]
}
```

Путь — из `which pyright-langserver` (обычно `~/.local/bin/` или npm prefix
bin; на Windows — `%APPDATA%\npm\pyright-langserver.cmd` или
`~\AppData\Roaming\Python\...`). Файл — локальный для машины (как .env):
пути не переносимы между машинами.

Запуск: `agent-lsp` (auto-detect серверов) или
`agent-lsp --config mcp/agent-lsp/config.json` (только python из нашего venv).
Подключение — через install_mcp.py в живой конфиг opencode
(`opencode.json`/`.jsonc`; проверено: `opencode mcp list` → connected).

Замер на sherpa-voice (2026-08-09, зафиксирован в research.db):
- `get_diagnostics audio.py` — «No errors» (pyright), первая индексация ~30с, дальше тёплый runtime
- `find_symbol transcribe_offline` — тип, позиция `audio.py:356` (2026-08-09, после правок микрофона/тегов; раньше 322:4)
- `find_references transcribe_offline` — 7 ссылок (все использования: импорты, тернарные вызовы), наша база `--calls` нашла только 1 прямой вызов `имя(...)`
- Вывод: agent-lsp — слой «глубины» поверх нашей базы (типы, скоуп, rename), не замена ей

## code-review-graph (граф кода + blast radius по диффу)

Структурный граф кода (tree-sitter): blast radius по ДИФФУ (impact), dead-code,
communities, flows. 30 инструментов MCP + CLI-команды.

Установка: `pip install code-review-graph` в venv проекта (см. раздел
«Зависимости»). Сборка графа: `./venv/bin/code-review-graph build` (для
sherpa-voice: 17 файлов, 215 узлов, 2326 рёбер; на Windows —
`venv\Scripts\code-review-graph.exe build`). Инкрементальный перепарс <200мс,
всё локально (SQLite в `.code-review-graph/`).

Запуск как MCP: `./venv/bin/code-review-graph mcp` (подключён через
install_mcp.py; `opencode mcp list` → connected). Есть и собственный
инсталлятор: `code-review-graph install --platform opencode`.

Замер (2026-08-09):
- `impact --files transcribe.py audio.py --depth 2`: 47 узлов изменено,
  147 затронуто, 12 файлов — дифф-blast radius, которого нет у agent-lsp
- `dead-code`: 3 ЛОЖНЫХ срабатывания (callback/indicator/worker —
  передаются аргументом и в Thread(target=...)); CRG не понимает
  callback-паттерны — проверять agent-lsp/грепом
- `search «теги»`: 0 без эмбеддингов (наш FTS находит) — по смыслу слабее
- Вывод: CRG дополняет agent-lsp (дифф-анализ), не заменяет

Примечание: pip-конфликт — semgrep требует mcp==1.23.3, CRG принёс
mcp 1.29.0; semgrep пока работает, следить при апгрейдах.

Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->
