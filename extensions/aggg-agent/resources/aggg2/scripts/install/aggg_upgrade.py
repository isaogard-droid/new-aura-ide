#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Обновление AGGG2.0 «по месту»: снапшот → сверка манифестов → чистка
устаревшего (в бэкап, не в небытие) → наложение нового с .old-копиями.

Источник новой версии — архив aggg2-<версия>.tar.gz/.zip ИЛИ распакованная
папка (режим «две папки»: --root указывает старую явно, источник — новая).
Манифест: manifest.txt (везёт сам архив — у получателя нет
make_archive.sh; паттерн sdist SOURCES.txt / dpkg .list) →
make_archive.sh --list (рабочая копия) → все файлы (фолбэк для новой
стороны). Если --root не существует/пуст — install-режим: установка с
нуля (все файлы манифеста источника + manifest.txt ложится в корень —
будущие обновления на этой машине знают манифест).
По манифесту: в систему заносится ВСЁ из нового манифеста, убирается
то, чем владела старая версия и чего нет в новой; --clean-junk
дополнительно вычищает следы вне манифеста (старые архивы, .bak, левые
файлы) — тоже в бэкап. Данные (db/, venv/, models/, .env, .git/,
projects/, CHANGELOG/, ...) не трогаются никогда.

Установку и диагностику НЕ запускает — печатает следующие команды
(setup.py --check → setup.py → doctor.py).

Имя и путь папки роли не играют: корень опознаётся маркерами
(_compat.chulan_root — любые 2 из VERSION / db-tools/ /
scripts/_compat.py); --root задаёт его явно.

Паттерны индустрии (research.db id=694/695/696):
- manifest-prune: чистятся ТОЛЬКО файлы, которыми владела старая версия
  (манифест make_archive.sh --list) и которых нет в новой — семантика
  dpkg; manifest-driven sync двух каталогов — MSDeploy custom manifests;
- reviewed, recoverable prune: вычищенное ПЕРЕНОСИТСЯ в
  ~/aggg-backups/, не удаляется (rsync --delete с бэкапом; safer
  alternatives to rm — move, не delete);
- защита данных — rsync --exclude (НЕ --delete-excluded: тот удаляет
  и защищённое);
- verify-then-swap (cli-update-spec): снапшот до, откат одной командой.

Запуск:
    python3 scripts/install/aggg_upgrade.py aggg2-2.8.tar.gz --dry-run
    python3 scripts/install/aggg_upgrade.py /tmp/aggg2-2.8 --root /data/AGGG --clean-junk
    python3 scripts/install/aggg_upgrade.py aggg2-2.8.tar.gz --backup-dir ~/aggg-backups
