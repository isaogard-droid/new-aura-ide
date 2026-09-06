#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.



# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
"""audio_constants — константы аудио-слоя: частоты, таймауты, MODELS, пути hotwords."""
import os

RECORD_RATE = 48000          # родная частота карты (ALSA не отдаёт 16k для ALC887)
MODEL_RATE = 16000           # sherpa-onnx ожидает 16kHz
MIN_RECORD_SEC = 0.5         # запись короче — считаем стоп случайным (двойной Enter)

# Шумоподавление перед распознаванием: GTCRN (523KB, 16kHz, RTF~0.06).
# Модель скачивается отдельно (speech-enhancement-models) — без неё всё
# работает как раньше, с честным сообщением.
DENOISER_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "models", "denoiser", "gtcrn_simple.onnx")

MAX_RECORD_SEC = 30
SILENCE_RMS = 0.01          # ниже этого уровня звука считаем «тишиной» (автостоп)

OPEN_TIMEOUT = 5.0           # максимум на открытие потока
FIRST_DATA_TIMEOUT = 2.0     # ждать первый callback после открытия

# Модели (int8): офлайн 74MB — лучшее качество; стриминговая 29MB — быстрее
MODELS = {
    "offline": {
        "dir": "sherpa-onnx-zipformer-ru-int8-2025-04-20",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-ru-int8-2025-04-20.tar.bz2",
        "size": 74,
    },
    "streaming": {
        "dir": "sherpa-onnx-streaming-zipformer-small-ru-vosk-int8-2025-08-16",
        "url": "https://huggingface.co/csukuangfj/sherpa-onnx-streaming-zipformer-small-ru-vosk-int8-2025-08-16/resolve/main/",
        "size": 29,
    },
    "gigaam": {
        # Лучшее качество русского (WER ~4.4-4.7%, бенчмарк onnx-asr):
        # официальная NeMo transducer GigaAM v3 от k2-fsa. Transducer —
        # поддерживает hotwords (contextual biasing), в отличие от старой
        # CTC v2: редкие слова («црг», «гигаам») распознаются по словарю.
        # Не стриминговая: одна фраза = одно распознавание после записи.
        "dir": "sherpa-onnx-nemo-transducer-giga-am-v3-russian-2025-12-16",
        "url": "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-transducer-giga-am-v3-russian-2025-12-16/resolve/main/",
        "size": 230,
        "files": ["encoder.int8.onnx", "decoder.onnx", "joiner.onnx",
                  "tokens.txt"],
    },
}

# --- hotwords (contextual biasing) — только transducer-модели ---
HOTWORDS_CACHE = os.path.expanduser("~/.cache/sherpa-voice")
HOTWORDS_BASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "hotwords_base.txt")

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
