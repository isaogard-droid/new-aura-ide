#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""lint_skills.py — проверка целостности скиллов канона (skills/ и
agent/*/skills/) по спеке Agent Skills + практике AGGG2.0.

ОШИБКИ (exit 1) — скилл не сработает или нарушает спеку:
  - нет SKILL.md в каталоге скилла;
  - нет/битый YAML-frontmatter;
  - поля name нет или оно не совпадает с именем каталога;
  - name вне формата: 1-64, [a-z0-9-], без ведущих/хвостовых/двойных дефисов;
  - description нет/пустой или длиннее 1024 символов (лимит спеки);
  - SKILL.md больше ~5000 токенов (лимит спеки; оценка: символы/4).

ПРЕДУПРЕЖДЕНИЯ (exit 0) — рекомендации индустрии:
  - description длиннее 512 символов (agent-layer.dev: бюджет каталога
    при многих скиллах);
  - нет license или metadata.author (наше решение канона об атрибуции,
    research.db id=362);
  - SKILL.md длиннее 500 строк (рекомендация спеки);
  - битая относительная md-ссылка из SKILL.md.

Использование:
  python3 lint_skills.py            # канон skills/ + agent/*/skills/
  python3 lint_skills.py <каталог-со-скиллами>
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESC_LIMIT = 1024          # лимит спеки
DESC_BUDGET = 512          # рекомендация agent-layer.dev (каталог)
LINE_LIMIT = 500           # рекомендация спеки
TOKEN_LIMIT = 5000         # рекомендация спеки (оценка: символы/4)


def parse_frontmatter(text: str) -> dict | None:
    """dict из YAML-frontmatter или None, если его нет/он битый."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    if yaml is not None:
        try:
            data = yaml.safe_load(block)
            return data if isinstance(data, dict) else None
        except yaml.YAMLError:
            return None
    data = {}
    for line in block.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2)
    return data


def _rel_broken_links(text: str, skill_dir: Path) -> list[str]:
    """Относительные md-ссылки из SKILL.md, которых нет на диске."""
    broken = []
    for m in re.findall(r"\]\(([^)#]+\.md)\)", text):
        link = m.split("#", 1)[0]
        if link.startswith(("http://", "https://")):
            continue
        if not (skill_dir / link).is_file():
            broken.append(link)
    return broken


def check_skill(skill_dir: Path) -> tuple[list[str], list[str]]:
    """(errors, warnings) для одного каталога скилла."""
    errors: list[str] = []
    warnings: list[str] = []
    rel = skill_dir.name
    sk = skill_dir / "SKILL.md"
    if not sk.is_file():
        return [f"{rel}: нет SKILL.md"], []
    text = sk.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        return [f"{rel}: нет/битый YAML-frontmatter"], []

    name = fm.get("name")
    if not name:
        errors.append(f"{rel}: нет поля 'name' в frontmatter")
    else:
        name = str(name)
        if name != rel:
            errors.append(f"{rel}: name '{name}' != имени каталога")
        if not NAME_RE.fullmatch(name):
            errors.append(f"{rel}: name '{name}' вне формата [a-z0-9-] 1-64")
        if len(name) > 64:
            errors.append(f"{rel}: name длиннее 64 символов")

    desc = fm.get("description")
    if not desc:
        errors.append(f"{rel}: нет поля 'description'")
    else:
        desc = str(desc)
        if len(desc) > DESC_LIMIT:
            errors.append(f"{rel}: description {len(desc)} симв > "
                          f"лимита спеки {DESC_LIMIT}")
        elif len(desc) > DESC_BUDGET:
            warnings.append(f"{rel}: description {len(desc)} симв > "
                            f"бюджета {DESC_BUDGET} (agent-layer.dev)")

    if not fm.get("license"):
        warnings.append(f"{rel}: нет license в frontmatter")
    meta = fm.get("metadata")
    if not isinstance(meta, dict) or not meta.get("author"):
        warnings.append(f"{rel}: нет metadata.author")

    n_lines = text.count("\n") + 1
    if n_lines > LINE_LIMIT:
        warnings.append(f"{rel}: SKILL.md {n_lines} строк (> {LINE_LIMIT})")
    if len(text) / 4 > TOKEN_LIMIT:
        errors.append(f"{rel}: SKILL.md ~{int(len(text) / 4)} токенов "
                      f"(> {TOKEN_LIMIT})")

    for link in _rel_broken_links(text, skill_dir):
        warnings.append(f"{rel}: битая ссылка '{link}'")
    return errors, warnings


def find_skills(root: Path) -> list[Path]:
    """Каталоги скиллов: <root>/skills/*/ и <root>/agent/*/skills/*/."""
    out = []
    canon = root / "skills"
    if canon.is_dir():
        out.extend(sorted(d for d in canon.iterdir()
                          if d.is_dir()
                          and d.name != "__pycache__"
                          and not d.name.startswith(".")))
    agents = root / "agent"
    if agents.is_dir():
        for adir in sorted(agents.iterdir()):
            sk = adir / "skills"
            if sk.is_dir():
                out.extend(sorted(
                    d for d in sk.iterdir()
                    if d.is_dir()
                    and d.name != "__pycache__"
                    and not d.name.startswith(".")
                ))
    return out


def lint_all(root: Path) -> tuple[list[str], list[str]]:
    """(errors, warnings) по всем скиллам воркспейса."""
    errors: list[str] = []
    warnings: list[str] = []
    for d in find_skills(root):
        errs, warns = check_skill(d)
        errors.extend(errs)
        warnings.extend(warns)
    return errors, warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Проверка скиллов канона по спеке Agent Skills")
    ap.add_argument("root", nargs="?", default=None,
                    help="корень воркспейса (по умолчанию автоопределение)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else \
        Path(__file__).resolve().parents[3]

    errors, warnings = lint_all(root)
    n = len(find_skills(root))
    print(f"Скиллов: {n}")
    if errors:
        print(f"\nОшибок: {len(errors)}")
        for e in errors:
            print(f"  ✗ {e}")
    if warnings:
        print(f"Предупреждений: {len(warnings)}")
        for w in warnings:
            print(f"  ⚠ {w}")
    if not errors and not warnings:
        print("Ошибок: 0, предупреждений: 0 — скиллы в порядке")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
