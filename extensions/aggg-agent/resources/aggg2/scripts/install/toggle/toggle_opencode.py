# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""toggle_opencode — хирургия конфига opencode (json/jsonc) для выключения/
включения прошивки: agent.build.prompt, permission.edit (god-файлы из
снапшота установщика), mcp-серверы с путём чулана.

Вынесено из toggle_config_ops.py механически (verbatim) — гейт god-файлов
(docs/canon/FILE-SIZE.md). Текстовые правки по оффсетам (паттерн node-jsonc-parser,
jsonc_edit) — комментарии и чужой контент сохраняются.
"""
import json
import os
import sys

# scripts/ — кирпичи канона (jsonc_edit); подпапка toggle/ (деление каталога)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from pathlib import Path

from jsonc_edit import _jsonc_key_map

CHULAN = Path(__file__).resolve().parent.parent.parent
SIG_SNAPS = Path.home() / ".config" / "aggg2"  # снапшоты permissions


# ---------- opencode (json/jsonc: build.prompt + permissions + mcp) ----------

def _remove_in_object(raw: str, obj_vs: int, obj_ve: int, key: str):
    """Точечно удалить ключ key из JSONC-объекта (vs/ve — границы {}).
    Возвращает (new_raw, removed_value_text|None). Комментарии вокруг
    сохраняются (паттерн node-jsonc-parser)."""
    inner, _ = _jsonc_key_map(raw, 0, base=obj_vs + 1, limit=obj_ve - 1)
    if key not in inner:
        return raw, None
    kstart, vs, ve = inner[key]
    value_text = raw[vs:ve]
    s = kstart
    while s > obj_vs and raw[s - 1] in " \t\r\n":
        s -= 1
    if s > obj_vs and raw[s - 1] == ",":
        s -= 1  # снимаем запятую предыдущего элемента
    else:
        # первый элемент: снять запятую ПОСЛЕ значения
        e = ve
        while e < obj_ve and raw[e] in " \t\r\n":
            e += 1
        if e < obj_ve and raw[e] == ",":
            e += 1
        ve = e
    return raw[:s] + raw[ve:], value_text


def remove_opencode(raw: str, god_paths: list | None = None) -> tuple[str, dict]:
    """Вынуть из текста конфига opencode: agent.build.prompt (наш),
    permission.edit-ключи (god_paths; None — из снапшота установщика) и
    mcp-серверы с путём чулана. Возвращает (new_raw, removed)."""
    removed = {}
    try:
        top, root_end = _jsonc_key_map(raw, 1)
    except Exception:  # noqa: BLE001 — не JSON: не трогаем
        return raw, removed
    if root_end is None:
        return raw, removed

    edits = []  # (start, end, repl) — применяются с конца

    # 1) agent.build.prompt == {file:./prompts/build.txt}
    if "agent" in top:
        _, agent_vs, agent_ve = top["agent"]
        agent_inner, _ = _jsonc_key_map(raw, 0, base=agent_vs + 1,
                                        limit=agent_ve - 1)
        if "build" in agent_inner:
            _, build_vs, build_ve = agent_inner["build"]
            build_inner, _ = _jsonc_key_map(raw, 0, base=build_vs + 1,
                                            limit=build_ve - 1)
            if "prompt" in build_inner:
                _, p_vs, p_ve = build_inner["prompt"]
                prompt_val = raw[p_vs:p_ve]
                if "{file:./prompts/build.txt}" in prompt_val:
                    new_raw, gone = _remove_in_object(raw, build_vs, build_ve,
                                                      "prompt")
                    if gone is not None:
                        removed["agent_build_prompt"] = prompt_val
                        raw = new_raw
                        # карта могла сместиться — перестроить
                        top, root_end = _jsonc_key_map(raw, 1)

    # 2) permission.edit-ключи (по умолчанию — из снапшота file-size-paths.json)
    if god_paths is None:
        snap = SIG_SNAPS / "file-size-paths.json"
        god_paths = []
        if snap.is_file():
            try:
                loaded = json.loads(snap.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    god_paths = [p for p in loaded if isinstance(p, str)]
            except (OSError, ValueError):
                pass
    if god_paths and "permission" in top:
        _, perm_vs, perm_ve = top["permission"]
        perm_inner, _ = _jsonc_key_map(raw, 0, base=perm_vs + 1,
                                       limit=perm_ve - 1)
        if "edit" in perm_inner:
            _, edit_vs, edit_ve = perm_inner["edit"]
            gone_paths = []
            for p in god_paths:
                new_raw, gone = _remove_in_object(raw, edit_vs, edit_ve, p)
                if gone is not None:
                    raw = new_raw
                    gone_paths.append(p)
                    top, root_end = _jsonc_key_map(raw, 1)
                    _, perm_vs, perm_ve = top["permission"]
                    perm_inner, _ = _jsonc_key_map(raw, 0, base=perm_vs + 1,
                                                   limit=perm_ve - 1)
                    _, edit_vs, edit_ve = perm_inner["edit"]
            if gone_paths:
                removed["permission_edit"] = gone_paths

    # 3) mcp-серверы с путём чулана
    if "mcp" in top:
        _, mcp_vs, mcp_ve = top["mcp"]
        inner, _ = _jsonc_key_map(raw, 0, base=mcp_vs + 1, limit=mcp_ve - 1)
        gone_servers = {}
        for name in list(inner):
            vs, ve = inner[name][1], inner[name][2]
            if str(CHULAN) in raw[vs:ve]:
                gone_servers[name] = raw[vs:ve]
                s = inner[name][0]
                while s > mcp_vs and raw[s - 1] in " \t\r\n":
                    s -= 1
                if s > mcp_vs and raw[s - 1] == ",":
                    edits.append((s - 1, ve, ""))
                else:
                    e = ve
                    while e < mcp_ve and raw[e] in " \t\r\n":
                        e += 1
                    if e < mcp_ve and raw[e] == ",":
                        e += 1
                    edits.append((inner[name][0], e, ""))
        if gone_servers:
            removed["mcp_servers"] = gone_servers

    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        raw = raw[:start] + repl + raw[end:]
    return raw, removed


def insert_opencode(raw: str, removed: dict) -> tuple[str, bool]:
    """Вернуть в opencode-конфиг build.prompt и permission.edit (текстовая
    вставка недостающего). mcp-серверы не восстанавливаем — их вернёт
    install_mcp.py (см. toggle_proshivka.on: подсказка). Возвращает
    (new_raw, changed)."""
    try:
        top, root_end = _jsonc_key_map(raw, 1)
    except Exception:  # noqa: BLE001 — не JSON
        return raw, False
    if root_end is None:
        return raw, False
    changed = False

    # build.prompt
    if "agent_build_prompt" in removed:
        prompt_val = removed["agent_build_prompt"]
        if "{file:./prompts/build.txt}" not in raw and "agent" in top:
            _, agent_vs, agent_ve = top["agent"]
            agent_inner, _ = _jsonc_key_map(raw, 0, base=agent_vs + 1,
                                            limit=agent_ve - 1)
            if "build" in agent_inner:
                _, build_vs, build_ve = agent_inner["build"]
                build_inner, _ = _jsonc_key_map(raw, 0, base=build_vs + 1,
                                                limit=build_ve - 1)
                if "prompt" not in build_inner:
                    indent = len(raw[:build_vs].rsplit("\n", 1)[-1]) + 2
                    block = (" " * (indent + 2) + '"prompt": ' + prompt_val)
                    insert_at = build_ve - 1
                    while insert_at > build_vs and raw[insert_at - 1] in " \t\r\n":
                        insert_at -= 1
                    comma = ",\n" if raw[build_vs + 1:insert_at].strip() else "\n"
                    raw = (raw[:insert_at] + comma + block + "\n"
                           + " " * indent + raw[insert_at:])
                    changed = True
                    top, root_end = _jsonc_key_map(raw, 1)

    # permission.edit
    if "permission_edit" in removed and "permission" in top:
        _, perm_vs, perm_ve = top["permission"]
        perm_inner, _ = _jsonc_key_map(raw, 0, base=perm_vs + 1,
                                       limit=perm_ve - 1)
        if "edit" in perm_inner:
            _, edit_vs, edit_ve = perm_inner["edit"]
            edit_inner, _ = _jsonc_key_map(raw, 0, base=edit_vs + 1,
                                           limit=edit_ve - 1)
            missing = [p for p in removed["permission_edit"]
                       if p not in edit_inner]
            if missing:
                indent = len(raw[:edit_vs].rsplit("\n", 1)[-1]) + 2
                blocks = [(" " * (indent + 2) + json.dumps(p) + ": \"ask\"")
                          for p in missing]
                insert_at = edit_ve - 1
                while insert_at > edit_vs and raw[insert_at - 1] in " \t\r\n":
                    insert_at -= 1
                comma = ",\n" if raw[edit_vs + 1:insert_at].strip() else "\n"
                raw = (raw[:insert_at] + comma + ",\n".join(blocks) + "\n"
                       + " " * indent + raw[insert_at:])
                changed = True
    return raw, changed


# ---------- codex config.toml ([mcp_servers.*]) ----------
