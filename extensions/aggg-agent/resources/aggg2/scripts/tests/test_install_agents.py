#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты разноски скиллов (install_agents.py): состояния sync_skill
(ok/backup/oldbak/new) и copy_skill (бэкап + перезапись старого бэкапа).
Работают на временных каталогах — реальные харнесы не трогаем.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import io
import os
import shutil
import sys
import tempfile

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'install'))
import install_agents as ia


class SyncSkillTest(unittest.TestCase):
    """sync_skill(src_dir, dst_dir, args) → (status, bak_path)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.canon = self.tmp / "canon"
        self.harness = self.tmp / "harness"
        (self.canon / "demo").mkdir(parents=True)
        (self.harness / "demo").mkdir(parents=True)

    def _write(self, d, text):
        (d / "SKILL.md").write_text(text, encoding="utf-8")

    def test_ok_when_identical(self):
        self._write(self.canon / "demo", "# v1\n")
        self._write(self.harness / "demo", "# v1\n")
        status, bak = ia.sync_skill(self.canon / "demo", self.harness, None)
        self.assertEqual(status, "ok")
        self.assertIsNone(bak)

    def test_backup_when_different_no_bak(self):
        self._write(self.canon / "demo", "# v2\n")
        self._write(self.harness / "demo", "# v1\n")
        status, bak = ia.sync_skill(self.canon / "demo", self.harness, None)
        self.assertEqual(status, "backup")
        self.assertEqual(bak, self.harness.parent / "harness.bak" / "demo")

    def test_oldbak_when_different_and_bak_exists(self):
        self._write(self.canon / "demo", "# v3\n")
        self._write(self.harness / "demo", "# v2\n")
        (self.harness.parent / "harness.bak" / "demo").mkdir(parents=True)
        self._write(self.harness.parent / "harness.bak" / "demo", "# v1\n")
        status, _ = ia.sync_skill(self.canon / "demo", self.harness, None)
        self.assertEqual(status, "oldbak")

    def test_new_when_missing(self):
        shutil.rmtree(self.harness / "demo", ignore_errors=True)
        self._write(self.canon / "demo", "# v1\n")
        status, _ = ia.sync_skill(self.canon / "demo", self.harness, None)
        self.assertEqual(status, "new")


class CopySkillTest(unittest.TestCase):
    """copy_skill: бэкап старого, копия нового; старый .bak перезаписывается."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.canon = self.tmp / "canon"
        self.harness = self.tmp / "harness"
        (self.canon / "demo").mkdir(parents=True)
        (self.harness / "demo").mkdir(parents=True)
        self.out = io.StringIO()

    def test_backup_and_copy(self):
        (self.canon / "demo" / "SKILL.md").write_text("# v2\n",
                                                      encoding="utf-8")
        (self.harness / "demo" / "SKILL.md").write_text("# v1\n",
                                                        encoding="utf-8")
        with redirect_stdout(self.out):
            ia.copy_skill(self.canon / "demo", self.harness, None)
        self.assertEqual((self.harness / "demo" / "SKILL.md").read_text(),
                         "# v2\n")
        self.assertEqual((self.harness.parent / "harness.bak" / "demo" / "SKILL.md").read_text(),
                         "# v1\n")

    def test_old_bak_replaced(self):
        """Регрессия oldbak: старый бэкап НЕ блокирует обновление,
        а заменяется свежим (фикс: research.db id=264)."""
        (self.canon / "demo" / "SKILL.md").write_text("# v3\n",
                                                      encoding="utf-8")
        (self.harness / "demo" / "SKILL.md").write_text("# v2\n",
                                                        encoding="utf-8")
        (self.harness.parent / "harness.bak" / "demo").mkdir(parents=True)
        (self.harness.parent / "harness.bak" / "demo" / "SKILL.md").write_text("# v1\n",
                                                            encoding="utf-8")
        with redirect_stdout(self.out):
            ia.copy_skill(self.canon / "demo", self.harness, None)
        self.assertEqual((self.harness / "demo" / "SKILL.md").read_text(),
                         "# v3\n")
        # бэкап теперь v2 (предыдущая версия), не v1
        self.assertEqual((self.harness.parent / "harness.bak" / "demo" / "SKILL.md").read_text(),
                         "# v2\n")

    def test_new_no_backup(self):
        # dst не существует — бэкапа быть не должно
        shutil.rmtree(self.harness / "demo", ignore_errors=True)
        (self.canon / "demo" / "SKILL.md").write_text("# v1\n",
                                                      encoding="utf-8")
        with redirect_stdout(self.out):
            ia.copy_skill(self.canon / "demo", self.harness, None)
        self.assertEqual((self.harness / "demo" / "SKILL.md").read_text(),
                         "# v1\n")
        self.assertFalse((self.harness.parent / "harness.bak" / "demo").exists())


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


class SubagentCanonTest(unittest.TestCase):
    """_subagent_canon: парсинг файлов субагентов (харнес = последний
    сегмент имени — точки в именах не ломают)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, rel, text="---\nname: x\ndescription: d\n---\nbody\n"):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_generic_and_harness_specific(self):
        self._write("agent/reverser/agents/reverser.md")
        self._write("agent/reverser/agents/reverser.codex.toml")
        canon = ia._subagent_canon(self.tmp / "agent")
        self.assertIn("reverser", canon)
        self.assertEqual(canon["reverser"]["*"].name, "reverser.md")
        self.assertEqual(canon["reverser"]["codex"].name, "reverser.codex.toml")

    def test_dotted_name_not_treated_as_harness(self):
        self._write("agent/my.agent/agents/my.agent.md")
        canon = ia._subagent_canon(self.tmp / "agent")
        self.assertIn("my.agent", canon)
        self.assertIn("*", canon["my.agent"])
        # "agent" не харнес — файл общий, а не для харнеса
        self.assertNotIn("agent", canon["my.agent"])

    def test_ignores_other_files(self):
        self._write("agent/reverser/agents/notes.txt")
        canon = ia._subagent_canon(self.tmp / "agent")
        self.assertEqual(canon, {})


class ExpandTest(unittest.TestCase):
    """expand: шаблоны путей (posix ~ / nt %USERPROFILE%)."""

    def test_posix_tilde_only_leading(self):
        p = ia.expand("~/.claude/CLAUDE.md", "posix")
        self.assertEqual(p, Path.home() / ".claude" / "CLAUDE.md")

    def test_posix_tilde_midstring_untouched(self):
        p = ia.expand("/data/keep~this", "posix")
        self.assertEqual(p, Path("/data/keep~this"))

    def test_nt_userprofile_fallback(self):
        old = os.environ.pop("USERPROFILE", None)
        try:
            p = ia.expand("%USERPROFILE%\\.claude\\AGENTS.md", "nt")
        finally:
            if old:
                os.environ["USERPROFILE"] = old
        # на posix-тесте бэкслеши — литералы; проверяем саму подстановку
        self.assertEqual(str(p), str(Path.home()) + "\\.claude\\AGENTS.md")

    def test_none_returns_none(self):
        self.assertIsNone(ia.expand(None, "posix"))
