#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Гейты прошивки (вынесено из aggg2_prompt_hook.py, docs/canon/FILE-SIZE.md):
nudge-состояние по сессиям (база-первым/веб-первым), скилл-роутер,
файловые лимиты. Хук импортирует функции и константы обратно."""
import json
import os
import re
import sys
from contextlib import suppress
from pathlib import Path

from hook_hints import (
    _ANALYTICS_MARKERS,
    _ANALYTICS_RESEARCH_HINT,
    _BATTLE_TEST_HINT,
    _COMMIT_MARKERS,
    _CRG_MARKERS,
    _CURL_SITE_BLOCK,
    _DEBUG_BASH,  # noqa: F401 — реэкспорт для aggg2_prompt_hook
    _DOD_HINT,
    _DONE_MARKERS,
    _ERROR_MARKERS,
    _FORGOTTEN_FINDINGS_HINT,
    _IMPROVEMENT_MARKERS,
    _INTERNAL_LINK_BLOCK,
    _LOCAL_DB_BASH,
    _LOCAL_DB_MARKERS,
    _LSP_HINT,
    _LSP_QUESTION_MARKERS,
    _MIN_SOURCES_NUDGE,
    _OUTPUT_SECRETS_BLOCK,
    _PRODUCT_MARKERS,
    _PRODUCT_SKILL_HINT,
    _QA_MARKERS,
    _QUARANTINE_BASH,  # noqa: F401 — реэкспорт для aggg2_prompt_hook
    _REPEAT_ERROR_HINT,
    _SEMBLE_BASH,
    _SEMBLE_HINT,
    _SEMBLE_QUESTION_MARKERS,
    _SEMBLE_TOOL_MARKERS,
    _SIMPLIFY_HINT,
    _SIMPLIFY_MARKERS,
    _SKILL_TOOLS,
    _SKILLS_BASH,
    _SKILLS_MARKERS,
    _TEST_HINT,
    _WEB_BASH,
    _WEB_MARKERS,
    _WIKI_GREP_BLOCK,
    _WINDOWS_CI_MARKERS,
    _WINDOWS_SKILL_HINT,
    _WORKSPACE_DB_HINT,
    _WORKSPACE_MARKERS,
    FILE_TIERS,
    INDEX_HINT,
    RESEARCH_HINT,
    SEMBLE_READ_HINT,
    SKILLS_HINT,
)


def _mark_crg(session_id: str, tool_name: str, command: str = "") -> bool:
    """Пометить сессию как «CRG использовался» (detect_changes/get_impact_radius).
    Возвращает True, если это был CRG-вызов."""
    from datetime import date
    if not (_CRG_MARKERS.search(tool_name or "")
            or _CRG_MARKERS.search(command or "")):
        return False
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if not state.get("crg_used"):
        state["crg_used"] = True
        _idx_save(session_id, state)
    return True


def _sources_nudge(session_id: str) -> str:
    """Nudge «норматив 10 источников»: если веб-вызовов < 10 → напомнить.
    Возвращает текст напоминания или \"\"."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    web_count = state.get("web_count_since_findings", 0)
    if web_count >= 10:
        return ""
    return _MIN_SOURCES_NUDGE


def _windows_ci_nudge(command: str) -> str:
    """Nudge «Windows/CI — скилл первым»: если команда содержит Windows/CI →
    напомнить загрузить windows-encoding-fixes. Возвращает текст или \"\"."""
    if _WINDOWS_CI_MARKERS.search(command or ""):
        return _WINDOWS_SKILL_HINT
    return ""


def _lsp_nudge(command: str) -> str:
    """Nudge «LSP для кода»: если вопрос про типы/связи/символы → напомнить
    использовать agent-lsp. Возвращает текст или \"\"."""
    if _LSP_QUESTION_MARKERS.search(command or ""):
        return _LSP_HINT
    return ""


def _semble_nudge(command: str) -> str:
    """Nudge «лестница поиска»: смысловой вопрос про код → напомнить
    semble.search. Возвращает текст или \"\"."""
    if _SEMBLE_QUESTION_MARKERS.search(command or ""):
        return _SEMBLE_HINT
    return ""


