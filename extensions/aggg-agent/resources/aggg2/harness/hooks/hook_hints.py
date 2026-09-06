#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Константы-подсказки гейтов прошивки (вынесено из hook_gates.py,
docs/canon/FILE-SIZE.md): nudge-тексты, маркеры и regex-паттерны.
Barrel-реэкспорт из hook_gates через __all__ (механическая резка:
код перенесён дословно, импортёры hook_gates не трогаются)."""

import re

__all__ = ['FILE_TIERS', '_WEB_MARKERS', '_WEB_BASH', 'INDEX_HINT', 'RESEARCH_HINT', '_QUARANTINE_BASH', '_DEBUG_BASH', 'SKILLS_HINT', '_SKILLS_MARKERS', '_SKILLS_BASH', '_SKILL_TOOLS', '_LOCAL_DB_MARKERS', '_LOCAL_DB_BASH', '_WIKI_GREP_BLOCK', '_CURL_SITE_BLOCK', '_INTERNAL_LINK_BLOCK', '_COMMIT_MARKERS', '_CRG_MARKERS', '_MIN_SOURCES_NUDGE', '_WINDOWS_CI_MARKERS', '_WINDOWS_SKILL_HINT', '_LSP_QUESTION_MARKERS', '_LSP_HINT', '_SEMBLE_QUESTION_MARKERS', '_SEMBLE_TOOL_MARKERS', '_SEMBLE_BASH', '_SEMBLE_HINT', 'SEMBLE_READ_HINT', '_IMPROVEMENT_MARKERS', '_BATTLE_TEST_HINT', '_DONE_MARKERS', '_QA_MARKERS', '_DOD_HINT', '_ANALYTICS_MARKERS', '_ANALYTICS_RESEARCH_HINT', '_WORKSPACE_MARKERS', '_WORKSPACE_DB_HINT', '_PRODUCT_MARKERS', '_PRODUCT_SKILL_HINT', '_TEST_HINT', '_ERROR_MARKERS', '_REPEAT_ERROR_HINT', '_OUTPUT_SECRETS_BLOCK', '_SIMPLIFY_MARKERS', '_SIMPLIFY_HINT', '_FORGOTTEN_FINDINGS_HINT']

FILE_TIERS = {
    "code": (500, 1000, (".py", ".js", ".ts", ".sh", ".go", ".rs", ".java",
                        ".c", ".cpp", ".css", ".html", ".toml")),
    "docs": (300, 500, (".md",)),
}

_WEB_MARKERS = re.compile(
    r"^(mcp__camoufox__|web_search$|fetch_page$|batch_fetch$|"
    r"browser_navigate$|browser_click$|browser_type$|extract_links$)")

_WEB_BASH = re.compile(
    r"camoufox|web_search|fetch_page|browser_navigate|skills_search\.py")
# Установка сторонних скиллов (npx skills add и аналоги) — nudge
# «карантин-первым»: скачанный скилл → quarantine-skills/, не в рантайм.

INDEX_HINT = (
    "AGGG2.0-гейт: чтение файлов ДО базы — СНАЧАЛА индекс: search.py / "
    "MCP db-tools (search, symbol, calls) / findings.py; карта первой: "
    "repomap.py project (или MCP repo_map); «мы это уже разбирали» дешевле "
    "через базу (DB-FIRST). База не проиндексирована? python3 "
    "db-tools/build.py -r <корень> -o db/<имя>.db"
)

RESEARCH_HINT = (
    "AGGG2.0-гейт «ресёрч-первым»: правишь код ДО ресёрча — для задач "
    "с выбором/неизвестностью СНАЧАЛА быстрые пути: локальная база "
    "(search.py/findings.py) → скиллы (db/skills.db → skills_search.py) "
    "→ потом Camoufox (web_search): МИНИМУМ 10 источников на любую "
    "задачу (справка/факт — 10, решения/выборы — 30-50, docs/canon/CAMOUFOX.md). "
    "«Подумал» без поиска = догадка."
)

# Веб-ресёрч: MCP-тулы Camoufox (mcp__camoufox__web_search и т.п.), CLI-формы
# и шелл-вызовы — маркеры сессии «ресёрч уже был» (гейт «ресёрч-первым»).
_WEB_MARKERS = re.compile(
    r"^(mcp__camoufox__|web_search$|fetch_page$|batch_fetch$|"
    r"browser_navigate$|browser_click$|browser_type$|extract_links$)")
_WEB_BASH = re.compile(
    r"camoufox|web_search|fetch_page|browser_navigate|skills_search\.py")
# Установка сторонних скиллов (npx skills add и аналоги) — nudge
# «карантин-первым»: скачанный скилл → quarantine-skills/, не в рантайм.
_QUARANTINE_BASH = re.compile(
    r"(^|\s)(npx\s+\S*\bskills\b|skills\s+(add|install|update))")
# Дебаг/инцидент: журнал, логи, статус сервиса — nudge «скиллы-первым»
# срабатывает и здесь (грабля 17.08: инцидент чинился без поиска скиллов).
_DEBUG_BASH = re.compile(
    r"journalctl|systemctl|dmesg|\.log|tail .*var|gdb|strace")

# Скиллы: поиск в ЛОКАЛЬНОЙ базе db/skills.db (search.py -b db/skills.db,
# MCP db-tools search db=skills) или загрузка скилла (Skill/skill tool) —
# маркеры сессии «локальный скилл искался» (nudge «скиллы-первым»,
# docs/canon/SKILLS-LOCAL.md). НЕ MCP skills-mcp — удалён, поиск через базу.

SKILLS_HINT = (
    "AGGG2.0-nudge «скиллы-первым»: идёшь в веб/дебаг — СНАЧАЛА локальный "
    "скилл: python3 db-tools/search.py -b db/skills.db <тема> (или MCP "
    "search db=skills, авто-пересборка при рассинхроне). Локальных нет — "
    "ищи ВНЕШНИЕ через skills_search.py (100+ скиллов skills.sh за ~1с, "
    "--top по установкам, --read/--tree читают ЛЮБОЙ файл скилла: "
    "SKILL.md, references/, scripts/; воркфлоу — скилл skill-search). "
    "ДАЖЕ ДЛЯ ДЕБАГА/ИНЦИДЕНТА: сначала чужие скиллы "
    "(skills_search.py \"<симптом>\" — debugging/systemd/incident-скиллы), "
    "потом факты/лог (qa-debugging: Search The Validated Corpus First). "
    "Верни НЕСКОЛЬКО подходящих (3-5+, лучше больше — кандидаты, отбор "
    "за тобой). Нашёл подходящий — ЗАГРУЗИ И СЛЕДУЙ; пусто — зафиксируй "
    "«локальных нет» и иди в веб (docs/canon/SKILLS-LOCAL.md, docs/canon/skills.sh.md)."
)

_SKILLS_MARKERS = re.compile(
    r"^(mcp__db-?tools|search$|symbol$|db_stats$)|db=skills|skills\.db")
_SKILLS_BASH = re.compile(r"db/skills\.db|skills\.db|search\.py.*-b|skills_search\.py")
_SKILL_TOOLS = {"Skill", "skill"}

# Локальные базы знаний (local-databases): skill-knowledge.db и context-internet.db.
# Гейт «local-databases-первым»: ПЕРЕД веб-ресёрчем проверь локальные базы
# (--knowledge, --internet). Маркеры — CLI-команды поиска по базам.
_LOCAL_DB_MARKERS = re.compile(
    r"skills_search\.py\s+.*--(knowledge|internet)|"
    r"--(knowledge|internet)\s+.*skills_search\.py")
_LOCAL_DB_BASH = re.compile(r"--knowledge|--internet")

# Wiki-grep-block: агент НЕ должен грепать Wiki/ по содержимому (только база db=wiki).
# Маркеры: grep/rg/ack с путём Wiki/ (относительный или абсолютный).
_WIKI_GREP_BLOCK = re.compile(
    r"\b(grep|rg|ack|ag)\b.*\bWiki/", re.IGNORECASE)

# curl-блок для сайтов: агент НЕ должен проверять доступность сайтов через curl
# (curl не воспроизводит браузер: TLS-фингерпринт, JS, куки, капчи → ложные 403).
# Используй Camoufox (browser_navigate/fetch_page). Исключения: localhost, 127.0.0.1,
# API-эндпоинты (с /api/ или /v1/ в пути).
_CURL_SITE_BLOCK = re.compile(
    r"\bcurl\b\s+(?:-[a-zA-Z]+\s+)*https?://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)"
    r"(?!.*(?:/api/|/v1/|/v2/))", re.IGNORECASE)

# Внутренние ссылки в продукте: research.db id=N в .md файлах = мёртвая ссылка
# (research.db не входит в архив, ссылка мёртва для получателя).
# Используй "проверено живьём" / "опыт AGGG2.0" без номеров.
_INTERNAL_LINK_BLOCK = re.compile(
    r"research\.db\s+id\s*[:=]?\s*\d+", re.IGNORECASE)

# CRG-гейт перед commit: напоминание использовать code-review-graph
# (detect_changes/get_impact_radius) перед коммитом.
_COMMIT_MARKERS = re.compile(r"\bgit\s+commit\b")
_CRG_MARKERS = re.compile(r"detect_changes|get_impact_radius|build_or_update_graph")

# Норматив 10 источников: считать веб-вызовы, nudge если < 10 перед ответом.
# Маркеры веб-вызовов уже есть (_WEB_MARKERS), нужен счётчик и проверка перед "готово".
_MIN_SOURCES_NUDGE = (
    "ГЕЙТ «норматив 10 источников»: меньше 10 веб-вызовов в сессии — для задач "
    "с выбором/неизвестностью добери до норматива: web_search/fetch_page/batch_fetch "
    "(docs/canon/CAMOUFOX.md). Справка/факт — 10, решение/выбор — 30-50. «Подумал» без поиска = "
    "догадка (core.txt п.1)."
)

# Windows/CI — загрузка скилла windows-encoding-fixes перед кодом.
_WINDOWS_CI_MARKERS = re.compile(
    r"(Windows|CI|GitHub Actions|GitLab CI|Azure DevOps|PowerShell|cmd\.exe|"
    r"cross-platform|кроссплатформ)", re.IGNORECASE)
_WINDOWS_SKILL_HINT = (
    "ГЕЙТ «Windows/CI — скилл первым»: код/CI для Windows — СНАЧАЛА загрузи скилл "
    "windows-encoding-fixes (кодировки cp1251/UTF-8, CRLF vs LF, BOM PowerShell 5.1, "
    "npm.cmd, venv Scripts vs bin, ассеты по платформе). Одна грабля = час дебага "
    "(CLAUDE.md п.12)."
)

# LSP для вопросов по коду: если вопрос про типы/связи/символы → agent-lsp.
_LSP_QUESTION_MARKERS = re.compile(
    r"(\bтипы\b|\btype hierarchy\b|\bscope\b|\bshadowing\b|все ссылки|find references|"
    r"кто вызывает|find callers|blast radius|\bсимвол\b|\bsymbol\b|\brename\b|\bпереименование\b|"
    r"\bдиагностика\b|\bdiagnostics\b)", re.IGNORECASE)
_LSP_HINT = (
    "ГЕЙТ «LSP для кода»: вопрос про типы/связи/символы — используй agent-lsp "
    "(find_symbol, find_references, get_diagnostics, rename_symbol, blast_radius), "
    "не grep/чтение. База (search.py) — быстрый слой, agent-lsp — глубина "
    "(CLAUDE.md п.3, docs/canon/AGENT-LSP.md)."
)

# Смысловой вопрос про код → semble (лестница code-search-ladder).
# «как улучшить/аудит» — задачи-аудиты: смысловые вопросы по коду в них
# тоже идут через semble (грабля 19.08: аудит vpn-gui прошёл мимо semble).
_SEMBLE_QUESTION_MARKERS = re.compile(
    r"(найди код|где код|как обрабатываются|как реализован|как устроен|"
    r"кто отвечает за|какая функция|что делает код|find the code|"
    r"how is .* handled|where is .* implemented|"
    r"как улучшить|что улучшить|аудит|проверь проект|улучшить код|"
    r"разобрать проект|разбор проекта)", re.IGNORECASE)
# Вызов semble: MCP-тул (mcp__semble*, tools.semble.*, execute-обёртка) или
# CLI/execute-форма в bash — маркер сессии «semble использовался».
_SEMBLE_TOOL_MARKERS = re.compile(
    r"(^mcp__semble|^tools\.semble|semble\.search|semble\.find_related)",
    re.IGNORECASE)
_SEMBLE_BASH = re.compile(
    r"semble\.search|semble\.find_related|semble_mcp|tools\.semble")
_SEMBLE_HINT = (
    "ГЕЙТ «лестница поиска»: смысловой вопрос про код — сначала MCP "
    "semble.search (запрос ТЕРМИНАМИ дока, не бытовым пересказом; батл 19.08: "
    "термины 23/23, перефразы 0-1/10), потом db-tools (структура) → agent-lsp "
    "(символы). Точное имя символа — сразу agent-lsp; keyword — db-tools FTS, "
    "не semble (docs/canon/SEMBLE.md, скилл code-search-ladder)."
)

SEMBLE_READ_HINT = (
    "ГЕЙТ «лестница semble»: читаешь/грепаешь код после базы ДО semble — "
    "смысловые вопросы по коду («где реализовано X», аудит/«что улучшить») "
    "идут СНАЧАЛА через MCP semble.search (термины дока), потом db-tools → "
    "agent-lsp. Чтение файлов — только после semble/карты "
    "(docs/canon/SEMBLE.md, скилл code-search-ladder)."
)

# Боевое крещение: если утверждает "улучшил/ускорил/оптимизировал" → дай цифры.
_IMPROVEMENT_MARKERS = re.compile(
    r"\b(улучшил|ускорил|оптимизировал|усилил|повысил|снизил|увеличил|"
    r"improved|optimized|accelerated|enhanced)\b", re.IGNORECASE)
_BATTLE_TEST_HINT = (
    "ГЕЙТ «боевое крещение»: утверждаешь «улучшил/ускорил/оптимизировал» — "
    "дай цифры ДО/ПОСЛЕ в %: «было X → стало Y». Без цифры — мнение, не улучшение "
    "(core.txt п.5б, CLAUDE.md п.13)."
)

# 1. DoD перед "готово": агент говорит "готово" без QA/тестов.
_DONE_MARKERS = re.compile(
    r"\b(готово|done|finished|complete|завершено|выполнено|сделано)\b", re.IGNORECASE)
_QA_MARKERS = re.compile(r"(get_diagnostics|ruff|semgrep|pytest|test)")
_DOD_HINT = (
    "ГЕЙТ «DoD перед готово»: говоришь «готово» — проверь QA: get_diagnostics → "
    "ruff → semgrep → тесты. Без QA = незавершённая правка (core.txt п.9, CLAUDE.md п.4)."
)

# 2. Ресёрч для аналитики: вопрос "как лучше/что выбрать" без веб-вызовов.
_ANALYTICS_MARKERS = re.compile(
    r"\b(как лучше|что выбрать|какой подход|сравни|vs|альтернативы|рекомендуй|"
    r"how to|which|what's better|compare|alternatives)\b", re.IGNORECASE)
_ANALYTICS_RESEARCH_HINT = (
    "ГЕЙТ «ресёрч для аналитики»: вопрос «как лучше/что выбрать» — СНАЧАЛА веб-ресёрч "
    "(Camoufox web_search 3-5 запросов), потом отвечай. «Подумал» без поиска = догадка "
    "(core.txt п.1, CLAUDE.md «Веб-ресёрч — постоянно и сразу»)."
)

# 3. База для воркспейса: вопрос про файлы AGGG2.0 без поиска в базе.
_WORKSPACE_MARKERS = re.compile(
    r"\b(где лежит|где находится|что за файл|покажи код|найди в проекте|"
    r"where is|find in project|show code)\b", re.IGNORECASE)
_WORKSPACE_DB_HINT = (
    "ГЕЙТ «база для воркспейса»: вопрос про файлы AGGG2.0 — СНАЧАЛА база "
    "(search.py / MCP db-tools), потом чтение файлов. Не по памяти (core.txt п.2, docs/canon/DB-FIRST.md)."
)

# 4. Скилл для типа задачи: продуктовая задача без ask-nodumb.
_PRODUCT_MARKERS = re.compile(
    r"\b(продукт|ux|интерфейс|экран|флоу|редизайн|фича|feature|ui|user experience|"
    r"как спроектировать|как реализовать)\b", re.IGNORECASE)
_PRODUCT_SKILL_HINT = (
    "ГЕЙТ «скилл для типа задачи»: продуктовая/UX-задача — загрузи скилл ask-nodumb "
    "ДО проектирования решения (CLAUDE.md п.14, aggg2-mandatory-reads)."
)

# 5. Тесты после правки: изменил .py/.js, но тесты не запустил.
_TEST_HINT = (
    "ГЕЙТ «тесты после правки»: изменил код — запусти тесты (pytest/npm test). "
    "Пропущенные тесты = незавершённая правка (core.txt п.9, CLAUDE.md п.4)."
)

# 6. Повторная ошибка: одна и та же ошибка 2+ раза в сессии.
_ERROR_MARKERS = re.compile(r"(error|exception|traceback|failed|ошибка|сбой)", re.IGNORECASE)
_REPEAT_ERROR_HINT = (
    "ГЕЙТ «повторная ошибка»: одна и та же ошибка 2+ раза — смени метод, получи НОВЫЙ факт "
    "(лог, дамп, изоляция). Не делай ещё одну правку вслепую (CYCLE.md «Цикл ошибок»)."
)

# 7. Секреты в выводе: агент выводит API keys в ответ.
_OUTPUT_SECRETS_BLOCK = (
    "БЛОК: обнаружен потенциальный секрет в выводе. Используй плейсхолдеры "
    "(YOUR_API_KEY, YOUR_PASSWORD и т.п.). Секреты — только плейсхолдеры (core.txt п.6)."
)

# 8. Объяснение сложности: пользователь просит "проще".
_SIMPLIFY_MARKERS = re.compile(
    r"\b(проще|простыми словами|объясни|не понимаю|сложно|elaborate|simplify|"
    r"explain like i'm five|eli5)\b", re.IGNORECASE)
_SIMPLIFY_HINT = (
    "ГЕЙТ «объяснение сложности»: пользователь просит «проще» — используй скилл "
    "explain-fingers (аналогия → шаги → пример → резюме → проверка понимания)."
)

# 9. Забытый findings.py: был ресёрч, но findings.py add не вызывался.
_FORGOTTEN_FINDINGS_HINT = (
    "ГЕЙТ «забытый findings.py»: 10+ веб-вызовов без findings.py add — запиши находки "
    "в research.db: python3 db-tools/findings.py add «тема» --text «вывод» --tags «теги» "
    "(иначе знание теряется после разговора, core.txt п.5)."
)
