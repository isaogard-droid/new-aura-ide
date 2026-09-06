# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""proshivka_hermes — hermes-хуки: YAML-хирургия
(_ensure_hermes_hooks/_auto_accept/_seed_hermes_allowlist) + apply_hermes_hook.

Вынесено из proshivka_hooks.py механически (verbatim) — гейт god-файлов.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
import shlex
import shutil
from pathlib import Path

from _compat import replace_top_level_yaml_block  # noqa: E402
from proshivka_helpers import MATCHER_HERMES, SRC, _python_cmd, deploy_file


def _ensure_hermes_hooks(cfg: Path, command: str, args) -> bool:
    """Вписывает pre_tool_call-хук в ~/.hermes/config.yaml (блок hooks:).

    YAML-текстовая хирургия без парсера (парсер убил бы комментарии) —
    тот же подход, что apply_hermes в install_mcp.py. Чужие записи внутри
    блока hooks сохраняются: если есть наш command — ничего не делаем,
    иначе вставляем свою запись в существующий pre_tool_call (или создаём
    секцию). Схема по источнику (agent/shell_hooks.py docstring: «Reads the
    hooks: block») + how-to (event → список {command, matcher, timeout}).
    ГРАБЛЯ: command пишется БЕЗ кавычек — Hermes режет его shlex.split
    (закавыченная строка стала бы одним токеном и хук не запустился);
    сам command собирается shlex.join (кавычки только при пробелах в пути).
    """
    entry_lines = [
        f"    - command: {command}",
        f'      matcher: "{MATCHER_HERMES}"',
        "      timeout: 10",
    ]
    header = "# AGGG2.0-прошивка: сторож запретов (install_proshivka.py)"
    if not cfg.is_file():
        block = "\n".join([header, "hooks:", "  pre_tool_call:"]
                          + entry_lines) + "\n"
        if args.dry_run:
            print(f"[ ] (dry-run) hooks: pre_tool_call -> {cfg}")
            return False
        cfg.parent.mkdir(parents=True, exist_ok=True)
        replace_top_level_yaml_block(str(cfg), block, "hooks:")
        print(f"[✓] hook pre_tool_call -> {cfg}")
        return True

    text = cfg.read_text(encoding="utf-8-sig")
    new_cmd_line = entry_lines[0]
    if "aggg2_prompt_hook.py" in text:
        if new_cmd_line in text:
            if f'      matcher: "{MATCHER_HERMES}"' in text:
                print(f"[=] hook уже в конфиге: pre_tool_call -> {cfg}")
                return False
            # матчер отстал (edit-тулы) — обновить только строку matcher
            lines = []
            for ln in text.splitlines():
                if ln.strip().startswith("matcher:") and "terminal" in ln:
                    ln = f'      matcher: "{MATCHER_HERMES}"'
                lines.append(ln)
            if args.dry_run:
                print(f"[ ] (dry-run) matcher pre_tool_call -> {cfg}")
                return False
            bak = cfg.with_suffix(cfg.suffix + ".bak")
            shutil.copy2(cfg, bak)
            print(f"[~] бэкап конфига -> {bak}")
            cfg.write_text("\n".join(lines) + "\n", encoding="utf-8",
                           newline="\n")
            print(f"[✓] matcher pre_tool_call обновлён -> {cfg}")
            return True
        # старый/битый вид (закавыченная команда прошлых версий) —
        # переписать только строку команды, остальное не трогать
        lines = [new_cmd_line
                 if ("aggg2_prompt_hook.py" in ln
                     and ln.strip().startswith("- command:"))
                 else ln
                 for ln in text.splitlines()]
        if args.dry_run:
            print(f"[ ] (dry-run) правка строки команды -> {cfg}")
            return False
        bak = cfg.with_suffix(cfg.suffix + ".bak")
        shutil.copy2(cfg, bak)
        print(f"[~] бэкап конфига -> {bak}")
        cfg.write_text("\n".join(lines) + "\n", encoding="utf-8",
                       newline="\n")
        print(f"[✓] строка команды хука исправлена -> {cfg}")
        return True

    lines = text.splitlines()
    hooks_idx = next((i for i, ln in enumerate(lines)
                      if ln and not ln[0].isspace()
                      and ln.strip().startswith("hooks:")), None)
    if hooks_idx is None:
        block = "\n".join([header, "hooks:", "  pre_tool_call:"] + entry_lines)
        new_lines = lines + ([""] if lines and lines[-1].strip() else []) + [block]
    else:
        pre_idx = None
        for j in range(hooks_idx + 1, len(lines)):
            ln = lines[j]
            if (ln.startswith("  ") and not ln.startswith("    ")
                    and "pre_tool_call" in ln):
                pre_idx = j
                break
            if ln.strip() and not ln[0].isspace():
                break
        if pre_idx is None:
            new_lines = (lines[:hooks_idx + 1]
                         + ["  pre_tool_call:"] + entry_lines
                         + lines[hooks_idx + 1:])
        else:
            new_lines = (lines[:pre_idx + 1] + entry_lines
                         + lines[pre_idx + 1:])
    if args.dry_run:
        print(f"[ ] (dry-run) hook pre_tool_call -> {cfg}")
        return False
    bak = cfg.with_suffix(cfg.suffix + ".bak")
    shutil.copy2(cfg, bak)
    print(f"[~] бэкап конфига -> {bak}")
    cfg.write_text("\n".join(new_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"[✓] hook pre_tool_call -> {cfg}")
    return True

def _ensure_hermes_auto_accept(cfg: Path, args) -> bool:
    """hooks_auto_accept: true — не-TTY-запуски регистрируют shell hooks без
    интерактивного согласия (ключ подтверждён docstring agent/shell_hooks.py).
    Tirith-одобрения команд НЕ трогаются — это только про хуки."""
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8-sig")
        if any(ln.strip() == "hooks_auto_accept: true"
               for ln in text.splitlines()):
            return False
    if args.dry_run:
        print(f"[ ] (dry-run) hooks_auto_accept: true -> {cfg}")
        return False
    cfg.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg, "a", encoding="utf-8", newline="\n") as f:
        f.write("hooks_auto_accept: true\n")
    print(f"[✓] hooks_auto_accept: true -> {cfg}")
    return True