def _mark_semble(session_id: str, tool_name: str, command: str = "") -> bool:
    """Пометить сессию как «semble вызывался» (MCP semble / CLI-форма).
    Возвращает True, если это был semble-вызов. Харнесы без session_id —
    дневной ключ."""
    from datetime import date
    if not (_SEMBLE_TOOL_MARKERS.search(tool_name or "")
            or _SEMBLE_BASH.search(command or "")):
        return False
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    state["semble"] = True
    _idx_save(session_id, state)
    return True


def _semble_read_nudge(session_id: str, tool_name: str,
                       command: str = "") -> str:
    """Nudge «лестница semble»: чтение/греп кода ПОСЛЕ базы, но ДО semble.
    Эскалация: 1-е чтение — мягко, 3-е — настойчивее, дальше тишина.
    Вызов semble или отсутствие базы гасит nudge. Харнесы без session_id —
    дневной ключ."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("semble") or not state.get("indexed"):
        return ""
    is_read = tool_name in _READ_TOOLS or bool(
        re.match(r"^(grep|cat|head|tail|find|rg)\s", command or ""))
    if not is_read:
        return ""
    n = state.get("semble_reads", 0) + 1
    state["semble_reads"] = n
    _idx_save(session_id, state)
    if n == 1:
        return SEMBLE_READ_HINT
    if n == 3:
        return (SEMBLE_READ_HINT + " (3-й раз без semble — сверься с "
                "лестницей: docs/canon/SEMBLE.md, скилл code-search-ladder)")
    return ""


def _battle_test_nudge(command: str) -> str:
    """Nudge «боевое крещение»: если утверждает «улучшил/ускорил» → напомнить
    дать цифры ДО/ПОСЛЕ. Возвращает текст или \"\"."""
    if _IMPROVEMENT_MARKERS.search(command or ""):
        return _BATTLE_TEST_HINT
    return ""


# 1. DoD перед "готово"
def _dod_nudge(session_id: str, command: str) -> str:
    """Nudge «DoD перед готово»: если говорит «готово» без QA → напомнить."""
    if not _DONE_MARKERS.search(command or ""):
        return ""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("qa_used"):
        return ""
    return _DOD_HINT


def _mark_qa(session_id: str, command: str) -> bool:
    """Пометить сессию как «QA использовался»."""
    if not _QA_MARKERS.search(command or ""):
        return False
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    state["qa_used"] = True
    _idx_save(session_id, state)
    return True


# 2. Ресёрч для аналитики
def _analytics_research_nudge(session_id: str, command: str) -> str:
    """Nudge «ресёрч для аналитики»: если вопрос «как лучше» без веб-вызовов."""
    if not _ANALYTICS_MARKERS.search(command or ""):
        return ""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("web"):
        return ""
    return _ANALYTICS_RESEARCH_HINT


# 3. База для воркспейса
def _workspace_db_nudge(session_id: str, command: str) -> str:
    """Nudge «база для воркспейса»: если вопрос про файлы без поиска в базе."""
    if not _WORKSPACE_MARKERS.search(command or ""):
        return ""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("indexed"):
        return ""
    return _WORKSPACE_DB_HINT


# 4. Скилл для типа задачи
def _product_skill_nudge(command: str) -> str:
    """Nudge «скилл для типа задачи»: если продуктовая задача без ask-nodumb."""
    if not _PRODUCT_MARKERS.search(command or ""):
        return ""
    return _PRODUCT_SKILL_HINT


# 5. Тесты после правки
def _test_nudge(session_id: str, tool_name: str, command: str) -> str:
    """Nudge «тесты после правки»: если изменил код, но тесты не запустил."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if not state.get("code_changed"):
        return ""
    if state.get("tests_run"):
        return ""
    return _TEST_HINT


def _mark_code_change(session_id: str, tool_name: str, command: str) -> bool:
    """Пометить сессию как «код изменён»."""
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        return False
    target = command or ""
    if not target.endswith((".py", ".js", ".ts", ".go", ".rs")):
        return False
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    state["code_changed"] = True
    _idx_save(session_id, state)
    return True


def _mark_tests_run(session_id: str, command: str) -> bool:
    """Пометить сессию как «тесты запущены»."""
    if not re.search(r"(pytest|npm test|cargo test|go test)", command or ""):
        return False
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    state["tests_run"] = True
    _idx_save(session_id, state)
    return True


# 6. Повторная ошибка
def _repeat_error_nudge(session_id: str, command: str) -> str:
    """Nudge «повторная ошибка»: если одна и та же ошибка 2+ раза."""
    if not _ERROR_MARKERS.search(command or ""):
        return ""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    state["error_count"] = state.get("error_count", 0) + 1
    _idx_save(session_id, state)
    if state["error_count"] >= 2:
        return _REPEAT_ERROR_HINT
    return ""


# 7. Секреты в выводе
def _output_secrets_check(content: str) -> str | None:
    """Проверка: секрет в выводе = блок. Возвращает причину или None."""
    secret = _secrets_check(content)
    if secret:
        return _OUTPUT_SECRETS_BLOCK
    return None


# 8. Объяснение сложности
def _simplify_nudge(command: str) -> str:
    """Nudge «объяснение сложности»: если пользователь просит «проще»."""
    if not _SIMPLIFY_MARKERS.search(command or ""):
        return ""
    return _SIMPLIFY_HINT


# 9. Забытый findings.py
def _forgotten_findings_nudge(session_id: str) -> str:
    """Nudge «забытый findings.py»: если 10+ веб-вызовов без findings.py add."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    web_count = state.get("web_count_since_findings", 0)
    if web_count < 10:
        return ""
    if state.get("findings"):
        return ""
    return _FORGOTTEN_FINDINGS_HINT

