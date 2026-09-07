# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""skills_sync — разноска скиллов по харнесам (sync/copy/install).

Вынесено из install_agents.py механически (verbatim) — гейт god-файлов
(docs/canon/FILE-SIZE.md)."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

from harness_map import AGENTS_SKILLS_DIRS, HARNESSES, _warn_secrets, expand


def skills_targets(platform, only=None):
    """Список каталогов, куда разносить скиллы канона.

    Пропускает харнесы без подтверждённого пути (reasonix, gemini —
    читает общий ~/.agents/skills/). Всегда добавляет общий
    ~/.agents/skills/ (стандарт Agent Skills). Значение skills может быть
    списком (несколько каталогов на харнес, напр. agy — доки разнятся).
    """
    targets = []
    for h in HARNESSES:
        if only and h["name"] not in only:
            continue
        d = (h.get("skills") or {}).get(platform)
        if not d:
            continue
        if isinstance(d, str):
            d = [d]
        for path in d:
            targets.append((h["name"], expand(path, platform)))
    common = expand(AGENTS_SKILLS_DIRS[platform], platform)
    if common:
        targets.append(("agents (общий стандарт)", common))
    return targets


def _bak_dir(dst_dir):
    """Каталог бэкапов скиллов — РЯДОМ с каталогом разноски, а не внутри:
    харнесы сканируют skills/ как скиллы, и папка *.bak внутри него
    подхватывалась как устаревший скилл (opencode грузил версию из .bak)."""
    return dst_dir.parent / f"{dst_dir.name}.bak"


def sync_skill(src_dir, dst_dir, args):
    """Определяет состояние скилла в dst: ok / backup / new.

    Возвращает (status, bak_path). Ничего не двигает — только смотрит.
    """
    name = src_dir.name
    dst = dst_dir / name
    if dst.is_dir() and _dirs_equal(src_dir, dst):
        return "ok", None
    if dst.exists():
        bak = _bak_dir(dst_dir) / name
        if bak.exists():
            return "oldbak", bak
        return "backup", bak
    return "new", None


def _dirs_equal(a, b):
    """Сравнивает два каталога рекурсивно по содержимому файлов."""
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    if [str(p) for p in fa] != [str(p) for p in fb]:
        return False
    for rel in fa:
        if not (b / rel).is_file():
            return False
        if (a / rel).read_bytes() != (b / rel).read_bytes():
            return False
    return True


def copy_skill(src_dir, dst_dir, args):
    """Кладёт скилл в dst: бэкап старого, копия нового. Реальный диск."""
    name = src_dir.name
    dst = dst_dir / name
    dst_dir.mkdir(parents=True, exist_ok=True)
    skill_md = src_dir / "SKILL.md"
    if skill_md.is_file():
        _warn_secrets(f"скилл {name}", skill_md.read_text(encoding="utf-8",
                                                         errors="replace"))
    if dst.exists():
        bak = _bak_dir(dst_dir) / name
        if bak.exists():
            shutil.rmtree(bak)
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dst), str(bak))
        print(f"[~] {name}: бэкап -> {bak}")
    shutil.copytree(src_dir, dst)


def install_skills(args, include_agents=True, only_agents=False):
    """Разносит скиллы канона (корень/skills/) и агентов (agent/*/skills/)
    по каталогам харнесов."""
    platform = "nt" if os.name == "nt" else "posix"
    root = Path(__file__).resolve().parent.parent.parent
    skills = []
    src_label = []

    if not only_agents:
        canon = root / "skills"
        if not canon.is_dir():
            print(f"[✗] канон скиллов не найден: {canon}", file=sys.stderr)
            sys.exit(1)
        skills += sorted(d for d in canon.iterdir() if (d / "SKILL.md").is_file())
        src_label.append("канон skills/")

    if include_agents:
        agent_root = root / "agent"
        if agent_root.is_dir():
            agent_skills = []
            for ad in sorted(agent_root.iterdir()):
                askills = ad / "skills"
                if askills.is_dir():
                    agent_skills += [
                        d for d in askills.iterdir() if (d / "SKILL.md").is_file()
                    ]
            if agent_skills:
                skills += sorted(agent_skills)
                src_label.append("agent/*/skills/")

    # Дубликаты имён (канон приоритетнее агентских)
    seen = set()
    unique = []
    for s in skills:
        if s.name in seen:
            continue
        seen.add(s.name)
        unique.append(s)
    skills = unique

    if not skills:
        print("[✗] скиллов не найдено (SKILL.md)", file=sys.stderr)
        sys.exit(1)

    targets = skills_targets(platform, only=args.harness)
    print(f"источник: {' + '.join(src_label)} ({len(skills)} скиллов), "
          f"каталогов разноски: {len(targets)}")
    if args.dry_run:
        print("\n[dry-run] план (ничего не записывается):")

    installed = 0
    for name, dst_dir in targets:
        for src in skills:
            status, bak = sync_skill(src, dst_dir, args)
            if status == "ok":
                continue
            # oldbak (бэкап уже есть) НЕ блокирует обновление: канон — источник
            # истины, зеркала — производные. Паттерн индустрии (Ansible backup=yes,
            # rsync --backup): бэкап перезаписывается при каждом реальном изменении.
            # copy_skill сам удалит старый .bak перед записью нового.
            if args.dry_run:
                what = f"бэкап {bak.name} + запись" if bak else "запись"
                print(f"[ ] {name}/{src.name}: {what} -> {dst_dir}")
                continue
            copy_skill(src, dst_dir, args)
            print(f"[✓] {name}/{src.name} -> {dst_dir}")
            installed += 1

    print(f"\nитого: скиллов {len(skills)}, каталогов {len(targets)}, "
          f"установлено/обновлено {installed}"
          + (" (dry-run, ничего не записано)" if args.dry_run else ""))

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
