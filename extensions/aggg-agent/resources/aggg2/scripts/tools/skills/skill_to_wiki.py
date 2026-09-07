#!/usr/bin/env python3
"""skill_to_wiki — перенос скилла из skills/ в Wiki/ одним заходом.

Полный пайплайн миграции (docs/canon/WIKI.md «скиллы-на-полке», вариант A): пост с
frontmatter → встраивание references//scripts/ code-блоками → gen_index →
log.md append → пересборка db/wiki.db → lint_wiki → удаление из канона и
всех каталогов харнесов → скан бэклинков. Сначала всегда --dry-run.

Паттерны индустрии (ресёрч 08.2026): skills.sh CLI (npx skills add/remove),
SkillShelf skillshelf doctor (skill governance как CLI), /doctor pruning по
usage-логам (daniliants 2026). Проверено: вторая волна миграции (3 скилла,
~15 ручных шагов стали одной командой).

Использование:
  python3 scripts/tools/skills/skill_to_wiki.py <skill> --category fedora
  python3 scripts/tools/skills/skill_to_wiki.py <skill> --category tools --dry-run
"""

import argparse
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _compat import chulan_root, fix_encoding  # noqa: E402

ROOT = chulan_root()
SKILLS = ROOT / "skills"
WIKI = ROOT / "Wiki"
WIKI_DB = ROOT / "db" / "wiki.db"
GEN_INDEX = SKILLS / "wiki-karpathy" / "scripts" / "gen_index.py"
LINT_WIKI = SKILLS / "wiki-karpathy" / "scripts" / "lint_wiki.py"
BUILD = ROOT / "db-tools" / "build.py"

MAX_DESC = 200
SCAN_EXTS = {".md", ".py", ".sh", ".txt", ".toml", ".json", ".js", ".yml", ".yaml"}
SKIP_DIRS = {".git", "db", "Wiki", "__pycache__", "node_modules", ".venv", "venv"}
FENCE = {".json": "json", ".sh": "bash", ".py": "python", ".toml": "toml",
         ".js": "javascript", ".yml": "yaml", ".yaml": "yaml", ".txt": "text"}

PRIVATE_NET = (
    re.compile(r"^(10|127)\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^172\.(1[6-9]|2\d|3[01])\."),
)
PUBLIC_DNS = {"1.1.1.1", "8.8.8.8", "8.8.4.4", "9.9.9.9", "149.112.112.112",
              "208.67.222.222", "208.67.220.220"}
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DB_RE = re.compile(r"(?:research\.db|findings?\s+id\s*=?\s*\d+)[^\n]*")


def parse_skill(skill_dir):
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SystemExit(f"{skill_dir}: нет frontmatter (первая строка не ---)")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise SystemExit(f"{skill_dir}: frontmatter не закрыт")
    fm = {}
    for raw in lines[1:end]:
        if ":" in raw and not raw.lstrip().startswith(("#", "-")):
            k, v = raw.split(":", 1)
            fm[k.strip()] = v.strip().strip("'\"")
    return fm, "\n".join(lines[end + 1:]).lstrip("\n")


def sanitize(body):
    warnings = []
    stripped = []
    clean = []
    for ln in body.splitlines():
        if DB_RE.search(ln):
            stripped.append(ln.strip())
            continue
        clean.append(ln)
    ips = {}
    counter = 0
    for m in IP_RE.finditer("\n".join(clean)):
        ip = m.group(0)
        if any(r.match(ip) for r in PRIVATE_NET) or ip in PUBLIC_DNS:
            continue
        if ip not in ips:
            counter += 1
            ips[ip] = f"YOUR_IP_{counter}"
    for ip, ph in ips.items():
        clean = [ln.replace(ip, ph) for ln in clean]
        warnings.append(f"IP {ip} → {ph} (переименуй в осмысленный плейсхолдер)")
    return "\n".join(clean) + "\n", stripped, warnings


def embed_dirs(skill_dir):
    blocks = []
    for sub in ("references", "scripts"):
        d = skill_dir / sub
        if not d.is_dir():
            continue
        for f in sorted(p for p in d.rglob("*") if p.is_file()):
            rel = f.relative_to(skill_dir)
            lang = FENCE.get(f.suffix, "text")
            blocks.append(f"## {rel} (из скилла)\n\n```{lang}\n"
                          f"{f.read_text(encoding='utf-8').rstrip()}\n```")
    return "\n\n".join(blocks)


