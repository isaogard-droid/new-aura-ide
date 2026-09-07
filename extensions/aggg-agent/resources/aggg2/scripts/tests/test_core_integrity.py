#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Целостность прошивки: карта канон-доков в ядре ↔ реальные файлы ↔ копии.

Защищает от регрессий: выпилили док, а карта в core.txt осталась; обновили
ядро, а копии в харнессах устарели (напомнит перезапустить install_proshivka).

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CORE = ROOT / "harness" / "core.txt"
CORE_COPIES = [
    pathlib.Path.home() / ".config/opencode/plugins/core.txt",
    pathlib.Path.home() / ".claude/hooks/core.txt",
    pathlib.Path.home() / ".codex/hooks/core.txt",
]
CORE_MARKER = "КАНОН-ДОКИ ПО ТИПУ ЗАДАЧИ"
CORE_TAIL_MARKER = "DoD-СВЕРКА"
HOOK = ROOT / "harness" / "hooks" / "aggg2_prompt_hook.py"


def _load_hook():
    """Импортирует хук как модуль (имя файла — валидный идентификатор)."""
    spec = importlib.util.spec_from_file_location("aggg2_prompt_hook", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CoreIntegrityTest(unittest.TestCase):
    def test_core_has_docs_map(self):
        text = CORE.read_text(encoding="utf-8")
        self.assertIn(CORE_MARKER, text, "ядро потеряло карту канон-доков")

    def test_core_has_recency_tail(self):
        """Хвост primacy/recency: DoD-сверка в конце ядра (паттерн индустрии)."""
        text = CORE.read_text(encoding="utf-8")
        self.assertIn(CORE_TAIL_MARKER, text, "ядро потеряло DoD-хвост")
        self.assertLess(
            text.index(CORE_TAIL_MARKER), text.rindex("Принадлежит"),
            "DoD-хвост должен идти в конце правил (recency), а не в шапке",
        )

    def test_mapped_docs_exist(self):
        text = CORE.read_text(encoding="utf-8")
        for name in re.findall(r"([A-Z][A-Z0-9-]+\.md)", text):
            self.assertTrue(
                (ROOT / name).exists() or (ROOT / "docs" / "canon" / name).exists(),
                f"карта ссылается на {name}, а файла нет ни в корне, ни в docs/canon/",
            )

    def test_copies_in_sync(self):
        canon = hashlib.sha256(CORE.read_bytes()).hexdigest()
        for copy in CORE_COPIES:
            self.assertTrue(copy.exists(), f"копия ядра не установлена: {copy}")
            self.assertEqual(
                hashlib.sha256(copy.read_bytes()).hexdigest(), canon,
                f"копия устарела: {copy} — запусти python3 scripts/install/install_proshivka.py",
            )


class EnforcementDecideTest(unittest.TestCase):
    """Сторож PreToolUse: запреты блокируются, остальное живёт (канон CLAUDE.md п.8)."""

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()
        import tempfile

        import hook_gates  # состояние nudge-гейтов живёт в hook_gates
        cls.hook._STATE_DIR = pathlib.Path(tempfile.mkdtemp())  # изоляция
        hook_gates._STATE_DIR = cls.hook._STATE_DIR

    def decide(self, tool, **kwargs):
        return self.hook.decide_pre_tool_use(tool, kwargs)

    def decide_sid(self, tool, sid=None, **kwargs):
        return self.hook.decide_pre_tool_use(tool, kwargs, session_id=sid)

    def test_block_pkill_without_bracket_trick(self):
        out = self.decide("Bash", command="pkill -f aggg2")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_allow_pkill_with_trick(self):
        out = self.decide("Bash", command='pkill -f "[a]ggg2"')
        self.assertIsNone(out)
        out = self.decide("Bash", command="pkill -f [a]ggg2")
        self.assertIsNone(out)

    def test_block_rm_rf_root(self):
        for cmd in ("rm -rf /", "rm -rf ~", "rm -rf .", "sudo rm -rf /"):
            out = self.decide("Bash", command=cmd)
            self.assertEqual(
                out["hookSpecificOutput"]["permissionDecision"], "deny",
                f"не заблокировано: {cmd}",
            )

    def test_warn_not_block_rm_build_dir(self):
        """rm -rf /tmp/build — обратимое (сборки): allow + напоминание."""
        out = self.decide("Bash", command="rm -rf /tmp/build")
        self.assertIsNotNone(out)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "allow")

    def test_block_git_reset_hard(self):
        out = self.decide("Bash", command="git reset --hard HEAD~1")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_silent_for_harmless_command(self):
        self.assertIsNone(self.decide("Bash", command="ls -la"))

    def test_edit_code_reminds_qa(self):
        out = self.decide("Edit", file_path="src/main.py")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "allow")
        self.assertIn("QA", out["hookSpecificOutput"]["additionalContext"])

    def test_edit_md_silent(self):
        self.assertIsNone(self.decide("Edit", file_path="README.md"))

    def test_edit_code_without_web_research_nudges(self):
        """Гейт «ресёрч-первым»: правка кода без веб-ресёрча — напоминание
        с нормативом 10 источников (паритет opencode-плагина)."""
        out = self.decide_sid("Edit", "t-no-web", file_path="src/main.py")
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("10 источников", ctx)
        self.assertIn("QA", ctx)

    def test_web_research_marks_session(self):
        """Веб-вызов (Camoufox MCP) гасит гейт «ресёрч-первым» до конца
        сессии: правка кода после ресёрча — без напоминания. Сам веб-вызов
        может вернуть nudge «скиллы-первым» (локальный скилл до веба,
        docs/canon/SKILLS-LOCAL.md) — это не гейт ресёрча, а skills-nudge."""
        out = self.decide_sid("Edit", "t-web", file_path="src/main.py")
        self.assertIn("10 источников",
                      out["hookSpecificOutput"]["additionalContext"])
        out = self.decide_sid("mcp__camoufox__web_search", "t-web")
        if out is not None:
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("10 источников", ctx)
            self.assertIn("скиллы-первым", ctx)
        out = self.decide_sid("Edit", "t-web", file_path="src/main.py")
        self.assertNotIn("10 источников",
                         out["hookSpecificOutput"]["additionalContext"])

    def test_web_nudge_escalation(self):
        """Эскалация: 3-я правка без ресёрча — настойчивее (вернись в
        RESEARCH)."""
        for _ in (1, 2):
            out = self.decide_sid("Edit", "t-esc", file_path="src/main.py")
            self.assertEqual(
                out["hookSpecificOutput"]["permissionDecision"], "allow")
        out = self.decide_sid("Edit", "t-esc", file_path="src/main.py")
        self.assertIn("вернись в RESEARCH",
                      out["hookSpecificOutput"]["additionalContext"])


