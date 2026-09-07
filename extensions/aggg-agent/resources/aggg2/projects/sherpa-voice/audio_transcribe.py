#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.



# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
"""audio_transcribe — распознавание: transcribe_offline, transcribe_streaming, denoise, read_wav."""
import os

import numpy as np
import sherpa_onnx
import soxr

from audio_constants import DENOISER_MODEL, MODEL_RATE


def transcribe_offline(recognizer, audio):
    """Распознаёт float32-аудио, уже приведённое к 16 кГц (MODEL_RATE).
    Единый формат пайплайна: конвертация 48к→16к делается один раз на
    входе (микрофон), а read_wav уже отдаёт 16к. Раньше функция сама
    считала вход 48-килогерцевым и ресэмплила повторно — голосовые из
    Telegram и --file превращались в ускоренный в 3 раза писк и
    распознавались пусто («Пустое распознавание — не отправляю»)."""
    audio16 = denoise(audio.astype(np.float32))
    stream = recognizer.create_stream()
    stream.accept_waveform(MODEL_RATE, audio16)
    recognizer.decode_stream(stream)
    return stream.result.text.strip()



def transcribe_streaming(recognizer, audio):
    """Распознаёт float32-аудио в 16 кГц (см. transcribe_offline)."""
    audio16 = denoise(audio.astype(np.float32))
    stream = recognizer.create_stream()
    stream.accept_waveform(MODEL_RATE, audio16)
    # хвост тишины, чтобы модель дочитала конец фразы
    tail = np.zeros(int(0.66 * MODEL_RATE), dtype=np.float32)
    stream.accept_waveform(MODEL_RATE, tail)
    stream.input_finished()
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)
    return recognizer.get_result(stream).strip()



_DENOISER = None
_DENOISER_WARNED = False

def denoise(audio16):
    """Чистит аудио (16kHz float32) от шума через GTCRN.
    Без модели — возвращает как есть (один раз честно предупредив)."""
    global _DENOISER, _DENOISER_WARNED
    if _DENOISER is None:
        if not os.path.isfile(DENOISER_MODEL):
            if not _DENOISER_WARNED:
                _DENOISER_WARNED = True
                print("[i] Шумодав не подключён: нет", DENOISER_MODEL)
            return audio16
        cfg = sherpa_onnx.OfflineSpeechDenoiserConfig(
            model=sherpa_onnx.OfflineSpeechDenoiserModelConfig(
                gtcrn=sherpa_onnx.OfflineSpeechDenoiserGtcrnModelConfig(
                    model=DENOISER_MODEL),
                num_threads=1))
        _DENOISER = sherpa_onnx.OfflineSpeechDenoiser(cfg)
        print("[✓] Шумодав GTCRN готов.")
    out = _DENOISER.run(audio16.astype(np.float32), MODEL_RATE)
    return np.asarray(out.samples, dtype=np.float32)


def read_wav(path):
    import wave
    with wave.open(path, "rb") as wf:
        rate = wf.getframerate()
        n = wf.getnframes()
        data = wf.readframes(n)
        ch = wf.getnchannels()
    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1)
    if rate != MODEL_RATE:
        audio = soxr.resample(audio, rate, MODEL_RATE)
    return audio

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
