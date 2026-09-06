#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""gen_index.py — генерация index.md Wiki-библиотеки из frontmatter постов.

Паттерн LLM Wiki at Scale: индекс генерируется скриптом, агент НЕ читает
и НЕ правит index.md руками — один прогон = актуальный каталог. Это снимает
потолок «index.md стал слишком большим для чтения целиком» (после ~100-200
постов таблицу нельзя читать в контекст, но скрипту всё равно: он читает
только frontmatter каждого файла).

Что делает:
  - сканирует Wiki/<категория>/*.md (кроме служебных: README, index, log, _templates);
  - читает frontmatter: title, description, date, tags;
  - генерирует index.md: шапка + таблица (свежие сверху) + секция «По тегам» (алфавит).

Использование:
  python3 gen_index.py [путь-к-Wiki] [--dry-run]
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


try:
    import yaml
except ImportError:
    yaml = None

SERVICE_FILES = {"README.md", "index.md", "log.md"}
SKIP_DIRS = {"_templates", "raw", "assets", "log-archive"}
DESC_MAX = 80  # максимальная длина «Темы» в таблице


def parse_frontmatter(text: str) -> dict | None:
    """Возвращает dict из YAML-frontmatter или None, если его нет."""
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


def short_title(title: str) -> str:
    """'Tencent WorldClaw — агентная генерация 3D-миров' → 'Tencent WorldClaw'."""
    if not title:
        return ""
    return title.split(" — ")[0].strip()


def short_desc(desc: str) -> str:
    """Обрезает описание до DESC_MAX символов (по словам), добавляя '…'."""
    desc = (desc or "").strip().replace("|", "\\|")
    if len(desc) <= DESC_MAX:
        return desc
    cut = desc[:DESC_MAX]
    # режем по последнему пробелу, чтобы не разрывать слово
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:—") + "…"


def esc(value: str) -> str:
    """Экранирует '|' в ячейках markdown-таблицы."""
    return (value or "").replace("|", "\\|")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    root = Path(args[0]) if args else Path(__file__).resolve().parents[3] / "Wiki"
    if not root.is_dir():
        print(f"✗ Wiki не найдена: {root}", file=sys.stderr)
        return 1

    posts: list[tuple[Path, dict]] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if path.name in SERVICE_FILES or rel.parts[0] in SKIP_DIRS:
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if fm is None:
            print(f"⚠ {rel}: нет frontmatter — пропущен из индекса", file=sys.stderr)
            continue
        posts.append((rel, fm))

    # сортировка: свежие сверху (date DESC); внутри даты сохраняется
    # алфавитный порядок исходной выборки (стабильная сортировка)
    posts.sort(key=lambda item: str(item[1].get("date", "")), reverse=True)

    lines: list[str] = []
    lines.append("# Index — каталог Wiki")
    lines.append("")
    lines.append(f"Последнее обновление: "
                 f"{datetime.now(timezone.utc).astimezone().date().isoformat()}")
    lines.append("")
    lines.append("| Пост | Тема | Теги | Дата | Папка |")
    lines.append("|------|------|------|------|-------|")
    for rel, fm in posts:
        title = esc(short_title(str(fm.get("title", ""))))
        desc = esc(short_desc(str(fm.get("description", ""))))
        tags = ", ".join(str(t) for t in (fm.get("tags") or []))
        d = str(fm.get("date", ""))
        folder = str(rel.parent) + "/" if str(rel.parent) != "." else ""
        lines.append(f"| [{title}]({rel}) | {desc} | {esc(tags)} | {d} | {folder} |")

    # секция «По тегам»: теги по алфавиту, внутри — посты по папке+имени
    tag_map: dict[str, list[tuple[Path, str]]] = {}
    for rel, fm in posts:
        for tag in fm.get("tags") or []:
            tag = str(tag)
            tag_map.setdefault(tag, []).append((rel, rel.stem))
    for lst in tag_map.values():
        lst.sort(key=lambda item: str(item[0]))
    lines.append("")
    lines.append("## По тегам")
    lines.append("")
    for tag in sorted(tag_map):
        links = ", ".join(f"[{slug}]({rel})" for rel, slug in tag_map[tag])
        lines.append(f"- `{tag}`: {links}")

    output = "\n".join(lines) + "\n"
    if dry_run:
        print(output)
        return 0

    dst = root / "index.md"
    backup = dst.with_suffix(".md.bak")
    if dst.exists():
        backup.write_text(dst.read_text(encoding="utf-8"), encoding="utf-8")
    dst.write_text(output, encoding="utf-8")
    print(f"[✓] index.md сгенерирован: {len(posts)} постов, {len(tag_map)} тегов")
    print(f"    файл: {dst} (бэкап: {backup.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
