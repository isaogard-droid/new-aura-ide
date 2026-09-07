#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты Telegram-логики telegram.py — без сети и без ключа.

Запуск (из корня проекта, через venv — там numpy/sounddevice):
    ./venv/bin/python -m unittest discover -s tests -t .
"""

import unittest
from unittest import mock

import telegram


class TgSendTextTest(unittest.TestCase):
    def setUp(self):
        self.enabled, self.token, self.chat = True, "tok", "42"
        patcher = mock.patch.object(telegram, "load_telegram",
                                    return_value=(self.enabled, self.token,
                                                  self.chat))
        self.load = patcher.start()
        self.addCleanup(patcher.stop)

    def test_disabled_skips_request(self):
        self.load.return_value = (False, "tok", "42")
        with mock.patch.object(telegram, "_tg_request") as req:
            ok, err = telegram.tg_send_text("hi")
        self.assertFalse(ok)
        self.assertIn("выключен", err)
        req.assert_not_called()

    def test_missing_chat_id_skips_request(self):
        self.load.return_value = (True, "tok", "")
        with mock.patch.object(telegram, "_tg_request") as req:
            ok, _ = telegram.tg_send_text("hi")
        self.assertFalse(ok)
        req.assert_not_called()

    def test_prefix_becomes_bold(self):
        with mock.patch.object(telegram, "_tg_request",
                               return_value=(True, None)) as req:
            ok, _ = telegram.tg_send_text("текст", "📝 Транскрипт")
        self.assertTrue(ok)
        payload = req.call_args.args[2]
        self.assertTrue(payload["text"].startswith("<b>Транскрипт</b>\n\n"))
        self.assertIn("parse_mode", payload)

    def test_long_text_split_into_4096_chunks(self):
        text = "а" * 9000
        with mock.patch.object(telegram, "_tg_request",
                               return_value=(True, None)) as req:
            ok, _ = telegram.tg_send_text(text)
        self.assertTrue(ok)
        self.assertEqual(req.call_count, 3)
        chunks = [c.args[2]["text"] for c in req.call_args_list]
        self.assertTrue(all(len(c) <= 4096 for c in chunks))
        self.assertEqual(sum(len(c) for c in chunks), 9000)

    def test_reply_markup_only_on_first_chunk(self):
        text = "а" * 9000
        markup = {"inline_keyboard": []}
        with mock.patch.object(telegram, "_tg_request",
                               return_value=(True, None)) as req:
            telegram.tg_send_text(text, reply_markup=markup)
        chunks = [c.args[2] for c in req.call_args_list]
        self.assertEqual(chunks[0]["reply_markup"], markup)
        self.assertNotIn("reply_markup", chunks[1])

    def test_parse_error_retries_without_parse_mode(self):
        answers = [iter([(False, "can't parse entities"), (True, None)])]
        def side(*a):
            return next(answers[0])
        with mock.patch.object(telegram, "_tg_request", side_effect=side) as req:
            ok, _ = telegram.tg_send_text("текст")
        self.assertTrue(ok)
        self.assertEqual(req.call_count, 2)
        self.assertNotIn("parse_mode", req.call_args_list[1].args[2])

    def test_request_failure_propagates(self):
        with mock.patch.object(telegram, "_tg_request",
                               return_value=(False, "boom")) as req:
            ok, err = telegram.tg_send_text("текст")
        self.assertFalse(ok)
        self.assertEqual(err, "boom")
        req.assert_called_once()


class TgSendRichTextTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(
            telegram, "load_telegram", return_value=(True, "tok", "42"))
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_too_long_falls_back(self):
        with mock.patch.object(telegram, "_tg_request") as req:
            ok, err = telegram.tg_send_rich_text("а" * 5000)
        self.assertFalse(ok)
        self.assertIn("слишком длинный", err)
        req.assert_not_called()

    def test_payload_blocks(self):
        with mock.patch.object(telegram, "_tg_request",
                               return_value=(True, None)) as req:
            ok, _ = telegram.tg_send_rich_text("текст")
        self.assertTrue(ok)
        payload = req.call_args.args[2]
        self.assertEqual(req.call_args.args[1], "sendRichMessage")
        blocks = payload["rich_message"]["blocks"]
        self.assertEqual(blocks[0]["type"], "heading")
        self.assertEqual(blocks[1]["type"], "pullquote")
        self.assertEqual(blocks[1]["text"], "текст")

    def test_disabled_skips_request(self):
        with mock.patch.object(telegram, "load_telegram",
                               return_value=(False, "tok", "42")), \
             mock.patch.object(telegram, "_tg_request") as req:
            ok, _ = telegram.tg_send_rich_text("текст")
        self.assertFalse(ok)
        req.assert_not_called()


class TgSendResultTest(unittest.TestCase):
    """_tg_send_result: транскрипт/промпт — документом с датой-временем,
    результаты действий — rich с фолбэком на plain."""

    def test_transcript_sent_as_document(self):
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(True, None)) as file, \
             mock.patch.object(telegram, "tg_send_rich_text") as rich:
            ok, _ = telegram._tg_send_result("текст", "📝 Транскрипт",
                                             reply_markup={"x": 1})
        self.assertTrue(ok)
        rich.assert_not_called()
        args, kwargs = file.call_args
        self.assertEqual(args[0], "текст")
        self.assertTrue(args[1].startswith("транскрипт_"))
        self.assertTrue(args[1].endswith(".txt"))
        self.assertEqual(kwargs["caption"], "Транскрипт")
        self.assertEqual(kwargs["reply_markup"], {"x": 1})

    def test_prompt_sent_as_document(self):
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(True, None)) as file, \
             mock.patch.object(telegram, "tg_send_rich_text") as rich:
            ok, _ = telegram._tg_send_result("промпт", "💬 Промпт")
        self.assertTrue(ok)
        rich.assert_not_called()
        self.assertTrue(file.call_args.args[1].startswith("промпт_"))

    def test_actions_sent_as_document(self):
        # ВСЕ результаты уходят файлом .txt с датой-временем (решение:
        # единый лог всех текстовых сущностей — задача/ответ/саммари/сводка)
        with mock.patch.object(telegram, "tg_send_rich_text",
                               return_value=(True, None)) as rich, \
             mock.patch.object(telegram, "tg_send_text") as plain, \
             mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(True, None)) as file:
            ok, _ = telegram._tg_send_result("ответ", "✅ Задачи")
        self.assertTrue(ok)
        rich.assert_not_called()
        plain.assert_not_called()
        self.assertTrue(file.call_args.args[1].startswith("задачи_"))

    def test_summary_sent_as_document(self):
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(True, None)) as file, \
             mock.patch.object(telegram, "tg_send_rich_text") as rich:
            ok, _ = telegram._tg_send_result("саммари", "📝 Саммари")
        self.assertTrue(ok)
        rich.assert_not_called()
        self.assertTrue(file.call_args.args[1].startswith("саммари_"))

    def test_file_failure_falls_back_to_plain(self):
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(False, "file: слишком длинный")) as file, \
             mock.patch.object(telegram, "tg_send_text",
                               return_value=(True, None)) as plain, \
             mock.patch.object(telegram, "tg_send_rich_text") as rich:
            ok, _ = telegram._tg_send_result("длинный" * 1000, "Саммари")
        self.assertTrue(ok)
        file.assert_called_once()
        plain.assert_called_once_with("длинный" * 1000, "Саммари",
                                      chat_id=None, reply_markup=None)
        rich.assert_not_called()

    def test_both_fail_propagates_error(self):
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(False, "file fail")), \
             mock.patch.object(telegram, "tg_send_text",
                               return_value=(False, "plain fail")) as plain:
            ok, err = telegram._tg_send_result("текст")
        self.assertFalse(ok)
        self.assertEqual(err, "plain fail")
        plain.assert_called_once()

    def test_title_from_prefix_bold_map(self):
        # все префиксы — файлы с kind в имени; без префикса — «результат»
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(True, None)) as file, \
             mock.patch.object(telegram, "tg_send_rich_text") as rich:
            telegram._tg_send_result("текст", "✅ Задачи")
        self.assertTrue(file.call_args.args[1].startswith("задачи_"))
        rich.assert_not_called()
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(True, None)) as file2, \
             mock.patch.object(telegram, "tg_send_rich_text") as rich2:
            telegram._tg_send_result("текст", None)
        self.assertTrue(file2.call_args.args[1].startswith("результат_"))
        rich2.assert_not_called()

    def test_footer_sent_as_file_with_timestamp(self):
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(True, None)) as file, \
             mock.patch.object(telegram, "tg_send_rich_text") as rich, \
             mock.patch.object(telegram, "tg_send_text") as plain:
            ok, _ = telegram._tg_send_result("основной", footer="приписка")
        self.assertTrue(ok)
        rich.assert_not_called()
        plain.assert_not_called()
        args = file.call_args.args
        # первый вызов — основной текст файлом «результат_…», второй — подмешка
        self.assertEqual(args[0], "приписка")
        self.assertTrue(args[1].startswith("подмешка_"))
        self.assertTrue(args[1].endswith(".txt"))
        self.assertEqual(file.call_count, 2)

    def test_footer_skipped_when_main_failed(self):
        with mock.patch.object(telegram, "tg_send_text_file",
                               return_value=(False, "file fail")) as file, \
             mock.patch.object(telegram, "tg_send_text",
                               return_value=(False, "plain fail")) as plain:
            ok, _ = telegram._tg_send_result("основной", footer="приписка")
        self.assertFalse(ok)
        # файл слался один раз — для основного текста, футер не слали
        self.assertEqual(file.call_count, 1)
        self.assertEqual(plain.call_count, 1)


if __name__ == "__main__":
    unittest.main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
