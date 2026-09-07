"""Пути, константы и конфигурация для skills_search."""
import os
import sys

API = "https://www.skills.sh/api/search"
RAW = "https://raw.githubusercontent.com"

_HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import skills_catalog  # sitemap-каталоги docs/canon/SKILLS-WEB.md
except Exception:  # noqa: S110,BLE001 — без каталогов живём (API-only)
    skills_catalog = None


def _get_cache_dir():
    """Кроссплатформенная директория для кэша.

    Windows: %LOCALAPPDATA%/aggg2-hook или %APPDATA%/aggg2-hook
    macOS: ~/Library/Caches/aggg2-hook
    Linux: $XDG_CACHE_HOME/aggg2-hook или ~/.cache/aggg2-hook
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = os.path.expanduser("~")
        return os.path.join(base, "aggg2-hook")
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Caches", "aggg2-hook")
    else:
        base = os.environ.get("XDG_CACHE_HOME")
        if not base:
            base = os.path.join(os.path.expanduser("~"), ".cache")
        return os.path.join(base, "aggg2-hook")


CACHE_DIR_BASE = _get_cache_dir()
os.makedirs(CACHE_DIR_BASE, exist_ok=True)

CACHE_DIR = os.path.join(CACHE_DIR_BASE, "camoufox")
CACHE_DB = os.path.join(CACHE_DIR, "cache.db")
TTL = 86400  # сутки

TTL_BY_SOURCE = {
    "skills.sh": 3600,
    "skillsmp": 21600,
    "sitemap": 86400,
}

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_TIMEOUT = 300  # 5 минут


def _get_github_token():
    """Получить GitHub токен: env → gh CLI (keyring)."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        import subprocess
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:  # noqa: BLE001 — gh CLI недоступен
        pass
    return None


GITHUB_TOKEN = _get_github_token()
GITHUB_HAS_TOKEN = GITHUB_TOKEN is not None

CIRCUIT_BREAKER_CONFIG = {
    "github": {
        "threshold": 10 if GITHUB_HAS_TOKEN else 5,
        "timeout": 1800 if GITHUB_HAS_TOKEN else 3600,
    },
    "default": {"threshold": 3, "timeout": 300},
}

MIRROR_DIR = os.path.join(CACHE_DIR_BASE, "skills")

AGGG2_ROOT = os.environ.get("AGGG2_ROOT",
                            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))))

EVENTS_DIR = os.path.join(CACHE_DIR_BASE, "events")
os.makedirs(EVENTS_DIR, exist_ok=True)
EVENTS_FILE = os.path.join(EVENTS_DIR, "events-skills.jsonl")

SKILL_KNOWLEDGE_DB = os.path.join(AGGG2_ROOT, "db", "skill-knowledge.db")
CONTEXT_INTERNET_DB = os.path.join(AGGG2_ROOT, "db", "context-internet.db")
