#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Тесты toggle_config_ops (выключение/включение прошивки по конфигам):
пары remove_*/insert_* — roundtrip: после off+on структура возвращается,
чужие записи не трогаются. Запуск:

    python3 -m unittest discover -s scripts/tests -t scripts -p "test_toggle*.py"
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'install'))

from toggle import toggle_config_ops as ops  # noqa: E402


class TestHooksGeneric(unittest.TestCase):
    def test_roundtrip_keeps_foreign(self):
        data = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [
                        {"type": "command",
                         "command": "python3 /h/aggg2_prompt_hook.py"},
                        {"type": "command", "command": "/usr/bin/foreign"},
                    ]},
                ],
                "PreToolUse": [
                    {"matcher": "Bash|Edit",
                     "hooks": [{"type": "command",
                                "command": "python3 /h/aggg2_prompt_hook.py"}]},
                ],
            },
            "theme": "dark",
        }
        removed = ops.remove_hooks_generic(data)
        # осталась чужая запись и пустые секции убраны
        self.assertIn("UserPromptSubmit", data["hooks"])
        self.assertEqual(
            data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"],
            "/usr/bin/foreign")
        self.assertNotIn("PreToolUse", data["hooks"])
        self.assertIn("theme", data)
        # insert возвращает всё
        self.assertTrue(ops.insert_hooks_generic(data, removed))
        self.assertEqual(
            data["hooks"]["PreToolUse"][0]["hooks"][0]["command"],
            "python3 /h/aggg2_prompt_hook.py")
        # повторный insert — идемпотентен
        self.assertFalse(ops.insert_hooks_generic(data, removed))


class TestReasonix(unittest.TestCase):
    def test_roundtrip(self):
        data = {"hooks": {"PreToolUse": [
            {"match": "bash", "command": "python3 /h/aggg2_prompt_hook.py"},
            {"match": "bash", "command": "/usr/bin/foreign"},
        ]}}
        removed = ops.remove_reasonix(data)
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 1)
        self.assertEqual(data["hooks"]["PreToolUse"][0]["command"],
                         "/usr/bin/foreign")
        ops.insert_reasonix(data, removed)
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 2)


class TestMcpKeys(unittest.TestCase):
    def test_remove_only_ours(self):
        data = {"mcpServers": {
            "db-tools": {"command": ["python", str(ops.CHULAN) + "/mcp/x.py"]},
            "foreign": {"command": ["/usr/bin/foo"]},
        }}
        removed = ops._remove_mcp_keys(data, "mcpServers")
        self.assertIn("foreign", data["mcpServers"])
        self.assertNotIn("db-tools", data["mcpServers"])
        ops._insert_mcp_keys(data, removed)
        self.assertIn("db-tools", data["mcpServers"])


class TestGemini(unittest.TestCase):
    def test_roundtrip(self):
        data = {
            "hooks": {"BeforeTool": [
                {"matcher": "run_shell_command",
                 "hooks": [{"type": "command",
                            "command": "AGGG2_HOOK_MODE=gemini python3 "
                                       "/h/aggg2_prompt_hook.py",
                            "name": "aggg2-storozh"}]},
            ]},
            "mcpServers": {"db-tools": {"command": str(ops.CHULAN) + "/x"}},
            "model": {"name": "x"},
        }
        removed = ops.remove_gemini(data)
        self.assertNotIn("hooks", data)
        self.assertNotIn("mcpServers", data)
        self.assertIn("model", data)
        ops.insert_gemini(data, removed)
        self.assertIn("hooks", data)
        self.assertIn("db-tools", data["mcpServers"])


class TestAgyHooks(unittest.TestCase):
    def test_roundtrip(self):
        data = {"aggg2-storozh": {"PreToolUse": []},
                "other-hook": {"PreToolUse": []}}
        removed = ops.remove_agy_hooks(data)
        self.assertNotIn("aggg2-storozh", data)
        self.assertIn("other-hook", data)
        ops.insert_agy_hooks(data, removed)
        self.assertIn("aggg2-storozh", data)


