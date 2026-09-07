#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Гейт размера файлов: collect/gate на временных деревьях + хук прошивки.

Регрессии: лимиты поменялись, baseline-логика сломалась, хук перестал
блокировать god-файлы. Работают на временных каталогах — дерево и
baseline не трогаем.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools' / 'audit'))
import check_file_sizes as cfs  # noqa: E402

HOOK = (Path(__file__).resolve().parent.parent.parent
        / "harness" / "hooks" / "aggg2_prompt_hook.py")
SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "audit" / "check_file_sizes.py"

# Нельзя включать настоящий baseline в тесты — подмена на временный.
REAL_BASELINE = cfs.BASELINE_PATH


def _make_file(path: Path, lines: int, text: str = "x = 1"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text for _ in range(lines)) + "\n",
                    encoding="utf-8")


def _run_hook(payload: dict):
    r = subprocess.run([sys.executable, str(HOOK)],
                       input=json.dumps(payload), capture_output=True,
                       text=True, timeout=30)
    d = json.loads(r.stdout) if r.stdout.strip() else {}
    out = d.get("hookSpecificOutput", {})
    if not out:
        # agy/gemini-формат: {"decision": "deny"|"allow", "reason": ...}
        return d.get("decision"), str(d.get("reason") or "")
    return out.get("permissionDecision"), str(
        out.get("permissionDecisionReason")
        or out.get("additionalContext") or "")


class CollectGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aggg2-fs-"))
        self._old = cfs.BASELINE_PATH
        cfs.BASELINE_PATH = self.tmp / "baseline.json"

    def tearDown(self):
        cfs.BASELINE_PATH = self._old

    def test_clean_tree_no_violations(self):
        _make_file(self.tmp / "small.py", 100)
        _make_file(self.tmp / "doc.md", 100)
        self.assertEqual(cfs.collect(self.tmp), [])

    def test_hard_violation_and_gate(self):
        _make_file(self.tmp / "god.py", 1100)
        rows = cfs.collect(self.tmp)
        self.assertEqual(rows[0]["level"], "hard")
        errors, warnings, _ = cfs.gate(rows)
        self.assertEqual(len(errors), 1)
        self.assertEqual(warnings, [])

    def test_soft_violation_is_warning(self):
        _make_file(self.tmp / "mid.py", 600)
        rows = cfs.collect(self.tmp)
        self.assertEqual(rows[0]["level"], "soft")
        errors, warnings, _ = cfs.gate(rows)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_baseline_ok_grown_done(self):
        _make_file(self.tmp / "legacy.py", 1044)
        baseline = {"legacy.py": {"lines": 1044, "why": "тест"}}
        cfs.BASELINE_PATH.write_text(json.dumps(baseline), encoding="utf-8")
        # в cap — не нарушение (grandfather)
        self.assertEqual(cfs.collect(self.tmp), [])
        # рост выше cap — error
        _make_file(self.tmp / "legacy.py", 1100)
        rows = cfs.collect(self.tmp)
        self.assertEqual(rows[0]["level"], "baseline-grown")
        errors, _, _ = cfs.gate(rows)
        self.assertEqual(len(errors), 1)
        # урезали ниже hard — info (фиксатор можно снять)
        _make_file(self.tmp / "legacy.py", 900)
        rows = cfs.collect(self.tmp)
        self.assertEqual(rows[0]["level"], "baseline-done")
        errors, _, info = cfs.gate(rows)
        self.assertEqual(errors, [])
        self.assertEqual(len(info), 1)

    def test_exclusions(self):
        _make_file(self.tmp / "index.md", 2000)
        _make_file(self.tmp / "log.md", 2000)
        _make_file(self.tmp / "data.json", 2000)
        _make_file(self.tmp / "note.bak", 2000)
        # CHANGELOG/ — директория, исключается через EXCLUDE_DIRS
        changelog_dir = self.tmp / "CHANGELOG"
        changelog_dir.mkdir()
        _make_file(changelog_dir / "2026-08-19.md", 2000)
        self.assertEqual(cfs.collect(self.tmp), [])


