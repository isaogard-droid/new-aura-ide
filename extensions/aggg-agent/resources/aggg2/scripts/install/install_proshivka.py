#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Установщик прошивки правил AGGG2.0 в агентные харнесы (кроссплатформенный).

Ставит на машину уровни прошивки из корня чулана harness/ (по-харнессовые
подпапки + общее сверху: core.txt, hooks/):
1. opencode/prompts/build.txt -> ~/.config/opencode/prompts/build.txt
   (промпт build-агента, подключается через agent.build.prompt);
2. agent.build.prompt     -> вписывается в opencode.json/.jsonc (идемпотентно);
3. opencode/plugins/proshivka.js + core.txt -> ~/.config/opencode/plugins/
   (opencode-плагин: ядро правил в системный промпт на каждый ход через
   experimental.chat.system.transform + переживает компакцию + сторож
   запретов tool.execute.before: блок throw, напоминания client.app.log);
3б. permission.edit -> opencode.jsonc: 'ask' на baseline god-файлы
   (opencode v2 не имеет tool.execute.before — нативный сторож правок,
   docs/canon/FILE-SIZE.md; список из scripts/file_size_baseline.json);
4. hooks/aggg2_prompt_hook.py + core.txt -> ~/.claude/hooks/ + ~/.codex/hooks/   + ~/.reasonix/hooks/ с прописыванием хуков UserPromptSubmit (ядро правил
   как additionalContext в каждый промпт) и PreToolUse (сторож запретов:
   блок опасных Bash-команд — pkill без трюка, rm -rf, git reset --hard;
   напоминание QA/CHANGELOG на правках кода — паттерн индустрии «restraint
   rules need external enforcement», agentpatterns.ai):
   - Claude Code: ~/.claude/settings.json (code.claude.com/docs/en/hooks);
   - Codex: ~/.codex/hooks.json (learn.chatgpt.com/docs/hooks; требуется
     доверие хука через /hooks при первом запуске);
   - Reasonix: ~/.reasonix/settings.json hooks.PreToolUse (gating: exit 2 =
     блок; internal/hook/hook.go);
   - Hermes: ~/.hermes/config.yaml hooks: pre_tool_call (shell hooks:
     сторож запретов, wire protocol agent/shell_hooks.py — блок через
     stdout {"action":"block"} + exit 2; инъекция ядра не нужна: монолит
     уже в SOUL.md слоте #1);
   - Gemini CLI: ~/.gemini/settings.json hooks.BeforeTool (matcher
     run_shell_command, блок {"decision":"deny"} + exit 2);
   - Antigravity/agy: ~/.gemini/config/hooks.json PreToolUse (matcher
     run_command, гейт {"decision":"deny"}).

Пути — через Path.home() (posix/nt), файлы сравниваются по байтам,
повторные запуски ничего не портят. Перед заменой — бэкап <файл>.bak.

Запуск:
    python3 install_proshivka.py --check    # план без записи
    python3 install_proshivka.py            # установить
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — опционально, без него живём
    pass

from jsonc_edit import load_jsonc, write_json  # общие парсеры конфигов

# Хелперы/хуки вынесены в модули (гейт god-файлов, docs/canon/FILE-SIZE.md):
# proshivka_helpers (константы+общее), proshivka_hooks (apply_* харнесов),
# proshivka_permissions (permission.ask). Реэкспорт — контракт:
# doctor (MATCHER_*) и тесты (ip.apply_*).
from proshivka_helpers import (  # noqa: F401
    CHULAN,
    MATCHER_AGY,
    MATCHER_CLAUDE,
    MATCHER_GEMINI,
    MATCHER_HERMES,
    MATCHER_OMP,
    OPCODE_DIR,
    SRC,  # noqa: F401
    deploy_file,
)
from proshivka_hooks import (  # noqa: F401
    _ensure_hermes_auto_accept,
    _ensure_hermes_hooks,
    _seed_hermes_allowlist,
    apply_antigravity_hooks,
    apply_claude_hooks,
    apply_codewhale_hooks,
    apply_codex_hooks,
    apply_gemini_hooks,
    apply_hermes_hook,
    apply_omp_hooks,
    apply_reasonix_hooks,
)
from proshivka_permissions import (  # noqa: F401
    apply_claude_permissions,
    apply_opencode_permissions,
)

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


def apply_opencode_prompt(args) -> bool:
    """Вписывает agent.build.prompt в живой конфиг opencode (json/jsonc)."""
    path = OPCODE_DIR / "opencode.json"
    if not path.is_file():
        path = OPCODE_DIR / "opencode.jsonc"
    data = {}
    if path.is_file():
        try:
            data = load_jsonc(str(path))
        except Exception as e:  # noqa: BLE001 — НЕ перезаписываем: битый конфиг
            # БАГ-РЕПОРТ v2.4 BUG-3: раньше здесь молча подставлялся {} и
            # write_json стирал ВСЁ содержимое (MCP-серверы, чужие записи).
            # Теперь при ошибке парсинга конфиг не трогаем — только сообщаем.
            print(f"[!] не могу разобрать конфиг {path}: {e!r}")
            print("    конфиг НЕ тронут — разберись с файлом и повтори")
            return False
    agent = data.setdefault("agent", {})
    build = agent.setdefault("build", {})
    if build.get("prompt") == "{file:./prompts/build.txt}":
        print(f"[=] agent.build.prompt уже в конфиге: {path}")
        return False
    build["prompt"] = "{file:./prompts/build.txt}"
    if args.dry_run:
        print(f"[ ] (dry-run) agent.build.prompt -> {path}")
        return False
    if path.is_file():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(path), data)
    print(f"[✓] agent.build.prompt -> {path}")
    return True

