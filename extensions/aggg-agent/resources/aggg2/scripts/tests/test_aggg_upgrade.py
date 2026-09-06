#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Регрессия aggg_upgrade.py: режим «две папки» (--root старая, источник —
распакованная новая), замена по манифесту, --clean-junk, защита данных;
manifest.txt у получателя без make_archive.sh; zip-архив; install-режим.
Изоляция: throwaway-деревья в tempfile, продакшн-пути не читаются.

Имена тестов = спека:
  test_dry_run_lists_all — план: устарело/добавлено/мусор, записи нет
  test_replace_by_manifest — всё из нового манифеста занесено,
      старое/мусор уехали в бэкап, .old и данные на месте
  test_junk_stays_without_flag — без --clean-junk мусор не тронут
  test_archive_mode — источник-tar работает так же
  test_manifest_only_participant — у получателя нет make_archive.sh,
      но есть manifest.txt: замена и чистка работают
  test_zip_archive_mode — zip (как make_archive.sh) с паролем
  test_install_mode — --root не существует: установка с нуля,
      manifest.txt ложится в корень

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = ROOT / "scripts" / "install" / "aggg_upgrade.py"
# пароль архива — не секрет: это ссылка на гиг (как в make_archive.sh)
PASSWORD = "t.me/aidvizh_hub"  # noqa: S105


def _make_tree(root: Path, version: str, keep: str, extra: tuple[str, ...],
               manifest: str = "script"):
    """Мини-AGGG: маркеры + манифест (manifest="script" — make_archive.sh,
    "file" — manifest.txt как у получателя архива, None — старая версия
    без манифеста) + файлы ядра."""
    (root / "db-tools").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(exist_ok=True)
    (root / "VERSION").write_text(version)
    (root / "scripts/_compat.py").touch()
    files = ("VERSION", "keep.txt") + extra
    if manifest == "file":
        (root / "manifest.txt").write_text("\n".join(files) + "\n")
    elif manifest == "script":
        lines = ["#!/bin/sh", "echo '== манифест =='"]
        for f in files + ("make_archive.sh",):
            lines.append(f"echo \"{f}\"")
        (root / "make_archive.sh").write_text("\n".join(lines) + "\n")
    (root / "keep.txt").write_text(keep)
    for f in extra:
        (root / f).write_text(f)


class UpgradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.old = self.d / "aggg_old"
        self.new = self.d / "aggg2-2.0"
        self.backups = self.d / "backups"
        _make_tree(self.old, "1.0", "старый keep", ("old.txt",))
        _make_tree(self.new, "2.0", "новый keep", ("new.txt",))
        (self.old / "junk.txt").write_text("мусор")  # не в манифесте
        (self.old / "CHANGELOG.md").write_text("журнал владельца")
        (self.old / "db").mkdir(exist_ok=True)
        (self.old / "db/research.db").write_text("данные")

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *argv):
        return subprocess.run([sys.executable, str(TOOL), *argv],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")

    def test_dry_run_lists_all(self):
        p = self.run_tool(str(self.new), "--root", str(self.old),
                          "--dry-run", "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stderr)
        out = p.stdout
        self.assertIn("[У] old.txt", out)
        self.assertIn("[Д] new.txt", out)
        self.assertIn("[М] junk.txt", out)
        self.assertIn("--clean-junk", out)
        self.assertIn("ничего не записано", out)
        self.assertTrue((self.old / "old.txt").exists())

    def test_replace_by_manifest(self):
        p = self.run_tool(str(self.new), "--root", str(self.old),
                          "--clean-junk", "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((self.old / "VERSION").read_text().strip(), "2.0")
        self.assertEqual((self.old / "keep.txt").read_text().strip(),
                         "новый keep")
        self.assertTrue((self.old / "keep.txt.old").exists())
        self.assertTrue((self.old / "new.txt").exists())
        self.assertFalse((self.old / "old.txt").exists())
        self.assertFalse((self.old / "junk.txt").exists())
        self.assertTrue((self.old / "CHANGELOG.md").exists())  # не сурсы — не тронут
        self.assertTrue((self.old / "scripts/_compat.py").exists())
        self.assertEqual((self.old / "db/research.db").read_text(), "данные")
        self.assertTrue(list(self.backups.glob("pruned-*/old.txt")))
        self.assertTrue(list(self.backups.glob("junk-*/junk.txt")))

    def test_junk_stays_without_flag(self):
        p = self.run_tool(str(self.new), "--root", str(self.old),
                          "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((self.old / "junk.txt").exists())
        self.assertEqual((self.old / "db/research.db").read_text(), "данные")
        self.assertEqual((self.old / "VERSION").read_text().strip(), "2.0")

    def test_archive_mode(self):
        tar = self.d / "aggg2-2.0.tar.gz"
        with tarfile.open(tar, "w:gz") as t:
            t.add(self.new, arcname="aggg2-2.0")
        p = self.run_tool(str(tar), "--root", str(self.old),
                          "--clean-junk", "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((self.old / "VERSION").read_text().strip(), "2.0")
        self.assertTrue((self.old / "new.txt").exists())
        self.assertFalse((self.old / "old.txt").exists())

    def test_manifest_only_participant(self):
        """У получателя нет make_archive.sh — манифест из manifest.txt."""
        old2 = self.d / "old_manifest"
        new2 = self.d / "new_manifest"
        _make_tree(old2, "1.0", "старый keep", ("old.txt",), manifest="file")
        _make_tree(new2, "2.0", "новый keep", ("new.txt",), manifest="file")
        p = self.run_tool(str(new2), "--root", str(old2),
                          "--clean-junk", "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((old2 / "VERSION").read_text().strip(), "2.0")
        self.assertFalse((old2 / "old.txt").exists())
        self.assertTrue((old2 / "new.txt").exists())
        self.assertTrue(list(self.backups.glob("pruned-*/old.txt")))

    def test_zip_archive_mode(self):
        """Архив как у make_archive.sh: zip с паролем, внутри aggg2/."""
        zip_path = self.d / "aggg2-2.0.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.setpassword(PASSWORD.encode())
            for f in self.new.rglob("*"):
                if f.is_file():
                    zf.write(f, f"aggg2/{f.relative_to(self.new)}")
        p = self.run_tool(str(zip_path), "--root", str(self.old),
                          "--clean-junk", "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((self.old / "VERSION").read_text().strip(), "2.0")
        self.assertTrue((self.old / "new.txt").exists())
        self.assertFalse((self.old / "old.txt").exists())

    def test_full_replace_legacy_without_manifest(self):
        """--full: старая версия БЕЗ манифеста (как 2.4) — ядро строится
        обходом; данные, .env и личные вики-посты защищены."""
        old2 = self.d / "old_legacy"
        new2 = self.d / "new_legacy"
        _make_tree(old2, "1.0", "старый keep", ("old.txt",), manifest=None)
        _make_tree(new2, "2.0", "новый keep", ("new.txt",))
        (old2 / "junk.txt").write_text("мусор")
        (old2 / "db").mkdir(exist_ok=True)
        (old2 / "db/research.db").write_text("данные")
        (old2 / "Wiki").mkdir(exist_ok=True)
        (old2 / "Wiki/личное").mkdir(exist_ok=True)
        (old2 / "Wiki/личное/mine.md").write_text("личный пост")
        p = self.run_tool(str(new2), "--root", str(old2), "--full",
                          "--clean-junk", "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("--full", p.stdout)
        self.assertEqual((old2 / "VERSION").read_text().strip(), "2.0")
        self.assertEqual((old2 / "keep.txt").read_text().strip(),
                         "новый keep")
        self.assertFalse((old2 / "old.txt").exists())
        self.assertFalse((old2 / "junk.txt").exists())
        self.assertTrue((old2 / "new.txt").exists())
        self.assertEqual((old2 / "db/research.db").read_text(), "данные")
        self.assertEqual((old2 / "Wiki/личное/mine.md").read_text(),
                         "личный пост")
        self.assertTrue(list(self.backups.glob("pruned-*/old.txt")))
        self.assertTrue(list(self.backups.glob("pruned-*/junk.txt")))

    def test_install_mode(self):
        """--root на несуществующую папку: установка с нуля."""
        fresh = self.d / "fresh_aggg"
        p = self.run_tool(str(self.new), "--root", str(fresh),
                          "--backup-dir", str(self.backups))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("install-режим", p.stdout)
        self.assertEqual((fresh / "VERSION").read_text().strip(), "2.0")
        self.assertTrue((fresh / "new.txt").exists())
        self.assertTrue((fresh / "manifest.txt").exists())
        self.assertNotIn("Откат", p.stdout)


if __name__ == "__main__":
    unittest.main()
