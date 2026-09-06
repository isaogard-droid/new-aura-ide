#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Включить/выключить прошивку AGGG2.0 для конкретных харнесов.

Что выключает (по слоям, см. AGENTS.md «Прошивка правил»):
1. Прошивка правил — хуки-сторожа и ядро в конфигах харнесов, плагин
   opencode, agent.build.prompt, permissions, монолиты правил
   (AGENTS.md/CLAUDE.md/GEMINI.md/SOUL.md...).
2. Скиллы канона и агентов — каталоги скиллов харнеса.
3. Субагенты агентов — файлы в каталогах агентов харнесов.
4. MCP-серверы (db-tools, camoufox, agent-lsp, code-review-graph + серверы
   агентов) — записи в конфигах харнесов.

Принцип (паттерн индустрии — нативные переключатели: Claude Code
disableAllHooks, Codex --profile, opencode plugins/): ничего не удаляем
насовсем — артефакты переименовываются в <имя>.aggg2-off, конфиги правятся
хирургически (вынимаются только НАШИ записи по сигнатуре), что вынули —
хранится в ~/.aggg2/toggle-state.json и возвращается командой on.
on = обратная хирургия + переименование обратно. Обе операции обратимы
(two-way door), чужие настройки не трогаются, перед записью — бэкап .bak.