# Секреты-гейт: regex для обнаружения реальных API-ключей/паролей при правке файлов.
# Блок если найдено совпадение (не плейсхолдер YOUR_*).
_SECRETS_PATTERNS = [
    # API keys: api_key = "sk-...", password = "real123" (не YOUR_API_KEY)
    (re.compile(r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']{20,})["\']', re.IGNORECASE),
     "API_KEY"),
    (re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\']{8,})["\']', re.IGNORECASE),
     "PASSWORD"),
    (re.compile(r'(?:secret|token)\s*[:=]\s*["\']([^"\']{20,})["\']', re.IGNORECASE),
     "SECRET"),
    (re.compile(r'(?:aws_access_key_id|aws_secret_access_key)\s*[:=]\s*["\']([^"\']{16,})["\']',
                re.IGNORECASE),
     "AWS_KEY"),
]
# Исключения: плейсхолдеры YOUR_*, TODO, example, test
_SECRETS_EXCEPTIONS = re.compile(
    r'^(YOUR_|TODO|example|test|placeholder|CHANGE_ME|REPLACE)', re.IGNORECASE)

# Находки-в-базу: маркеры веб-ресёрча (для подсчёта) и findings.py add (для сброса).
_FINDINGS_MARKERS = re.compile(r"findings\.py\s+add")
_FINDINGS_BASH = re.compile(r"findings\.py")

# Состояние nudge-гейта «база-первым» между вызовами хука (хук —
# отдельный процесс на каждый вызов; сессии разделяются session_id).

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


_STATE_DIR = Path(_get_cache_dir())
_DB_MARKERS = re.compile(
    r"(search\.py|search_all\.py|repomap\.py|findings\.py|build\.py|"
    r"githist\.py|tasks\.py|db-tools|repo_map|sqlite3\s+db/)")
_READ_TOOLS = {"Read", "View", "Glob", "Grep", "read_file", "read"}


def _idx_key(session_id: str) -> str:
    """Стабильный ключ файла состояния (hash() рандомизирован между
    процессами — PYTHONHASHSEED; hук живёт один вызов — только sha256)."""
    import hashlib
    return hashlib.sha256((session_id or "default").encode()).hexdigest()[:16]


def _idx_state(session_id: str) -> dict:
    """Состояние сессии: {"reads": int, "indexed": bool, "web": bool,
    "web_warned": int}. Файл-бэкап в кэше — хук не держит память между
    вызовами; гонка двух параллельных тулов допустима (цена — лишний
    nudge, не блок)."""
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = _STATE_DIR / f"idx_{_idx_key(session_id)}.json"
        if state_file.is_file():
            with suppress(Exception):
                return json.loads(state_file.read_text(encoding="utf-8"))
    except OSError:
        pass
    return {"reads": 0, "indexed": False, "web": False, "web_warned": 0}


def _idx_save(session_id: str, state: dict) -> None:
    with suppress(Exception):
        state_file = _STATE_DIR / f"idx_{_idx_key(session_id)}.json"
        state_file.write_text(json.dumps(state), encoding="utf-8")