class TestCodexToml(unittest.TestCase):
    def test_roundtrip(self):
        chulan = str(ops.CHULAN)
        text = ('model = "gpt-5"\n'
                '[mcp_servers.db-tools]\n'
                f'command = "python"\nargs = ["{chulan}/mcp/db_tools_mcp.py"]\n'
                "[mcp_servers.db-tools.env]\n"
                'X = "1"\n'
                "\n"
                '[mcp_servers.foreign]\n'
                'command = "/usr/bin/foo"\n')
        new, removed = ops.remove_codex_toml(text)
        self.assertNotIn("db-tools", new)
        self.assertIn("foreign", new)
        self.assertIn('model = "gpt-5"', new)
        restored, changed = ops.insert_codex_toml(new, removed)
        self.assertTrue(changed)
        self.assertIn("[mcp_servers.db-tools]", restored)
        self.assertIn("[mcp_servers.db-tools.env]", restored)
        _, changed2 = ops.insert_codex_toml(restored, removed)
        self.assertFalse(changed2)

    def test_parent_without_chulan_env_with(self):
        # code-review-graph: тело секции без CHULAN, путь чулана — в .env
        chulan = str(ops.CHULAN)
        text = ('[mcp_servers.code-review-graph]\n'
                'command = "/usr/local/bin/code-review-graph"\n'
                'args = ["mcp"]\n'
                "[mcp_servers.code-review-graph.env]\n"
                f'CRG_REPO_ROOT = "{chulan}"\n'
                "[mcp_servers.foreign]\n"
                'command = "/usr/bin/foo"\n')
        new, removed = ops.remove_codex_toml(text)
        self.assertNotIn("code-review-graph", new)
        self.assertIn("foreign", new)
        restored, changed = ops.insert_codex_toml(new, removed)
        self.assertTrue(changed)
        self.assertIn("[mcp_servers.code-review-graph]", restored)
        self.assertIn("CRG_REPO_ROOT", restored)


class TestCodewhaleToml(unittest.TestCase):
    def test_roundtrip(self):
        text = ('model = "x"\n'
                "# AGGG2.0-прошивка: сторож запретов (install_proshivka.py)\n"
                "[[hooks.hooks]]\n"
                'event = "tool_call_before"\n'
                'name = "aggg2-guard"\n'
                'command = "python3 /h/aggg2_prompt_hook.py"\n'
                "\n[hooks]\nenabled = true\n")
        new, removed = ops.remove_codewhale_toml(text)
        self.assertNotIn("aggg2", new)
        self.assertIn("[hooks]", new)
        restored, changed = ops.insert_codewhale_toml(new, removed)
        self.assertTrue(changed)
        self.assertIn("aggg2-guard", restored)


class TestHermesYaml(unittest.TestCase):
    def test_roundtrip(self):
        chulan = str(ops.CHULAN)
        text = ("hooks:\n"
                "  pre_tool_call:\n"
                "    - command: python3 /h/aggg2_prompt_hook.py\n"
                '      matcher: "terminal|write_file"\n'
                "      timeout: 10\n"
                "    - command: /usr/bin/foreign\n"
                '      matcher: "terminal"\n'
                "hooks_auto_accept: true\n"
                "mcp_servers:\n"
                "  db-tools:\n"
                f'    command: python "{chulan}/mcp/db_tools_mcp.py"\n'
                "  foreign:\n"
                '    command: /usr/bin/foo\n')
        new, removed = ops.remove_hermes_yaml(text)
        self.assertNotIn("aggg2_prompt_hook.py", new)
        self.assertNotIn("db-tools:", new)
        self.assertIn("foreign:", new)
        self.assertIn("hooks_auto_accept: true", new)
        restored, changed = ops.insert_hermes_yaml(new, removed)
        self.assertTrue(changed)
        self.assertIn("aggg2_prompt_hook.py", restored)
        self.assertIn("db-tools:", restored)


class TestOpenCode(unittest.TestCase):
    def test_roundtrip(self):
        raw = ('{\n'
               '  "$schema": "https://opencode.ai/config.json",\n'
               '  // мой комментарий\n'
               '  "agent": {\n'
               '    "build": {\n'
               '      "prompt": "{file:./prompts/build.txt}"\n'
               '    }\n'
               '  },\n'
               '  "permission": {\n'
               '    "edit": {\n'
               '      "*": "allow",\n'
               '      "projects/x/chat.py": "ask"\n'
               '    }\n'
               '  },\n'
               '  "mcp": {\n'
               '    "db-tools": {"type": "local", '
               '"command": ["python", "<CHULAN>/mcp/db_tools_mcp.py"]},\n'
               '    "foreign": {"type": "local", "command": ["/usr/bin/foo"]}\n'
               '  },\n'
               '  "theme": "dark"\n'
               '}\n').replace("<CHULAN>", str(ops.CHULAN))
        new, removed = ops.remove_opencode(raw, god_paths=["projects/x/chat.py"])
        self.assertIn("// мой комментарий", new)  # комментарий сохранён
        self.assertNotIn("build.txt", new)
        self.assertNotIn("db-tools", new)
        self.assertIn('"foreign"', new)
        self.assertIn('"theme": "dark"', new)
        self.assertIn("permission_edit", removed)
        restored, changed = ops.insert_opencode(new, removed)
        self.assertTrue(changed)
        self.assertIn('"{file:./prompts/build.txt}"', restored)
        self.assertIn('"projects/x/chat.py": "ask"', restored)
        # JSONC остаётся валидным после roundtrip
        from jsonc_edit import _parse_jsonc
        _parse_jsonc(restored)  # не упадёт — текст остался корректным JSONC


if __name__ == "__main__":
    unittest.main()
