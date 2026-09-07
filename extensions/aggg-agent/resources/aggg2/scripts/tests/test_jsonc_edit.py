#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты jsonc_edit.py: хирургическая правка JSONC — комментарии и
чужие записи сохраняются (паттерн jsonc-parser от Microsoft, VS Code).

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import shutil
import sys
import tempfile

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import jsonc_edit as je


class JsoncEditTest(unittest.TestCase):
    """Точечная правка JSONC: комментарии и чужие записи сохраняются
    (паттерн jsonc-parser от Microsoft: текстовые edits по оффсетам)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _edit(self, text, servers, clean_stale=False, known=None):
        known = known or ["agent-lsp", "db-tools", "myagent", "mytool"]
        return je._edit_mcp_section(text, servers, known, clean_stale)

    def test_comments_preserved(self):
        raw = ('{\n'
               '  // MCP-серверы воркспейса\n'
               '  "mcp": {\n'
               '    // сервер базы\n'
               '    "db-tools": {"type": "local", "command": ["py", "db"],'
               ' "enabled": true},\n'
               '    "myagent": {"type": "local", "command": ["py", "rev"],'
               ' "enabled": true}\n'
               '  },\n'
               '  "agent": {"build": {"prompt": "p"}} // промпт билда\n'
               '}\n')
        new = self._edit(raw, {"myagent": {"command": ["py", "rev2"]},
                               "mytool": {"command": ["sh", "g.sh"]}})
        # комментарии на месте (и шапка, и внутри секции, и хвост)
        self.assertIn("// MCP-серверы воркспейса", new)
        self.assertIn("// сервер базы", new)
        self.assertIn("// промпт билда", new)
        data = je._parse_jsonc(new)
        self.assertEqual(set(data["mcp"]), {"db-tools", "myagent", "mytool"})
        self.assertEqual(data["mcp"]["myagent"]["command"], ["py", "rev2"])

    def test_partial_keeps_foreign(self):
        raw = json.dumps({"mcp": {
            "agent-lsp": {"command": ["/a"]},
            "db-tools": {"command": ["py", "db"]},
            "myagent": {"command": ["py", "rev"]},
        }}, indent=2)
        new = self._edit(raw, {"myagent": {"command": ["py", "rev2"]}})
        data = je._parse_jsonc(new)
        # частичная установка НЕ вычищает известных, которых не доставляет
        self.assertEqual(set(data["mcp"]),
                         {"agent-lsp", "db-tools", "myagent"})

    def test_full_cleans_stale(self):
        raw = json.dumps({"$schema": "x", "mcp": {
            "agent-lsp": {"command": ["/a"]},
            "myagent": {"command": ["py", "rev"]},
        }}, indent=2)
        new = self._edit(raw, {"myagent": {"command": ["py", "rev"]}},
                         clean_stale=True)
        data = je._parse_jsonc(new)
        self.assertEqual(set(data["mcp"]), {"myagent"})

    def test_create_section_keeps_rest(self):
        raw = ('{\n'
               '  // шапка\n'
               '  "agent": {"build": {"prompt": "p"}}\n'
               '}\n')
        new = self._edit(raw, {"myagent": {"command": ["py", "rev"]}})
        data = je._parse_jsonc(new)
        self.assertEqual(set(data["mcp"]), {"myagent"})
        self.assertEqual(data["agent"]["build"]["prompt"], "p")
        self.assertIn("// шапка", new)

    def test_idempotent(self):
        raw = ('{\n'
               '  "mcp": {\n'
               '    "myagent": {"type": "local", "command": ["py", "rev"],'
               ' "enabled": true}\n'
               '  }\n'
               '}\n')
        servers = {"myagent": {"command": ["py", "rev2"]},
                   "mytool": {"command": ["sh", "g.sh"]}}
        once = self._edit(raw, servers)
        twice = self._edit(once, servers)
        self.assertEqual(once, twice)
        self.assertEqual(set(je._parse_jsonc(twice)["mcp"]),
                         {"myagent", "mytool"})

    def test_empty_mcp_section(self):
        raw = '{\n  "mcp": {},\n  "agent": {"x": "y"}\n}\n'
        new = self._edit(raw, {"myagent": {"command": ["py", "rev"]}})
        data = je._parse_jsonc(new)
        self.assertEqual(set(data["mcp"]), {"myagent"})

    def test_env_becomes_environment_field(self):
        """env из server-словаря пишется в opencode как `environment`
        (не `env` — тот silently игнорируется схемой opencode, #26332)."""
        raw = ('{\n'
               '  "mcp": {\n'
               '    "myagent": {"type": "local", "command": ["py", "rev"],'
               ' "enabled": true}\n'
               '  }\n'
               '}\n')
        servers = {"myagent": {"command": ["py", "rev2"],
                               "env": {"CRG_REPO_ROOT": "/repo"}}}
        new = self._edit(raw, servers)
        data = je._parse_jsonc(new)
        self.assertEqual(data["mcp"]["myagent"]["environment"],
                         {"CRG_REPO_ROOT": "/repo"})
        self.assertNotIn("env", data["mcp"]["myagent"])

    def test_env_absent_leaves_no_environment(self):
        """Без env запись остаётся прежней формы (без environment)."""
        raw = ('{\n'
               '  "mcp": {\n'
               '    "myagent": {"type": "local", "command": ["py", "rev"],'
               ' "enabled": true}\n'
               '  }\n'
               '}\n')
        new = self._edit(raw, {"myagent": {"command": ["py", "rev2"]}})
        data = je._parse_jsonc(new)
        self.assertNotIn("environment", data["mcp"]["myagent"])

    def test_load_jsonc_bom_file(self):
        """BUG-3 (багрепорт v2.4): файл с UTF-8 BOM (Windows) парсится —
        раньше json.loads падал на "\ufeff" и конфиг терялся."""
        p = self.tmp / "cfg.json"
        p.write_bytes(b"\xef\xbb\xbf" + json.dumps(
            {"agent": {"build": {"prompt": "p"}}}).encode("utf-8"))
        data = je.load_jsonc(str(p))
        self.assertEqual(data["agent"]["build"]["prompt"], "p")

    def test_parse_jsonc_strips_bom(self):
        """BUG-3: _parse_jsonc снимает BOM в начале текста (страховка
        поверх utf-8-sig)."""
        data = je._parse_jsonc('\ufeff{"a": 1}')
        self.assertEqual(data["a"], 1)



if __name__ == "__main__":
    unittest.main()

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