def _idx_nudge(session_id: str, tool_name: str, command: str = "") -> str:
    """Nudge «база-первым»: чтение файлов до индекса. Возвращает текст
    напоминания или "". Эскалация: 1-е чтение — мягко, 3-е — настойчивее,
    дальше тишина (не спамить). Вызов базы (CLI или MCP db-tools) гасит
    nudge до конца сессии. Харнесы без session_id (Codewhale/omp) —
    дневной ключ: nudge не чаще двух раз в день до вызова базы.
    Паттерн индустрии: soft guardrails + детерминизм хука (nader/zarar:
    «промпты — подсказки, хуки — поведение на каждый раз»; audit
    17.08.2026, research.db id=792)."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if (_DB_MARKERS.search(command)
            or re.search(r"^mcp__db-?tools|^mcp__(repo_map|search_all)",
                         tool_name or "")):
        state["indexed"] = True
        _idx_save(session_id, state)
        return ""
    is_read = tool_name in _READ_TOOLS or bool(
        re.match(r"^(grep|cat|head|tail|find|rg)\s", command or ""))
    if not is_read or state.get("indexed"):
        return ""
    state["reads"] = state.get("reads", 0) + 1
    _idx_save(session_id, state)
    # Телеметрия nudge-событий (аудит 17.08.2026, research.db id=794):
    # JSONL в кэше — сырьё для замеров «чтение-до-базы» по сессиям.
    with suppress(Exception):
        from datetime import datetime
        ev_file = _STATE_DIR / "events.jsonl"
        with ev_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "session": session_id, "reads": state["reads"],
                "tool": tool_name,
            }, ensure_ascii=False) + "\n")
    if state["reads"] == 1:
        return INDEX_HINT
    if state["reads"] == 3:
        return (INDEX_HINT + " (3-й раз за сессию без базы — сверься с "
                "DB-FIRST: индекс → свежесть → карта → связи → живой код)")
    return ""


def _mark_web(session_id: str, tool_name: str, command: str = "") -> bool:
    """Пометить сессию как «веб-ресёрч был» (вызов Camoufox/поиска).
    Также увеличивает счётчик веб-вызовов для гейта «находки-в-базу».
    Возвращает True, если это был веб-вызов. Харнесы без session_id —
    дневной ключ (как у _idx_nudge)."""
    from datetime import date
    if not (_WEB_MARKERS.search(tool_name or "")
            or _WEB_BASH.search(command or "")):
        return False
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if not state.get("web"):
        state["web"] = True
    # Увеличиваем счётчик веб-вызовов для гейта «находки-в-базу»
    state["web_count_since_findings"] = state.get("web_count_since_findings", 0) + 1
    _idx_save(session_id, state)
    return True


def _web_nudge(session_id: str) -> str:
    """Nudge «ресёрч-первым»: правка кода до веб-ресёрча. Возвращает текст
    напоминания или "". Эскалация: 1-я правка — мягко, 3-я — настойчивее,
    дальше тишина (не спамить). Веб-вызов (Camoufox MCP/CLI) гасит nudge
    до конца сессии. Паритет с opencode-плагином (proshivka.js)."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("web"):
        return ""
    state["web_warned"] = state.get("web_warned", 0) + 1
    _idx_save(session_id, state)
    if state["web_warned"] == 1:
        return RESEARCH_HINT
    if state["web_warned"] == 3:
        return (RESEARCH_HINT + " (3-я правка без ресёрча — вернись в "
                "RESEARCH: docs/canon/CAMOUFOX.md «Исследовательский цикл»)")
    return ""


# Skill-роутер (UserPromptSubmit): детект типа задачи по маркерам промпта
# -> рекомендация скилла В КОНТЕКСТ до работы. Паттерн индустрии:
# UserPromptSubmit skill router (hwells4), auto-skill-router (scuensen).
def _skill_router(prompt: str) -> str:
    """Рекомендация скилла по типу задачи (первый матч). Возвращает
    строку для additionalContext или ""."""
    for pattern, skill_name in _SKILL_ROUTES:
        if pattern.search(prompt or ""):
            return (f"СКИЛЛ ДЛЯ ЭТОЙ ЗАДАЧИ: `{skill_name}` — ЗАГРУЗИ И "
                    f"СЛЕДУЙ перед действиями (скилл ядра).")
    return ""


