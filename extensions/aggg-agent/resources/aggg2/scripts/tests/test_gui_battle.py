#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Боевое крещение раннера gui_battle.py: condition-based waiting быстрее
фиксированных sleep, откат в finally, отчёт и код выхода.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts' / 'tools' / 'battle'))
import gui_battle  # noqa: E402


class FakeApp:
    """Асинхронное приложение: тумблеры с переменной задержкой срабатывания."""

    def __init__(self):
        self.state = {"power": False, "dialog": False, "tick": 0}
        self.calls = []

    def toggle(self, key, delay):
        self.calls.append(key)
        time.sleep(delay)
        self.state[key] = not self.state[key]
        return "fired"

    def bump(self, delay):
        time.sleep(delay)
        self.state["tick"] += 1
        return "fired"


class TestPoll(unittest.TestCase):
    def test_fast_condition_resolves_first_iteration(self):
        t0 = time.time()
        ok, _ = gui_battle.poll(None, lambda _: True, None, timeout=5)
        self.assertTrue(ok)
        self.assertLess(time.time() - t0, 2)

    def test_stable_false_times_out_with_trace(self):
        t0 = time.time()
        ok, firsts = gui_battle.poll(None, lambda _: "", None, timeout=1.2)
        self.assertFalse(ok)
        self.assertEqual(firsts, [""])
        self.assertLess(time.time() - t0, 3.5)

    def test_value_trace_caps_three_distinct(self):
        vals = [0, "", None]
        seen = []

        def wait2(_):
            seen.append(1)
            return vals[(len(seen) - 1) % 3]

        ok, firsts = gui_battle.poll(None, wait2, None, timeout=1.4)
        self.assertFalse(ok)
        self.assertEqual(len(firsts), 3)


class TestRun(unittest.TestCase):
    def _config(self, app):
        ns = {"app": app}

        def eval_js(code):
            return eval(code, {"__builtins__": {}}, ns)  # noqa: S307 — свой конфиг

        steps = []
        for i, d in enumerate([0.4, 0.6, 0.4, 0.6, 0.4, 0.6, 0.4, 0.6, 0.4, 0.6]):
            want_true = (i % 2 == 0)
            steps.append({
                "name": f"тумблер {i}",
                "action": f"app.toggle('power', {d})",
                "wait": "app.state['power']",
                "want": (lambda v, wt=want_true: v is True if wt else v is False),
                "timeout": 5,
            })
        steps += [
            {"name": "диалог-цикл", "action": "app.toggle('dialog', 0.3)",
             "wait": "app.state['dialog']", "timeout": 5},
            {"name": "тики", "action": "app.bump(0.2)",
             "wait": "app.state['tick']", "want": lambda v: v >= 1, "timeout": 5},
        ]
        return {
            "launch": lambda: None,
            "snapshot": lambda: {"marker": "snap"},
            "restore": None,
            "eval_js": eval_js,
            "boot_wait": 0,
            "steps": steps,
        }

    def test_run_all_pass_and_faster_than_fixed_sleep(self):
        app = FakeApp()
        cfg = self._config(app)
        t0 = time.time()
        code = gui_battle.run(cfg)
        wall = time.time() - t0
        self.assertEqual(code, 0)
        self.assertEqual(len(gui_battle.RESULTS), 12)
        self.assertTrue(all(g for _, g in gui_battle.RESULTS))
        naive = sum(0.4 if i % 2 == 0 else 0.6 for i in range(10)) + 0.3 + 0.2
        self.assertLessEqual(wall, naive * 2.5 + 1.0)

    def test_run_failure_reports_and_restore_called(self):
        app = FakeApp()
        cfg = self._config(app)
        cfg["steps"] = [{"name": "недостижимо", "wait": "0", "timeout": 1}]
        restored = []
        cfg["restore"] = lambda snap: restored.append(snap)
        code = gui_battle.run(cfg)
        self.assertEqual(code, 1)
        self.assertEqual(restored, [{"marker": "snap"}])

    def test_report_json(self):
        app = FakeApp()
        cfg = self._config(app)
        gui_battle.RESULTS.clear()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            code = gui_battle.run(cfg, report_out=str(out))
            report = json.loads(out.read_text()) if code == 0 else None
        self.assertIsNotNone(report)
        self.assertEqual(report["total"], 12)
        self.assertEqual(report["ok"], 12)
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
