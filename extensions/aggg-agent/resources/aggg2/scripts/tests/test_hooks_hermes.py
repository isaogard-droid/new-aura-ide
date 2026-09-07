#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Тесты hermes-прошивки: ветка hermes в aggg2_prompt_hook.py (wire-протокол
shell_hooks.py: hook_event_name/tool_name/tool_input, блок = {"action":
"block"} + exit 2) и YAML-хирургия hooks-блока в install_proshivka.py.

Работают на временных каталогах — реальные ~/.hermes не трогаем.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'install'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'doctor'))

import install_proshivka as ip  # noqa: E402

HOOK = (Path(__file__).resolve().parent.parent.parent
        / "harness" / "hooks" / "aggg2_prompt_hook.py")


class HermesHookTest(unittest.TestCase):
    """Ветка hermes хука: wire-протокол pre_tool_call."""

    def _run(self, payload):
        return subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(payload),
            capture_output=True, text=True, timeout=30, check=False)

    def test_pkill_without_trick_blocks(self):
        r = self._run({"hook_event_name": "pre_tool_call",
                       "tool_name": "terminal",
                       "tool_input": {"command": "pkill -f foo"}})
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertEqual(out["action"], "block")
        self.assertIn("скобочного трюка", out["message"])

    def test_rm_rf_root_blocks(self):
        r = self._run({"hook_event_name": "pre_tool_call",
                       "tool_name": "terminal",
                       "tool_input": {"command": "rm -rf /"}})
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["action"], "block")

    def test_git_reset_hard_blocks(self):
        r = self._run({"hook_event_name": "pre_tool_call",
                       "tool_name": "terminal",
                       "tool_input": {"command": "git reset --hard"}})
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["action"], "block")

    def test_safe_command_allows(self):
        r = self._run({"hook_event_name": "pre_tool_call",
                       "tool_name": "terminal",
                       "tool_input": {"command": "ls -la"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_empty_tool_input_allows(self):
        """Пустой tool_input ({} / без command) — хук не падает, пропускает."""
        for payload in ({"hook_event_name": "pre_tool_call",
                         "tool_name": "terminal", "tool_input": {}},
                        {"hook_event_name": "pre_tool_call",
                         "tool_name": "terminal", "tool_input": None}):
            r = self._run(payload)
            self.assertEqual(r.returncode, 0, f"payload={payload}")
            self.assertEqual(r.stdout.strip(), "")

    def test_non_shell_tool_ignored(self):
        """Не-шелл-инструмент (write_file) — хук не вмешивается."""
        r = self._run({"hook_event_name": "pre_tool_call",
                       "tool_name": "write_file",
                       "tool_input": {"path": "notes.txt"}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")


class HermesConfigTest(unittest.TestCase):
    """YAML-хирургия hooks-блока в ~/.hermes/config.yaml."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.args = Namespace(dry_run=False)
        self.cmd = "python3 ~/.hermes/hooks/aggg2_prompt_hook.py"

    def test_fresh_config_created(self):
        cfg = self.tmp / "config.yaml"
        ip._ensure_hermes_hooks(cfg, self.cmd, self.args)
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("hooks:", text)
        self.assertIn("pre_tool_call:", text)
        import yaml
        data = yaml.safe_load(text)
        entry = data["hooks"]["pre_tool_call"][0]
        self.assertEqual(entry["matcher"], "terminal|write_file|edit_.*")
        self.assertEqual(entry["command"], self.cmd)

    def test_foreign_hook_kept_ours_inserted(self):
        cfg = self.tmp / "config.yaml"
        cfg.write_text(
            "model:\n  default: \"x\"\n"
            "hooks:\n"
            "  pre_tool_call:\n"
            "    - command: \"bash /other/hook.sh\"\n"
            "      matcher: \"write_file\"\n",
            encoding="utf-8")
        ip._ensure_hermes_hooks(cfg, self.cmd, self.args)
        text = cfg.read_text(encoding="utf-8")
        self.assertIn('command: "bash /other/hook.sh"', text)  # чужая цела
        self.assertIn("aggg2_prompt_hook.py", text)  # наша добавлена
        import yaml
        data = yaml.safe_load(text)
        entries = data["hooks"]["pre_tool_call"]
        self.assertEqual(len(entries), 2)
        # наша вставлена сразу после ключа pre_tool_call (первой в списке)
        self.assertEqual(entries[0]["command"], self.cmd)
        self.assertEqual(entries[1]["command"], "bash /other/hook.sh")
        # чужие секции не тронуты
        self.assertEqual(data["model"], {"default": "x"})

    def test_pre_tool_call_section_created_next_to_foreign(self):
        cfg = self.tmp / "config.yaml"
        cfg.write_text("hooks:\n  post_tool_call:\n    - command: \"x\"\n",
                       encoding="utf-8")
        ip._ensure_hermes_hooks(cfg, self.cmd, self.args)
        import yaml
        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        self.assertIn("pre_tool_call", data["hooks"])
        self.assertIn("post_tool_call", data["hooks"])

    def test_no_hooks_block_appended(self):
        cfg = self.tmp / "config.yaml"
        cfg.write_text("model:\n  default: \"x\"\n", encoding="utf-8")
        ip._ensure_hermes_hooks(cfg, self.cmd, self.args)
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("hooks:", text)
        import yaml
        data = yaml.safe_load(text)
        self.assertEqual(data["hooks"]["pre_tool_call"][0]["command"], self.cmd)

    def test_idempotent(self):
        cfg = self.tmp / "config.yaml"
        self.assertTrue(ip._ensure_hermes_hooks(cfg, self.cmd, self.args))
        before = cfg.read_text(encoding="utf-8")
        self.assertFalse(ip._ensure_hermes_hooks(cfg, self.cmd, self.args))
        self.assertEqual(cfg.read_text(encoding="utf-8"), before)

    def test_auto_accept_appended_once(self):
        cfg = self.tmp / "config.yaml"
        ip._ensure_hermes_auto_accept(cfg, self.args)
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("hooks_auto_accept: true", text)
        before = text
        self.assertFalse(ip._ensure_hermes_auto_accept(cfg, self.args))
        self.assertEqual(cfg.read_text(encoding="utf-8"), before)

    def test_allowlist_seeded_and_idempotent(self):
        """_seed_hermes_allowlist: запись {event, command, approved_at,
        script_mtime_at_approval}; повторный запуск не трогает файл."""
        hooks_dir = self.tmp / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "aggg2_prompt_hook.py").write_text(
            "print('x')\n", encoding="utf-8")
        cmd = "python3 ~/.hermes/hooks/aggg2_prompt_hook.py"
        real_home = ip.Path.home()
        ip.Path.home = classmethod(lambda cls: self.tmp)
        try:
            self.assertTrue(ip._seed_hermes_allowlist(hooks_dir, cmd, self.args))
            allow = self.tmp / ".hermes" / "shell-hooks-allowlist.json"
            data = json.loads(allow.read_text(encoding="utf-8"))
            entry = data["approvals"][0]
            self.assertEqual(entry["event"], "pre_tool_call")
            self.assertEqual(entry["command"], cmd)
            self.assertIn("approved_at", entry)
            self.assertIn("script_mtime_at_approval", entry)
            # идемпотентно: тот же mtime → повторно не пишем
            before = allow.read_text(encoding="utf-8")
            self.assertFalse(
                ip._seed_hermes_allowlist(hooks_dir, cmd, self.args))
            self.assertEqual(allow.read_text(encoding="utf-8"), before)
        finally:
            ip.Path.home = classmethod(lambda cls: real_home)


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
