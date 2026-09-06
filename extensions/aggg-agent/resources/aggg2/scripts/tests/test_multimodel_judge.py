#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты multimodel_judge.py: резолв моделей из конфига.

Приоритет: CLI > --config > проектный .multimodel-judge.json >
глобальный ~/.config/aggg2/multimodel-judge.json > дефолты.
Модели НЕ вызываются — только логика конфига.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import json
import shutil

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools' / 'judge'))
import multimodel_judge as mj


class ResolveModelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.global_cfg = self.tmp / "global" / "multimodel-judge.json"
        self.global_cfg.parent.mkdir(parents=True)

    def write(self, path: Path, data: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_defaults_when_nothing(self):
        rev, judge = mj.resolve_models(str(self.tmp), None, None,
                                       global_path=self.global_cfg)
        self.assertEqual(rev, mj.DEFAULT_REVIEWERS)
        self.assertEqual(judge, mj.DEFAULT_JUDGE)

    def test_cli_overrides_config(self):
        self.write(self.global_cfg, {"reviewers": ["a/x", "b/y"], "judge": "c/z"})
        rev, judge = mj.resolve_models(str(self.tmp), "m1,m2", "m9",
                                       global_path=self.global_cfg)
        self.assertEqual(rev, ["m1", "m2"])
        self.assertEqual(judge, "m9")

    def test_project_config_over_global(self):
        self.write(self.global_cfg, {"reviewers": ["g1", "g2"], "judge": "gj"})
        self.write(self.tmp / mj.CONFIG_NAME,
                   {"reviewers": ["p1", "p2", "p3"], "judge": "pj"})
        rev, judge = mj.resolve_models(str(self.tmp), None, None,
                                       global_path=self.global_cfg)
        self.assertEqual(rev, ["p1", "p2", "p3"])
        self.assertEqual(judge, "pj")

    def test_global_fallback(self):
        self.write(self.global_cfg, {"reviewers": ["g1", "g2"], "judge": "gj"})
        rev, judge = mj.resolve_models(str(self.tmp), None, None,
                                       global_path=self.global_cfg)
        self.assertEqual(rev, ["g1", "g2"])
        self.assertEqual(judge, "gj")

    def test_explicit_config_wins(self):
        self.write(self.global_cfg, {"reviewers": ["g1", "g2"], "judge": "gj"})
        explicit = self.write(self.tmp / "my.json",
                              {"reviewers": ["e1", "e2"], "judge": "ej"})
        rev, judge = mj.resolve_models(str(self.tmp), None, None,
                                       explicit=str(explicit),
                                       global_path=self.global_cfg)
        self.assertEqual(rev, ["e1", "e2"])
        self.assertEqual(judge, "ej")

    def test_too_few_reviewers_raises(self):
        cfg = self.write(self.global_cfg, {"reviewers": ["only-one"], "judge": "j"})
        with self.assertRaises(ValueError) as ctx:
            mj.resolve_models(str(self.tmp), None, None, global_path=self.global_cfg)
        self.assertIn("минимум 2", str(ctx.exception))
        self.assertIn(str(cfg), str(ctx.exception))

    def test_broken_json_raises_with_path(self):
        bad = self.tmp / "bad.json"
        bad.write_text("{oops", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            mj.resolve_models(str(self.tmp), None, None, explicit=str(bad),
                              global_path=self.global_cfg)
        self.assertIn("не JSON", str(ctx.exception))
        self.assertIn(str(bad), str(ctx.exception))

    def test_cli_partial_uses_defaults_for_judge(self):
        rev, judge = mj.resolve_models(str(self.tmp), "m1,m2", None,
                                       global_path=self.global_cfg)
        self.assertEqual(rev, ["m1", "m2"])
        self.assertEqual(judge, mj.DEFAULT_JUDGE)

    def test_harness_default_opencode(self):
        self.assertEqual(mj.resolve_harness(str(self.tmp), None,
                                            global_path=self.global_cfg),
                         mj.DEFAULT_HARNESS)

    def test_harness_from_config(self):
        self.write(self.global_cfg, {"reviewers": ["a/x", "b/y"],
                                     "judge": "c/z", "harness": "reasonix"})
        self.assertEqual(mj.resolve_harness(str(self.tmp), None,
                                            global_path=self.global_cfg),
                         "reasonix")

    def test_harness_cli_overrides_config(self):
        self.write(self.global_cfg, {"reviewers": ["a/x", "b/y"],
                                     "judge": "c/z", "harness": "reasonix"})
        self.assertEqual(mj.resolve_harness(str(self.tmp), "codex",
                                            global_path=self.global_cfg),
                         "codex")


class ParseOutputTest(unittest.TestCase):
    def test_codex_parse_text_parts(self):
        stream = (
            '{"type":"turn.completed","usage":{}}\n'
            '{"type":"item.completed","item":{"content":[{"type":"text","text":"Один"}]}}\n'
            '{"type":"item.completed","item":{"content":[{"type":"text","text":"два"}]}}\n'
        )
        self.assertEqual(mj.parse_codex_output(stream), "Один\nдва")

    def test_codex_parse_string_content(self):
        stream = '{"type":"item.completed","item":{"content":"просто текст"}}\n'
        self.assertEqual(mj.parse_codex_output(stream), "просто текст")

    def test_codex_parse_empty(self):
        self.assertEqual(mj.parse_codex_output(""), "(пусто)")
        self.assertEqual(mj.parse_codex_output("not json at all"), "(пусто)")


class ParseJudgeQuestionsTest(unittest.TestCase):
    REVIEWERS = ["a/x", "b/y", "c/z"]

    def test_valid_questions(self):
        text = ('{"questions": [{"model": "a/x", "question": "проверь X?"},'
                ' {"model": "b/y", "question": "а что с Y?"}]}')
        qs, ok = mj.parse_judge_questions(text, self.REVIEWERS)
        self.assertTrue(ok)
        self.assertEqual(len(qs), 2)
        self.assertEqual(qs[0], {"model": "a/x", "question": "проверь X?"})

    def test_empty_questions(self):
        qs, ok = mj.parse_judge_questions('{"questions": []}', self.REVIEWERS)
        self.assertTrue(ok)
        self.assertEqual(qs, [])

    def test_garbage_not_json(self):
        qs, ok = mj.parse_judge_questions("никакого json тут нет", self.REVIEWERS)
        self.assertFalse(ok)
        self.assertEqual(qs, [])

    def test_unknown_model_dropped(self):
        text = ('{"questions": [{"model": "hacker/evil", "question": "?"},'
                ' {"model": "a/x", "question": "ок"}]}')
        qs, ok = mj.parse_judge_questions(text, self.REVIEWERS)
        self.assertTrue(ok)
        self.assertEqual(qs, [{"model": "a/x", "question": "ок"}])

    def test_markdown_wrapped_json(self):
        text = 'Вот вопросы:\n```json\n{"questions": [{"model": "a/x", "question": "q?"}]}\n```'
        qs, ok = mj.parse_judge_questions(text, self.REVIEWERS)
        self.assertTrue(ok)
        self.assertEqual(len(qs), 1)

    def test_empty_question_skipped(self):
        text = '{"questions": [{"model": "a/x", "question": "  "}]}'
        qs, ok = mj.parse_judge_questions(text, self.REVIEWERS)
        self.assertTrue(ok)
        self.assertEqual(qs, [])

    def test_braces_inside_question(self):
        text = ('{"questions": [{"model": "a/x", '
                '"question": "проверь формат {\\"issues\\": []}"}]}')
        qs, ok = mj.parse_judge_questions(text, self.REVIEWERS)
        self.assertTrue(ok)
        self.assertEqual(len(qs), 1)


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
