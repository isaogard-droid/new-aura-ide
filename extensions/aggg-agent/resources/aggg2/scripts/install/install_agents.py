#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Распространяет файл правил (AGENTS.md — указатель на CLAUDE.md) и скиллы
канона по корням агентных харнесов: opencode, Claude Code, Codex, Reasonix,
Antigravity/agy/Gemini CLI, Hermes и др. Для харнесов Google пишется МОНОЛИТ
(harness/monolith.md — персона + ядро правил) в ~/.gemini/GEMINI.md, для
Hermes — в ~/.hermes/SOUL.md: эти файлы впрыскиваются в каждый промпт
(системный слот), указатель там бесполезен (нет доступа к воркспейсу),
полный CLAUDE.md — перегруз (индустрия: always-on слой должен быть
компактным).

Кроссплатформенный (Linux / macOS / Windows): пути определяются по
переменным окружения, без хардкода. Существующие файлы не затираются —
перед заменой делается бэкап <файл>.bak.

Запуск:
    python3 install_agents.py --list          # показать обнаруженные харнесы
    python3 install_agents.py --dry-run       # показать, что будет сделано
    python3 install_agents.py                 # установить (с бэкапами)
    python3 install_agents.py --harness codex # только один харнес
    python3 install_agents.py --skills        # разнести скиллы канона
                                              # (skills/ корня) по харнесам
    python3 install_agents.py --all           # AGENTS.md + скиллы

Источники путей (проверено ресёрчем, 08.2026):
- opencode:  https://opencode.ai/docs/rules/  (global: ~/.config/opencode/AGENTS.md)
- claude:    docs.anthropic.com (memory: ~/.claude/CLAUDE.md; opencode читает его как фолбэк)
- codex:     https://learn.chatgpt.com/docs/agent-configuration/agents-md (~/.codex/AGENTS.md)
- reasonix:  подтверждено фактом на машине (~/.reasonix/AGENTS.md)
- antigravity/agy: семейство Google (Antigravity 2.0 IDE + CLI `agy`).
  Глобальный ФАЙЛ ПРАВИЛ — ~/.gemini/GEMINI.md (не AGENTS.md;
  antigravity.google/docs/rules-workflows); AGENTS.md читают из корня
  проекта (поддержка с v1.20.3).
- gemini:    Gemini CLI (npm @google/gemini-cli). Глобальный контекст —
  ~/.gemini/GEMINI.md (geminicli.com/docs/cli/gemini-md); AGENTS.md —
  в дефолтных контекст-файлах с PR #28240 (google-gemini/gemini-cli).
  С 18.06.2026 Google переводит индивидуальных пользователей на agy
  (developers.googleblog.com), gemini-cli остаётся для Enterprise/OSS.
- hermes:    Hermes Agent (Nous Research, github.com/NousResearch/hermes-agent).
  CLI `hermes` и Desktop делят агент-ядро и конфиг ~/.hermes/ (HERMES_HOME).
  Глобальный слот #1 системного промпта — ~/.hermes/SOUL.md; глобального
  AGENTS.md нет: AGENTS.md/CLAUDE.md читаются из корня проекта (цепочка
  git-root → cwd; first match: .hermes.md → AGENTS.md → CLAUDE.md →
  .cursorrules). Субагенты динамические (delegate_task), файлового
  каталога не задокументировано.
- amp:       Amp (Sourcegraph): глобальный AGENTS.md — ~/.config/amp/AGENTS.md
  (ampcode.com/manual: всегда включается; + ~/.config/AGENTS.md как фолбэк).

Скиллы (Agent Skills, SKILL.md в каталоге): путь у каждого харнеса свой,
проверено ресёрчем 08.2026 (находка research.db id=79):
- opencode:  ~/.config/opencode/skills/
- opencode2: те же пути, что opencode (v2 читает v1-расположения,
             migrate-v1); бинарь opencode2, ставится beta-тегом
- claude:    ~/.claude/skills/            (code.claude.com/docs/en/skills)
- codex:     ~/.codex/skills/             (github.com/openai/codex, docs/skills.md)
- deepcode:  ~/.deepcode/skills/          (deepcode.vegamo.cn, docs agent-skills)
- codewhale: ~/.codewhale/skills/         (github.com/Hmbown/CodeWhale, docs/skills)
- omp:       ~/.omp/agent/skills/ + читает чужие (claude/codex/agents);
             общий стандарт — ~/.agents/skills/ (github.com/can1357/oh-my-pi, docs/skills.md)
