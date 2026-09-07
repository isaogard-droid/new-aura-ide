#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Боевое крещение web/perf/fuzz/visual-раннеров (E2E через subprocess).

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import http.server
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS = ROOT / "scripts" / "tools" / "battle"
_venv_py = Path.home() / ".venvs" / "aggg2" / "bin" / "python"
PY = str(_venv_py) if _venv_py.is_file() else sys.executable  # venv с playwright/hypothesis/PIL

WEB_HTML = """<!DOCTYPE html><html><body>
<button id="btn" onclick="document.getElementById('out').textContent='clicked'">go</button>
<div id="out">initial</div></body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/page":
            body = WEB_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api":
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):
        pass


def _serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


WEB_CFG = '''
from PIL import Image
CONFIG = {
    "base": "%(base)s",
    "headless": True,
    "channel": "chrome",
    "steps": [
        {"name": "открыть и кликнуть", "action": "page.goto(base + '/page')",
         "wait": "page.locator('#btn').count()", "want": lambda v: v == 1,
         "timeout": 20},
        {"name": "клик меняет текст", "action": "page.locator('#btn').click()",
         "wait": "page.locator('#out').text_content()",
         "want": lambda v: v == 'clicked', "timeout": 10},
        {"name": "expect-авто-ожидание", "action": "None",
         "wait": "expect(page.locator('#out')).to_have_text('clicked') or True",
         "want": lambda v: v is True, "timeout": 10},
        {"name": "404 тоже шаг", "action": "page.goto(base + '/missing')",
         "wait": "page.url",
         "want": lambda v: v.endswith('/missing'), "timeout": 20},
    ],
}
'''

PERF_CFG = '''
CONFIG = {
    "steps": [
        {"name": "эндпоинт держит 200 rps и p95 < 2000мс",
         "url": "%(base)s/api", "n": 200, "c": 4,
         "want": lambda p: p["failed"] == 0 and p.get("p95_ms", 999999) < 2000},
        {"name": "порог p95 намеренно нереальный — ловится",
         "url": "%(base)s/api", "n": 100, "c": 2,
         "want": lambda p: p.get("p95_ms", 999999) < 1},
    ],
}
'''

FUZZ_CFG = '''
import string
import sys
sys.path.insert(0, "%(vpn)s")
from hypothesis import strategies as st
from vpn_gui import config_merge

_SAFE = string.ascii_letters + string.digits
_TOKEN = st.text(alphabet=_SAFE + "_-", min_size=1, max_size=10)
_HOST = st.builds(lambda a, b: a + b,
                  st.sampled_from(_SAFE),
                  st.text(alphabet=_SAFE + ".-", min_size=0, max_size=9))

CONFIG = {
    "targets": [
        {"name": "parse_share_link: только ValueError, никаких крашей",
         "fn": config_merge.parse_share_link,
         "strategy": st.text(min_size=0, max_size=200),
         "prop": lambda v: _safe(v),
         "n": 400},
        {"name": "socks-ссылка: поля переживают парсинг",
         "strategy": st.builds(
             lambda u, p, h, port: f"socks://{u}:{p}@{h}:{port}#t1",
             _TOKEN, _TOKEN, _HOST,
             st.integers(min_value=1, max_value=65535)),
         "prop": lambda s: _fields(s),
         "n": 200},
    ],
}

def _safe(v):
    try:
        config_merge.parse_share_link(v)
        return True
    except ValueError:
        return True
    except Exception:
        return False

def _fields(s):
    try:
        r = config_merge.parse_share_link(s)
    except Exception:
        return False
    return r.get("type") == "socks" and r.get("server_port")
'''


class TestWebBattle(unittest.TestCase):
    def test_e2e(self):
        srv = _serve()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            with tempfile.TemporaryDirectory() as tmp:
                cfg = Path(tmp) / "web_cfg.py"
                cfg.write_text(WEB_CFG % {"base": base}, encoding="utf-8")
                report = Path(tmp) / "r.json"
                t0 = time.time()
                r = subprocess.run([PY, str(TOOLS / "web_battle.py"), str(cfg),
                                    "--json", str(report)],
                                   capture_output=True, text=True, timeout=180)
                wall = time.time() - t0
                rep = json.loads(report.read_text())
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("ИТОГ: 4/4 (100%)", r.stdout)
            self.assertLessEqual(wall, 60)
            self.assertEqual(rep["ok"], 4)
        finally:
            srv.shutdown()


class TestPerfBattle(unittest.TestCase):
    def test_e2e(self):
        srv = _serve()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            with tempfile.TemporaryDirectory() as tmp:
                cfg = Path(tmp) / "perf_cfg.py"
                cfg.write_text(PERF_CFG % {"base": base}, encoding="utf-8")
                report = Path(tmp) / "r.json"
                r = subprocess.run([PY, str(TOOLS / "perf_battle.py"), str(cfg),
                                    "--json", str(report)],
                                   capture_output=True, text=True, timeout=300)
            # второй шаг (порог <1мс) обязан провалиться — это проверка порога
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("ИТОГ: 1/2 (50%)", r.stdout)
            self.assertIn("порог p95", r.stdout)
        finally:
            srv.shutdown()


class TestFuzzBattle(unittest.TestCase):
    def test_e2e(self):
        vpn = str(ROOT / "projects" / "vpn-gui")
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "fuzz_cfg.py"
            cfg.write_text(FUZZ_CFG % {"vpn": vpn}, encoding="utf-8")
            report = Path(tmp) / "r.json"
            r = subprocess.run([PY, str(TOOLS / "fuzz_battle.py"), str(cfg),
                                "--json", str(report)],
                               capture_output=True, text=True, timeout=300)
            rep = json.loads(report.read_text())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ИТОГ: 2/2 (100%)", r.stdout)
        self.assertEqual(rep["ok"], 2)


class TestVisualBattle(unittest.TestCase):
    def test_e2e(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "shots"
            base.mkdir()

            def mk(noise):
                import random
                rnd = random.Random(7)  # noqa: S311 — deterministic test noise
                img = Image.new("RGB", (64, 64), (30, 40, 50))
                px = img.load()
                if noise:
                    for _ in range(2000):
                        x, y = rnd.randrange(64), rnd.randrange(64)
                        px[x, y] = (rnd.randrange(256),) * 3
                return img

            cfg = Path(tmp) / "visual_cfg.py"
            cfg.write_text(f'''\nfrom PIL import Image\nimport random\n\ndef _mk(noise):\n    rnd = random.Random(7)\n    img = Image.new("RGB", (64, 64), (30, 40, 50))\n    px = img.load()\n    if noise:\n        for _ in range(2000):\n            x, y = rnd.randrange(64), rnd.randrange(64)\n            px[x, y] = (rnd.randrange(256),) * 3\n    return img\n\nCONFIG = {{\n    "shots": [\n        {{"name": "baseline", "capture": lambda: _mk(False),\n          "baseline": "{base}/a.png", "max_diff_ratio": 0.01}},\n        {{"name": "совпадает", "capture": lambda: _mk(False),\n          "baseline": "{base}/a.png", "max_diff_ratio": 0.01}},\n        {{"name": "шум 20%% ловится", "capture": lambda: _mk(True),\n          "baseline": "{base}/a.png", "max_diff_ratio": 0.05}},\n    ],\n}}\n''', encoding="utf-8")
            report = Path(tmp) / "r.json"
            r = subprocess.run([PY, str(TOOLS / "visual_battle.py"), str(cfg),
                                "--json", str(report)],
                               capture_output=True, text=True, timeout=120)
        # «шум ловится» обязан провалиться — проверка порога
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ИТОГ: 2/3 (67%)", r.stdout)
        self.assertIn("шум", r.stdout)


if __name__ == "__main__":
    unittest.main()
