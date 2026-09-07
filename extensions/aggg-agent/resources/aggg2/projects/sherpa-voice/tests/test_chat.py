#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""Юнит-тесты чат-логики: эхо-детект _is_echo (повтор ответа DeepSeek).

Запуск (из корня проекта):
    ./venv/bin/python -m unittest discover -s tests -t .
"""
import os
import unittest
from unittest import mock

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import transcribe
import ui_utils


class EchoDetectTest(unittest.TestCase):
    def test_exact_echo(self):
        self.assertTrue(transcribe._is_echo("Привет привет", "привет привет"))

    def test_echo_case_and_whitespace(self):
        self.assertTrue(transcribe._is_echo("Привет,  привет!", "привет привет"))

    def test_echo_extended_tail(self):
        self.assertTrue(transcribe._is_echo("привет привет привет",
                                            "привет привет"))

    def test_echo_number_word(self):
        self.assertTrue(transcribe._is_echo("Два.", "два"))
        self.assertTrue(transcribe._is_echo("25", "25"))

    def test_echo_prompt_inside_short_answer(self):
        self.assertTrue(transcribe._is_echo("нужно сделать x?",
                                            "нужно сделать x"))

    def test_echo_marked_prefixed(self):
        marked = "Транскрипт голосовой записи: «нет привет привет»"
        self.assertTrue(transcribe._is_echo(marked, marked))
        self.assertTrue(transcribe._is_echo(marked + " Ответ:", marked))

    def test_not_echo_marked_with_real_answer(self):
        marked = "Транскрипт голосовой записи: «нет привет привет»"
        answer = (marked + "\n\nПривет! Давай разберёмся, что тебя "
                  "беспокоит в записи — расскажи подробнее.")
        self.assertFalse(transcribe._is_echo(answer, marked))

    def test_not_echo_real_answer(self):
        self.assertFalse(transcribe._is_echo("Привет! Отлично, как сам?",
                                             "привет привет"))

    def test_not_echo_yes_question(self):
        self.assertFalse(transcribe._is_echo("Да.", "да?"))

    def test_not_echo_developed_reply(self):
        self.assertFalse(transcribe._is_echo("привет привет, как дела?",
                                             "привет привет"))

    def test_not_echo_long_content_answer(self):
        prompt = ("Напиши план починки эхо-бага в голосовом ассистенте: "
                  "детект повтора, ретрай, тесты, чек-лист проверки")
        answer = ("План: 1) детект эхо через нормализацию и сходство строк; "
                  "2) при повторе — переспрос с требованием содержательного "
                  "ответа; 3) покрыть юнит-тестами; 4) прогнать lint и тесты.")
        self.assertFalse(transcribe._is_echo(answer, prompt))

    def test_empty_inputs(self):
        self.assertFalse(transcribe._is_echo(None, "промпт"))
        self.assertFalse(transcribe._is_echo("ответ", ""))
        self.assertFalse(transcribe._is_echo("", ""))


class PolishSanitizeTest(unittest.TestCase):
    def test_model_answered_instead_of_editing(self):
        raw = "сколько тебе лет?"
        bad = ("Мне как программе нет возраста в привычном смысле — я не "
               "человек и не старею. Я существую в виде кода и данных, "
               "которые обновляются и совершенствуются разработчиками.")
        self.assertEqual(transcribe._sanitize_polish(raw, bad), raw)

    def test_normal_edit_kept(self):
        self.assertEqual(transcribe._sanitize_polish("привет привет",
                                                     "Привет, привет!"),
                         "Привет, привет!")

    def test_shorter_polish_kept(self):
        self.assertEqual(transcribe._sanitize_polish("твенти файв", "25"),
                         "25")

    def test_empty_polish_returns_raw(self):
        self.assertEqual(transcribe._sanitize_polish("текст", ""), "текст")
        self.assertEqual(transcribe._sanitize_polish("текст", None), "текст")

    def test_long_raw_legit_edit_kept(self):
        raw = "нужно сделать x и проверить y " * 10
        polished = raw + " с тестами"
        self.assertEqual(transcribe._sanitize_polish(raw, polished), polished)

    def test_verbose_but_plausible_edit_kept(self):
        raw = "сделай план починки бага с эхом"
        polished = ("Сделай план починки бага с эхом: детект повтора, "
                    "ретрай, тесты, чек-лист проверки.")
        self.assertEqual(transcribe._sanitize_polish(raw, polished), polished)


class PolishExamplesTest(unittest.TestCase):
    def _sess(self, messages):
        from types import SimpleNamespace
        return SimpleNamespace(messages=messages)

    def test_takes_edit_pairs_newest_first(self):
        sess = self._sess([
            {"role": "user", "content": "привет привет"},
            {"role": "assistant", "content": "Привет, привет!",
             "kind": "polish"},
            {"role": "user", "content": "твенти файв"},
            {"role": "assistant", "content": "25", "kind": "polish"},
            {"role": "user", "content": "кто ты"},
            {"role": "assistant", "content": "Привет, кто ты?",
             "kind": "polish"},
        ])
        out = transcribe._polish_examples(sess)
        self.assertIn("Было: кто ты\nСтало: Привет, кто ты?", out)
        self.assertIn("Было: твенти файв\nСтало: 25", out)
        self.assertLess(out.index("кто ты"), out.index("твенти файв"))

    def test_skips_model_answers_without_kind(self):
        sess = self._sess([
            {"role": "user", "content": "сколько тебе лет?"},
            {"role": "assistant", "content": "Мне как программе нет возраста "
             "в привычном смысле — я не человек и не старею."},
            {"role": "user", "content": "привет"},
            {"role": "assistant", "content": "Привет!", "kind": "polish"},
        ])
        out = transcribe._polish_examples(sess)
        self.assertNotIn("сколько тебе лет?", out)
        self.assertIn("Было: привет\nСтало: Привет!", out)

    def test_skips_identical(self):
        sess = self._sess([
            {"role": "user", "content": "привет"},
            {"role": "assistant", "content": "привет", "kind": "polish"},
        ])
        self.assertEqual(transcribe._polish_examples(sess), "")

    def test_limit_and_truncation(self):
        msgs = []
        for i in range(5):
            msgs.append({"role": "user", "content": f"текст {i}"})
            msgs.append({"role": "assistant", "content": f"Текст {i}.",
                         "kind": "polish"})
        out = transcribe._polish_examples(self._sess(msgs))
        self.assertEqual(out.count("Было:"), 3)

    def test_empty(self):
        self.assertEqual(transcribe._polish_examples(self._sess([])), "")
        self.assertEqual(transcribe._polish_examples(object()), "")


class VocabTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        patcher = mock.patch.object(
            ui_utils, "VOCAB_FILE",
            os.path.join(self.tmp, "vocab.txt"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_default_vocab_created(self):
        pairs = transcribe._vocab_load()
        self.assertTrue(pairs)
        self.assertIn(("опен код", "OpenCode"), pairs)
        self.assertIn(("клоуд код", "Claude Code"), pairs)
        self.assertTrue(os.path.isfile(ui_utils.VOCAB_FILE))

    def test_load_supported_separators(self):
        with open(ui_utils.VOCAB_FILE, "w", encoding="utf-8") as f:
            f.write("# комментарий\nопен код → OpenCode\n")
            f.write("ди би тулс -> DB-Tools\nмусор без разделителя\n")
        pairs = transcribe._vocab_load()
        self.assertIn(("опен код", "OpenCode"), pairs)
        self.assertIn(("ди би тулс", "DB-Tools"), pairs)
        self.assertEqual(len(pairs), 2)

    def test_save_roundtrip(self):
        transcribe._vocab_save([("фуу бар", "FooBar"), ("а б", "AB")])
        self.assertEqual(transcribe._vocab_load(),
                         [("фуу бар", "FooBar"), ("а б", "AB")])

    def test_vocab_text_format(self):
        text = transcribe._vocab_text()
        self.assertIn("опен код → OpenCode", text)

    def test_polish_request_includes_vocab(self):
        req = transcribe._polish_request("скажи про опен код")
        self.assertIn("Словарь терминов", req)
        self.assertIn("опен код → OpenCode", req)
        self.assertIn("Текст для правки:\nскажи про опен код", req)


class AskNoEchoIsolationTest(unittest.TestCase):
    """_ask_no_echo — одноразовая задача с ИЗОЛИРОВАННЫМ контекстом (без
    истории сессии). С историей при низкой температуре DeepSeek «продолжает»
    последнее сообщение ассистента (приветствие из сессии) вместо результата
    — проверено живьём: «Задачи»/«Саммари» возвращали приветствие."""

    def test_summary_call_has_no_session_messages(self):
        calls = []
        with mock.patch(
                "deepseek_ai.ask",
                side_effect=lambda *a, **kw: calls.append(kw)
                or ("Реальный пересказ", None)):
            out, err = transcribe._ask_no_echo(
                "summary", "Транскрипт голосовой записи: «надо разобраться»")
        self.assertIsNone(err)
        self.assertEqual(out, "Реальный пересказ")
        self.assertEqual(len(calls), 1)
        self.assertNotIn("messages", calls[0])

    def test_echo_retry_also_without_history(self):
        seq = [("привет привет", None), ("Итог: купить молоко.", None)]
        calls = []
        with mock.patch(
                "deepseek_ai.ask",
                side_effect=lambda *a, **kw: calls.append(kw)
                or seq.pop(0)):
            out, err = transcribe._ask_no_echo(
                "action_items", "привет привет", echo_ref="привет привет",
                temperature=0)
        self.assertEqual(out, "Итог: купить молоко.")
        self.assertEqual(len(calls), 2)
        for kw in calls:
            self.assertNotIn("messages", kw)


if __name__ == "__main__":
    unittest.main()

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