def _seed_hermes_allowlist(hooks_dir: Path, command: str, args) -> bool:
    """Сеет согласие на shell-хук в ~/.hermes/shell-hooks-allowlist.json.

    Без этого хук НЕ стреляет (hermes hooks doctor: «not allowlisted —
    hook will NOT fire at runtime»). Форма — из исходника Hermes
    (agent/shell_hooks.py _record_approval): {"approvals": [{event,
    command, approved_at, script_mtime_at_approval}]}; совпадение — по
    точной паре (event, command). Идемпотентно: если запись уже есть с
    актуальным mtime скрипта — не трогаем (иначе doctor флагует mtime-drift).
    """
    from datetime import datetime, timezone

    allow = Path.home() / ".hermes" / "shell-hooks-allowlist.json"
    script = hooks_dir / "aggg2_prompt_hook.py"
    if not script.is_file():
        return False

    def _iso(ts_seconds):
        return datetime.fromtimestamp(ts_seconds, tz=timezone.utc).isoformat() \
            .replace("+00:00", "Z")

    now = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    mtime = _iso(os.path.getmtime(script))
    data = {"approvals": []}
    if allow.is_file():
        try:
            loaded = json.loads(allow.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                data = loaded
        except (ValueError, OSError):
            data = {"approvals": []}
    existing = [
        e for e in data.get("approvals", [])
        if isinstance(e, dict) and e.get("event") == "pre_tool_call"
        and e.get("command") == command
    ]
    if existing and existing[0].get("script_mtime_at_approval") == mtime:
        print(f"[=] allowlist уже на месте -> {allow}")
        return False
    entry = {"event": "pre_tool_call", "command": command,
             "approved_at": now,
             "script_mtime_at_approval": mtime}
    approvals = [e for e in data.get("approvals", []) if e not in existing]
    approvals.append(entry)
    data["approvals"] = approvals
    if args.dry_run:
        print(f"[ ] (dry-run) allowlist -> {allow}")
        return False
    allow.parent.mkdir(parents=True, exist_ok=True)
    allow.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8", newline="\n")
    print(f"[✓] allowlist (согласие на хук) -> {allow}")
    return True

def apply_hermes_hook(args) -> bool:
    """Hermes: сторож запретов через shell hooks (pre_tool_call).

    Хук-скрипт — общий aggg2_prompt_hook.py (ветка hermes по
    hook_event_name). Инъекция ядра НЕ нужна: монолит уже в SOUL.md
    (слот #1 каждого промпта) — pre_llm_call не используем. Согласие на
    хук — hooks_auto_accept (наш собственный хук, только наш скрипт).
    """
    hooks_dir = Path.home() / ".hermes" / "hooks"
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
    src_handlers = SRC / "hooks" / "handlers_misc.py"
    if src_handlers.is_file():
        changed |= deploy_file(src_handlers, hooks_dir / "handlers_misc.py", args)
    cfg = Path.home() / ".hermes" / "config.yaml"
    # shlex.join: Hermes режет command через shlex.split — кавычки только
    # там, где реально нужны (пробелы в пути), иначе команда не стартует
    command = shlex.join([_python_cmd(), str(hooks_dir / "aggg2_prompt_hook.py")])
    changed |= _ensure_hermes_hooks(cfg, command, args)
    changed |= _ensure_hermes_auto_accept(cfg, args)
    changed |= _seed_hermes_allowlist(hooks_dir, command, args)
    if not args.dry_run:
        print("[!] Hermes: проверьте хук: hermes hooks doctor")
    return changed

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