def _log_skill_load(session_id: str, tool_name: str, tool_input: dict) -> None:
    """Телеметрия загрузки скиллов (compliance, паттерн PostToolUse-log):
    каждый вызов Skill пишется в events.jsonl — сырьё для замеров «% задач,
    где скилл реально загружен» (Skill-Use: trigger ≠ compliance)."""
    name = str(tool_input.get("name") or tool_input.get("skill") or "")
    if tool_name not in ("Skill", "skill") and not name:
        return
    if not name:
        name = tool_name
    with suppress(Exception):
        from datetime import datetime
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        ev_file = _STATE_DIR / "events.jsonl"
        with ev_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "session": session_id or "-",
                "event": "skill_loaded", "skill": name,
            }, ensure_ascii=False) + "\n")


def _mark_skills(session_id: str, tool_name: str, command: str = "") -> bool:
    """Пометить сессию как «локальный скилл искался/загружался»
    (db/skills.db через search.py/MCP, Skill-загрузка). Возвращает True,
    если это был skills-вызов. Харнесы без session_id — дневной ключ."""
    from datetime import date
    if not (_SKILLS_MARKERS.search(tool_name or "")
            or _SKILLS_BASH.search(command or "")
            or tool_name in _SKILL_TOOLS):
        return False
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if not state.get("skills"):
        state["skills"] = True
        _idx_save(session_id, state)
    return True


def _skills_nudge(session_id: str) -> str:
    """Nudge «скиллы-первым»: веб-вызов до поиска локального скилла.
    Возвращает текст напоминания или "". Эскалация: 1-й веб-вызов —
    мягко, 3-й — настойчивее, дальше тишина. Skills-вызов гасит nudge
    до конца сессии. Паритет с opencode-плагином (proshivka.js)."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("skills"):
        return ""
    state["skills_warned"] = state.get("skills_warned", 0) + 1
    _idx_save(session_id, state)
    if state["skills_warned"] == 1:
        return SKILLS_HINT
    if state["skills_warned"] == 3:
        return (SKILLS_HINT + " (3-й веб-вызов без локального поиска — "
                "сверься с docs/canon/SKILLS-LOCAL.md: фаза 1б цикла)")
    return ""


LOCAL_DB_HINT = (
    "ГЕЙТ «local-databases-первым»: ПЕРЕД веб-ресёрчем (Camoufox web_search/"
    "batch_fetch) — СНАЧАЛА проверь локальные базы знаний: "
    "python3 scripts/tools/skills/skills_search.py --knowledge \"<тема>\" "
    "(прочитанные внешние скиллы, skill-knowledge.db) и "
    "python3 scripts/tools/skills/skills_search.py --internet \"<тема>\" "
    "(прочитанные веб-страницы, context-internet.db). Если ответ уже есть "
    "в базе — НЕ ходи в веб (экономия токенов и времени). Скилл: local-databases."
)


def _mark_local_databases(session_id: str, tool_name: str, command: str = "") -> bool:
    """Пометить сессию как «локальные базы знаний проверены» (--knowledge,
    --internet). Возвращает True, если это был local-db-вызов. Харнесы без
    session_id — дневной ключ."""
    from datetime import date
    if not (_LOCAL_DB_MARKERS.search(command or "")
            or _LOCAL_DB_BASH.search(command or "")):
        return False
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if not state.get("local_databases"):
        state["local_databases"] = True
        _idx_save(session_id, state)
    return True


def _local_databases_nudge(session_id: str) -> str:
    """Nudge «local-databases-первым»: веб-вызов до проверки локальных баз.
    Возвращает текст напоминания или "". Эскалация: 1-й веб-вызов — мягко,
    3-й — настойчивее, дальше тишина. Local-db-вызов гасит nudge до конца
    сессии."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("local_databases"):
        return ""
    state["local_db_warned"] = state.get("local_db_warned", 0) + 1
    _idx_save(session_id, state)
    if state["local_db_warned"] == 1:
        return LOCAL_DB_HINT
    if state["local_db_warned"] == 3:
        return (LOCAL_DB_HINT + " (3-й веб-вызов без проверки локальных баз — "
                "сверься с docs/canon/LOCAL_DATABASES.md: иерархия поиска)")
    return ""


# Wiki-grep-block: агент НЕ должен грепать Wiki/ по содержимому (только база db=wiki).
# Возвращает причину блокировки или None.
def _wiki_grep_check(command: str) -> str | None:
    """Проверка: grep/rg по Wiki/ = блок. Возвращает причину или None."""
    if _WIKI_GREP_BLOCK.search(command or ""):
        return ("БЛОК: grep/rg по Wiki/ запрещён — агент НИКОГДА не грепает Wiki/ "
                "по содержимому, только через базу (search.py -b db/wiki.db или "
                "MCP search с db: wiki). Wiki/ — библиотека знаний, поиск только "
                "через индекс. Подробности: AGENTS.md «Wiki/ — библиотека знаний».")
    return None


