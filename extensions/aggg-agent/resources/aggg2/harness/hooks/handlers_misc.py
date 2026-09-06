# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ

# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Харнес-хендлеры PreToolUse (Codewhale/omp/Hermes/Gemini/Antigravity/
Reasonix). Вынесено из aggg2_prompt_hook.py (механическая резка
god-файла, docs/canon/FILE-SIZE.md): код хендлеров перенесён дословно.
decide_pre_tool_use/EDIT_TOOLS передаются хуком через bind() — модуль не
импортирует ни hook_gates, ни __main__ (слойная изоляция и отсутствие
маскировки реальных ImportError). Хук импортирует этот модуль лениво
(внутри main) и сразу вызывает bind(). Копируется install_proshivka.py
ВМЕСТЕ с aggg2_prompt_hook.py.
"""
import json
import os
import sys
from contextlib import suppress

_EDIT_TOOLS: frozenset = frozenset()
_decide = None


def bind(decide, edit_tools):
    """Хук регистрирует свои decide_pre_tool_use/EDIT_TOOLS (вызов до
    обработки событий; хендлеры без bind() — ошибка, а не тихий allow)."""
    global _EDIT_TOOLS, _decide
    _EDIT_TOOLS = frozenset(edit_tools)
    _decide = decide


def _decide_call(*args, **kwargs):
    if _decide is None:
        raise RuntimeError("handlers_misc.bind() не вызван хук-скриптом")
    return _decide(*args, **kwargs)


def _reasonix_tool_input(data: dict) -> dict:
    """ToolArgs у Reasonix — JSON-строка; развернуть в dict."""
    raw = data.get("ToolArgs")
    if isinstance(raw, dict):
        return raw
    with suppress(Exception):
        parsed = json.loads(str(raw))
        if isinstance(parsed, dict):
            return parsed
    return {}


def _codewhale_mode() -> bool:
    """Codewhale шлёт контекст в env (DEEPSEEK_TOOL_NAME/ARGS), не в stdin."""
    return bool(os.environ.get("DEEPSEEK_TOOL_NAME"))


def _omp_mode() -> bool:
    """omp-hooks: блок только через exit 2, stdout при exit 0 = скрытый контекст."""
    return os.environ.get("AGGG2_HOOK_MODE") == "omp"


def _codewhale_handle() -> int:
    """Codewhale tool_call_before: вердикт stdout JSON, exit 0 (docs/HOOKS.md)."""
    name = os.environ.get("DEEPSEEK_TOOL_NAME", "")
    args = {}
    with suppress(Exception):
        parsed = json.loads(os.environ.get("DEEPSEEK_TOOL_ARGS", "") or "{}")
        if isinstance(parsed, dict):
            args = parsed
    out = _decide_call(name, args,
                              session_id=os.environ.get("DEEPSEEK_SESSION_ID"))
    if out is None:
        return 0
    decision = out["hookSpecificOutput"]
    if decision.get("permissionDecision") == "deny":
        sys.stdout.write(json.dumps(
            {"decision": "deny", "reason": decision.get("permissionDecisionReason", "блок")},
            ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(json.dumps(
            {"decision": "allow",
             "additionalContext": decision.get("additionalContext", "")},
            ensure_ascii=False) + "\n")
    return 0


def _omp_handle(data: dict) -> int:
    """omp-hooks PreToolUse: блок = exit 2 + stderr, allow-напоминание = stdout
    (omp-hooks инжектит stdout как скрытый контекст модели)."""
    out = _decide_call(str(data.get("tool_name", "")),
                              data.get("tool_input") or {},
                              session_id=data.get("session_id"))
    if out is None:
        return 0
    decision = out["hookSpecificOutput"]
    if decision.get("permissionDecision") == "deny":
        sys.stderr.write(decision.get("permissionDecisionReason", "блок") + "\n")
        return 2
    sys.stdout.write(decision.get("additionalContext", "") + "\n")
    return 0


def _hermes_handle(data: dict) -> int:
    """Hermes shell hooks pre_tool_call (agent/shell_hooks.py wire protocol):
    блок = stdout JSON {"action": "block", "message": ...} + exit 2 (принимаются
    обе формы: action/decision; exit 2 блокирует сам по себе). Allow-напоминание
    не доставляется (pre_tool_call не принимает контекст — инъекция только на
    pre_llm_call, а ядро и так в SOUL.md слоте #1) — тишина."""
    out = _decide_call(str(data.get("tool_name", "")),
                              data.get("tool_input") or {})
    if out is None:
        return 0
    decision = out["hookSpecificOutput"]
    if decision.get("permissionDecision") == "deny":
        sys.stdout.write(json.dumps(
            {"action": "block",
             "message": decision.get("permissionDecisionReason", "блок")},
            ensure_ascii=False) + "\n")
        return 2
    return 0


def _gemini_handle(data: dict) -> int:
    """Gemini CLI BeforeTool (geminicli.com/docs/hooks/reference): блок =
    stdout {"decision": "deny", "reason": ...} + exit 2 (System Block,
    stderr = причина; Golden Rule: stdout — ТОЛЬКО JSON). tool_name/
    tool_input совпадают с Claude-форматом — решается тем же decide_*.
    Режим включается env AGGG2_HOOK_MODE=gemini (команда в settings.json
    с env-префиксом, как у omp). Allow-напоминание некуда слать
    (BeforeTool принимает только перезапись tool_input) — тишина."""
    out = _decide_call(str(data.get("tool_name", "")),
                              data.get("tool_input") or {})
    if out is None:
        return 0
    decision = out["hookSpecificOutput"]
    if decision.get("permissionDecision") == "deny":
        reason = decision.get("permissionDecisionReason", "блок")
        sys.stderr.write(reason + "\n")
        sys.stdout.write(json.dumps({"decision": "deny", "reason": reason},
                                    ensure_ascii=False) + "\n")
        return 2
    return 0


def _antigravity_handle(data: dict) -> int:
    """Antigravity/agy hooks.json PreToolUse (antigravity.google/docs/hooks):
    stdin {toolCall: {name, args}, stepIdx, ...} (camelCase); гейт — stdout
    {"decision": "allow"|"deny", "reason": ...} (exit 0). Запреты — общие
    BLOCK_RULES; с 15.08 матчер покрывает edit-тулы (write_to_file/
    replace_file_content/multi_replace_file_content) — файл-гейт тоже
    работает (deny). Напоминания некуда слать — тишина."""
    tc = data.get("toolCall") or {}
    name = str(tc.get("name") or "")
    args = tc.get("args") or {}
    if name == "run_command":
        tool_input = {"command": str(args.get("CommandLine") or "")}
    elif name in _EDIT_TOOLS:
        tool_input = args  # camelCase-ключи хук понимает (TargetFile и т.п.)
    else:
        return 0
    out = _decide_call(name, tool_input)
    if out is None:
        return 0
    decision = out["hookSpecificOutput"]
    if decision.get("permissionDecision") == "deny":
        sys.stdout.write(json.dumps(
            {"decision": "deny",
             "reason": decision.get("permissionDecisionReason", "блок")},
            ensure_ascii=False) + "\n")
    return 0
