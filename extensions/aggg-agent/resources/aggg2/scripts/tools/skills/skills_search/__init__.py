"""skills_search — поиск и чтение ВНЕШНИХ скиллов (skills.sh).

Быстрый CLI вместо веб-ресёрча. Обёртка над skills.sh /api/search + чтение
SKILL.md через raw.githubusercontent.com. Без зависимостей (urllib), без браузера.

Запуск:
    python3 -m skills_search <запрос> [--limit N] [--top]   # поиск
    python3 -m skills_search --read <owner/repo/skill>      # прочитать SKILL.md
    python3 -m skills_search --tree <owner/repo/skill>      # список файлов
    python3 -m skills_search --knowledge <запрос>           # поиск по базе знаний
    python3 -m skills_search --internet <запрос>            # поиск по интернет-контексту
    python3 -m skills_search --stats                        # статистика баз

Почему не MCP (ресёрч 17.08.2026, 25 источников):
- Perplexity выкинул MCP ради REST+CLI: до 72% контекст-вэйст на схемах;
- nerveband/cli-best-practices: JSON по умолчанию, без интерактива;
- mastra-ai/skills-api: skills.sh как API — наш путь.

Кэш на сутки (как camoufox-воркер): повторный запрос — мгновенно.
"""

from .cache import cache_init
from .events import log_event
from .internet import get_internet_stats, save_to_internet, search_internet
from .knowledge import get_knowledge_stats, save_skill_to_knowledge, search_knowledge
from .reader import check_maturity, list_skill_files, read_skill
from .search import SkillsSearchUnavailable, search, search_multi

__all__ = [
    "cache_init",
    "log_event",
    "save_to_internet",
    "search_internet",
    "get_internet_stats",
    "save_skill_to_knowledge",
    "search_knowledge",
    "get_knowledge_stats",
    "read_skill",
    "list_skill_files",
    "check_maturity",
    "search",
    "search_multi",
    "SkillsSearchUnavailable",
]
