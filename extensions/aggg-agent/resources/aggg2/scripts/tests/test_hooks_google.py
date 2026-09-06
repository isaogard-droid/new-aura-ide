#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Тесты сторожей Google-харнесов: ветки gemini (BeforeTool, env-режим) и
antigravity (hooks.json PreToolUse, camelCase) в aggg2_prompt_hook.py +
конфиг-хирургия в install_proshivka.py (apply_gemini_hooks,
apply_antigravity_hooks).

Работают на временных каталогах — реальные ~/.gemini не трогаем.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import os
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


def _run_hook(payload, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=30, check=False, env=e)


class GeminiHookTest(unittest.TestCase):
    """Ветка gemini: BeforeTool, блок = {"decision":"deny"} + exit 2."""

    def test_deny_on_pkill(self):
        r = _run_hook({"tool_name": "run_shell_command",
                       "tool_input": {"command": "pkill -f foo"}},
                      env={"AGGG2_HOOK_MODE": "gemini"})
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)  # Golden Rule: stdout — только JSON
        self.assertEqual(out["decision"], "deny")
        self.assertIn("скобочного трюка", out["reason"])

    def test_allow_on_safe(self):
        r = _run_hook({"tool_name": "run_shell_command",
                       "tool_input": {"command": "npm test"}},
                      env={"AGGG2_HOOK_MODE": "gemini"})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_without_env_plain_claude_format(self):
        """Без env-режима gemini-пейлоад идёт обычной claude-веткой
        (hookSpecificOutput) — режимы не пересекаются."""
        r = _run_hook({"tool_name": "run_shell_command",
                       "tool_input": {"command": "pkill -f foo"}})
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"],
                         "deny")


class AntigravityHookTest(unittest.TestCase):
    """Ветка antigravity: PreToolUse, camelCase, гейт decision (exit 0)."""

    def test_deny_on_rm_rf(self):
        r = _run_hook({"toolCall": {"name": "run_command",
                                    "args": {"CommandLine": "rm -rf /"}},
                       "stepIdx": 1})
        self.assertEqual(r.returncode, 0)  # гейт через decision, не exit 2
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "deny")
        self.assertIn("rm -rf", out["reason"])

    def test_safe_silence(self):
        r = _run_hook({"toolCall": {"name": "run_command",
                                    "args": {"CommandLine": "ls -la"}},
                       "stepIdx": 1})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_other_tool_ignored(self):
        r = _run_hook({"toolCall": {"name": "view_file",
                                    "args": {"AbsolutePath": "/etc/passwd"}},
                       "stepIdx": 1})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")


class GoogleHooksConfigTest(unittest.TestCase):
    """apply_gemini_hooks / apply_antigravity_hooks — конфиги."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.args = Namespace(dry_run=False)

    def test_gemini_settings_merge(self):
        settings = self.tmp / ".gemini" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"model": {"name": "gemini-3"}}),
                            encoding="utf-8")
        # подменяем харнесы на временные каталоги
        real_home = ip.Path.home()
        ip.Path.home = classmethod(lambda cls: self.tmp)
        try:
            ip.apply_gemini_hooks(self.args)
        finally:
            ip.Path.home = classmethod(lambda cls: real_home)
        data = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(data["model"], {"name": "gemini-3"})
        bt = data["hooks"]["BeforeTool"][0]
        self.assertEqual(bt["matcher"], "run_shell_command|write_file|edit_.*")
        self.assertEqual(bt["hooks"][0]["name"], "aggg2-storozh")
        self.assertIn("AGGG2_HOOK_MODE=gemini", bt["hooks"][0]["command"])
        # идемпотентно
        before = settings.read_text(encoding="utf-8")
        ip.Path.home = classmethod(lambda cls: self.tmp)
        try:
            ip.apply_gemini_hooks(self.args)
        finally:
            ip.Path.home = classmethod(lambda cls: real_home)
        self.assertEqual(settings.read_text(encoding="utf-8"), before)

    def test_antigravity_hooks_json_created_and_merged(self):
        hooks_json = self.tmp / ".gemini" / "config" / "hooks.json"
        real_home = ip.Path.home()
        ip.Path.home = classmethod(lambda cls: self.tmp)
        try:
            ip.apply_antigravity_hooks(self.args)
            data = json.loads(hooks_json.read_text(encoding="utf-8"))
            self.assertIn("aggg2-storozh", data)
            pre = data["aggg2-storozh"]["PreToolUse"][0]
            self.assertEqual(pre["matcher"],
                             "run_command|write_to_file|replace_file_content|multi_replace_file_content")
            # чужая запись не трогается
            data["my-hook"] = {"enabled": True, "Stop": []}
            hooks_json.write_text(json.dumps(data), encoding="utf-8")
            ip.apply_antigravity_hooks(self.args)
        finally:
            ip.Path.home = classmethod(lambda cls: real_home)
        data = json.loads(hooks_json.read_text(encoding="utf-8"))
        self.assertIn("my-hook", data)
        self.assertIn("aggg2-storozh", data)


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
