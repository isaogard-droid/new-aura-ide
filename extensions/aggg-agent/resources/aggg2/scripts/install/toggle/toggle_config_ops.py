# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""toggle_config_ops — хирургия конфигов харнесов для выключения/включения
прошивки AGGG2.0 (используется scripts/install/toggle_proshivka.py).

Принцип (паттерн индустрии — нативные переключатели харнесов: Claude Code
disableAllHooks, Codex --profile, opencode plugins/): мы НЕ удаляем чужие
настройки — вынимаем ТОЛЬКО записи с нашей сигнатурой (хук
aggg2_prompt_hook.py, MCP с путём в чулан AGGG2.0, agent.build.prompt,
permissions из наших снапшотов). removed-структуры возвращаются
функциями insert_* — включение восстанавливает ровно то, что вынимали.

Каждая пара remove_*/insert_* — чистые функции (данные внутрь, данные
наружу), чтобы тестироваться без живых конфигов.
"""
import json
from pathlib import Path

from toggle.toggle_opencode import (  # noqa: F401 — контракт (toggle_proshivka)
    insert_opencode,
    remove_opencode,
)

CHULAN = Path(__file__).resolve().parent.parent
SIG_HOOK = "aggg2_prompt_hook.py"
SIG_SNAPS = Path.home() / ".config" / "aggg2"  # снапшоты permissions

__all__ = [  # реэкспорт-контракт: toggle_proshivka импортирует отсюда
    "_insert_mcp_keys",
    "_remove_mcp_keys",
    "insert_agy_hooks",
    "insert_claude_permissions",
    "insert_codewhale_toml",
    "insert_codex_toml",
    "insert_gemini",
    "insert_hermes_yaml",
    "insert_hooks_generic",
    "insert_opencode",
    "insert_reasonix",
    "remove_agy_hooks",
    "remove_claude_permissions",
    "remove_codewhale_toml",
    "remove_codex_toml",
    "remove_gemini",
    "remove_hermes_yaml",
    "remove_hooks_generic",
    "remove_opencode",
    "remove_reasonix",
]


def _is_ours_mcp(value) -> bool:
    """Запись MCP-сервера наша, если command/args/env ссылаются на чулан."""
    chulan = str(CHULAN)
    if isinstance(value, str):
        return chulan in value
    if isinstance(value, (list, tuple)):
        return any(_is_ours_mcp(v) for v in value)
    if isinstance(value, dict):
        return any(_is_ours_mcp(v) for v in value.values())
    return False


def _ours_hook(h) -> bool:
    return isinstance(h, dict) and SIG_HOOK in str(h.get("command", ""))


# ---------- hooks в формате Claude (claude/codex/omp/gemini) ----------

def remove_hooks_generic(data: dict) -> dict:
    """Вынуть наши хуки из data["hooks"] (события → группы → хуки).
    Возвращает удалённое: {event: [{"hooks": [...], "matcher": ...|None}]}."""
    removed = {}
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return removed
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        removed_groups, keep = [], []
        for grp in groups:
            if not isinstance(grp, dict) or not isinstance(grp.get("hooks"), list):
                keep.append(grp)
                continue
            ours = [h for h in grp["hooks"] if _ours_hook(h)]
            others = [h for h in grp["hooks"] if not _ours_hook(h)]
            if ours:
                entry = {"hooks": ours}
                if "matcher" in grp:
                    entry["matcher"] = grp["matcher"]
                removed_groups.append(entry)
            if others:
                ng = dict(grp)
                ng["hooks"] = others
                keep.append(ng)
        if removed_groups:
            removed[event] = removed_groups
        if keep:
            hooks[event] = keep
        else:
            del hooks[event]
    if not hooks:
        data.pop("hooks", None)
    return removed


def insert_hooks_generic(data: dict, removed: dict) -> bool:
    """Вернуть удалённые хуки (недостающие) в data["hooks"]. True — если
    что-то вставили. Не-list ключи (mcpServers, permissions_ask) пропускает."""
    changed = False
    hooks = data.setdefault("hooks", {})
    for event, groups in removed.items():
        if not isinstance(groups, list):
            continue
        ev = hooks.setdefault(event, [])
        for grp in groups:
            matcher = grp.get("matcher")
            target = next((g for g in ev if isinstance(g, dict)
                           and g.get("matcher") == matcher), None)
            if target is None:
                entry = {"hooks": list(grp["hooks"])}
                if "matcher" in grp:
                    entry["matcher"] = grp["matcher"]
                ev.append(entry)
                changed = True
                continue
            thooks = target.setdefault("hooks", [])
            known = {str(h.get("command")) for h in thooks}
            for h in grp["hooks"]:
                if str(h.get("command")) not in known:
                    thooks.append(dict(h))
                    changed = True
    return changed


# ---------- reasonix (~/.reasonix/settings.json) ----------

def remove_reasonix(data: dict) -> dict:
    """Вынуть записи PreToolUse с нашей командой. Формат:
    {"hooks": {"PreToolUse": [{"match": ..., "command": ...}]}}."""
    removed = {}
    hooks = data.get("hooks", {})
    pre = hooks.get("PreToolUse")
    if not isinstance(pre, list):
        return removed
    ours = [e for e in pre if isinstance(e, dict) and SIG_HOOK in str(e.get("command", ""))]
    if not ours:
        return removed
    hooks["PreToolUse"] = [e for e in pre if e not in ours]
    if not hooks["PreToolUse"]:
        del hooks["PreToolUse"]
    if not hooks:
        data.pop("hooks", None)
    removed["PreToolUse"] = ours
    return removed


def insert_reasonix(data: dict, removed: dict) -> bool:
    pre = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    known = {e.get("command") for e in pre if isinstance(e, dict)}
    changed = False
    for e in removed.get("PreToolUse", []):
        if e.get("command") not in known:
            pre.append(dict(e))
            changed = True
    return changed


# ---------- MCP-секции JSON (mcpServers / servers) ----------

def _remove_mcp_keys(data: dict, key: str) -> dict:
    """Вынуть наши серверы из data[key] (mcpServers/servers)."""
    removed = {}
    section = data.get(key)
    if not isinstance(section, dict):
        return removed
    removed[key] = {}
    for name in list(section):
        if _is_ours_mcp(section[name]):
            removed[key][name] = section.pop(name)
    if not section:
        data.pop(key, None)
    if not removed[key]:
        del removed[key]
    return removed


def _insert_mcp_keys(data: dict, removed: dict) -> bool:
    changed = False
    for key, servers in removed.items():
        if not isinstance(servers, dict):
            continue
        section = data.setdefault(key, {})
        for name, conf in servers.items():
            if name not in section:
                section[name] = conf
                changed = True
    return changed


# ---------- gemini (~/.gemini/settings.json: hooks + mcpServers) ----------

def remove_gemini(data: dict) -> dict:
    removed = remove_hooks_generic(data)
    mcp_removed = _remove_mcp_keys(data, "mcpServers")
    removed.update(mcp_removed)
    return removed


def insert_gemini(data: dict, removed: dict) -> bool:
    changed = insert_hooks_generic(data, removed)
    return _insert_mcp_keys(data, removed) or changed


# ---------- antigravity/agy (~/.gemini/config/hooks.json) ----------

def remove_agy_hooks(data: dict) -> dict:
    """Формат: {имя_хука: {"PreToolUse": [...]}} — убрать весь aggg2-storozh."""
    removed = {}
    conf = data.get("aggg2-storozh")
    if conf is not None:
        removed["aggg2-storozh"] = data.pop("aggg2-storozh")
    return removed


def insert_agy_hooks(data: dict, removed: dict) -> bool:
    changed = False
    for name, conf in removed.items():
        if name not in data:
            data[name] = conf
            changed = True
    return changed


# ---------- claude permissions.ask (~/.claude/settings.json) ----------

def _claude_perm_rules() -> list:
    """Наши ask-правила из снапшота установщика (proshivka_permissions)."""
    snap = SIG_SNAPS / "claude-file-size-paths.json"
    if snap.is_file():
        try:
            rules = json.loads(snap.read_text(encoding="utf-8"))
            if isinstance(rules, list):
                return rules
        except (OSError, ValueError):
            pass
    return []


def remove_claude_permissions(data: dict, rules: list | None = None) -> dict:
    """Убрать наши permissions.ask-правила. rules=None — читать из
    снапшота установщика (~/.config/aggg2/claude-file-size-paths.json)."""
    removed = {}
    if rules is None:
        rules = _claude_perm_rules()
    if not rules:
        return removed
    perm = data.get("permissions")
    if not isinstance(perm, dict):
        return removed
    ask = perm.get("ask")
    if not isinstance(ask, list):
        return removed
    ours = [r for r in ask if r in rules]
    if ours:
        perm["ask"] = [r for r in ask if r not in ours]
        removed["permissions_ask"] = ours
        if not perm["ask"] and len(perm) == 1:
            data.pop("permissions", None)
    return removed


def insert_claude_permissions(data: dict, removed: dict) -> bool:
    ours = removed.get("permissions_ask")
    if not ours:
        return False
    ask = data.setdefault("permissions", {}).setdefault("ask", [])
    changed = False
    for r in ours:
        if r not in ask:
            ask.append(r)
            changed = True
    return changed



def remove_codex_toml(text: str) -> tuple[str, list]:
    """Удалить секции [mcp_servers.X], ссылающиеся на чулан — включая
    [mcp_servers.X.env]: тело родителя может не содержать CHULAN (env в
    под-секции). Возвращает (new_text, removed_blocks)."""
    chulan = str(CHULAN)
    lines = text.splitlines()
    out, removed = [], []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("[mcp_servers."):
            header = ln.strip()[1:-1]
            block = [ln]
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("["):
                block.append(lines[j])
                j += 1
            # под-секция .env этого сервера (следующий блок, если он есть)
            sub = []
            k = j
            if (j < len(lines)
                    and lines[j].strip() == f"[{header}.env]"):
                sub = [lines[j]]
                m = j + 1
                while m < len(lines) and not lines[m].strip().startswith("["):
                    sub.append(lines[m])
                    m += 1
                k = m
            if chulan in "\n".join(block + sub):
                removed.append("\n".join(block))
                if sub:
                    removed.append("\n".join(sub))
                if out and out[-1].strip() == "":
                    out.pop()
                i = k
                continue
            out.extend(block)
            i = j
        else:
            out.append(ln)
            i += 1
    return "\n".join(out) + "\n", removed


def insert_codex_toml(text: str, removed: list) -> tuple[str, bool]:
    changed = False
    for block in removed:
        header = block.splitlines()[0].strip()
        if header not in text:
            if text and not text.endswith("\n\n"):
                text += "\n"
            text += block + "\n"
            changed = True
    return text, changed


# ---------- codewhale config.toml ([[hooks.hooks]] aggg2-guard) ----------

def remove_codewhale_toml(text: str) -> tuple[str, list]:
    """Удалить наш блок [[hooks.hooks]] (сигнатура: имя aggg2-guard или
    aggg2_prompt_hook в команде) вместе с комментарием-заголовком."""
    lines = text.splitlines()
    out, removed, i = [], [], 0
    while i < len(lines):
        ln = lines[i]
        stripped = ln.strip()
        if stripped.startswith("# AGGG2.0-прошивка"):
            block = [ln]
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("[["):
                block.append(lines[j])
                j += 1
            removed.append("\n".join(block))
            i = j
            continue
        if stripped.startswith("[[hooks.hooks]]"):
            block = [ln]
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("["):
                block.append(lines[j])
                j += 1
            body = "\n".join(block)
            if "aggg2" in body:
                removed.append(body)
                if out and out[-1].strip() == "":
                    out.pop()
            else:
                out.extend(block)
            i = j
        else:
            out.append(ln)
            i += 1
    return "\n".join(out) + "\n", removed


def insert_codewhale_toml(text: str, removed: list) -> tuple[str, bool]:
    changed = False
    for block in removed:
        if "aggg2" not in text:
            if text and not text.endswith("\n\n"):
                text += "\n"
            text += block + "\n"
            changed = True
    return text, changed


# ---------- hermes config.yaml (hooks + mcp_servers) ----------

def remove_hermes_yaml(text: str) -> tuple[str, list]:
    """Удалить из config.yaml: entry нашего хука в pre_tool_call (3 строки)
    и записи mcp_servers с путём чулана. Возвращает (new_text, removed)."""
    chulan = str(CHULAN)
    lines = text.splitlines()
    out, removed, i = [], [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("- command:") and SIG_HOOK in ln:
            block = [lines[i], lines[i + 1], lines[i + 2]]
            removed.append("\n".join(block))
            i += 3
            continue
        out.append(ln)
        i += 1
    # второй проход: mcp_servers — запись вида "  имя:" + вложенные строки
    text2 = "\n".join(out)
    lines2 = text2.splitlines()
    out2, i = [], 0
    in_mcp = False
    while i < len(lines2):
        ln = lines2[i]
        stripped = ln.strip()
        if stripped == "mcp_servers:":
            in_mcp = True
            out2.append(ln)
            i += 1
            continue
        if in_mcp and stripped and not ln[0].isspace():
            in_mcp = False
        if in_mcp and ln.startswith("  ") and not ln.startswith("    ") and stripped.endswith(":"):
            block = [ln]
            j = i + 1
            while j < len(lines2) and lines2[j].startswith("    "):
                block.append(lines2[j])
                j += 1
            if chulan in "\n".join(block):
                removed.append("\n".join(block))
                i = j
                continue
            out2.extend(block)
            i = j
            continue
        out2.append(ln)
        i += 1
    return "\n".join(out2) + "\n", removed


def insert_hermes_yaml(text: str, removed: list) -> tuple[str, bool]:
    changed = False
    for block in removed:
        head = block.splitlines()[0].strip()
        if head.startswith("- command:") and SIG_HOOK in text:
            continue
        if head.endswith(":") and head in text:
            continue
        text = text.rstrip("\n") + "\n" + block + "\n"
        changed = True
    return text, changed
