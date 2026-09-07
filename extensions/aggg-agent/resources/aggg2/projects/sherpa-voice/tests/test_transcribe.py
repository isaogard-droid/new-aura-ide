"""Тесты facade transcribe.py: parse_args и целостность re-export'ов.

transcribe.py — facade после разбиения монолита (ui_utils → store → publish →
chat): внешние импорты должны работать как раньше. Файл — поведенческий
хотспот (33 правки в git, аудит 15.08, research.db id=540) — стабилизируем
тестами: сломанный re-export = разрыв цепочки импортов, ловится здесь.
"""
import sys
import unittest
from unittest import mock

import transcribe


class ParseArgsTest(unittest.TestCase):
    """parse_args: дефолты и флаги (имя теста = спека)."""

    def _parse(self, argv):
        with mock.patch.object(sys, "argv", ["transcribe.py"] + argv):
            return transcribe.parse_args()

    def test_defaults_gigaam_auto_2threads(self):
        a = self._parse([])
        self.assertEqual(a.model, "gigaam")
        self.assertEqual(a.device, "auto")
        self.assertEqual(a.threads, 2)
        self.assertEqual(a.silence, 0.0)
        self.assertFalse(a.once)

    def test_flags_streaming_file_once(self):
        a = self._parse(["--streaming", "--file", "x.wav", "--once"])
        self.assertTrue(a.streaming)
        self.assertEqual(a.file, "x.wav")
        self.assertTrue(a.once)

    def test_flags_list_devices_dont_load_model(self):
        a = self._parse(["--list-devices"])
        self.assertTrue(a.list_devices)


class FacadeReexportsTest(unittest.TestCase):
    """Имена, на которые опираются telegram.py/audio.py/тесты, живы."""

    def test_parse_args_main_exported(self):
        self.assertTrue(callable(transcribe.parse_args))
        self.assertTrue(callable(transcribe.main))

    def test_chat_reexports(self):
        for name in ("COMMANDS", "HELP_TEXT", "SLASH", "_append_history",
                     "deepseek_menu"):
            self.assertTrue(hasattr(transcribe, name), f"нет re-export: {name}")

    def test_store_publish_reexports(self):
        for name in ("publish_result", "_day_stats", "_session_context"):
            self.assertTrue(hasattr(transcribe, name), f"нет re-export: {name}")


if __name__ == "__main__":
    unittest.main()