# curl-блок для сайтов: агент НЕ должен проверять доступность сайтов через curl.
# Возвращает причину блокировки или None.
def _curl_site_check(command: str) -> str | None:
    """Проверка: curl https://site.com = блок (не API, не localhost).
    Возвращает причину или None."""
    if _CURL_SITE_BLOCK.search(command or ""):
        return ("БЛОК: curl https://site.com даёт ложные 403 (TLS-фингерпринт, JS, "
                "куки, капчи). Используй Camoufox: browser_navigate(url) или "
                "fetch_page(url). curl — только для localhost/API (с /api/ или /v1/). "
                "Подробности: CLAUDE.md п.9 «Доступность сайтов — через Camoufox».")
    return None


# Внутренние ссылки в продукте: research.db id=N в .md файлах = мёртвая ссылка.
# Возвращает причину блокировки или None.
def _internal_link_check(content: str, file_path: str = "") -> str | None:
    """Проверка: research.db id=N в .md файле = блок.
    Возвращает причину или None."""
    if not file_path.endswith(".md"):
        return None
    if _INTERNAL_LINK_BLOCK.search(content or ""):
        return ("БЛОК: research.db id=N в .md файле = мёртвая ссылка для получателя "
                "(research.db не входит в архив). Используй 'проверено живьём' / "
                "'опыт AGGG2.0' без номеров. Подробности: CLAUDE.md п.16 "
                "'Продукт без внутренних ссылок'.")
    return None


# CRG-гейт перед commit: напоминание использовать code-review-graph.
# Возвращает текст напоминания или "".
def _crg_commit_nudge(session_id: str, command: str) -> str:
    """Nudge «CRG перед commit»: git commit без detect_changes в сессии.
    Возвращает текст напоминания или \"\"."""
    from datetime import date
    if not _COMMIT_MARKERS.search(command or ""):
        return ""
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("crg_used"):
        return ""
    state["commit_warned"] = state.get("commit_warned", 0) + 1
    _idx_save(session_id, state)
    return ("НАПОМИНАНИЕ: git commit без ревью через code-review-graph — "
            "сначала detect_changes/get_impact_radius по диффу (CRG MCP), "
            "граф пересобран (build_or_update_graph_tool). Пропущенное ревью = "
            "правка не готова. Порядок: база → agent-lsp → CRG. "
            "Подробности: CLAUDE.md п.5 «Ревью изменений — через CRG».")


# Секреты-гейт: проверка контента на реальные API-ключи/пароли.
# Возвращает (тип_секрета, значение) или None.
def _secrets_check(content: str) -> tuple[str, str] | None:
    """Проверка контента на секреты. Возвращает (тип, значение) или None."""
    for pattern, secret_type in _SECRETS_PATTERNS:
        match = pattern.search(content or "")
        if match:
            value = match.group(1)
            # Исключаем плейсхолдеры
            if not _SECRETS_EXCEPTIONS.match(value):
                return (secret_type, value[:8] + "...")
    return None


# Находки-в-базу: напоминание после N веб-вызовов без findings.py add.
def _mark_findings(session_id: str, tool_name: str, command: str = "") -> bool:
    """Пометить сессию как «находки записаны» (findings.py add).
    Возвращает True, если это был findings-вызов."""
    from datetime import date
    if not (_FINDINGS_MARKERS.search(command or "")
            or _FINDINGS_BASH.search(command or "")):
        return False
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    state["findings"] = True
    state["web_count_since_findings"] = 0
    _idx_save(session_id, state)
    return True


