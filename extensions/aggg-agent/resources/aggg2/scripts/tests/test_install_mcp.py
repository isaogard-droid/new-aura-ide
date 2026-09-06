#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты install_mcp.py: автообнаружение MCP у агентов (convention over
configuration), allow-list доставки, core-серверы.

Работают на временных каталогах (CHULAN подменяется) — реальные конфиги
харнесов не трогаем.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'install'))
import install_mcp as im


class AgentServersTest(unittest.TestCase):
    """Автообнаружение agent/*/mcp/ + manifest.json."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.old_chulan = im.CHULAN
        im.CHULAN = str(self.tmp)
        self.addCleanup(setattr, im, "CHULAN", self.old_chulan)

    def _agent(self, name, files, manifest=None):
        """Создаёт агента: agent/<name>/mcp/<files> (+ manifest)."""
        mcp = self.tmp / "agent" / name / "mcp"
        mcp.mkdir(parents=True)
        for fn, content in files.items():
            (mcp / fn).write_text(content, encoding="utf-8")
        if manifest is not None:
            (mcp / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8")

    def test_scans_agent_mcp_dir(self):
        self._agent("myagent", {"myagent.py": "x", "mytool.sh": "x"})
        servers = im._agent_servers()
        self.assertEqual(set(servers), {"myagent", "mytool"})
        # .py запускается python-ом venv, .sh — напрямую
        self.assertEqual(servers["myagent"]["command"][-1],
                         str(self.tmp / "agent" / "myagent" / "mcp"
                             / "myagent.py"))
        self.assertEqual(servers["mytool"]["command"],
                         [str(self.tmp / "agent" / "myagent" / "mcp"
                              / "mytool.sh")])

    def test_default_harnesses_is_opencode(self):
        self._agent("a", {"srv.py": "x"})
        servers = im._agent_servers()
        self.assertEqual(servers["srv"]["harnesses"], ["opencode"])

    def test_manifest_harnesses_applied(self):
        self._agent("a", {"srv.py": "x"},
                    manifest={"srv": {"harnesses": ["claude", "codex"]}})
        servers = im._agent_servers()
        self.assertEqual(servers["srv"]["harnesses"], ["claude", "codex"])

    def test_manifest_json_not_a_server(self):
        self._agent("a", {"srv.py": "x"},
                    manifest={"srv": {"harnesses": ["opencode"]}})
        servers = im._agent_servers()
        self.assertNotIn("manifest", servers)

    def test_ignores_non_py_sh(self):
        self._agent("a", {"srv.py": "x", "notes.txt": "y", "readme.md": "z"})
        servers = im._agent_servers()
        self.assertEqual(set(servers), {"srv"})

    def test_no_agents_dir(self):
        self.assertEqual(im._agent_servers(), {})


class ForHarnessTest(unittest.TestCase):
    """_for_harness: allow-list доставки (least privilege)."""

    def test_core_goes_everywhere(self):
        servers = {"db-tools": {"command": ["py", "x"]}}
        self.assertIn("db-tools", im._for_harness(servers, "opencode"))
        self.assertIn("db-tools", im._for_harness(servers, "deepcode"))

    def test_allowlisted_only_in_allowed(self):
        servers = {"mytool": {"harnesses": ["opencode", "claude"],
                              "command": ["x"]}}
        self.assertIn("mytool", im._for_harness(servers, "opencode"))
        self.assertIn("mytool", im._for_harness(servers, "claude"))
        self.assertNotIn("mytool", im._for_harness(servers, "codex"))
        self.assertNotIn("mytool", im._for_harness(servers, "deepcode"))

    def test_mixed(self):
        servers = {"core": {"command": ["a"]},
                   "agent-srv": {"harnesses": ["opencode"],
                                 "command": ["b"]}}
        got = im._for_harness(servers, "opencode")
        self.assertEqual(set(got), {"core", "agent-srv"})
        got2 = im._for_harness(servers, "codewhale")
        self.assertEqual(set(got2), {"core"})


class ServersTest(unittest.TestCase):
    """_servers: core всегда на месте + агентские добавляются."""

    def test_core_servers_present(self):
        servers = im._servers()
        for name in ("agent-lsp", "battle", "camoufox", "code-review-graph",
                     "db-tools", "semble"):
            self.assertIn(name, servers)

    def test_known_names_covers_all(self):
        names = im._known_server_names()
        self.assertEqual(set(names), set(im._servers()))
        # core всегда в списке (чистка конфигов)
        self.assertIn("db-tools", names)

    def test_crg_has_repo_root_env(self):
        """CRG получает CRG_REPO_ROOT — без него агентский харнес из HOME
        читает пустую базу ~/.code-review-graph/ (грабля 13.08.2026)."""
        servers = im._servers()
        self.assertEqual(servers["code-review-graph"]["env"],
                         {"CRG_REPO_ROOT": im.CHULAN})
        # остальные core-серверы env не требуют
        self.assertNotIn("env", servers["db-tools"])


class ApplyTest(unittest.TestCase):
    """apply_*: запись в конфиги харнесов. Частичная установка (--server X)
    не должна трогать чужие записи (грабля: setup_mcp.sh myagent вычищал
    core-серверы из opencode.jsonc)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_hermes_new_file_created(self):
        """apply_hermes: файла нет → создаётся с блоком mcp_servers,
        command-список конвертируется в command + args + env (YAML-валидно)."""
        cfg = self.tmp / "config.yaml"
        servers = {"demo": {"command": ["/usr/bin/python3",
                                        "demo.py", "--flag"],
                            "env": {"CRG_REPO_ROOT": "/home/u/proj"}}}
        im.apply_hermes(str(cfg), servers)
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("mcp_servers:", text)
        self.assertIn('command: "/usr/bin/python3"', text)
        self.assertIn('      - "--flag"', text)
        self.assertIn('      CRG_REPO_ROOT: "/home/u/proj"', text)
        import yaml
        data = yaml.safe_load(text)
        self.assertEqual(data["mcp_servers"]["demo"]["command"],
                         "/usr/bin/python3")
        self.assertEqual(data["mcp_servers"]["demo"]["args"],
                         ["demo.py", "--flag"])
        self.assertEqual(data["mcp_servers"]["demo"]["env"],
                         {"CRG_REPO_ROOT": "/home/u/proj"})

    def test_hermes_block_replaced_foreign_kept(self):
        """apply_hermes: чужие секции и записи сохраняются verbatim,
        наш блок перезаписывается свежим."""
        cfg = self.tmp / "config.yaml"
        cfg.write_text(
            "model: anthropic/claude-sonnet-4\n"
            "desktop:\n"
            "  repo_scan_enabled: true\n"
            "mcp_servers:\n"
            "  filesystem:  # чужая запись\n"
            "    command: \"npx\"\n"
            "    args: [\"-y\", \"fs\"]\n"
            "  demo:\n"
            "    command: \"/usr/bin/python3\"\n"
            "    args:\n"
            "      - old.py\n"
            "  # комментарий внутри блока\n"
            "terminal:\n"
            "  backend: local\n",
            encoding="utf-8")
        im.apply_hermes(str(cfg), {"demo": {"command": ["py", "new.py"]}})
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("model: anthropic/claude-sonnet-4", text)
        self.assertIn("  repo_scan_enabled: true", text)
        self.assertIn("terminal:\n  backend: local", text)
        # чужая запись внутри блока — verbatim
        self.assertIn("  filesystem:  # чужая запись", text)
        self.assertIn('    command: "npx"', text)
        # наша перезаписана
        self.assertIn('    command: "py"', text)
        self.assertIn('      - "new.py"', text)
        self.assertNotIn("old.py", text)
        # один блок
        self.assertEqual(text.count("mcp_servers:"), 1)
        import yaml
        data = yaml.safe_load(text)
        self.assertIn("filesystem", data["mcp_servers"])
        self.assertIn("demo", data["mcp_servers"])

    def test_hermes_clean_stale_removes_ours_keeps_foreign(self):
        """apply_hermes clean_stale: наше устаревшее имя (в _known_server_names,
        но не в наборе) вычищается; чужие записи не трогаются."""
        cfg = self.tmp / "config.yaml"
        known = set(im._known_server_names())
        self.assertTrue(known, "core-серверы должны быть известны")
        stale = min(known)
        cfg.write_text(
            "mcp_servers:\n"
            f"  {stale}:\n"
            "    command: \"/usr/bin/python3\"\n"
            "    args:\n"
            "      - old.py\n"
            "  my_foreign:\n"
            "    command: \"npx\"\n",
            encoding="utf-8")
        im.apply_hermes(str(cfg), {"fresh": {"command": ["py", "f.py"]}},
                        clean_stale=True)
        text = cfg.read_text(encoding="utf-8")
        self.assertNotIn(f"  {stale}:", text)
        self.assertIn("  my_foreign:", text)
        self.assertIn("  fresh:", text)

    def test_gemini_settings_merge_keeps_categories(self):
        """apply_gemini: ~/.gemini/settings.json — mcpServers добавляется,
        остальные категории (model, context) не трогаются."""
        cfg = self.tmp / "settings.json"
        cfg.write_text(json.dumps({
            "model": {"name": "gemini-3-flash"},
            "context": {"fileName": ["GEMINI.md", "AGENTS.md"]},
            "mcpServers": {"foreign": {"command": "npx", "args": []}},
        }), encoding="utf-8")
        im.apply_gemini(str(cfg), {"demo": {"command": ["py", "d.py"],
                                            "env": {"K": "V"}}})
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["model"], {"name": "gemini-3-flash"})
        self.assertEqual(data["context"]["fileName"],
                         ["GEMINI.md", "AGENTS.md"])
        self.assertIn("foreign", data["mcpServers"])  # чужая запись цела
        self.assertEqual(data["mcpServers"]["demo"]["command"], "py")
        self.assertEqual(data["mcpServers"]["demo"]["args"], ["d.py"])
        self.assertEqual(data["mcpServers"]["demo"]["env"], {"K": "V"})

    def test_google_mcp_config_created_and_merged(self):
        """apply_google_mcp: mcp_config.json (Antigravity/agy) — единый
        объект mcpServers; повторный запуск перезаписывает свои записи,
        чужую не трогает."""
        cfg = self.tmp / "mcp_config.json"
        im.apply_google_mcp(str(cfg), {"demo": {"command": ["py", "d.py"]}})
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["demo"]["command"], "py")
        self.assertEqual(data["mcpServers"]["demo"]["args"], ["d.py"])
        # чужую запись добавляем вручную — повторный запуск не должен её тронуть
        data["mcpServers"]["foreign"] = {"command": "npx"}
        cfg.write_text(json.dumps(data), encoding="utf-8")
        im.apply_google_mcp(str(cfg), {"demo": {"command": ["py2", "d2.py"]}})
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertIn("foreign", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["demo"]["command"], "py2")

    def test_omp_mcp_json_with_schema_preserved(self):
        """apply_omp_mcp: ~/.omp/agent/mcp.json — $schema и чужие записи
        сохраняются, наши получают type stdio + command/args/env."""
        cfg = self.tmp / "mcp.json"
        cfg.write_text(json.dumps({
            "$schema": "https://example.com/mcp-schema.json",
            "mcpServers": {"foreign": {"command": "npx"}},
            "disabledServers": ["foreign"],
        }), encoding="utf-8")
        im.apply_omp_mcp(str(cfg), {"demo": {"command": ["py", "d.py"],
                                             "env": {"K": "V"}}})
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["$schema"], "https://example.com/mcp-schema.json")
        self.assertEqual(data["disabledServers"], ["foreign"])
        self.assertIn("foreign", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["demo"]["type"], "stdio")
        self.assertEqual(data["mcpServers"]["demo"]["command"], "py")
        self.assertEqual(data["mcpServers"]["demo"]["args"], ["d.py"])
        self.assertEqual(data["mcpServers"]["demo"]["env"], {"K": "V"})

    def test_mcp_json_created(self):
        """apply_mcp_json (cursor/windsurf/kiro): mcpServers, command/args/env."""
        cfg = self.tmp / "mcp.json"
        im.apply_mcp_json(str(cfg), {"demo": {"command": ["py", "d.py"],
                                              "env": {"K": "V"}}})
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["demo"]["command"], "py")
        self.assertEqual(data["mcpServers"]["demo"]["args"], ["d.py"])
        self.assertEqual(data["mcpServers"]["demo"]["env"], {"K": "V"})

    def test_partial_server_keeps_foreign_servers(self):
        cfg = self.tmp / "opencode.json"
        cfg.write_text(json.dumps({
            "mcp": {
                "agent-lsp": {"type": "local",
                              "command": ["/usr/local/bin/agent-lsp"],
                              "enabled": True},
                "db-tools": {"type": "local",
                             "command": ["py", "db_tools_mcp.py"],
                             "enabled": True},
                "myagent": {"type": "local",
                             "command": ["py", "myagent.py"],
                             "enabled": True},
            }
        }), encoding="utf-8")
        # частичная установка: только myagent (как setup_mcp.sh)
        im.apply_opencode(str(cfg), {"myagent": {"command": ["py", "rev2"]}})
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertIn("agent-lsp", data["mcp"])
        self.assertIn("db-tools", data["mcp"])
        # а свой сервер перезаписан свежей командой
        self.assertEqual(data["mcp"]["myagent"]["command"], ["py", "rev2"])

    def test_partial_claude_keeps_foreign_servers(self):
        cfg = self.tmp / "claude.json"
        cfg.write_text(json.dumps({
            "mcpServers": {
                "db-tools": {"command": "py", "args": ["db"]},
                "mytool": {"command": "sh", "args": ["mytool.sh"]},
            }
        }), encoding="utf-8")
        im.apply_claude(str(cfg), {"mytool": {"command": ["sh", "g2.sh"]}})
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertIn("db-tools", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["mytool"]["args"], ["g2.sh"])

    def test_codex_partial_keeps_foreign_sections(self):
        cfg = self.tmp / "config.toml"
        cfg.write_text("[model]\nprovider = \"x\"\n"
                       "[mcp_servers.db-tools]\ncommand = \"py\"\n"
                       "[mcp_servers.mytool]\ncommand = \"sh\"\n",
                       encoding="utf-8")
        im.apply_codex(str(cfg), {"mytool": {"command": ["sh", "g2.sh"]}})
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.db-tools]", text)
        self.assertIn("[model]", text)
        self.assertIn("g2.sh", text)

    def test_full_sync_rewrites_known_servers(self):
        """Полная установка (все известные) перезаписывает известные и
        не трогает незнакомые записи."""
        cfg = self.tmp / "opencode.json"
        cfg.write_text(json.dumps({
            "mcp": {
                "agent-lsp": {"type": "local",
                              "command": ["/old/path/agent-lsp"],
                              "enabled": True},
                "my-custom": {"type": "local",
                              "command": ["/custom/tool"],
                              "enabled": True},
            }
        }), encoding="utf-8")
        servers = im._servers()
        im.apply_opencode(str(cfg), servers)
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["mcp"]["agent-lsp"]["command"][0],
                         im._agent_lsp())
        self.assertIn("my-custom", data["mcp"])

    def test_env_in_opencode_becomes_environment(self):
        """В opencode env-ключ называется `environment` (не `env`)."""
        cfg = self.tmp / "opencode.json"
        servers = {"srv": {"command": ["py", "x.py"],
                           "env": {"CRG_REPO_ROOT": "/repo"}}}
        im.apply_opencode(str(cfg), servers)
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["mcp"]["srv"]["environment"],
                         {"CRG_REPO_ROOT": "/repo"})
        self.assertNotIn("env", data["mcp"]["srv"])

    def test_bom_config_parsed_foreign_kept(self):
        """BUG-3 (багрепорт v2.4): конфиг с UTF-8 BOM (Windows-файл) раньше
        не парсился — apply_opencode затирал его пустышкой. Теперь BOM
        снимается, чужие серверы сохраняются."""
        cfg = self.tmp / "opencode.json"
        text = json.dumps({
            "mcp": {
                "mistral": {"type": "local",
                            "command": ["/usr/bin/mistral"],
                            "enabled": True},
                "myagent": {"type": "local",
                             "command": ["py", "old.py"],
                             "enabled": True},
            }
        }, indent=2)
        cfg.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        im.apply_opencode(str(cfg), {"myagent": {"command": ["py", "rev2"]}})
        self.assertFalse(cfg.read_bytes().startswith(b"\xef\xbb\xbf"))
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertIn("mistral", data["mcp"])  # чужой сервер выжил
        self.assertEqual(data["mcp"]["myagent"]["command"], ["py", "rev2"])

    def test_broken_config_not_overwritten(self):
        """BUG-3: битый JSON больше не перезаписывается пустышкой —
        файл остаётся байт-в-байт как был."""
        cfg = self.tmp / "opencode.json"
        broken = b'{"mcp": {"x": [unclosed'
        cfg.write_bytes(broken)
        im.apply_opencode(str(cfg), {"myagent": {"command": ["py", "rev"]}})
        self.assertEqual(cfg.read_bytes(), broken)

    def test_env_in_claude_json(self):
        cfg = self.tmp / "claude.json"
        servers = {"srv": {"command": ["py", "x.py"],
                           "env": {"A": "B"}}}
        im.apply_claude(str(cfg), servers)
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["srv"]["env"], {"A": "B"})

    def test_env_in_codex_toml_subtable(self):
        cfg = self.tmp / "config.toml"
        servers = {"srv": {"command": ["py", "x.py"],
                           "env": {"A": "B"}}}
        im.apply_codex(str(cfg), servers)
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.srv.env]", text)
        self.assertIn('A = "B"', text)

    def test_env_in_deepcode_json(self):
        cfg = self.tmp / "settings.json"
        servers = {"srv": {"command": ["py", "x.py"],
                           "env": {"A": "B"}}}
        im.apply_deepcode(str(cfg), servers)
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["srv"]["env"], {"A": "B"})


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
