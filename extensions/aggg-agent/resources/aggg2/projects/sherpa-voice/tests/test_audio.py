#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.




# Принадлежит и разработано: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, новая — ещё лучше.
"""Тест аудио-callback: параметр звуковой библиотеки не должен затенять
модуль time (был баг: AttributeError 'PaStreamCallbackTimeInfo' has no
field 'time' — параметр `time` перекрывал импортированный модуль).

Запуск (из корня проекта):
    ./venv/bin/python -m unittest discover -s tests -t .
"""
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

import time
import unittest
from unittest import mock

import numpy as np

import audio


class AudioCallbackTest(unittest.TestCase):
    def test_callback_uses_time_module_not_shadowed_param(self):
        captured = {}

        class FakeStream:
            def __init__(self):
                self.started = False

            def start(self):
                self.started = True

            def close(self):
                pass

        def fake_open_microphone(callback, device=None):
            captured["callback"] = callback
            return FakeStream()

        with mock.patch.object(audio, "open_microphone",
                               fake_open_microphone), \
             mock.patch.object(audio, "RECORD_RATE", 16000), \
             mock.patch.object(audio, "FIRST_DATA_TIMEOUT", 0.01):
            result = audio.record_until_enter(device=None)

        self.assertIsNone(result)  # данные не пришли — честный отказ
        cb = captured["callback"]
        # фейковые аргументы PortAudio: time — объект cdata-подобный
        indata = np.zeros((1600, 1), dtype=np.float32)
        cb(indata, 1600, mock.Mock(), None)
        # callback не упал — значит time.time() работает, а не атрибут cdata
        self.assertGreater(time.time(), 0)


if __name__ == "__main__":
    unittest.main()

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