class HookFileSizeTest(unittest.TestCase):
    """Хук прошивки: deny на god-файлы, тишина на чистом коде."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aggg2-hook-"))

    def test_write_new_over_hard_deny(self):
        content = "\n".join(f"x{i} = 1" for i in range(1100))
        decision, reason = _run_hook(
            {"tool_name": "Write",
             "tool_input": {"file_path": str(self.tmp / "god_new.py"),
                            "content": content}})
        self.assertEqual(decision, "deny")
        self.assertIn("god-файл", reason)

    def test_antigravity_write_to_file_deny(self):
        """agy write_to_file: TargetFile + CodeContent — тот же deny."""
        content = "\n".join(f"x{i} = 1" for i in range(1100))
        decision, reason = _run_hook(
            {"toolCall": {"name": "write_to_file",
                          "args": {"TargetFile": str(self.tmp / "g.py"),
                                   "CodeContent": content}}})
        self.assertEqual(decision, "deny")
        self.assertIn("hard-лимите", reason)

    def test_antigravity_replace_growth_deny(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("\n".join(f"x{i} = 1" for i in range(990)) + "\n")
            target = f.name
        try:
            decision, reason = _run_hook(
                {"toolCall": {"name": "replace_file_content",
                              "args": {"TargetFile": target,
                                       "TargetContent": "x0 = 1",
                                       "ReplacementContent":
                                           "x0 = 1\n" + "y = 1\n" * 50}}})
            self.assertEqual(decision, "deny")
            self.assertIn("hard-лимите", reason)
        finally:
            Path(target).unlink(missing_ok=True)

    def test_gemini_edit_growth_deny(self):
        """gemini 'edit' (нижний регистр) с ростом выше hard — deny."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("\n".join(f"x{i} = 1" for i in range(990)) + "\n")
            target = f.name
        try:
            decision, _ = _run_hook(
                {"tool_name": "edit",
                 "tool_input": {"file_path": target,
                                "old_string": "x0 = 1",
                                "new_string": "x0 = 1\n" + "y = 1\n" * 50}})
            self.assertEqual(decision, "deny")
        finally:
            Path(target).unlink(missing_ok=True)

    def test_write_new_under_hard_allow(self):
        content = "\n".join(f"x{i} = 1" for i in range(100))
        decision, _ = _run_hook(
            {"tool_name": "Write",
             "tool_input": {"file_path": str(self.tmp / "ok_new.py"),
                            "content": content}})
        self.assertNotEqual(decision, "deny")

    def test_edit_grow_past_hard_deny(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("\n".join(f"x{i} = 1" for i in range(990)) + "\n")
            target = f.name
        try:
            decision, reason = _run_hook(
                {"tool_name": "Edit",
                 "tool_input": {"file_path": target,
                                "old_string": "x0 = 1",
                                "new_string": "x0 = 1\n" + "y = 1\n" * 50}})
            self.assertEqual(decision, "deny")
            self.assertIn("hard-лимите", reason)
        finally:
            Path(target).unlink(missing_ok=True)

    def test_edit_shrink_allow(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("a = 1\nb = 2\nc = 3\n" + "\n".join(
                f"x{i} = 1" for i in range(1050)) + "\n")
            target = f.name
        try:
            decision, _ = _run_hook(
                {"tool_name": "Edit",
                 "tool_input": {"file_path": target,
                                "old_string": "a = 1\nb = 2\nc = 3",
                                "new_string": "a = 1"}})
            self.assertNotEqual(decision, "deny")
        finally:
            Path(target).unlink(missing_ok=True)


class StagedGateTest(unittest.TestCase):
    """--staged: вердикт по ИНДЕКСИРОВАННОМУ содержимому (git pre-commit)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aggg2-stage-"))
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        for k, v in (("user.email", "t@t"), ("user.name", "t")):
            subprocess.run(["git", "config", k, v], cwd=str(self.tmp),
                           check=True)
        self._old = cfs.BASELINE_PATH
        cfs.BASELINE_PATH = self.tmp / "baseline.json"

    def tearDown(self):
        cfs.BASELINE_PATH = self._old

    def _stage(self, rel: str, lines: int):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(f"x{i} = 1" for i in range(lines)) + "\n",
                     encoding="utf-8")
        subprocess.run(["git", "add", rel], cwd=str(self.tmp), check=True)

    def test_staged_god_blocked(self):
        self._stage("big.py", 1100)
        rows = cfs.staged_rows(self.tmp)
        self.assertEqual(rows[0]["level"], "hard")
        errors, _, _ = cfs.gate(rows)
        self.assertEqual(len(errors), 1)

    def test_staged_clean(self):
        self._stage("small.py", 100)
        self.assertEqual(cfs.staged_rows(self.tmp), [])

    def test_staged_baseline_ok_and_growth(self):
        self._stage("legacy.py", 1044)
        cfs.BASELINE_PATH.write_text(
            json.dumps({"legacy.py": {"lines": 1044, "why": "тест"}}),
            encoding="utf-8")
        self.assertEqual(cfs.staged_rows(self.tmp), [])  # в cap — ок
        self._stage("legacy.py", 1100)  # рост выше cap — блок
        rows = cfs.staged_rows(self.tmp)
        self.assertEqual(rows[0]["level"], "baseline-grown")

    def test_reviewdog_output(self):
        _make_file(self.tmp / "god.py", 1100)
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--reviewdog", "--root",
             str(self.tmp)], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0)
        first = r.stdout.strip().splitlines()[0]
        self.assertRegex(first, r"^god\.py:1:1: god-файл:")


class LimitsMirrorTest(unittest.TestCase):
    """SSOT: лимиты hook_gates (hook_hints) == лимиты check_file_sizes.
    Оба места помечены «ЗЕРКАЛО — менять ОБА»; расхождение = дрейф
    enforcement (хук блокирует одно, CI — другое)."""

    def test_hook_gates_limits_match_check_file_sizes(self):
        import importlib.util
        gates_dir = Path(__file__).resolve().parent.parent.parent / "harness" / "hooks"
        spec = importlib.util.spec_from_file_location(
            "hook_gates", gates_dir / "hook_gates.py")
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(gates_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path.remove(str(gates_dir))
        self.assertEqual(set(mod.FILE_TIERS), set(cfs.LIMITS))
        for tier, (soft, hard, exts) in mod.FILE_TIERS.items():
            conf = cfs.LIMITS[tier]
            self.assertEqual((soft, hard), (conf["soft"], conf["hard"]), tier)
            self.assertEqual(set(exts), set(conf["ext"]), tier)


if __name__ == "__main__":
    unittest.main()

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