- reasonix:  свой registry (reasonix.io/skills/) — каталог не подтверждён,
             пропускается (читает общий ~/.agents/skills/ через совместимость)
- antigravity: ~/.gemini/config/skills/     (antigravity.google/docs/skills)
- agy:      ~/.gemini/antigravity-cli/skills/ (docs/cli/gcli-migration)
            + ~/.gemini/config/skills/ (docs/skills) — кладём в ОБА:
            доки разнятся, запасной каталог дёшев и идемпотентен
- gemini:   ~/.gemini/skills/ ИЛИ алиас ~/.agents/skills/ (алиас приоритетнее,
            geminicli.com/docs/cli/skills) — покрыт общим каталогом,
            отдельно не дублируем
- hermes:   ~/.hermes/skills/ (hermes-agent.nousresearch.com/docs
            user-guide/features/skills: основной каталог и source of truth;
            стандарт agentskills.io, external dirs через config)
- amp:      ~/.config/agents/skills/ (user-level; ampcode.com/news/
            agent-skills; Amp также читает ~/.claude/skills/ — совместимость)
- общий стандарт Agent Skills: ~/.agents/skills/ (zed, deepcode shared, omp)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass
import sys

from harness_map import (  # noqa: F401 — контракт (install_harnesses)
    AGENTS_SKILLS_DIRS,
    HARNESS_NAMES,
    HARNESSES,
    _warn_secrets,
    expand,
)
from skills_sync import (  # noqa: F401 — контракт (тесты)
    copy_skill,
    install_skills,
    skills_targets,
    sync_skill,
)


def _validate_harnesses():
    """Лёгкая проверка записей HARNESSES: обязательные ключи и уникальность
    имён — ловит опечатки структуры при старте, а не молчаливым skip."""
    names = []
    for h in HARNESSES:
        missing = [k for k in ("name", "paths") if k not in h]
        if missing:
            print(f"[!] запись харнеса без ключей {missing}: {h!r}",
                  file=sys.stderr)
        names.append(h.get("name"))
    dupes = sorted({n for n in names if n and names.count(n) > 1})
    if dupes:
        print(f"[!] дубли имён харнесов: {dupes}", file=sys.stderr)

def _subagent_canon(agent_root):
    """Собирает субагентов: {имя_агента: {харнес или "*": путь}}.

    Конвенция: <имя>.md/.toml — общий; <имя>.<харнес>.md/.toml —
    специфичный. Харнес = ПОСЛЕДНИЙ сегмент имени до расширения
    (имена с точками не ломают парсинг: my.agent.md → имя my.agent,
    reverser.codex.toml → reverser для codex).
    """
    canon = {}
    for ad in sorted(agent_root.iterdir()):
        adir = ad / "agents"
        if not adir.is_dir():
            continue
        for f in sorted(adir.iterdir()):
            if f.suffix not in (".md", ".toml"):
                continue
            parts = f.stem.split(".")
            if len(parts) >= 2 and parts[-1] in HARNESS_NAMES:
                canon.setdefault(".".join(parts[:-1]), {})[parts[-1]] = f
            else:
                canon.setdefault(f.stem, {})["*"] = f
    return canon


def _generate_agent_adapters(agent_root, dry_run=False):
    """Refresh agent adapters from optional per-agent generators."""
    for generator in sorted(agent_root.glob("*/scripts/generate_adapters.py")):
        command = [sys.executable, str(generator)]
        if dry_run:
            command.append("--check")
        result = subprocess.run(command, capture_output=True, text=True,
                                check=False)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.returncode:
            message = result.stderr.strip() or "adapter generator failed"
            print(f"[!] {generator}: {message}", file=sys.stderr)
            return False
    return True

