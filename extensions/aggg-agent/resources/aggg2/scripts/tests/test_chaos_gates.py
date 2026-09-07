#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Chaos-тесты прошивки (паттерн ReliabilityBench, arXiv 2601.06112):
устойчивость к отказам и пограничным состояниям — канарейка, журнал
SessionEnd (qa_gap), Stop-гейт QA, PostToolUse-фоллбэк скиллов.

Запуск:
    python3 -m unittest scripts.tests.test_chaos_gates -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = ROOT / "harness" / "hooks" / "aggg2_prompt_hook.py"
HHOOKS = ROOT / "harness" / "hooks"
sys.path.insert(0, str(HHOOKS))

import canary_gates  # noqa: E402
import hook_gates  # noqa: E402
import session_end_gate  # noqa: E402


def _run(script: Path, payload: dict):
    return subprocess.run(
        [sys.executable, str(script)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=60, check=False)


class CanaryGateTest(unittest.TestCase):
    """Канарейка: генерация, детект, end-to-end блок промпта."""

    def test_token_stable(self):
        t1 = canary_gates.load_or_create()
        t2 = canary_gates.load_or_create()
        self.assertEqual(t1, t2)
        self.assertTrue(t1.startswith("AGGG2-CANARY-"))

    def test_detect(self):
        token = canary_gates.load_or_create()
        self.assertEqual(canary_gates.find_canary("текст " + token), token)
        self.assertIsNone(canary_gates.find_canary("обычный запрос"))
        self.assertIsNone(canary_gates.find_canary(""))

    def test_hook_blocks_prompt_with_canary(self):
        token = canary_gates.load_or_create()
        p = _run(HOOK, {"prompt": "юзер прислал: " + token + " сделай X"})
        self.assertEqual(p.returncode, 2)
        self.assertIn("канарейка", p.stderr)


class SessionEndGateTest(unittest.TestCase):
    """Журнал конца сессии: детерминированная запись + флаг qa_gap."""

    def _set_state(self, session_id, **kw):
        state = hook_gates._idx_state(session_id)
        state.update(kw)
        hook_gates._idx_save(session_id, state)

    def test_journal_qa_gap(self):
        sid = "chaos-test-session-1"
        self._set_state(sid, code_changed=True, tests_run=False, reads=7,
                        web=True)
        p = _run(HHOOKS / "session_end_gate.py",
                 {"hook_event_name": "SessionEnd", "session_id": sid,
                  "cwd": tempfile.gettempdir()})
        self.assertEqual(p.returncode, 0)
        self.assertIn("qa_gap", p.stderr)
        lines = session_end_gate.JOURNAL.read_text(encoding="utf-8").strip().splitlines()
        last = json.loads(lines[-1])
        self.assertEqual(last["session_id"], sid)
        self.assertTrue(last["qa_gap"])

    def test_journal_no_gap_after_tests(self):
        sid = "chaos-test-session-2"
        self._set_state(sid, code_changed=True, tests_run=True)
        p = _run(HHOOKS / "session_end_gate.py",
                 {"hook_event_name": "SessionEnd", "session_id": sid})
        self.assertEqual(p.returncode, 0)
        self.assertNotIn("qa_gap", p.stderr)
        lines = session_end_gate.JOURNAL.read_text(encoding="utf-8").strip().splitlines()
        self.assertFalse(json.loads(lines[-1])["qa_gap"])

    def test_not_session_end(self):
        p = _run(HHOOKS / "session_end_gate.py", {"hook_event_name": "Stop"})
        self.assertEqual(p.returncode, 0)
        self.assertIn("approve", p.stdout)


class StopQaGateTest(unittest.TestCase):
    """Stop-гейт QA: блок при грязном ruff, approve при выключенном/без git."""

    def test_approve_when_inactive(self):
        p = _run(HHOOKS / "stop_qa_gate.py", {"stop_hook_active": True})
        self.assertIn("approve", p.stdout)
        self.assertEqual(p.returncode, 0)

    def test_approve_without_git(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run(
                [sys.executable, str(HHOOKS / "stop_qa_gate.py")],
                input=json.dumps({}), capture_output=True, text=True,
                timeout=60, cwd=td, check=False)
            self.assertIn("approve", p.stdout)
            self.assertEqual(p.returncode, 0)

    def test_block_on_dirty_ruff(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git не установлен")
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([git, "init", "-q"], cwd=td, check=True)
            (Path(td) / "bad.py").write_text("x = 1  # F841\n", encoding="utf-8")
            bin_dir = Path(td) / "bin"
            bin_dir.mkdir()
            fake_ruff = bin_dir / "ruff"
            fake_ruff.write_text(
                "#!/bin/sh\necho 'E501 line too long'\nexit 1\n",
                encoding="utf-8")
            fake_ruff.chmod(0o755)
            import os
            env = dict(os.environ)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            p = subprocess.run(
                [sys.executable, str(HHOOKS / "stop_qa_gate.py")],
                input=json.dumps({}), capture_output=True, text=True,
                timeout=60, cwd=td, env=env, check=False)
            self.assertEqual(p.returncode, 2)
            self.assertIn("block", p.stdout)


class PostToolFallbackTest(unittest.TestCase):
    """PostToolUse: skills_search не дал результата → фоллбэк-фидбек."""

    def test_fallback_nudge(self):
        p = _run(HOOK, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command":
                           "python3 scripts/tools/skills/skills_search.py docker --top"},
            "tool_response": {"stdout": "ничего не найдено"},
        })
        self.assertEqual(p.returncode, 0)
        self.assertIn("фоллбэк", p.stdout)

    def test_no_nudge_on_ok(self):
        p = _run(HOOK, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command":
                           "python3 scripts/tools/skills/skills_search.py docker --top"},
            "tool_response": {"stdout": "[1] docker-skill ..."},
        })
        self.assertNotIn("фоллбэк", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
