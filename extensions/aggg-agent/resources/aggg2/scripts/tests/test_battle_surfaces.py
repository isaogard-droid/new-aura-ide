#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Боевое крещение cli_battle/api_battle (E2E через subprocess):
exit/stdout/stderr-условия, wait_retry по паттерну, статус-коды,
schema-проверка, откат, --json отчёт, скорость (без фиксированных sleep).

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
PY = sys.executable

CLI_CFG = '''
CONFIG = {
    "timeout": 5,
    "snapshot": lambda: {"marker": "snap"},
    "restore": lambda snap: print("RESTORED", snap, flush=True),
    "steps": [
        {"name": "echo ok", "cmd": ["echo", "hello-ok"],
         "want": lambda r: r.returncode == 0 and "hello-ok" in r.stdout},
        {"name": "exit code", "cmd": ["false"],
         "want": lambda r: r.returncode != 0},
        {"name": "stderr", "cmd": ["sh", "-c", "echo boom >&2; exit 3"],
         "want": lambda r: r.returncode == 3 and "boom" in r.stderr},
        {"name": "таймаут команды убивает", "cmd": ["sleep", "30"], "timeout": 1,
         "want": lambda r: getattr(r, "timeout", False)},
        {"name": "wait_retry: счётчик дорастёт", "cmd": ["sh", "-c", "echo $(( $(cat %(counter)s 2>/dev/null || echo 0) + 1 )) > %(counter)s; cat %(counter)s"],
         "wait_retry": 1, "timeout": 6,
         "want": lambda r: int(r.stdout.strip() or 0) >= 2},
    ],
}
'''

API_CFG = '''
CONFIG = {
    "base": "%(base)s",
    "snapshot": lambda: {"marker": "snap"},
    "restore": lambda snap: print("RESTORED", snap, flush=True),
    "steps": [
        {"name": "200 + schema", "path": "/api/ok",
         "want": lambda r: r["status"] == 200,
         "schema": {"version": str, "count": int}},
        {"name": "404 тоже шаг", "path": "/api/missing",
         "want": lambda r: r["status"] == 404},
        {"name": "POST тело", "method": "POST", "path": "/api/echo",
         "body": {"k": "v"},
         "want": lambda r: r["status"] == 200 and r["json"] and r["json"].get("k") == "v"},
        {"name": "schema-нарушение ловится", "path": "/api/bad",
         "want": lambda r: r["status"] == 200 and not (
             isinstance(r.get("json"), dict)
             and isinstance(r["json"].get("version"), str))},
    ],
}
'''


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/ok":
            body = b'{"version": "1.0", "count": 3}'
        elif self.path == "/api/bad":
            body = b'{"version": 42}'
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, *args):
        pass


class TestCliBattle(unittest.TestCase):
    def test_e2e(self):
        with tempfile.TemporaryDirectory() as tmp:
            counter = Path(tmp) / "counter"
            cfg = Path(tmp) / "cli_cfg.py"
            cfg.write_text(CLI_CFG % {"counter": str(counter)}, encoding="utf-8")
            report = Path(tmp) / "report.json"
            t0 = time.time()
            r = subprocess.run([PY, str(TOOLS / "cli_battle.py"), str(cfg),
                                "--json", str(report)],
                               capture_output=True, text=True, timeout=60)
            wall = time.time() - t0
            rep = json.loads(report.read_text())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ИТОГ: 5/5 (100%)", r.stdout)
        self.assertIn("RESTORED {'marker': 'snap'}", r.stdout)
        self.assertLessEqual(wall, 20)  # sleep 30 убит таймаутом 1с, не 30
        self.assertEqual(rep["ok"], 5)
        self.assertEqual(rep["failures"], [])


class TestApiBattle(unittest.TestCase):
    def test_e2e(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            with tempfile.TemporaryDirectory() as tmp:
                cfg = Path(tmp) / "api_cfg.py"
                cfg.write_text(API_CFG % {"base": base}, encoding="utf-8")
                report = Path(tmp) / "report.json"
                t0 = time.time()
                r = subprocess.run([PY, str(TOOLS / "api_battle.py"), str(cfg),
                                    "--json", str(report)],
                                   capture_output=True, text=True, timeout=60)
                wall = time.time() - t0
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("ИТОГ: 4/4 (100%)", r.stdout)
            self.assertIn("RESTORED {'marker': 'snap'}", r.stdout)
            self.assertLessEqual(wall, 15)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