def make_post(name, description, body, category, tags, embeds):
    desc = description.replace('"', "'")
    if len(desc) > MAX_DESC:
        cut = desc[:MAX_DESC]
        sp = cut.rfind(" ")
        desc = cut[:sp] if sp > MAX_DESC // 2 else cut
    today = date.today().isoformat()
    tags_yaml = ", ".join(["skill-shelf", category] + tags)
    return f"""---
type: Howto
title: "{name}"
description: "{desc}"
date: {today}
tags: [{tags_yaml}]
source: skills/{name}/ (перенесено {today})
status: stable
---

# {name} — скилл-на-полке (Howto)

Перенесено из `skills/{name}/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — AGGG [AGENT OS], закрытое сообщество; связь с админом — только в Телеграме.

{body}
{embeds}
"""


def harness_skill_dirs():
    sys.path.insert(0, str(ROOT / "scripts" / "install"))
    from harness_map import AGENTS_SKILLS_DIRS, HARNESSES, expand  # noqa: E402
    plat = "nt" if sys.platform == "win32" else "posix"
    dirs = []
    for h in HARNESSES:
        skills = h.get("skills")
        val = skills.get(plat) if isinstance(skills, dict) else skills
        for p in (val if isinstance(val, list) else [val]):
            q = expand(p, plat) if p else None
            if q:
                dirs.append(q)
    dirs.append(expand(AGENTS_SKILLS_DIRS.get(plat), plat))
    return list(dict.fromkeys(dirs))


def run(cmd, label):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", check=False)
    if r.returncode != 0:
        raise SystemExit(f"ОШИБКА: {label} (rc={r.returncode})\n{r.stdout}\n{r.stderr}")
    print(f"[ok] {label}")
    return r.stdout


def backlinks(name):
    found = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in SCAN_EXTS:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            for i, ln in enumerate(p.read_text(encoding="utf-8",
                                               errors="replace").splitlines(), 1):
                if name in ln:
                    found.append(f"{p.relative_to(ROOT)}:{i}: {ln.strip()[:100]}")
        except OSError:
            continue
    return found


def main():
    fix_encoding()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("skill", help="имя скилла в skills/")
    ap.add_argument("--category", required=True,
                    help="папка Wiki/ (fedora, tools, coding, ...)")
    ap.add_argument("--tags", nargs="*", default=[],
                    help="доп. теги в frontmatter")
    ap.add_argument("--dry-run", action="store_true",
                    help="показать, что будет сделано, ничего не меняя")
    args = ap.parse_args()

    name = args.skill
    skill_dir = SKILLS / name
    if not skill_dir.is_dir():
        raise SystemExit(f"нет скилла: {skill_dir}")
    fm, body = parse_skill(skill_dir)
    clean_body, stripped, warnings = sanitize(body)
    embeds = embed_dirs(skill_dir)
    post = make_post(name, fm.get("description", ""), clean_body,
                     args.category, args.tags, embeds)
    dst = WIKI / args.category / f"{name}.md"
    cat_dirs = [d / name for d in harness_skill_dirs()] + [skill_dir]
    if not args.dry_run and dst.exists():
        raise SystemExit(f"пост уже есть: {dst} (удали или переименуй)")
    for w in warnings:
        print(f"[!] {w}")
    if stripped:
        print(f"[i] вырезано строк с research.db/findings id: {len(stripped)}")
        for s in stripped:
            print(f"    - {s}")

    print(f"пост: {dst.relative_to(ROOT)} ({post.count(chr(10)) + 1} строк)")
    print(f"удаление: {len(cat_dirs)} каталогов (канон + харнесы)")
    for d in cat_dirs:
        print(f"  rm -r {d}")

    if args.dry_run:
        print("[dry-run] — изменений нет")
        bl = backlinks(name)
        print(f"[i] бэклинки по «{name}»: {len(bl)}")
        for b in bl:
            print(f"  {b}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(post, encoding="utf-8", newline="\n")
    print(f"[ok] пост записан: {dst.relative_to(ROOT)}")

    run([str(GEN_INDEX)], "gen_index.py")
    with open(WIKI / "log.md", "a", encoding="utf-8", newline="\n") as f:
        f.write(f"- {datetime.now().strftime('%F %H:%M')} — add — "
                f"{args.category}/{name}.md — Howto (перенос из skills/)\n")
    run(["db-tools/build.py", "-r", "Wiki", "-o", "db/wiki.db"], "build wiki.db")
    lint = subprocess.run([sys.executable, str(LINT_WIKI)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          check=False)
    print(lint.stdout[-300:])
    if lint.returncode != 0:
        print("[!] lint_wiki != 0 — поправь пост и прогони снова")
        raise SystemExit(1)

    for d in cat_dirs:
        shutil.rmtree(d, ignore_errors=True)
        print(f"[ok] удалён: {d}")

    bl = backlinks(name)
    print(f"[i] бэклинки по «{name}» (поправь вручную): {len(bl)}")
    for b in bl:
        print(f"  {b}")
    print("ГОТОВО: пост в Wiki, скилл удалён из канона и харнесов.")


if __name__ == "__main__":
    main()
