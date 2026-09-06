---
name: db-first-search
description: "ПЕРЕД ответом о воркспейсе: «где определён символ/функция», «кто вызывает», «мы это уже разбирали», «находки по теме». Ответ — ТОЛЬКО через базу (search.py/MCP db-tools), не грепом и не по памяти; свежесть (--refresh). Не для веб-ресёрча (web-research-camoufox)."
compatibility: AGGG2.0 (db-tools); принцип «база до ответа» универсален
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# DB-FIRST: искать в базе, а не по памяти

Первоисточник: `docs/canon/DB-FIRST.md`. Вопрос про содержимое AGGG2.0/sherpa-voice → СНАЧАЛА база, потом ответ (ядро: core.txt п.2 — лестница, свежесть, пусто-лестница, греп = нарушение).

## Workflow (порядок применения)

1. **Какая база.** Скиллы/доки/паттерны → `aggg2.db`; код/история ассистента → `sherpa-voice.db`; «мы это смотрели / к чему пришли» → `research.db` (findings); прочитанные внешние скиллы → `skill-knowledge.db` (`--knowledge`, скилл `local-databases`); веб-страницы → `context-internet.db` (`--internet`); ЗНАНИЯ (посты, инструкции, разборы) → `db: wiki` (`search.py -b db/wiki.db` / MCP db: wiki). Не относится → база не нужна.
2. **База есть и свежая.** Нет базы → `python3 db-tools/build.py -r projects/<проект> -o db/<проект>.db`; свежесть → `search.py --refresh -r <корень>`. Устаревшая база = ложный ответ.
3. **Поиск ДО ответа.** `python3 db-tools/search.py "<запрос>"` (или `-b db/<имя>.db`); составные: `"паттерн AND агент"`; `--limit 5`. Найденное — ФАКТЫ, остальное — гипотезы.
4. **Символы через карту.** `search.py --symbol load_telegram`; `--calls`; наследование `--inherits TestCase` / `--inherits =FakeStream`; `--errors`; структура файла: sqlite `SELECT name, line FROM symbols WHERE rel_path='...' AND kind='h2'`.
5. **Найденное — читай файл, не пересказывай.** Открыть, процитировать, ссылаться (`skills/.../SKILL.md`); `[…]` в сниппете — место ответа.
6. **Не нашлось → лестница, не греп:** (1) короче, 2-3 слова без склонений; (2) `--substring`; (3) `search_all.py` / MCP `search_all`; (4) `findings.py search <тема>`; (5) свежесть (`build.py`; полный `--full`). **Wiki/ НЕ грепать** (grep по Wiki — человеку). Всё пусто → честно «не нашёл в базе».

## Находки и выводы (research.db)

- **Записать после ресёрча/эксперимента/разбора:** `python3 db-tools/findings.py add "Тема" --text "вывод: что выбрали, почему, что отвергли, ссылки" --tags "mcp lsp"` (ядро: core.txt п.5). Тема короткая; text — вывод на месяц; tags — 2-4 слова.
- **Искать перед «мы разбирали»:** `findings.py search mcp` / `"вывод AND LSP"`; список: `findings.py list` / `list --tags lsp`.
- **Связи:** `findings.py link add <id> <id> --kind related|extends|contradicts --note "..."`, `related <id>`, `show <id>`, `stats`.
- **Авто-кандидаты из истории сессий:** `db-tools/extract_findings.py` (показ) → `--add 1,3,7`.
- **Метрики:** `search.py --stats` — топ запросов, пустые результаты.

## Грабли

- Запрос `search.py` пишется ДО `--extra-files` (nargs='*' съест его как файл): `search.py "<запрос>" -b ... --refresh -r ... --extra-files ...`
- База — быстрый статический слой; типы/скоуп/ВСЕ ссылки/rename → agent-lsp (`lsp-code-depth`); ревью диффа → CRG (`code-graph-review`)
- Урок: сначала осмотр существующего (scripts/, db-tools/, findings), потом внедрение (поставили chezmoi, не посмотрев `scripts/install_*.py`)

## Чеклист

- [ ] вопрос про содержимое баз → поиск ДО ответа
- [ ] база свежая (--refresh при работе с кодом)
- [ ] найденное — факты; остальное — гипотеза
- [ ] после ресёрча/разбора — findings.py add
- [ ] не нашлось → переформулировал → честно сказал

## When NOT to use

- Общий вопрос, код вне проекта; вопрос про сам поиск (доки); уже искали в сессии и знаем ответ

## Этапы (handoff)

- **Вход из:** любая задача (фаза 1 — база), `task-cycle`
- **Дальше:** `semble`, `code-search-ladder`, `lsp-code-depth`, `skill-search`, `web-research-camoufox`

## References

- Первоисточник: `docs/canon/DB-FIRST.md`
- Смежные: `lsp-code-depth`, `code-graph-review`, `web-research-camoufox`

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
