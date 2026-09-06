---
name: code-search-ladder
description: "ПЕРЕД поиском по коду, когда непонятно чем искать: «где код, который...», «найди X», «кто вызывает». Лестница: смысл → semble.search; точное имя → agent-lsp; структура/keyword → db-tools FTS. Не для веб-ресёрча (web-research-camoufox) и поиска скиллов (skill-search)."
---
# Лестница поиска: Semble → db-tools → agent-lsp

Layered retrieval: ступень по типу вопроса (ресёрч 19.08, 12 источников). Основа — ядро: core.txt п.2; здесь — цифры и грабли.

## When to use / when NOT to use

ПЕРЕД любым поиском по коду, когда вопрос вслепую или рука тянется к grep/read. НЕ для веб-ресёрча и поиска скиллов.

## Таблица вопрос → ступень

| Вопрос | Ступень | Почему |
|---|---|---|
| «Найди код, который…» (смысл) | **semble.search** | −98% токенов vs grep+read |
| Пересказ без терминов | **db-tools FTS** или терминами дока | 0-1/10 на перефразах, 23/23 на терминах |
| Точное имя / все ссылки | **agent-lsp find_symbol/find_references** | 5-34x дешевле, 0 FP |
| Кто вызывает/импортирует, карта файла | **db-tools** (--symbol/--calls/--imports) | граф из базы |
| Короткий keyword («auth flow») | **db-tools FTS**, не semble | CoREB: ≈0 nDCG |
| «Мы это разбирали?» | findings → wiki → веб | знания прежде кода |

Греп — только после лестницы, для точных строк (греп вслепую = нарушение канона).

## Workflow

1. Классифицируй вопрос → нужная ступень СРАЗУ; не нашлось → шаг вниз: semble → db-tools → agent-lsp → read (только файл, что показала карта/база)
2. Правка — всегда agent-lsp: `blast_radius` ПЕРЕД edit, `get_diagnostics` ПОСЛЕ
3. Файл открывай `find_symbol` (тело + 10 строк), не read целиком

## Success criteria

- Ни одного grep/read вслепую; «где код, который…» закрыт за ≤2 вызова semble
- Правка с blast_radius до и диагностикой после

## Failure modes

- Семантика по короткому keyword → мусор (≈0 nDCG): переформулируй описательно или db-tools
- Греп по привычке → токен-стог, 92-99% хитов — FP: лестница сначала
- Пропуск LSP при правке → сломанные вызовы: blast_radius обязателен
- Ступень не отвечает → сменить ступень (разные инструменты — разные сигналы)

## Gotchas

- «semble → db-tools → agent-lsp» — дефолт для НЕЯСНОГО вопроса: классификация важнее порядка
- .txt/.json/.jsonc вне индекса semble — через db-tools/read
- Индексы: semble кэширует на сессию, db-tools — до пересборки (--refresh)

## Этапы (handoff)

- **Вход из:** `task-cycle`, `db-first-search`, `debug-incident-protocol`
- **Дальше:** `semble`, `db-first-search`, `lsp-code-depth`, `code-review`

## References

- docs/canon/SEMBLE.md, DB-FIRST.md, AGENT-LSP.md
- Ресёрч: findings id=957 (12 источников, layered retrieval)

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