"""
import argparse
import filecmp
import fnmatch
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from _compat import _validate_root, chulan_root  # noqa: E402

MANIFEST_SCRIPT = "make_archive.sh"
MANIFEST_FILE = "manifest.txt"  # манифест ВНУТРИ архива (sdist-паттерн:
                                 # SOURCES.txt, dpkg .list — артефакт
                                 # везёт список своих файлов с собой)
MARKERS = ("VERSION", "make_archive.sh", "db-tools")
DATA_GUARD = {"db", "venv", "models"}  # данные: не накладывать, не чистить

# Что НИКОГДА не считается мусором вне манифеста: данные, служебное,
# исключения make_archive.sh, доки-не-в-архиве (CHANGELOG/ и др.)
# и ЯДРО (каталоги канона — страховка, если манифест не снялся).
EXCLUDES_FILE = "aggg_excludes.txt"
CORE_DIRS = {"db", "venv", "models", ".venv", ".git", ".github",
             ".reasonix", "projects", "node_modules", "db-tools",
             "scripts", "skills", "mcp", "harness", "agent", "Wiki", "docs"}
CORE_NAMES = {"VERSION", "manifest.txt", "make_archive.sh"}


def _read_manifest_file(base: Path) -> set[str] | None:
    """Манифест из manifest.txt (везёт архив; у получателя нет
    make_archive.sh). Сам файл включается в манифест — он часть ядра
    (как SOURCES.txt в sdist). None, если файла нет или не читается."""
    mf = base / MANIFEST_FILE
    if not mf.is_file():
        return None
    try:
        lines = mf.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    manifest = {s for s in (line.strip() for line in lines)
                if s and not s.startswith("==") and (base / s).exists()}
    manifest.add(MANIFEST_FILE)
    return manifest


def _run_manifest(root: Path) -> set[str]:
    """Манифест через make_archive.sh --list (рабочая копия со скриптом).
    Пустой, если скрипта нет или bash недоступен."""
    script = root / MANIFEST_SCRIPT
    if not script.is_file():
        return set()
    try:
        proc = subprocess.run(["bash", str(script), "--list"], cwd=root,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return set()
    manifest = {s for s in (line.strip() for line in proc.stdout.splitlines())
                if s and not s.startswith("==") and (root / s).exists()}
    # manifest.txt — часть ядра всегда (в рабочей копии файла может ещё
    # не быть: генерится при сборке/установке; у получателя он есть).
    manifest.add(MANIFEST_FILE)
    return manifest


def _manifest_of(base: Path, fallback_walk: bool = False) -> set[str]:
    """Манифест каталога: manifest.txt → make_archive.sh --list →
    (опционально) все файлы. Паттерн: у получателя архива нет
    make_archive.sh, но есть manifest.txt."""
    manifest = _read_manifest_file(base)
    if manifest is not None:
        return manifest
    manifest = _run_manifest(base)
    if manifest or not fallback_walk:
        return manifest
    return _walk_files(base)


def _files_equal(a: Path, b: Path) -> bool:
    """Сравнение содержимого. Для manifest.txt — по отсортированным
    строкам (bash sort в make_archive.sh и Python sorted() расходятся в
    locale-порядке — это не изменение версии)."""
    if a.name == MANIFEST_FILE and b.name == MANIFEST_FILE:
        try:
            la = sorted(a.read_text(encoding="utf-8", errors="replace")
                        .splitlines())
            lb = sorted(b.read_text(encoding="utf-8", errors="replace")
                        .splitlines())
            return la == lb
        except OSError:
            return False
    if not a.is_file() or not b.is_file():
        return False
    return filecmp.cmp(a, b, shallow=False)


def _inner_root(names: list[str]) -> str:
    """Префикс внутренней корневой папки архива ('' если маркеры в корне)."""
    if any(n in names for n in ("VERSION", "make_archive.sh")) or \
            any(n.startswith("db-tools/") for n in names):
        return ""
    top = {n.split("/", 1)[0] for n in names if n and not n.endswith("/")}
    for t in sorted(top):
        if any(n.startswith(f"{t}/VERSION") or n.startswith(f"{t}/make_archive.sh")
               or n.startswith(f"{t}/db-tools/") for n in names):
            return t
    raise SystemExit(
        f"[✗] источник не похож на AGGG2.0: нет маркеров {', '.join(MARKERS)}")


def _new_manifest(source: Path, tmp: Path, password: str) -> tuple[Path, set[str]]:
    """(base, манифест нового ядра) для папки, zip (make_archive.sh,
    запаролен) или tar-архива."""
    if source.is_dir():
        base = source
        return base, _manifest_of(base, fallback_walk=True)
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as zf:
            names = zf.namelist()
            inner = _inner_root(names)
            if any(".." in n for n in names):
                raise SystemExit("[✗] архив с '..' в именах — не распаковываю")
            try:
                # архив свой; '..' отсечены строкой выше
                zf.extractall(tmp, pwd=password.encode("utf-8"))  # noqa: S202
            except RuntimeError as exc:
                raise SystemExit(
                    f"[✗] не распаковался (пароль/битый архив): {exc}") from None
        base = tmp / inner if inner else tmp
        return base, _manifest_of(base, fallback_walk=True)
    with tarfile.open(source, "r:*") as tar:
        names = tar.getnames()
        inner = _inner_root(names)
        _extract_tar_safely(tar, tmp)
    base = tmp / inner if inner else tmp
    return base, _manifest_of(base, fallback_walk=True)


def _extract_tar_safely(tar: tarfile.TarFile, destination: Path) -> None:
    """Extract regular files/directories after validating every member path."""
    root = destination.resolve()
    for member in tar.getmembers():
        target = (destination / member.name).resolve()
        if target != root and root not in target.parents:
            raise SystemExit(f"[✗] архив выходит за пределы каталога: {member.name}")
        if not (member.isdir() or member.isreg()):
            raise SystemExit(f"[✗] запрещённый тип записи в архиве: {member.name}")
        tar.extract(member, destination)  # nosemgrep: trailofbits.python.tarfile-extractall-traversal.tarfile-extractall-traversal — path and member type validated above


def _walk_files(base: Path) -> set[str]:
    """Все файлы каталога (относительные пути) — фолбэк без манифеста."""
    return {str(f.relative_to(base)) for f in base.rglob("*") if f.is_file()}


def _load_excludes() -> list[tuple[str, str]]:
    """Единый список исключений раздачи (SSOT: читает и make_archive.sh —
    что не в архиве, то не сурсы; два списка разъезжаются, один — нет)."""
    f = Path(__file__).resolve().parent.parent / EXCLUDES_FILE
    if not f.is_file():
        return []
    out = []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        kind, _, pat = s.partition(":")
        if kind in ("name", "path") and pat:
            out.append((kind, pat))
    return out


_PROTECT_PATTERNS = _load_excludes()


def _ssot_excluded(rel: str) -> bool:
    """Путь попадает под ЕДИНЫЙ список исключений раздачи (SSOT)."""
    parts = rel.split("/")
    for kind, pat in _PROTECT_PATTERNS:
        if kind == "name":
            if any(fnmatch.fnmatch(p, pat) for p in parts):
                return True
        elif fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(f"./{rel}", pat):
            return True
    return False


def _protected(rel: str) -> bool:
    """Путь, который НЕ считается мусором: исключения раздачи (SSOT) +
    страховка ядра на случай пустого манифеста. CHANGELOG/ и пр.
    защищены не спецкейсом, а правилом «в архив не входит»."""
    parts = rel.split("/")
    if any(p in CORE_DIRS for p in parts) or parts[-1] in CORE_NAMES:
        return True
    return _ssot_excluded(rel)


def _walk_old_manifest(root: Path, new_manifest: set[str]) -> set[str]:
    """Фолбэк --full для старых версий БЕЗ манифеста (2.4 и раньше):
    ядро старой версии строится обходом файлов — всё, кроме исключений
    раздачи (SSOT: данные, .env, .git, ...) и личных Wiki-постов,
    которых нет в новом манифесте. Паттерн reconciliation (K8s):
    желаемое = новый манифест + защита, остальное — неуправляемое."""
    old = set()
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        rel = str(f.relative_to(root))
        if _ssot_excluded(rel):
            continue
        if rel.startswith("Wiki/") and rel not in new_manifest:
            continue  # личные вики-посты — не ядро старой версии
        old.add(rel)
    return old


def _junk_files(root: Path, manifest: set[str]) -> list[str]:
    """Следы ВНЕ манифеста (мусор): файлы корня, не в манифесте и не
    защищённые. Данные и служебное сюда не попадают (_protected)."""
    return sorted(
        str(f.relative_to(root))
        for f in root.rglob("*")
        if f.is_file()
        and str(f.relative_to(root)) not in manifest
        and not _protected(str(f.relative_to(root))))


def _snapshot(root: Path, backup_dir: Path, ts: str) -> Path:
    """tar-снапшот ядра (данные исключены — их обновление не трогает)."""
    snapshot = backup_dir / f"aggg2-backup-{ts}.tar.gz"
    base = root.name
    excl = [f"--exclude={base}/{d}" for d in DATA_GUARD]
    proc = subprocess.run(
        ["tar", "-czf", str(snapshot), "-C", str(root.parent), *excl, base],
        capture_output=True)
    if proc.returncode == 0:
        print(f"[✓] снапшот ядра -> {snapshot}")
        return snapshot
    print(f"[!] tar недоступен — снапшот не сделан "
          f"({proc.stderr.decode(errors='replace')[:200]})")
    return Path()


def _move_away(src: Path, dst_root: Path, rel: str) -> None:
    """Перенос файла/дерева в бэкап-каталог с сохранением пути."""
    dst = dst_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Обновление AGGG2.0 из архива или распакованной папки: "
                    "снапшот → сверка манифестов → чистка → наложение")
    ap.add_argument("source", help="aggg2-<версия>.tar.gz ИЛИ папка новой версии")
    ap.add_argument("--root", help="старая версия (по умолчанию — по маркерам)")
    ap.add_argument("--dry-run", action="store_true",
                    help="план без записи (сверка и отчёт)")
    ap.add_argument("--clean-junk", action="store_true",
                    help="вычистить и мусор вне манифеста (в бэкап)")
    ap.add_argument("--full", action="store_true",
                    help="полная замена: если у старой версии нет манифеста, "
                         "построить его обходом файлов (личные данные и "
                         "вики защищены, остальное — старое ядро)")
    ap.add_argument("--backup-dir", default=str(Path.home() / "aggg-backups"),
                    help="куда класть снапшот и вычищенное")
    ap.add_argument("--password", default="t.me/aidvizh_hub",
                    help="пароль zip-архива (по умолчанию — гиг)")
    args = ap.parse_args()

    if args.root:
        root = Path(args.root).expanduser().resolve()
        install_mode = not root.is_dir() or not any(root.iterdir())
        if not install_mode:
            try:
                _validate_root(root, source="--root")
            except RuntimeError as exc:
                print(f"[✗] {exc}")
                return 1
    else:
        root = chulan_root()
        install_mode = False
    source = Path(args.source).expanduser().resolve()
    if not str(args.source).strip():
        print("[✗] источник не указан")
        return 1
    if not source.exists():
        print(f"[✗] нет источника: {source}")
        return 1
    backup_dir = Path(args.backup_dir).expanduser()
    ts = time.strftime("%Y%m%d-%H%M%S")
    print(f"AGGG2.0: {root}" + ("  [install-режим: старой версии нет]" if install_mode else ""))
    print(f"источник: {source} ({'папка' if source.is_dir() else 'архив'})")

    with tempfile.TemporaryDirectory(prefix="aggg_new_") as tmpdir:
        tmp = Path(tmpdir)
        new_base, new_manifest = _new_manifest(source, tmp, args.password)
        old_manifest = set() if install_mode else _manifest_of(root)
        if not install_mode and not old_manifest and args.full:
            old_manifest = _walk_old_manifest(root, new_manifest)
            print(f"[i] --full: манифеста у старой версии нет — построен "
                  f"обходом ({len(old_manifest)} файлов; данные, .env и "
                  f"личные вики-посты защищены)")
        if not install_mode and not old_manifest:
            print("[!] манифест старой версии пуст (нет manifest.txt и "
                  "make_archive.sh) — чистка пропущена, наложение пройдёт "
                  "по манифесту источника, данные защищены. Для полной "
                  "замены старых версий — флаг --full")
        added = sorted(new_manifest - old_manifest)
        removed = sorted(old_manifest - new_manifest)
        changed = sorted(f for f in (new_manifest & old_manifest)
                         if (new_base / f).is_file()
                         and not _files_equal(root / f, new_base / f))
        junk = _junk_files(root, old_manifest)
        print(f"\nсверка: +{len(added)} добавлено, ~{len(changed)} "
              f"изменено, -{len(removed)} устарело, "
              f"мусора вне манифеста {len(junk)}")
        for kind, items in (("ДОБАВЛЕНО", added), ("ИЗМЕНЕНО", changed),
                            ("УСТАРЕЛО", removed), ("МУСОР", junk)):
            for f in items[:20]:
                print(f"  [{kind[:1]}] {f}")
            if len(items) > 20:
                print(f"  ... и ещё {len(items) - 20}")
        if junk and not args.clean_junk:
            print("[i] мусор вне манифеста не тронут — для чистки: --clean-junk")

        if args.dry_run:
            print("\n[dry-run] ничего не записано")
            return 0

        backup_dir.mkdir(parents=True, exist_ok=True)
        snapshot = Path()
        n_pruned = 0
        if not install_mode:
            snapshot = _snapshot(root, backup_dir, ts)

            # 1. Чистка устаревшего: только манифест старой версии, в бэкап
            pruned_dir = backup_dir / f"pruned-{ts}"
            n_pruned = sum(
                1 for f in removed
                if (root / f).exists()
                and not _move_away(root / f, pruned_dir, f))
            if n_pruned:
                print(f"[✓] устаревшее вычищено ({n_pruned}) -> {pruned_dir}/")

            # 2. Мусор вне манифеста — по явному --clean-junk, в бэкап
            if args.clean_junk and junk:
                junk_dir = backup_dir / f"junk-{ts}"
                n_junk = sum(
                    1 for f in junk
                    if (root / f).exists()
                    and not _move_away(root / f, junk_dir, f))
                if n_junk:
                    print(f"[✓] мусор вычищен ({n_junk}) -> {junk_dir}/")
        else:
            root.mkdir(parents=True, exist_ok=True)

        # 3. Наложение нового манифеста: .old-копии заменённых, данные защищены
        n_copied = 0
        for f in sorted(new_manifest):
            if install_mode and f == MANIFEST_FILE:
                continue  # манифест пишется ниже единым списком
            if f.split("/", 1)[0] in DATA_GUARD or f.endswith((".db", ".env")):
                continue
            src, dst = new_base / f, root / f
            if not src.is_file():
                continue  # в источнике файла нет (рабочая копия) — не трогаем
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and not _files_equal(src, dst):
                shutil.copy2(dst, f"{dst}.old")
            if not dst.exists() or not _files_equal(src, dst):
                shutil.copy2(src, dst)
                n_copied += 1
        print(f"[✓] наложено файлов: {n_copied} (заменённые — с .old)")

        # install-режим: манифест ложится в корень единым списком —
        # будущие обновления на этой машине знают, чем владеет версия
        if install_mode:
            (root / MANIFEST_FILE).write_text(
                "\n".join(sorted(new_manifest - {MANIFEST_FILE})) + "\n",
                encoding="utf-8")

    print("\nДальше (официальная установка):")
    print(f"  python3 {root / 'scripts/setup.py'} --check")
    print(f"  python3 {root / 'scripts/setup.py'}")
    print(f"  python3 {root / 'scripts/doctor/doctor.py'}")
    if not install_mode:
        print("\nОткат:")
        if snapshot.is_file():
            print(f"  tar -xzf {snapshot} -C {root.parent}")
        if n_pruned:
            print(f"  вычищенное вернуть: cp -r {pruned_dir}/ {root}/")
        if args.clean_junk and junk and (backup_dir / f"junk-{ts}").is_dir():
            print(f"  мусор вернуть: cp -r {backup_dir / f'junk-{ts}'}/ {root}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