class EnforcementPipeTest(unittest.TestCase):
    """Скрипт целиком через stdin/stdout (контракт хука харнесов)."""

    def run_hook(self, stdin_text):
        proc = subprocess.run(
            [sys.executable, str(HOOK)], input=stdin_text, capture_output=True,
            text=True, timeout=30,
        )
        return proc

    def test_pretooluse_deny(self):
        proc = self.run_hook(
            json.dumps({"tool_name": "Bash",
                        "tool_input": {"command": "pkill -f foo"}}))
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_pretooluse_lowercase_bash(self):
        """openCode/reasonix шлют имя тула в нижнем регистре."""
        out = _load_hook().decide_pre_tool_use("bash", {"command": "git reset --hard"})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_reasonix_deny_exit2(self):
        """Reasonix: блок = exit 2 + stderr (payload CamelCase)."""
        proc = self.run_hook(json.dumps(
            {"Event": "PreToolUse", "ToolName": "bash",
             "ToolArgs": json.dumps({"command": "rm -rf /"})}))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("БЛОК", proc.stderr)

    def test_reasonix_allow_exit0(self):
        proc = self.run_hook(json.dumps(
            {"Event": "PreToolUse", "ToolName": "bash",
             "ToolArgs": json.dumps({"command": "ls"})}))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_reasonix_ignore_posttooluse(self):
        """PostToolUse у reasonix — notify: хук молчит, ничего не блокирует."""
        proc = self.run_hook(json.dumps(
            {"Event": "PostToolUse", "ToolName": "bash",
             "ToolArgs": json.dumps({"command": "pkill -f foo"})}))
        self.assertEqual(proc.returncode, 0)

    def _run_with_env(self, stdin_text, extra_env):
        import os as _os
        env = dict(_os.environ)
        env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(HOOK)], input=stdin_text, capture_output=True,
            text=True, timeout=30, env=env,
        )

    def test_codewhale_deny_json(self):
        """Codewhale: контекст в env, вердикт — stdout JSON decision=deny."""
        proc = self._run_with_env(
            "{}", {"DEEPSEEK_TOOL_NAME": "exec_shell",
                   "DEEPSEEK_TOOL_ARGS": json.dumps({"command": "pkill -f foo"})})
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(out["decision"], "deny")

    def test_codewhale_allow_silent(self):
        proc = self._run_with_env(
            "{}", {"DEEPSEEK_TOOL_NAME": "exec_shell",
                   "DEEPSEEK_TOOL_ARGS": json.dumps({"command": "ls"})})
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_omp_block_exit2(self):
        """omp-hooks: блок только через exit 2 + stderr."""
        proc = self._run_with_env(
            json.dumps({"tool_name": "Bash",
                        "tool_input": {"command": "rm -rf /"}}),
            {"AGGG2_HOOK_MODE": "omp"})
        self.assertEqual(proc.returncode, 2)
        self.assertIn("БЛОК", proc.stderr)

    def test_omp_allow_plain_stdout(self):
        """omp: allow-напоминание — plain-текст stdout (скрытый контекст модели)."""
        proc = self._run_with_env(
            json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "a.py"}}),
            {"AGGG2_HOOK_MODE": "omp"})
        self.assertEqual(proc.returncode, 0)
        self.assertIn("QA", proc.stdout)

    def test_pretooluse_silent(self):
        proc = self.run_hook(
            json.dumps({"tool_name": "Bash",
                        "tool_input": {"command": "ls"}}))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_userpromptsubmit_core(self):
        proc = self.run_hook("{}")
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"],
                         "UserPromptSubmit")
        self.assertIn(CORE_MARKER, out["hookSpecificOutput"]["additionalContext"])
        self.assertIn(CORE_TAIL_MARKER,
                      out["hookSpecificOutput"]["additionalContext"])

    def test_bad_input_never_breaks(self):
        proc = self.run_hook("not json")
        self.assertEqual(proc.returncode, 0)

    def test_pretooluse_doc_hint(self):
        """Правка канон-дока → напоминание про связанные файлы (doc_deps)."""
        proc = self.run_hook(
            json.dumps({"tool_name": "Write",
                        "tool_input": {"file_path":
                                       str(ROOT / "CYCLE.md")}}))
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        ctx = out["hookSpecificOutput"].get("additionalContext", "")
        self.assertIn("doc_deps.py", ctx)

    def test_doc_deps_map_valid(self):
        """Карта связанности doc_deps.py: все пути существуют, скрипт
        запускается и находит backlinks."""
        doc_deps = ROOT / "scripts" / "tools" / "audit" / "doc_deps.py"
        self.assertTrue(doc_deps.is_file(), "scripts/tools/audit/doc_deps.py нет")
        proc = subprocess.run(
            [sys.executable, str(doc_deps), "check",
             str(ROOT / "CYCLE.md")],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("BACKLINKS", proc.stdout)
        # CYCLE.md упоминается в AGENTS.md (указатель) — backlink обязан быть
        self.assertIn("AGENTS.md", proc.stdout)


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
