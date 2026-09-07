#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.



# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
"""Аудио-слой: запись, микрофон, распознавание, шумодав, чтение wav.

Вынесено из transcribe.py (монолит >1200 строк). Импортирует из transcribe
только маркеры фонового режима (REC_MARKER/STOP_FLAG); transcribe импортирует
audio локально в main — циклического импорта на верхнем уровне нет.

Резка god-файла (624 строки) — карта «что где лежит»:
- audio_constants.py — константы: RECORD_RATE, MODEL_RATE, MODELS, пути hotwords;
- audio_hotwords.py — hotwords: _seed_hotwords_base, _bpe_vocab_path, _build_hotwords_file;
- audio_models.py — load_model: скачивание и сборка распознавателя;
- audio_mic.py — микрофон: find_input_device, record_until_enter, open_microphone;
- audio_transcribe.py — распознавание: transcribe_offline, transcribe_streaming,
  denoise, read_wav.

Импортёры не тронуты: публичные имена re-export здесь (facade).
"""

from audio_constants import (  # noqa: F401
    DENOISER_MODEL,
    FIRST_DATA_TIMEOUT,
    HOTWORDS_BASE,
    HOTWORDS_CACHE,
    MAX_RECORD_SEC,
    MIN_RECORD_SEC,
    MODEL_RATE,
    MODELS,
    OPEN_TIMEOUT,
    RECORD_RATE,
    SILENCE_RMS,
)
from audio_hotwords import (  # noqa: F401
    _bpe_vocab_path,
    _build_hotwords_file,
    _seed_hotwords_base,
)
from audio_mic import (  # noqa: F401
    DEVICE_CONFIG_ERRS,
    _device_error,
    _open_stream,
    find_input_device,
    open_microphone,
    record_until_enter,
)
from audio_models import load_model  # noqa: F401
from audio_transcribe import (  # noqa: F401
    _DENOISER,
    _DENOISER_WARNED,
    denoise,
    read_wav,
    transcribe_offline,
    transcribe_streaming,
)
from transcribe import STOP_FLAG  # noqa: F401

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