def _findings_nudge(session_id: str) -> str:
    """Nudge «находки в базу»: N веб-вызовов без findings.py add.
    Возвращает текст напоминания или \"\". Эскалация: 5-й веб-вызов — мягко,
    10-й — настойчивее. Findings-вызов сбрасывает счётчик."""
    from datetime import date
    if not session_id:
        session_id = f"default-{date.today().isoformat()}"
    state = _idx_state(session_id)
    if state.get("findings"):
        return ""
    web_count = state.get("web_count_since_findings", 0)
    if web_count < 5:
        return ""
    if web_count == 5:
        return ("НАПОМИНАНИЕ: 5+ веб-вызовов без записи находок в research.db — "
                "после ресёрча/эксперимента/разбора: python3 db-tools/findings.py add "
                "«тема» --text «вывод» --tags «теги» (иначе знание теряется после "
                "разговора). core.txt п.5 «Находки в базу».")
    if web_count >= 10:
        return ("НАПОМИНАНИЕ: 10+ веб-вызовов без записи находок! Немедленно: "
                "python3 db-tools/findings.py add «тема» --text «вывод» --tags «теги». "
                "Знание без записи в базу = потеряно. core.txt п.5.")
    return ""

_SKILL_ROUTES = [
    (re.compile(r"(как улучшить|что улучшить|аудит|проверь проект|улучшить код|"
                r"разобрать проект)", re.IGNORECASE),
     "code-search-ladder"),
    (re.compile(r"(reverse|реверс|деобфус|чуж[а-я]* (код|сайт|api|бот)|"
                r"разбор (чужого|бинарника|протокола|бандла))", re.IGNORECASE),
     "triage-route"),
    (re.compile(r"(не работает|сломал[а-я]*|завис|висит|виснет|упал|"
                r"падает|пропал[ао] после|раньше работал|инцидент)",
                re.IGNORECASE),
     "debug-incident-protocol"),
    (re.compile(r"(рефакторинг|монолит|вынос модул|мерж.*проект|god-файл)", re.IGNORECASE),
     "agent-refactor-safety"),
    (re.compile(r"(фича|экран|флоу|редизайн|продукт|ux|юзабилити|"
                r"придумай.*(экран|кнопк|фич))", re.IGNORECASE),
     "ask-nodumb"),
    (re.compile(r"(тест|покрыти|fail.*тест|падающ[а-я]* тест|rate.limit|"
                r"лимит.*запрос)", re.IGNORECASE),
     "testing-discipline"),
    (re.compile(r"(windows|crlf|кодировк|bom|cp1251)", re.IGNORECASE),
     "windows-encoding-fixes"),
    (re.compile(r"(wiki|пост|библиотек.*знан|skill-notes)", re.IGNORECASE),
     "wiki-karpathy"),
    (re.compile(r"(оплат|куп|подписк|баланс|квот|лимит.*деньг|промокод)", re.IGNORECASE),
     "money-path-safety"),
    (re.compile(r"(rate.limit|метрик|алерт|лимит.*защит|аудит безопасн)", re.IGNORECASE),
     "hardening-observability"),
    (re.compile(r"(на пальцах|объясни просто|как динозавру|elI5|не понимаю)", re.IGNORECASE),
     "explain-fingers"),
    (re.compile(r"(changelog|журнал решений)", re.IGNORECASE),
     "changelog-discipline"),
    (re.compile(r"(релиз|деплой|конфиг.*продакшн|настро.*конфиг)", re.IGNORECASE),
     "release-helper"),
]

def _count_lines(path: str):
    """Число строк файла (как wc -l). Ошибки — None: хук не ломает работу."""
    with suppress(OSError), open(path, "rb") as fh:
        return sum(1 for _ in fh)
    return None