def main():
    ap = argparse.ArgumentParser(description="Прошивка правил AGGG2.0 в opencode")
    ap.add_argument("--check", action="store_true", help="план без записи")
    args = ap.parse_args()
    args.dry_run = args.check

    print(f"чулан: {CHULAN}")
    changed = False

    prompt_src = SRC / "opencode" / "prompts" / "build.txt"
    if prompt_src.is_file():
        changed |= deploy_file(
            prompt_src, OPCODE_DIR / "prompts" / "build.txt", args)
    else:
        print(f"[!] нет источника: {prompt_src}")

    # ГРАБЛЯ (Windows-багрепорт 08.2026): плагин proshivka.js читал core.txt
    # рядом с собой — ядро не инжектилось, если в plugins/ не было копии.
    # proshivka.js берётся из harness/opencode/plugins/, а core.txt — из
    # harness/core.txt (единственный источник правды).
    # OpenCode 2: V1-плагины НЕ работают (breaking change, migrate-v1) —
    # для opencode2 ядро в каждый ход придёт после порта плагина на новый
    # Effect API (пока не стабилизирован); до этого v2 живёт на
    # ~/.config/opencode/AGENTS.md (монолит) + permission.edit-сторож.
    plugin_src = SRC / "opencode" / "plugins" / "proshivka.js"
    if plugin_src.is_file():
        changed |= deploy_file(plugin_src, OPCODE_DIR / "plugins" / "proshivka.js",
                               args)
        if shutil.which("opencode2"):
            print("[i] opencode2: V1-плагин прошивки в нём не работает — "
                  "порт после стабилизации V2 plugin API "
                  "(opencode.ai/v2/docs/migrate-v1)")
    else:
        print(f"[!] нет источника: {plugin_src}")

    core_src = SRC / "core.txt"
    if core_src.is_file():
        changed |= deploy_file(core_src, OPCODE_DIR / "plugins" / "core.txt", args)
    else:
        print(f"[!] нет источника ядра: {core_src}")

    # Команды opencode (/loop и др.): harness/opencode/commands/*.md ->
    # ~/.config/opencode/commands/ (описаны в официальных доках opencode:
    # opencode.ai/docs/commands — markdown + $ARGUMENTS, TUI-автодополнение).
    cmds_src = SRC / "opencode" / "commands"
    if cmds_src.is_dir():
        cmds_dir = OPCODE_DIR / "commands"
        cmds_dir.mkdir(parents=True, exist_ok=True)
        for cmd_file in sorted(cmds_src.glob("*.md")):
            changed |= deploy_file(cmd_file, cmds_dir / cmd_file.name, args)

    # Компактный монолит (Tier 1): персона + ядро + указатели. Лежит в
    # ~/AGENTS.md — opencode и другие харнесы инжектят его в каждый ход.
    # Полный CLAUDE.md — по требованию (Tier 3). Правка 08.2026: было 40КБ
    # копии CLAUDE.md в каждом ходе → теперь ~4КБ ядра (research.db id=322).
    monolith_src = SRC / "monolith.md"
    if monolith_src.is_file():
        changed |= deploy_file(monolith_src, Path.home() / "AGENTS.md", args)
    else:
        print(f"[!] нет источника монолита: {monolith_src}")

    changed |= apply_opencode_prompt(args)
    changed |= apply_opencode_permissions(args)
    changed |= apply_claude_permissions(args)
    changed |= apply_claude_hooks(args)
    changed |= apply_codex_hooks(args)
    changed |= apply_reasonix_hooks(args)
    changed |= apply_codewhale_hooks(args)
    changed |= apply_omp_hooks(args)
    changed |= apply_hermes_hook(args)
    changed |= apply_gemini_hooks(args)
    changed |= apply_antigravity_hooks(args)

    # Команды Gemini CLI: harness/gemini/commands/*.toml ->
    # ~/.gemini/commands/ (официальные доки: geminicli.com/docs/cli/custom-commands)
    gem_cmds_src = SRC / "gemini" / "commands"
    if gem_cmds_src.is_dir():
        gem_cmds_dir = Path.home() / ".gemini" / "commands"
        gem_cmds_dir.mkdir(parents=True, exist_ok=True)
        for cmd_file in sorted(gem_cmds_src.glob("*.toml")):
            changed |= deploy_file(cmd_file, gem_cmds_dir / cmd_file.name, args)

    print("\n[✓] Прошивка на месте (перезапустите харнесы)"
          if not args.check else "\n[dry-run] ничего не записано")
    print("   ядро правил: ~/.config/opencode/plugins/core.txt")
    print("   источник правды: harness/ в корне чулана")



if __name__ == "__main__":
    main()

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