Shared-файлы (GEMINI.md, ~/.gemini/config/*, монолит ~/AGENTS.md, общий
~/.agents/skills/) выключаются только когда выключены ВСЕ владельцы (или
--all), и включаются обратно первым включённым владельцем.

Запуск:
    python3 scripts/install/toggle_proshivka.py status [harness ...]
    python3 scripts/install/toggle_proshivka.py off codex claude [--check]
    python3 scripts/install/toggle_proshivka.py on codex [--check]
    python3 scripts/install/toggle_proshivka.py off --all [--check]
    python3 scripts/install/toggle_proshivka.py on --all
    --proshivka-only   # только слой 1 (без скиллов/субагентов/MCP)
    --check            # план без записи (dry-run)

Проверка после off/on: перезапустите харнес (хуки/плагины читаются при
старте); `python3 scripts/install/toggle_proshivka.py status`.

Кроссплатформенно (Linux/macOS/Windows): все пути — через Path.home()
(первоисточники: code.claude.com/docs/en/settings — на Windows ~/.claude =
%USERPROFILE%/.claude; learn.chatgpt.com config-basic — ~/.codex;
opencode.ai/docs/config — ~/.config/opencode; geminicli docs —
~/.gemini/settings.json; hermes docs — ~/.hermes/). Нюанс: env-оверрайды
каталогов (CODEX_HOME, HERMES_HOME, OPENCODE_CONFIG_DIR и т.п.) не
учитываются — toggle идёт по стандартным ~/ путям, как и установщики
AGGG2.0 (при заданном оверрайде просто не найдёт файлы, ничего не сломает).
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # install/ — toggle хелперы
from pathlib import Path

from _compat import fix_encoding  # noqa: E402 — единый хелпер канона

fix_encoding()

from toggle.toggle_config_ops import (  # noqa: E402
    _insert_mcp_keys,
    _remove_mcp_keys,
    insert_agy_hooks,
    insert_claude_permissions,
    insert_codewhale_toml,
    insert_codex_toml,
    insert_gemini,
    insert_hermes_yaml,
    insert_hooks_generic,
    insert_opencode,
    insert_reasonix,
    remove_agy_hooks,
    remove_claude_permissions,
    remove_codewhale_toml,
    remove_codex_toml,
    remove_gemini,
    remove_hermes_yaml,
    remove_hooks_generic,
    remove_opencode,
    remove_reasonix,
)
from toggle.toggle_map import (  # noqa: E402,F401 — контракт (тесты)
    AGENT_DIRS,
    ALL,
    ARTIFACTS,
    CONFIGS,
    HARNESS_NAMES,
    SKILL_DIRS,
)
from toggle.toggle_state import (  # noqa: E402 — state-хелперы (резка soft)
    STATE_PATH,
    _backup,
    _load,
    _owners_off,
    _write,
    load_state,
    save_state,
)

CHULAN = Path(__file__).resolve().parent.parent


def canon_skill_names() -> set:
    """Имена скиллов, которые разносит install_agents (канон + агенты)."""
    names = set()
    for d in sorted((CHULAN / "skills").iterdir()):
        if (d / "SKILL.md").is_file():
            names.add(d.name)
    for ad in sorted((CHULAN / "agent").iterdir()):
        if ad.is_dir():
            for d in sorted((ad / "skills").iterdir()):
                if (d / "SKILL.md").is_file():
                    names.add(d.name)
    return names


def canon_subagent_names() -> set:
    """Имена субагентов (stem файлов agent/*/agents/* без харнес-суффикса)."""
    names = set()
    for ad in sorted((CHULAN / "agent").iterdir()):
        adir = ad / "agents"
        if not adir.is_dir():
            continue
        for f in sorted(adir.iterdir()):
            if f.suffix not in (".md", ".toml"):
                continue
            parts = f.stem.split(".")
            if len(parts) >= 2 and parts[-1] in HARNESS_NAMES:
                names.add(".".join(parts[:-1]))
            else:
                names.add(f.stem)
    return names


# ---------- off ----------

def _rename_off(path: Path, check: bool) -> bool:
    """Переименовать файл/каталог в <имя>.aggg2-off. True — отключено.
    Windows: файл, занятый процессом, не переименуется — предупреждаем,
    не роняем (перезапустите харнес и повторите)."""
    off_path = Path(str(path) + ".aggg2-off")
    if off_path.exists():
        return False
    if not path.exists():
        return False
    if check:
        print(f"[ ] (dry-run) {path} -> {off_path.name}")
        return False
    try:
        shutil.move(str(path), str(off_path))
    except OSError as e:
        print(f"[!] не могу отключить {path}: {e!r} — закройте харнес и "
              f"повторите")
        return False
    print(f"[✓] off: {off_path}")
    return True


def _config_remove(kind: str, path: Path, state: dict, check: bool) -> bool:
    """Вынуть наши записи из конфига. True — конфиг изменён/сохранён."""
    text_kinds = ("opencode", "codex-toml", "codewhale-toml", "hermes-yaml")
    if kind in text_kinds:
        text = path.read_text(encoding="utf-8-sig")
        if kind == "opencode":
            new_text, removed = remove_opencode(text)
        elif kind == "codex-toml":
            new_text, removed = remove_codex_toml(text)
        elif kind == "codewhale-toml":
            new_text, removed = remove_codewhale_toml(text)
        else:
            new_text, removed = remove_hermes_yaml(text)
        if not removed:
            return False
        if check:
            print(f"[ ] (dry-run) конфиг {path}: вынуто записей {len(removed)}")
            return False
        _backup(path)
        path.write_text(new_text, encoding="utf-8", newline="\n")
        print(f"[✓] off: {path}")
        state["configs"][str(path)] = {"kind": kind, "removed": removed}
        return True

    data = _load(path)
    if kind == "hooks":
        removed = remove_hooks_generic(data)
    elif kind == "claude-settings":
        removed = remove_hooks_generic(data)
        removed.update(remove_claude_permissions(data))
    elif kind == "reasonix":
        removed = remove_reasonix(data)
    elif kind == "gemini":
        removed = remove_gemini(data)
    elif kind == "agy-hooks":
        removed = remove_agy_hooks(data)
    elif kind == "claude-mcp":
        removed = _remove_mcp_keys(data, "mcpServers")
    elif kind == "mcp-servers":
        removed = _remove_mcp_keys(data, "servers")
    else:  # mcp-mcpServers
        removed = _remove_mcp_keys(data, "mcpServers")
    if not removed:
        return False
    if check:
        print(f"[ ] (dry-run) конфиг {path}: вынуто {len(removed)} секций")
        return False
    _backup(path)
    _write(path, data)
    print(f"[✓] off: {path}")
    state["configs"][str(path)] = {"kind": kind, "removed": removed}
    return True


def off_harness(name: str, state: dict, opts) -> None:
    print(f"\n=== off: {name} ===")
    check = opts.check
    all_mode = opts.all_mode
    done_any = False
    shared_note = set()

    if not opts.proshivka_only:
        for skill_dir, owners in SKILL_DIRS:
            if name not in owners:
                continue
            if not _owners_off(owners, state, all_mode, name):
                shared_note.update(o for o in owners if o != name)
                continue
            for d in sorted(skill_dir.iterdir() if skill_dir.is_dir() else []):
                if (d.is_dir() and d.name in canon_skill_names()
                        and _rename_off(d, check)):
                    done_any = True
                    state["files"].setdefault(str(d), {"owners": owners})
        for agent_dir, owners in AGENT_DIRS:
            if name not in owners:
                continue
            if not _owners_off(owners, state, all_mode, name):
                shared_note.update(o for o in owners if o != name)
                continue
            for f in sorted(agent_dir.iterdir() if agent_dir.is_dir() else []):
                if (f.is_file() and f.stem in canon_subagent_names()
                        and f.suffix in (".md", ".toml", ".agent.md")
                        and _rename_off(f, check)):
                    done_any = True
                    state["files"].setdefault(str(f), {"owners": owners})

    for path, owners in ARTIFACTS:
        if name not in owners:
            continue
        if not _owners_off(owners, state, all_mode, name):
            shared_note.update(o for o in owners if o not in (name, ALL))
            continue
        if _rename_off(path, check):
            done_any = True
            state["files"].setdefault(str(path), {"owners": owners})

    for path, kind, owners in CONFIGS:
        if name not in owners:
            continue
        if not _owners_off(owners, state, all_mode, name):
            shared_note.update(o for o in owners if o != name)
            continue
        if not path.is_file():
            continue
        if _config_remove(kind, path, state, check):
            done_any = True

    if not done_any and shared_note:
        print(f"[~] {name}: все слои shared с {', '.join(sorted(shared_note))} — "
              f"выключите их вместе (или --all)")
    if check:
        print(f"[ ] (dry-run) {name} -> off")
    elif name not in state["off"]:
        state["off"].append(name)
        state["off"].sort()


# ---------- on ----------

def _rename_on(path: Path, check: bool) -> bool:
    off_path = Path(str(path) + ".aggg2-off")
    if not off_path.exists():
        return False
    if check:
        print(f"[ ] (dry-run) {off_path.name} -> {path.name}")
        return False
    if path.exists():
        try:
            if off_path.is_file():
                off_path.unlink()
            else:
                shutil.rmtree(off_path)
        except OSError as e:
            print(f"[!] не могу снять {off_path.name}: {e!r}")
            return False
        print(f"[✓] on: {path} уже на месте, снят {off_path.name}")
    else:
        try:
            shutil.move(str(off_path), str(path))
        except OSError as e:
            print(f"[!] не могу включить {path}: {e!r} — закройте харнес и "
                  f"повторите")
            return False
        print(f"[✓] on: {path}")
    return True


def _config_insert(entry: dict, path: Path, check: bool) -> bool:
    kind, removed = entry["kind"], entry["removed"]
    text_kinds = ("opencode", "codex-toml", "codewhale-toml", "hermes-yaml")
    if kind in text_kinds:
        text = path.read_text(encoding="utf-8-sig")
        if kind == "opencode":
            new_text, changed = insert_opencode(text, removed)
            if "mcp_servers" in removed:
                print("[!] mcp-серверы opencode: вернёт install_mcp.py "
                      "(python3 scripts/install/install_mcp.py --harness opencode)")
        elif kind == "codex-toml":
            new_text, changed = insert_codex_toml(text, removed)
        elif kind == "codewhale-toml":
            new_text, changed = insert_codewhale_toml(text, removed)
        else:
            new_text, changed = insert_hermes_yaml(text, removed)
        if not changed:
            return False
        if check:
            print(f"[ ] (dry-run) конфиг {path}: вернул бы {len(removed)}")
            return False
        _backup(path)
        path.write_text(new_text, encoding="utf-8", newline="\n")
        print(f"[✓] on: {path}")
        return True

    data = _load(path)
    if kind == "hooks":
        changed = insert_hooks_generic(data, removed)
    elif kind == "claude-settings":
        changed = insert_hooks_generic(data, removed)
        changed = insert_claude_permissions(data, removed) or changed
    elif kind == "reasonix":
        changed = insert_reasonix(data, removed)
    elif kind == "gemini":
        changed = insert_gemini(data, removed)
    elif kind == "agy-hooks":
        changed = insert_agy_hooks(data, removed)
    elif kind in ("claude-mcp", "mcp-servers", "mcp-mcpServers"):
        changed = _insert_mcp_keys(data, removed)
    else:
        changed = False
    if not changed:
        return False
    if check:
        print(f"[ ] (dry-run) конфиг {path}: вернул бы {len(removed)}")
        return False
    _backup(path)
    _write(path, data)
    print(f"[✓] on: {path}")
    return True


def on_harness(name: str, state: dict, opts) -> None:
    print(f"\n=== on: {name} ===")
    check = opts.check
    all_mode = opts.all_mode

    for path_s, entry in list(state.get("files", {}).items()):
        path = Path(path_s)
        owners = tuple(entry.get("owners", ()))
        if name not in owners:
            continue
        if owners == (ALL,) and not all_mode:
            continue
        if _rename_on(path, check):
            del state["files"][path_s]

    for path_s, entry in list(state.get("configs", {}).items()):
        path = Path(path_s)
        owners = ()
        for cfg_path, _, cfg_owners in CONFIGS:
            if _same_path(cfg_path, path):
                owners = cfg_owners
                break
        if name not in owners:
            continue
        if owners == (ALL,) and not all_mode:
            continue
        if not path.is_file():
            continue
        if _config_insert(entry, path, check):
            del state["configs"][path_s]

    if name in state["off"] and not check:
        state["off"].remove(name)


def _same_path(a: Path, b: Path) -> bool:
    return str(a) == str(b)


# ---------- status ----------

def status(names: list | None) -> None:
    state = load_state()
    off = state.get("off", [])
    print(f"state: {STATE_PATH}")
    print(f"выключено: {', '.join(off) if off else '— (все харнесы включены)'}")
    print(f"отключённые файлы/скиллы/субагенты: {len(state.get('files', {}))}")
    for p in sorted(state.get("files", {})):
        print(f"  • {p} (.aggg2-off)")
    print(f"изменённые конфиги: {len(state.get('configs', {}))}")
    for p in sorted(state.get("configs", {})):
        print(f"  • {p}")
    if names:
        for n in names:
            print(f"{n}: {'OFF' if n in off else 'ON'}")


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(
        description="Включить/выключить прошивку AGGG2.0 для харнесов")
    ap.add_argument("command", choices=("off", "on", "status"))
    ap.add_argument("harnesses", nargs="*",
                    help="имена харнесов (status: необязательно) или --all")
    ap.add_argument("--all", action="store_true",
                    help="все харнесы (включая shared-слои)")
    ap.add_argument("--proshivka-only", action="store_true",
                    help="только прошивка правил (без скиллов/субагентов/MCP)")
    ap.add_argument("--check", action="store_true", help="план без записи")
    args = ap.parse_args()

    if args.command == "status":
        status(args.harnesses or None)
        return

    if args.harnesses and args.all:
        print("[!] укажите либо --all, либо список харнесов", file=sys.stderr)
        sys.exit(1)
    names = list(HARNESS_NAMES) if args.all else list(dict.fromkeys(args.harnesses))
    if not names:
        print(f"харнесы: {', '.join(HARNESS_NAMES)}", file=sys.stderr)
        sys.exit(1)
    unknown = [n for n in names if n not in HARNESS_NAMES]
    if unknown:
        print(f"[!] неизвестные харнесы: {', '.join(unknown)}", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    opts = argparse.Namespace(check=args.check, all_mode=args.all,
                              proshivka_only=args.proshivka_only)
    for name in names:
        if args.command == "off":
            off_harness(name, state, opts)
        else:
            on_harness(name, state, opts)

    if args.check:
        print("\n[dry-run] ничего не записано")
    else:
        save_state(state)
        print("\n[✓] готово. Перезапустите харнесы, чтобы изменения вступили "
              "в силу (хуки/плагины читаются при старте).")
        print(f"    state: {STATE_PATH}")


if __name__ == "__main__":
    main()

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
