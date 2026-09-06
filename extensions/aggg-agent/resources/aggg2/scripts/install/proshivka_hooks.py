# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""proshivka_hooks — apply-функции хуков всех харнесов:
claude/codex/reasonix/codewhale/hermes/gemini/antigravity/omp
(включая YAML-хирургию hermes: _ensure_hermes_hooks/_auto_accept/
_seed_hermes_allowlist).

Вынесено из install_proshivka.py механически (verbatim) — гейт god-файлов.
"""
import json
import shutil
from pathlib import Path

from jsonc_edit import load_jsonc, write_json
from proshivka_helpers import (
    MATCHER_AGY,
    MATCHER_CLAUDE,
    MATCHER_GEMINI,
    MATCHER_OMP,
    SRC,
    _deploy_hooks,
    _ensure_json_hook,
    _matcher_upgrade,
    _python_cmd,
    deploy_file,
)


def apply_claude_hooks(args) -> bool:
    """Claude Code: ~/.claude/settings.json + хук в ~/.claude/hooks/.

    UserPromptSubmit (ядро в каждый промпт) + PreToolUse (сторож запретов:
    block опасных Bash-команд, напоминание QA/CHANGELOG на правках кода).
    """
    hooks_dir = Path.home() / ".claude" / "hooks"
    py = _python_cmd()
    changed = _deploy_hooks(hooks_dir, args)
    src_gate = SRC / "hooks" / "stop_qa_gate.py"
    if src_gate.is_file():
        changed |= deploy_file(src_gate, hooks_dir / "stop_qa_gate.py", args)
    settings = Path.home() / ".claude" / "settings.json"
    command = f"{py} {hooks_dir / 'aggg2_prompt_hook.py'}"
    changed |= _ensure_json_hook(settings, "UserPromptSubmit", command, args)
    changed |= _ensure_json_hook(settings, "PreToolUse", command, args,
                                 matcher=MATCHER_CLAUDE)
    stop_command = f"{py} {hooks_dir / 'stop_qa_gate.py'}"
    changed |= _ensure_json_hook(settings, "Stop", stop_command, args)
    ses_command = f"{py} {hooks_dir / 'session_end_gate.py'}"
    changed |= _ensure_json_hook(settings, "SessionEnd", ses_command, args)
    return changed


def apply_codex_hooks(args) -> bool:
    """Codex: ~/.codex/hooks.json + хук в ~/.codex/hooks/ (нужен /hooks trust).

    UserPromptSubmit (ядро) + PreToolUse (сторож запретов на Bash).
    """
    hooks_dir = Path.home() / ".codex" / "hooks"
    py = _python_cmd()
    changed = _deploy_hooks(hooks_dir, args)
    settings = Path.home() / ".codex" / "hooks.json"
    command = f"{py} {hooks_dir / 'aggg2_prompt_hook.py'}"
    changed |= _ensure_json_hook(settings, "UserPromptSubmit", command, args)
    changed |= _ensure_json_hook(settings, "PreToolUse", command, args,
                                 matcher="Bash")
    if not args.dry_run:
        print("[!] Codex: при первом запуске подтвердите хук: /hooks (trust)")
    # matcher=Bash: PreToolUse в Codex перехватывает ТОЛЬКО shell — by design
    # (apply_patch/Edit/Write/Read не шлют событие; ресёрч 15.08: codex hooks
    # docs, issue #16732). Файл-гейт для codex-edit = pre-commit + CI + ядро.
    return changed


def apply_reasonix_hooks(args) -> bool:
    """Reasonix: ~/.reasonix/settings.json (global, всегда доверен) + хук.

    PreToolUse (gating: exit 2 = блок, payload CamelCase — internal/hook/
    hook.go): сторож запретов на bash. UserPromptSubmit не подключаем —
    reasonix не шлёт stdout-контекст модели, только юзеру (ядро инжектится
    через AGENTS.md, который уже разносится install_agents.py).
    """
    hooks_dir = Path.home() / ".reasonix" / "hooks"
    py = _python_cmd()
    changed = _deploy_hooks(hooks_dir, args)
    settings = Path.home() / ".reasonix" / "settings.json"
    data = {}
    if settings.is_file():
        try:
            # utf-8-sig: BOM (Windows) не должен убивать парсинг —
            # битый конфиг НЕ перезаписываем (багрепорт v2.4 BUG-3).
            data = json.loads(settings.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001 — конфиг не трогаем
            print(f"[!] не могу разобрать конфиг {settings}: {e!r}")
            print("    конфиг НЕ тронут — разберись с файлом и повтори")
            return changed
    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    command = f"{py} {hooks_dir / 'aggg2_prompt_hook.py'}"
    for grp in pre:
        if grp.get("command") == command:
            print(f"[=] hook уже в конфиге: PreToolUse -> {settings}")
            return changed
    pre.append({"match": "bash", "command": command})
    # match=bash: reasonix-гейт покрывает shell; edit-тулы через hook не
    # перехватываются (internal/hook/hook.go) — файл-гейт для reasonix =
    # pre-commit + CI + ядро в AGENTS.md (матрица — docs/canon/FILE-SIZE.md).
    if args.dry_run:
        print(f"[ ] (dry-run) hook PreToolUse -> {settings}")
        return changed
    if settings.is_file():
        bak = settings.with_suffix(settings.suffix + ".bak")
        shutil.copy2(settings, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(settings), data)
    print(f"[✓] hook PreToolUse -> {settings}")
    return True

def apply_codewhale_hooks(args) -> bool:
    """Codewhale: ~/.codewhale/config.toml [[hooks.hooks]] + хук.

    tool_call_before (docs/HOOKS.md): контекст в env
    DEEPSEEK_TOOL_NAME/DEEPSEEK_TOOL_ARGS, вердикт — stdout JSON
    {decision, reason, additionalContext}. Только TUI-режим (не exec).
    """
    hooks_dir = Path.home() / ".codewhale" / "hooks"
    py = _python_cmd()
    changed = _deploy_hooks(hooks_dir, args)
    cfg = Path.home() / ".codewhale" / "config.toml"
    if not cfg.is_file():
        print(f"[!] нет конфига codewhale: {cfg}")
        return changed
    text = cfg.read_text(encoding="utf-8", errors="replace")
    if "aggg2_prompt_hook" in text:
        print(f"[=] hook уже в конфиге: tool_call_before -> {cfg}")
        return changed
    hook_block = (
        "# AGGG2.0-прошивка: сторож запретов (install_proshivka.py)\n"
        "[[hooks.hooks]]\n"
        'event = "tool_call_before"\n'
        'name = "aggg2-guard"\n'
        f'command = "{py} {hooks_dir / "aggg2_prompt_hook.py"}"\n'
        'condition = { type = "tool_name", name = "exec_shell" }\n'
    )
    addition = ("\n[hooks]\nenabled = true\n" if "[hooks]" not in text else "\n") + hook_block
    if args.dry_run:
        print(f"[ ] (dry-run) tool_call_before -> {cfg}")
        return changed
    bak = cfg.with_suffix(cfg.suffix + ".bak")
    shutil.copy2(cfg, bak)
    print(f"[~] бэкап конфига -> {bak}")
    with open(cfg, "a", encoding="utf-8") as f:
        f.write(addition)
    print(f"[✓] hook tool_call_before -> {cfg}")
    return True

from proshivka_hermes import (  # noqa: F401 — контракт (тесты)
    _ensure_hermes_auto_accept,
    _ensure_hermes_hooks,
    _seed_hermes_allowlist,
    apply_hermes_hook,
)


def apply_gemini_hooks(args) -> bool:
    """Gemini CLI: ~/.gemini/settings.json hooks.BeforeTool + хук-скрипт.

    Сторож запретов (geminicli.com/docs/hooks/reference): matcher —
    run_shell_command; блок = stdout {"decision":"deny"} + exit 2.
    Инъекция ядра не нужна: монолит уже в ~/.gemini/GEMINI.md (каждый
    промпт). Режим хука — env AGGG2_HOOK_MODE=gemini (префикс в команде,
    как у omp).
    """
    hooks_dir = Path.home() / ".gemini" / "hooks"
    src_hook = SRC / "hooks" / "aggg2_prompt_hook.py"
    if not src_hook.is_file():
        print(f"[!] нет источника хука: {src_hook}")
        return False
    changed = deploy_file(src_hook, hooks_dir / "aggg2_prompt_hook.py", args)
    # hook_gates.py — гейты (резка god-файла): едет рядом с хуком
    src_gates = SRC / "hooks" / "hook_gates.py"
    if src_gates.is_file():
        changed |= deploy_file(src_gates, hooks_dir / "hook_gates.py", args)
    src_hints = SRC / "hooks" / "hook_hints.py"
    if src_hints.is_file():
        changed |= deploy_file(src_hints, hooks_dir / "hook_hints.py", args)
    settings = Path.home() / ".gemini" / "settings.json"
    data = {}
    if settings.is_file():
        try:
            data = load_jsonc(str(settings))
        except Exception as e:  # noqa: BLE001 — конфиг не трогаем
            print(f"[!] не могу разобрать конфиг {settings}: {e!r}")
            print("    конфиг НЕ тронут — разберись с файлом и повтори")
            return changed
    hooks = data.setdefault("hooks", {})
    before = hooks.setdefault("BeforeTool", [])
    command = (f"AGGG2_HOOK_MODE=gemini {_python_cmd()} "
               f"{hooks_dir / 'aggg2_prompt_hook.py'}")
    for grp in before:
        for h in grp.get("hooks", []):
            if h.get("command") == command:
                changed |= _matcher_upgrade(settings, data, grp,
                                            MATCHER_GEMINI, args,
                                            "BeforeTool")
                print(f"[=] hook уже в конфиге: BeforeTool -> {settings}")
                return changed
    before.append({"matcher": MATCHER_GEMINI,
                   "hooks": [{"type": "command", "command": command,
                              "name": "aggg2-storozh", "timeout": 10000}]})
    if args.dry_run:
        print(f"[ ] (dry-run) hook BeforeTool -> {settings}")
        return changed
    if settings.is_file():
        bak = settings.with_suffix(settings.suffix + ".bak")
        shutil.copy2(settings, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(settings), data)
    print(f"[✓] hook BeforeTool -> {settings}")
    print("[!] gemini-cli: /hooks enable aggg2-storozh (или /hooks enable-all)")
    return True

def apply_antigravity_hooks(args) -> bool:
    """Antigravity 2.0 / IDE / agy CLI: ~/.gemini/config/hooks.json.

    PreToolUse, matcher run_command (antigravity.google/docs/hooks);
    гейт — stdout {"decision":"deny","reason"} (exit 0). Инъекция ядра
    не нужна: монолит уже в ~/.gemini/GEMINI.md.
    """
    hooks_dir = Path.home() / ".gemini" / "hooks"
    src_hook = SRC / "hooks" / "aggg2_prompt_hook.py"
    if not src_hook.is_file():
        print(f"[!] нет источника хука: {src_hook}")
        return False
    changed = deploy_file(src_hook, hooks_dir / "aggg2_prompt_hook.py", args)
    # hook_gates.py — гейты (резка god-файла): едет рядом с хуком
    src_gates = SRC / "hooks" / "hook_gates.py"
    if src_gates.is_file():
        changed |= deploy_file(src_gates, hooks_dir / "hook_gates.py", args)
    src_hints = SRC / "hooks" / "hook_hints.py"
    if src_hints.is_file():
        changed |= deploy_file(src_hints, hooks_dir / "hook_hints.py", args)
    hooks_json = Path.home() / ".gemini" / "config" / "hooks.json"
    data = {}
    if hooks_json.is_file():
        try:
            data = load_jsonc(str(hooks_json))
        except Exception as e:  # noqa: BLE001 — конфиг не трогаем
            print(f"[!] не могу разобрать конфиг {hooks_json}: {e!r}")
            print("    конфиг НЕ тронут — разберись с файлом и повтори")
            return changed
    command = f"{_python_cmd()} {hooks_dir / 'aggg2_prompt_hook.py'}"
    for _hname, conf in data.items():
        if not isinstance(conf, dict):
            continue
        for grp in conf.get("PreToolUse", []):
            for h in grp.get("hooks", []):
                if h.get("command") == command:
                    changed |= _matcher_upgrade(hooks_json, data, grp,
                                                MATCHER_AGY, args,
                                                "PreToolUse")
                    print(f"[=] hook уже в конфиге: PreToolUse -> {hooks_json}")
                    return changed
    data["aggg2-storozh"] = {
        "PreToolUse": [{"matcher": MATCHER_AGY,
                        "hooks": [{"type": "command", "command": command,
                                   "timeout": 10}]}],
    }
    if args.dry_run:
        print(f"[ ] (dry-run) hook PreToolUse -> {hooks_json}")
        return changed
    hooks_json.parent.mkdir(parents=True, exist_ok=True)
    if hooks_json.is_file():
        bak = hooks_json.with_suffix(hooks_json.suffix + ".bak")
        shutil.copy2(hooks_json, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(hooks_json), data)
    print(f"[✓] hook PreToolUse -> {hooks_json}")
    return True

def apply_omp_hooks(args) -> bool:
    """omp: ~/.omp/agent/settings.json (Claude-формат, плагин omp-hooks) + хук.

    PreToolUse: блок только через exit 2 + stderr; stdout при exit 0 —
    скрытый контекст модели. Режим хука — env AGGG2_HOOK_MODE=omp.
    Требуется установленный плагин: omp install omp-hooks.
    """
    hooks_dir = Path.home() / ".omp" / "hooks"
    py = _python_cmd()
    changed = _deploy_hooks(hooks_dir, args)
    settings = Path.home() / ".omp" / "agent" / "settings.json"
    data = {}
    if settings.is_file():
        try:
            # utf-8-sig: BOM (Windows) не должен убивать парсинг —
            # битый конфиг НЕ перезаписываем (багрепорт v2.4 BUG-3).
            data = json.loads(settings.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001 — конфиг не трогаем
            print(f"[!] не могу разобрать конфиг {settings}: {e!r}")
            print("    конфиг НЕ тронут — разберись с файлом и повтори")
            return changed
    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    command = f"AGGG2_HOOK_MODE=omp {py} {hooks_dir / 'aggg2_prompt_hook.py'}"
    for grp in pre:
        for h in grp.get("hooks", []):
            if h.get("command") == command:
                changed |= _matcher_upgrade(settings, data, grp,
                                            MATCHER_OMP, args, "PreToolUse")
                print(f"[=] hook уже в конфиге: PreToolUse -> {settings}")
                return changed
    pre.append({"matcher": MATCHER_OMP, "hooks": [{"type": "command", "command": command}]})
    if args.dry_run:
        print(f"[ ] (dry-run) hook PreToolUse -> {settings}")
        return changed
    if settings.is_file():
        bak = settings.with_suffix(settings.suffix + ".bak")
        shutil.copy2(settings, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(settings), data)
    print(f"[✓] hook PreToolUse -> {settings}")
    print("[!] omp: перезапустите omp или /reload, чтобы omp-hooks подхватил хук")
    return True

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
