#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""lint_wiki.py — проверка целостности Wiki-библиотеки (паттерн LLM Wiki Карпатого).

Проверяет у каждого поста (все *.md, кроме служебных):
  - наличие YAML-frontmatter;
  - обязательные поля: type, title, description, date, tags;
  - теги: нижний регистр, без пробелов;
  - имя файла: kebab-case.

Выводит отчёт об ошибках и статистику тегов. Код возврата 0 = чисто, 1 = есть ошибки.

Использование:
  python3 lint_wiki.py [путь-к-Wiki]
"""
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

REQUIRED = ("type", "title", "description", "date", "tags")
SERVICE_FILES = {"README.md", "index.md", "log.md"}
SKIP_DIRS = {"_templates", "raw", "assets"}


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
        except yaml.YAMLError as exc:
            print(f"  ⚠ YAML-ошибка в frontmatter: {exc}", file=sys.stderr)
            return None
    # fallback без yaml: только ключи верхнего уровня
    data = {}
    for line in block.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2)
    return data


def is_kebab(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*\.md", name))


def check_index(root: Path, posts: list[Path]) -> list[str]:
    """Проверка табличной части index.md: дубли строк, битые ссылки, посты вне индекса.

    Секция «По тегам» (ниже таблицы) содержит каждый пост по числу его тегов —
    это НЕ дубли (проверено 12.08.2026: первая версия
    проверки считала все ссылки и давала ложные срабатывания). Считаем
    только ссылки ДО строки «## По тегам». Лечится рассинхрон: gen_index.py <Wiki>.
    """
    errors: list[str] = []
    index_file = root / "index.md"
    if not index_file.is_file():
        return ["index.md не найден — сгенерируй: python3 gen_index.py <Wiki>"]
    text = index_file.read_text(encoding="utf-8")
    table = text.split("## По тегам", 1)[0]
    links = re.findall(r"\]\(([^)#]+\.md)\)", table)
    counts: Counter = Counter(links)
    for link, n in counts.items():
        if n > 1:
            errors.append(f"index.md: строка '{link}' повторяется в таблице {n} раз")
        if not (root / link).is_file():
            errors.append(f"index.md: битая ссылка '{link}' — файла нет")
    indexed = set(counts)
    post_rels = {str(p.relative_to(root)) for p in posts}
    for rel in sorted(post_rels - indexed):
        errors.append(f"index.md: пост '{rel}' отсутствует в индексе")
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3] / "Wiki"
    errors: list[str] = []
    posts: list[Path] = []
    tag_counter: Counter = Counter()

    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if path.name in SERVICE_FILES or rel.parts[0] in SKIP_DIRS:
            continue
        posts.append(path)
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: нет YAML-frontmatter (начинается с '---' и закрыт '---')")
            continue
        for field in REQUIRED:
            value = fm.get(field)
            if value in (None, ""):
                errors.append(f"{rel}: отсутствует обязательное поле '{field}'")
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            errors.append(f"{rel}: 'tags' должен быть списком [a, b]")
            tags = []
        for tag in tags:
            tag = str(tag)
            if tag != tag.lower() or " " in tag:
                errors.append(f"{rel}: тег '{tag}' — нужен нижний регистр без пробелов")
            tag_counter[tag] += 1
        if not is_kebab(path.name):
            errors.append(f"{rel}: имя файла не kebab-case")

    errors.extend(check_index(root, posts))

    # Свежесть индекса поиска: пост без пересборки build.py невидим для
    # search.py — библиотека «в порядке», а знания не находятся
    # (аудит 17.08.2026, research.db id=785).
    wiki_db = root.parent / "db" / "wiki.db"
    if posts and wiki_db.is_file():
        newest_post = max(p.stat().st_mtime for p in posts)
        if wiki_db.stat().st_mtime < newest_post:
            newest = max(posts, key=lambda p: p.stat().st_mtime)
            errors.append(f"db/wiki.db старее поста '{newest.relative_to(root)}'"
                          " — пересобери: python3 db-tools/build.py -r Wiki"
                          " -o db/wiki.db")
    elif posts:
        errors.append("db/wiki.db нет — собери: python3 db-tools/build.py"
                      " -r Wiki -o db/wiki.db")

    print(f"Постов: {len(posts)}")
    if tag_counter:
        print("Теги: " + ", ".join(f"{t} ({n})" for t, n in tag_counter.most_common()))
    if errors:
        print(f"\nОшибок: {len(errors)}")
        for err in errors:
            print(f"  ✗ {err}")
        return 1
    print("Ошибок: 0 — библиотека в порядке")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
