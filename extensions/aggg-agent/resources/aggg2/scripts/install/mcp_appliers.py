#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""Форматы записи MCP-конфигов харнесов (apply_* + APPLY).

Вынесено из install_mcp.py (резка soft-файла, docs/canon/FILE-SIZE.md: per-concern
модули + тонкий barrel, перенос verbatim). Отдельный concern: КАК пишутся
конфиги харнесов (opencode/claude/codex/deepcode/codewhale/hermes/google/
gemini/omp/mcp-json) — без реестра серверов и CLI.

_known_server_names из реестра (install_mcp) берётся на месте вызова:
from install_mcp import _known_server_names (apply_opencode/apply_hermes).
"""


import json
import os
import sys

# Общие YAML-хирурги (текстовая замена top-level блоков без парсера —
# парсер убил бы комментарии пользователя): живут в _compat.py,
# используются apply_hermes здесь и hermes-хуком в install_proshivka.py.
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from _compat import replace_top_level_yaml_block, yaml_scalar  # noqa: E402
from jsonc_edit import (  # noqa: E402
    _edit_mcp_section,  # jsonc-редактор (см. jsonc-surgical-edit)
    _opencode_entry,
    write_json,
)


def apply_opencode(path, servers, clean_stale=False):
    if not os.path.exists(path):
        write_json(path, {"mcp": {name: _opencode_entry(s["command"],
                                                        s.get("env"))
                                  for name, s in servers.items()}})
        return
    # utf-8-sig: конфиги с BOM (Windows) не должны убивать парсинг —
    # багрепорт v2.4 BUG-3 (BOM → JSONDecodeError → пустой конфиг).
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read()
    from install_mcp import _known_server_names
    new = _edit_mcp_section(raw, servers, _known_server_names(), clean_stale)
    if new is None:  # файл не парсится — НЕ пишем пустышку (BUG-3)
        print(f"[!] не могу разобрать конфиг {path} — НЕ тронут")
        print("    разберись с файлом и повтори установку MCP")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)


def apply_claude(path, servers, clean_stale=False):
    data = {}
    if os.path.exists(path):
        try:
            # utf-8-sig: BOM (Windows) не должен убивать парсинг —
            # битый конфиг НЕ перезаписываем (багрепорт v2.4 BUG-3).
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] не могу разобрать конфиг {path}: {e!r} — НЕ тронут")
            return
    mcp = data.setdefault("mcpServers", {})
    for name in servers:
        mcp.pop(name, None)
    for name, s in servers.items():
        entry = {"command": s["command"][0], "args": s["command"][1:]}
        if s.get("env"):
            entry["env"] = s["env"]
        mcp[name] = entry
    write_json(path, data)


def apply_codex(path, servers, clean_stale=False):
    """Codex config.toml: секции [mcp_servers.<имя>]. Чистый merge: удаляются
    только ДОСТАВЛЯЕМЫЕ секции перед записью (повторный запуск не копит
    дубли, чужие секции не трогает), command экранируется через json.dumps —
    на Windows пути вида C:\\Users\\... в «сыром» виде дают невалидный TOML
    (\\U, \\a — invalid escape). Инцидент 16.08: [mcp_servers.<имя>.env]
    (под-таблица env) НЕ удалялась — TOML запрещает дубли ключей, Codex
    падал 'duplicate key' (openai/codex#13464). Теперь вычищаются и
    вложенные под-таблицы [mcp_servers.<имя>.*] (не только .env)."""
    lines = []
    if os.path.exists(path):
        # utf-8-sig: BOM (Windows) на первой строке ломал бы [hooks]-маппинг
        # (багрепорт v2.4 BUG-3 — класс BOM в конфигах).
        with open(path, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    tops = {f"[mcp_servers.{name}]" for name in servers}
    subs = tuple(f"[mcp_servers.{name}." for name in servers)
    out, skip = [], False
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            skip = stripped in tops or stripped.startswith(subs)
            if not skip:
                out.append(ln)
            continue
        if not skip:
            out.append(ln)
    text = "\n".join(out)
    for name, s in servers.items():
        cmd = s["command"]
        text += (f"\n[mcp_servers.{name}]\n"
                 f"command = {json.dumps(cmd[0])}\n"
                 f"args = {json.dumps(cmd[1:])}\n")
        # env — под-таблица [mcp_servers.name.env] (формат дока Codex MCP)
        if s.get("env"):
            text += f"\n[mcp_servers.{name}.env]\n"
            for k, v in s["env"].items():
                text += f"{k} = {json.dumps(v)}\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")


def apply_deepcode(path, servers, clean_stale=False):
    data = {}
    if os.path.exists(path):
        try:
            # utf-8-sig: BOM (Windows) не должен убивать парсинг —
            # битый конфиг НЕ перезаписываем (багрепорт v2.4 BUG-3).
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] не могу разобрать конфиг {path}: {e!r} — НЕ тронут")
            return
    mcp = data.setdefault("mcpServers", {})
    for name in servers:
        mcp.pop(name, None)
    for name, s in servers.items():
        entry = {"command": s["command"][0], "args": s["command"][1:]}
        if s.get("env"):
            entry["env"] = s["env"]
        mcp[name] = entry
    write_json(path, data)


def apply_codewhale(path, servers, clean_stale=False):
    """~/.codewhale/mcp.json: ключ servers, поля command/args/env
    (github.com/Hmbown/CodeWhale docs/MCP.md)."""
    data = {}
    if os.path.exists(path):
        try:
            # utf-8-sig: BOM (Windows) не должен убивать парсинг —
            # битый конфиг НЕ перезаписываем (багрепорт v2.4 BUG-3).
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] не могу разобрать конфиг {path}: {e!r} — НЕ тронут")
            return
    mcp = data.setdefault("servers", {})
    for name in servers:
        mcp.pop(name, None)
    for name, s in servers.items():
        entry = {"command": s["command"][0],
                 "args": s["command"][1:]}
        if s.get("env"):
            entry["env"] = s["env"]
        mcp[name] = entry
    write_json(path, data)


def _hermes_server_lines(name, s):
    """Строки записи сервера в блоке mcp_servers (отступ 2 пробела).

    Схема Hermes (docs/reference/mcp-config-reference): command (строка) +
    args (список) + env (mapping). Наш command-список конвертируется:
    первый элемент — command, остальные — args (как в codewhale)."""
    lines = [f"  {name}:"]
    cmd = s["command"]
    lines.append(f"    command: {yaml_scalar(cmd[0])}")
    if len(cmd) > 1:
        lines.append("    args:")
        for a in cmd[1:]:
            lines.append(f"      - {yaml_scalar(a)}")
    env = s.get("env") or {}
    if env:
        lines.append("    env:")
        for k, v in env.items():
            lines.append(f"      {k}: {yaml_scalar(v)}")
    return lines


def _parse_hermes_block(block_text):
    """Разбирает СОДЕРЖИМОЕ блока mcp_servers на {имя: [сырые строки]}.

    Запись начинается строкой с РОВНО 2 пробелами и ':' в имени; вложенные
    строки (4+ пробелов) принадлежат записи. Строки до первой записи
    (комментарии) — ключ '' (вставляются сверху нового блока). Чужие записи
    сохраняются verbatim — их содержимое мы не интерпретируем."""
    entries = {}
    cur = None
    for line in block_text.splitlines():
        if line.startswith("  ") and not line.startswith("    ") \
                and ":" in line.strip():
            name = line.strip().split(":", 1)[0].strip()
            cur = name
            entries.setdefault(cur, []).append(line)
        else:
            entries.setdefault("" if cur is None else cur, []).append(line)
    return entries


def _merge_hermes_block(old_block_text, servers, known_names, clean_stale):
    """Новый текст блока mcp_servers: наши серверы (перезаписывают свои
    старые версии) + чужие записи verbatim. clean_stale вычищает имена,
    которые когда-то разносили МЫ, а сейчас в наборе нет (полная установка);
    чужие записи не трогаются никогда."""
    entries = _parse_hermes_block(old_block_text)
    header = entries.pop("", [])
    for name, s in servers.items():
        entries[name] = _hermes_server_lines(name, s)
    if clean_stale:
        for stale in known_names - set(servers):
            entries.pop(stale, None)
    lines = ["mcp_servers:"]
    lines += header
    for name, elines in entries.items():
        if name in servers:
            lines += elines
    for name, elines in entries.items():
        if name not in servers:
            lines += elines
    return "\n".join(lines) + "\n"


def apply_hermes(path, servers, clean_stale=False):
    """~/.hermes/config.yaml: top-level блок mcp_servers (YAML).

    Текстовая хирургия БЕЗ YAML-парсера (jsonc-parser-философия, но для
    YAML): парсер (pyyaml/ruamel) переписал бы файл и убил комментарии.
    Чужие записи внутри блока сохраняются verbatim — интерпретируем только
    свои имена. clean_stale чистит устаревшие НАШИ записи (как у других
    харнесов), чужие не трогаются. Паттерн: микросервис-конфиг, секция —
    наша, остальное — пользователя."""
    old_block = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if line and not line[0].isspace() and stripped == "mcp_servers:":
                # контент блока: строки с отступом после ключа (до первой
                # top-level строки или конца файла)
                cut = 0
                for ln in lines[idx + 1:]:
                    if ln.strip() and not ln[0].isspace():
                        break
                    cut += 1
                body = lines[idx + 1: idx + 1 + cut]
                old_block = "\n".join(body) + ("\n" if body else "")
                break
    from install_mcp import _known_server_names
    merged = _merge_hermes_block(old_block, servers,
                                 set(_known_server_names()), clean_stale)
    if not os.path.exists(path):
        merged = ("# MCP-серверы AGGG2.0 (управляется install_mcp.py — "
                  "блок mcp_servers перезаписывается)\n" + merged)
    replace_top_level_yaml_block(path, merged, "mcp_servers:")


def apply_google_mcp(path, servers, clean_stale=False):
    """~/.gemini/config/mcp_config.json (Antigravity 2.0 / IDE / agy CLI):
    единый объект mcpServers, stdio-поля command/args/env
    (antigravity.google/docs/mcp). Тот же контракт, что codewhale."""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] не могу разобрать конфиг {path}: {e!r} — НЕ тронут")
            return
    mcp = data.setdefault("mcpServers", {})
    for name in servers:
        mcp.pop(name, None)
    for name, s in servers.items():
        entry = {"command": s["command"][0], "args": s["command"][1:]}
        if s.get("env"):
            entry["env"] = s["env"]
        mcp[name] = entry
    write_json(path, data)


def apply_gemini(path, servers, clean_stale=False):
    """~/.gemini/settings.json (Gemini CLI): top-level mcpServers, поля
    command/args/env (geminicli.com/docs/tools/mcp-server). JSON-конфиг —
    json round-trip, как ~/.claude.json: данные сохраняются, форматирование
    нормализуется."""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] не могу разобрать конфиг {path}: {e!r} — НЕ тронут")
            return
    mcp = data.setdefault("mcpServers", {})
    for name in servers:
        mcp.pop(name, None)
    for name, s in servers.items():
        entry = {"command": s["command"][0], "args": s["command"][1:]}
        if s.get("env"):
            entry["env"] = s["env"]
        mcp[name] = entry
    write_json(path, data)


def apply_omp_mcp(path, servers, clean_stale=False):
    """~/.omp/agent/mcp.json (oh-my-pi): mcpServers, stdio-записи
    type/command/args/env (can1357/oh-my-pi docs/mcp-config.md)."""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] не могу разобрать конфиг {path}: {e!r} — НЕ тронут")
            return
    mcp = data.setdefault("mcpServers", {})
    for name in servers:
        mcp.pop(name, None)
    for name, s in servers.items():
        entry = {"type": "stdio", "command": s["command"][0],
                 "args": s["command"][1:]}
        if s.get("env"):
            entry["env"] = s["env"]
        mcp[name] = entry
    write_json(path, data)


def apply_mcp_json(path, servers, clean_stale=False):
    """Claude-style mcpServers JSON (command/args/env) — общий для харнесов,
    использующих этот формат: Cursor (~/.cursor/mcp.json, cursor.com/docs/
    cli/using + оmp-трансляция), Windsurf (~/.codeium/windsurf/mcp_config.json,
    оmp-трансляция), Kiro (~/.kiro/settings/mcp.json, kiro.dev/docs/mcp/
    configuration)."""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] не могу разобрать конфиг {path}: {e!r} — НЕ тронут")
            return
    mcp = data.setdefault("mcpServers", {})
    for name in servers:
        mcp.pop(name, None)
    for name, s in servers.items():
        entry = {"command": s["command"][0], "args": s["command"][1:]}
        if s.get("env"):
            entry["env"] = s["env"]
        mcp[name] = entry
    write_json(path, data)


APPLY = {"opencode": apply_opencode, "claude": apply_claude,
         "codex": apply_codex, "deepcode": apply_deepcode,
         "codewhale": apply_codewhale, "hermes": apply_hermes,
         "google-mcp": apply_google_mcp, "gemini": apply_gemini,
         "omp-mcp": apply_omp_mcp, "mcp-json": apply_mcp_json}