def _file_size_verdict(tool_input: dict, target: str):
    """Гейт god-файлов (docs/canon/FILE-SIZE.md): ("deny"|"nudge", текст) или None.

    deny: новый файл > hard (Write с известным контентом) или правка растит
    файл выше hard (Edit с old/new, MultiEdit — сумма дельт). nudge: файл
    выше soft / уже выше hard — напоминание «режь, а не расти». Ошибки
    любого шага = тишина: правило не должно ломать работу агента."""
    ext = os.path.splitext(target)[1].lower()
    tier = next((t for t, (_s, _h, exts) in FILE_TIERS.items()
                 if ext in exts), None)
    if tier is None:
        return None
    soft, hard, _exts = FILE_TIERS[tier]
    cur = _count_lines(target)
    # Write/создание: контент известен (Claude/Codex: content/file_text;
    # antigravity write_to_file: CodeContent)
    content = None
    with suppress(Exception):
        content = (tool_input.get("content") or tool_input.get("file_text")
                   or tool_input.get("fileContents") or tool_input.get("text")
                   or tool_input.get("CodeContent"))
    if isinstance(content, str) and content:
        new_lines = content.count("\n") + 1
        if new_lines > hard:
            return ("deny",
                    f"БЛОК: файл {target} будет {new_lines} строк при "
                    f"hard-лимите {hard} ({tier}) — god-файл запрещён. "
                    f"Разбей на части; правила — docs/canon/FILE-SIZE.md")
        if new_lines > soft and (cur is None or cur <= soft):
            return ("nudge",
                    f"НАПОМИНАНИЕ: {target} будет {new_lines} строк (soft "
                    f"{soft}, hard {hard}) — дальше не расти: режь "
                    f"(docs/canon/FILE-SIZE.md)")
        return None
    # Edit: дельта по старым/новым строкам (Claude Edit: old_string/new_string;
    # antigravity replace_file_content: TargetContent/ReplacementContent)
    old = new = None
    with suppress(Exception):
        old = (tool_input.get("old_string") or tool_input.get("oldString")
               or tool_input.get("old_str")
               or tool_input.get("TargetContent"))
        new = (tool_input.get("new_string") or tool_input.get("newString")
               or tool_input.get("new_str")
               or tool_input.get("ReplacementContent"))
    if not isinstance(old, str) or not isinstance(new, str):
        # MultiEdit/мульти-замена: сумма дельт по edits[]/ReplacementChunks[]
        with suppress(Exception):
            edits = tool_input.get("edits") or tool_input.get(
                "ReplacementChunks")
            if isinstance(edits, list) and edits and cur is not None:
                delta = 0
                for e in edits:
                    eo = str(e.get("old_string") or e.get("oldString")
                             or e.get("TargetContent") or "")
                    en = str(e.get("new_string") or e.get("newString")
                             or e.get("ReplacementContent") or "")
                    delta += en.count("\n") - eo.count("\n")
                if cur + delta > hard:
                    return ("deny",
                            f"БЛОК: правка растит {target} до {cur + delta} "
                            f"строк при hard-лимите {hard} ({tier}) — не "
                            f"расти: режь (docs/canon/FILE-SIZE.md)")
        if cur is not None and cur >= hard:
            return ("nudge",
                    f"НАПОМИНАНИЕ: {target} уже {cur} строк (> hard {hard}) — "
                    f"правь только в сторону резки (docs/canon/FILE-SIZE.md)")
        return None
    delta = new.count("\n") - old.count("\n")
    if cur is None:
        return None
    if cur >= hard:
        # уже god-файл: расти нельзя, резать можно (только в сторону резки)
        if delta > 0:
            return ("deny",
                    f"БЛОК: {target} уже {cur} строк (> hard {hard}) — рост "
                    f"запрещён, только резка (docs/canon/FILE-SIZE.md)")
        return ("nudge",
                f"НАПОМИНАНИЕ: {target} уже {cur} строк (> hard {hard}) — "
                f"правь только в сторону резки (docs/canon/FILE-SIZE.md)")
    if cur + delta > hard:
        return ("deny",
                f"БЛОК: правка растит {target} до {cur + delta} строк при "
                f"hard-лимите {hard} ({tier}) — god-файл запрещён. Не расти: "
                f"режь (docs/canon/FILE-SIZE.md)")
    if cur + delta > soft:
        return ("nudge",
                f"НАПОМИНАНИЕ: {target} перерастёт soft-лимит {soft} "
                f"(hard {hard}) — режь (docs/canon/FILE-SIZE.md)")
    return None

def _dir_limit_hint(target: str) -> str:
    """Гейт лимита каталога (docs/canon/ARCHITECTURE.md): > 15 файлов-братьев —
    nudge «дели по доменам» (паттерн Nx module boundaries / Packwerk:
    границы как гейт; ошибки = тишина, не ломаем агента)."""
    try:
        d = os.path.dirname(os.path.abspath(target))
        sibs = [f for f in os.listdir(d)
                if os.path.isfile(os.path.join(d, f))
                and not f.startswith(".")
                and f != "README.md"
                and f.endswith((".py", ".js", ".ts", ".sh", ".go", ".rs",
                                ".java", ".c", ".cpp", ".md", ".toml"))]
        if len(sibs) > 15:
            return ("AGGG2.0-сторож: каталог-переросток "
                    f"({os.path.basename(d)}: {len(sibs)} файлов > 15) — "
                    "дели по доменам, не добавляй в кучу (docs/canon/ARCHITECTURE.md)")
    except OSError:
        pass
    return ""