def install_subagents(args):
    """Разносит субагентов агентов (agent/*/agents/*) по каталогам
    агентов харнесов. Паттерн индустрии (dotfiles: Claude Code
    .claude/agents/*.md, opencode ~/.config/opencode/agents/*.md,
    codex ~/.codex/agents/*.toml, reasonix subagent create) —
    канон в репо, скрипт разносит по харнессам.

    Конвенция: agent/<имя>/agents/<харнес>.<ext> = субагент для харнеса
    (имя файла = имя субагента). Расширения: .md (opencode/claude),
    .toml (codex), .md для reasonix — через команду `reasonix subagent
    create` (профиль runAs: subagent).
    """
    platform = "nt" if os.name == "nt" else "posix"
    root = Path(__file__).resolve().parent.parent.parent
    agent_root = root / "agent"
    if not agent_root.is_dir():
        return
    if not _generate_agent_adapters(agent_root, args.dry_run):
        return
    only = args.harness

    canon = _subagent_canon(agent_root)
    if not canon:
        return

    targets = []
    for h in HARNESSES:
        if only and h["name"] not in only:
            continue  # КРИТ-1 (судья): --harness фильтрует и субагентов
        agents_dir = (h.get("agents") or {}).get(platform)
        if not agents_dir:
            continue
        targets.append((h["name"], expand(agents_dir, platform)))

    print(f"субагентов: {len(canon)}, каталогов: {len(targets)}"
          f" (+reasonix, если установлен)"
          + (f", фильтр: {', '.join(only)}" if only else ""))
    if args.dry_run:
        print("\n[dry-run] план субагентов (ничего не записывается):")

    # формат субагента по харнесу: md (opencode/claude/omp), toml
    # (codex/codewhale), agent.md (copilot — ~/.copilot/agents/*.agent.md)
    ext_by_harness = {"codex": ".toml", "codewhale": ".toml",
                      "copilot": ".agent.md"}

    installed = 0
    fmt_skipped = []
    for hname, dst_dir in targets:
        ext = ext_by_harness.get(hname, ".md")
        for sub_name, files in canon.items():
            # харнес-специфичный файл приоритетнее общего
            src = files.get(hname) or files.get("*")
            if src is None:
                continue
            # формат совпадает ИЛИ copilot (.agent.md — тот же markdown +
            # frontmatter name/description, что и наш .md; dst получает
            # нужное расширение, контент не меняется)
            if not (src.suffix == ext
                    or (ext == ".agent.md" and src.name.endswith(".md"))):
                fmt_skipped.append((hname, sub_name, ext))
                continue
            dst = Path(dst_dir) / f"{sub_name}{ext}"
            if dst.is_file() and dst.read_text(encoding="utf-8") == src.read_text(encoding="utf-8"):
                continue
            if args.dry_run:
                print(f"[ ] {hname}/{sub_name}{ext} -> {dst_dir}")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"[✓] {hname}/{sub_name}{ext} -> {dst_dir}")
            installed += 1

    # честный вывод пропусков формата (РИСК-3 судьи): автор агента должен
    # знать, что харнес не получил субагента из-за несовпадения расширения
    for hname, sub_name, ext in fmt_skipped:
        print(f"[~] {hname}/{sub_name}: пропущен — нет файла формата {ext} "
              f"(положите {sub_name}.{hname}{ext} в agent/*/agents/)")

    # reasonix: профиль через команду (SKILL.md runAs: subagent)
    reasonix_bin = shutil.which("reasonix")
    if reasonix_bin and (not only or "reasonix" in only):
        # список профилей — ОДИН раз на всех (ЗАМ-3), парсим JSON (ЗАМ-4)
        list_stdout = ""
        parsed_ok = False
        existing = set()
        try:
            r = subprocess.run([reasonix_bin, "subagent", "list", "--json"],
                               capture_output=True, text=True, check=False,
                               timeout=30)
            list_stdout = r.stdout or ""
            try:
                data = json.loads(list_stdout)
                parsed_ok = True
                items = (data.values() if isinstance(data, dict)
                         else data if isinstance(data, list) else [])
                for v in items:
                    if isinstance(v, dict) and v.get("name"):
                        existing.add(v["name"])
                    elif isinstance(v, str):
                        existing.add(v)
            except ValueError:
                # Старые Reasonix не знают --json. Повторяем plain list и
                # извлекаем имена из строк вида "name [scope] description".
                plain = subprocess.run(
                    [reasonix_bin, "subagent", "list"],
                    capture_output=True, text=True, check=False, timeout=30,
                )
                list_stdout = plain.stdout or ""
                for line in list_stdout.splitlines():
                    match = re.match(r"^([A-Za-z0-9_.-]+)\s+\[", line.strip())
                    if match:
                        existing.add(match.group(1))
                parsed_ok = True
        except (OSError, subprocess.TimeoutExpired):
            pass
        for sub_name, files in canon.items():
            src = files.get("reasonix") or files.get("*")
            if src is None or src.suffix != ".md":
                continue
            if args.dry_run:
                print(f"[ ] reasonix/{sub_name}: subagent create --prompt-file {src}")
                continue
            exists = (sub_name in existing if parsed_ok
                      else sub_name in list_stdout)
            # description — из frontmatter канона (общего md), чтобы не дублировать
            desc = sub_name
            canon_md = canon.get(sub_name, {}).get("*")
            if canon_md is not None and canon_md.suffix == ".md":
                m = re.search(r'^description:\s*"?([^"\n]+)', canon_md.read_text(encoding="utf-8"))
                if m:
                    desc = m.group(1)
            cmd = ["edit" if exists else "create", sub_name,
                   "--description", desc, "--prompt-file", str(src)]
            if not exists:
                cmd.extend(["--scope", "global"])
            res = subprocess.run([reasonix_bin, "subagent", *cmd],
                                 capture_output=True, text=True, check=False,
                                 timeout=60)
            if res.returncode == 0:
                print(f"[✓] reasonix/{sub_name}: profile {'updated' if exists else 'created'}")
                installed += 1
            else:
                print(f"[!] reasonix/{sub_name}: {res.stderr.strip()[:200]}",
                      file=sys.stderr)

    if installed:
        print(f"итого субагентов установлено/обновлено: {installed}")
    elif not args.dry_run:
        print("субагенты уже актуальны")


