#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты установщика LSP-серверов: данные (lsp_data) и генерация
config.json (gen_config) на временных файлах — реальный конфиг не трогаем.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'install'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'doctor'))

import install_lsp_servers as ils
from lsp.lsp_data import check_bins


class LspDataTest(unittest.TestCase):
    def test_check_bins_unique_and_extra(self):
        bins = check_bins()
        self.assertIn("gopls", bins)
        self.assertIn("pyright-langserver", bins)
        self.assertIn("lua-language-server", bins)
        # уникальность: vscode-json-language-server и ...server не дублируются
        self.assertEqual(len(bins), len(set(bins)))

    def test_check_bins_custom(self):
        custom = [{"exts": ["x"], "names": ["aa", "bb", "aa"]}]
        self.assertEqual(check_bins(custom, extra=("cc",)), ["aa", "bb", "cc"])

    def test_resolve_extra(self):
        res = {"go_bin": "/opt/go/bin", "win_get": None}
        out = ils._resolve_extra(["{go_bin}/gopls", "{win_get}/clangd.exe"], res)
        self.assertEqual(out, ["/opt/go/bin/gopls"])  # win_get=None → пропущен


class FindTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_find_in_names(self):
        (self.tmp / "gopls").write_text("x")
        with mock.patch.object(shutil, "which",
                               side_effect=lambda n: str(self.tmp / n)
                               if (self.tmp / n).exists() else None):
            self.assertEqual(ils._find(["gopls", "nope"]),
                             str(self.tmp / "gopls"))

    def test_find_fallback_extra(self):
        extra_file = self.tmp / "rust-analyzer"
        extra_file.write_text("x")
        with mock.patch.object(shutil, "which", return_value=None):
            self.assertEqual(ils._find(["rust-analyzer"], [str(extra_file)]),
                             str(extra_file))

    def test_find_nothing(self):
        with mock.patch.object(shutil, "which", return_value=None):
            self.assertIsNone(ils._find(["zzz-none"]))


class GenConfigTest(unittest.TestCase):
    """gen_config на временном конфиге с фейковыми бинарями."""

    BINARIES = (
        "gopls", "rust-analyzer", "typescript-language-server", "clangd",
        "bash-language-server", "vscode-json-languageserver",
        "yaml-language-server", "docker-langserver", "lua-language-server",
        "pyright-langserver",
    )

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        for name in self.BINARIES:
            (self.tmp / name).write_text("x", encoding="utf-8")
        self.old_config = ils.CONFIG
        ils.CONFIG = self.tmp / "config.json"
        self.addCleanup(setattr, ils, "CONFIG", self.old_config)

    def _run(self):
        resolvers = {"go_bin": str(self.tmp), "cargo_bin": str(self.tmp),
                     "npm_bin": str(self.tmp), "local_bin": str(self.tmp),
                     "home": str(self.tmp), "win_get": None}
        with mock.patch.object(shutil, "which",
                               side_effect=lambda n: str(self.tmp / n)
                               if (self.tmp / n).exists() else None), \
             mock.patch.object(ils, "_resolvers", return_value=resolvers):
            ils.gen_config()
        return json.loads((ils.CONFIG).read_text(encoding="utf-8"))

    def test_generates_all_servers(self):
        data = self._run()
        servers = data["servers"]
        self.assertEqual(len(servers), 10)  # 9 из LANG_SERVERS + pyright
        names = [Path(s["command"][0]).name for s in servers]
        for b in self.BINARIES:
            self.assertIn(b, names)

    def test_pyright_first_with_stdio(self):
        servers = self._run()["servers"]
        self.assertEqual(servers[0]["extensions"], ["py"])
        self.assertEqual(servers[0]["command"],
                         [str(self.tmp / "pyright-langserver"), "--stdio"])

    def test_bash_server_uses_start(self):
        servers = self._run()["servers"]
        bash = next(s for s in servers
                    if "bash-language-server" in s["command"][0])
        self.assertEqual(bash["command"],
                         [str(self.tmp / "bash-language-server"), "start"])

    def test_gopls_no_args(self):
        servers = self._run()["servers"]
        gopls = next(s for s in servers if "gopls" in s["command"][0])
        self.assertEqual(gopls["command"], [str(self.tmp / "gopls")])
        self.assertEqual(gopls["extensions"], ["go"])

    def test_missing_servers_skipped(self):
        # убираем половину бинарей — они не попадут в конфиг
        for name in ("gopls", "clangd", "lua-language-server"):
            (self.tmp / name).unlink()
        servers = self._run()["servers"]
        names = [Path(s["command"][0]).name for s in servers]
        self.assertNotIn("gopls", names)
        self.assertNotIn("clangd", names)
        self.assertIn("bash-language-server", names)


if __name__ == "__main__":
    unittest.main()

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