def main():
    ap = argparse.ArgumentParser(description="Распространение AGENTS.md и скиллов по харнесам")
    ap.add_argument("--list", action="store_true", help="показать харнесы и их пути")
    ap.add_argument("--dry-run", action="store_true", help="показать план без записи")
    ap.add_argument("--harness", action="append", help="только указанные харнесы")
    ap.add_argument("--yes", action="store_true", help="не спрашивать при перезаписи")
    ap.add_argument("--skills", action="store_true",
                    help="разнести скиллы канона (skills/ корня) по харнесам")
    ap.add_argument("--agent-skills", action="store_true",
                    help="только скиллы агентов (agent/*/skills/)")
    ap.add_argument("--subagents", action="store_true",
                    help="только субагенты агентов (agent/*/agents/*.md)")
    ap.add_argument("--all", action="store_true", help="AGENTS.md + скиллы + субагенты (канон + агенты)")
    args = ap.parse_args()
    _validate_harnesses()

    platform = "nt" if os.name == "nt" else "posix"
    root = Path(__file__).resolve().parent.parent.parent
    if not (root / "AGENTS.md").is_file():
        print(f"[✗] источник по умолчанию не найден: {root / 'AGENTS.md'}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        for h in HARNESSES:
            p = expand(h["paths"][platform], platform)
            print(f"{h['name']:12s} -> {p or '—'}   [{h['source']}]")
            src_rel = h.get("src")
            if src_rel:
                print(f"             источник правил: {root / src_rel}")
            inst = (h.get("install") or {}).get(platform)
            repo = h.get("repo")
            if inst:
                print(f"             установка: {inst}")
            elif "install" in h:
                print("             установка: — (GUI/вручную, команды нет)")
            if repo:
                print(f"             репо: {repo}")
            sk = (h.get("skills") or {}).get(platform)
            if sk:
                if isinstance(sk, str):
                    sk = [sk]
                print(f"             скиллы: {', '.join(str(expand(s, platform)) for s in sk)}")
            ag = (h.get("agents") or {}).get(platform)
            if ag:
                print(f"             субагенты: {expand(ag, platform)}")
        common = expand(AGENTS_SKILLS_DIRS[platform], platform)
        print(f"{'agents':12s} -> {common or '—'}   [общий стандарт Agent Skills]")
        return

    if args.skills:
        install_skills(args, include_agents=False)
        return

    if args.agent_skills:
        install_skills(args, include_agents=True, only_agents=True)
        return

    if args.subagents:
        install_subagents(args)
        return

    if args.all:
        # agent/*/skills/ НЕ разносим: скиллы агента — его собственные,
        # читаются субагентом напрямую из $AGGG2_ROOT/agent/<имя>/skills/
        # (не грузятся в общий контекст харнеса — изоляция, архитектура
        # «общая база не знает об агентах»). Явно — --agent-skills.
        install_skills(args, include_agents=False)
        print()
        install_subagents(args)
        print()

    if args.harness:
        selected = [h for h in HARNESSES if h["name"] in args.harness]
        unknown = set(args.harness) - {h["name"] for h in HARNESSES}
        if unknown:
            print(f"[!] неизвестные харнесы: {', '.join(sorted(unknown))}", file=sys.stderr)
        if not selected:
            sys.exit(1)
    else:
        selected = HARNESSES

    installed, skipped = [], []
    for h in selected:
        # источник правил: по умолчанию корневой AGENTS.md (указатель);
        # харнесы Google берут монолит (harness/monolith.md) — их глобальный
        # файл впрыскивается в каждый промпт, указатель там бесполезен.
        src = root / h.get("src", "AGENTS.md")
        if not src.is_file():
            print(f"[!] {h['name']}: источник правил не найден: {src}", file=sys.stderr)
            skipped.append((h["name"], f"нет источника правил {src}"))
            continue
        content = src.read_text(encoding="utf-8")
        dst = expand(h["paths"][platform], platform)
        if not dst:
            skipped.append((h["name"], h["source"]))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Сравнение по байтам: на Windows write_text без newline пишет CRLF,
        # и md5-проверки зеркал ложно падают. Записываем всегда LF.
        try:
            dst_bytes = dst.read_bytes() if dst.is_file() else None
        except OSError:
            dst_bytes = None
        if dst_bytes == content.encode("utf-8"):
            print(f"[=] {h['name']}: уже актуально ({dst})")
            continue
        # КРИТ-2 (судья): dry-run НЕ должен спрашивать ввод и делать бэкапы —
        # проверка до промпта и до копирования .bak
        if args.dry_run:
            print(f"[ ] {h['name']}: (dry-run) записал бы -> {dst}")
            continue
        if dst.exists() and not args.yes:
            if sys.stdin.isatty():
                ans = input(f"[?] {h['name']}: {dst} существует — заменить (бэкап .bak)? [y/N] ")
                if ans.strip().lower() not in ("y", "yes"):
                    print(f"[ ] {h['name']}: пропущено")
                    continue
            else:
                # не-TTY (агент/CI): промпт зависнет на EOF — авто-замена
                # с бэкапом (интерактив — только человеку, skill-authoring)
                print(f"[~] {h['name']}: {dst} существует — не-TTY: заменяю (бэкап .bak)")
        # РИСК-1 (судья): лимит Windsurf 6000 симв. — предупреждаем заранее
        if h["name"] == "windsurf" and len(content) > 6000:
            print(f"[!] windsurf: {len(content)} симв. > лимита 6000 "
                  f"(global_rules.md) — Windsurf обрежет хвост правил",
                  file=sys.stderr)
        # РИСК-6 (судья): сигнал, если контент похож на реальный секрет
        _warn_secrets(f"правила для {h['name']}", content)
        if dst.exists():
            bak = dst.with_suffix(dst.suffix + ".bak")
            shutil.copy2(dst, bak)
            print(f"[~] {h['name']}: бэкап -> {bak}")
        dst.write_text(content, encoding="utf-8", newline="\n")
        installed.append((h["name"], dst))
        print(f"[✓] {h['name']}: записано -> {dst}")

    for name, why in skipped:
        print(f"[!] {name}: пропущен — {why}")

    if args.dry_run:
        print("\n[dry-run] ничего не записано")
    else:
        print(f"\nитого: установлено {len(installed)}, пропущено {len(skipped)}")



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nотменено")
        sys.exit(130)


# Разработано для https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, дальше — ещё лучше.

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
