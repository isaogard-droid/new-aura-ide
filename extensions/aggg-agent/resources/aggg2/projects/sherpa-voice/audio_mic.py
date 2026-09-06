#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.



# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
"""audio_mic — микрофон: find_input_device, record_until_enter, open_microphone."""
import os
import sys
import threading
import time

import numpy as np
import sounddevice as sd

from audio_constants import (
    FIRST_DATA_TIMEOUT,
    MAX_RECORD_SEC,
    MIN_RECORD_SEC,
    OPEN_TIMEOUT,
    RECORD_RATE,
    SILENCE_RMS,
)
from transcribe import STOP_FLAG


def find_input_device(preferred="auto"):
    """Выбирает входное устройство (та же логика, что в groq-voice).
    На Windows имён ALSA нет — возвращаем None (дефолтный вход WASAPI),
    явное устройство задаётся через --device по имени.
    ВАЖНО: распознавание работает на 16 кГц, а hw:* (ALSA-железо, напр.
    ALC887) часто поддерживает только 48 кГц — поток не открывается.
    Приоритет: дефолтный вход PipeWire ('default' — пересэмплит под любую
    частоту; при выбранном Easy Effects Source это чистый микрофон с
    шумоподавлением) → sysdefault → hw:* как последний fallback."""
    if preferred != "auto":
        return preferred
    if os.name == "nt":
        return None
    try:
        devs = sd.query_devices()
    except Exception:
        return None
    inputs = [(i, d["name"]) for i, d in enumerate(devs)
              if d["max_input_channels"] > 0]
    for name in ("default", "pipewire"):
        for _, n in inputs:
            if n == name:
                return n
    for _, n in inputs:
        if "sysdefault" in n:
            return n
    for _, n in inputs:
        if "hw:" in n:
            return n


def record_until_enter(device=None, background=False, silence_stop=0.0):
    """Пишет с микрофона, пока не нажат Enter (как в groq-voice).

    silence_stop — секунды тишины, после которых запись останавливается сама
    (как диктофон). Работает в фоновом режиме (--once, без окна); в обычном
    режиме стоп — всегда Enter (push-to-talk). 0 — отключить автостоп."""
    audio = []
    stop_indicator = threading.Event()
    total_samples = 0
    last_rms = 0.0
    last_sound_ts = time.time()

    def callback(indata, frames, t, status):
        nonlocal total_samples, last_rms, last_sound_ts
        total_samples += len(indata)
        last_rms = float(np.sqrt(np.mean(indata ** 2)))
        if last_rms > SILENCE_RMS:
            last_sound_ts = time.time()
        audio.append(indata.copy())

    def indicator():
        while not stop_indicator.is_set():
            secs = total_samples / RECORD_RATE
            bar = "█" * min(int(last_rms * 40), 20)
            sys.stdout.write(f"\r[🔴] {secs:5.1f}с · уровень {last_rms:0.3f} {bar:<20} "
                             f"(Enter — стоп, Ctrl+C — выход)   ")
            sys.stdout.flush()
            stop_indicator.wait(0.2)
        sys.stdout.write("\r" + " " * 70 + "\r")
        sys.stdout.flush()

    stream = _audio.open_microphone(callback, device=device)
    # ВАЖНО: конструктор sd.InputStream() не запускает поток — без start()
    # callback вообще не вызывается (запись «молча» пустая). Это был главный
    # баг «не записывает» (см. README, «Грабли»).
    stream.start()
    print("[🔴] Запись… (Enter — остановить, Ctrl+C — выход)")

    # Страховка от «молчаливого» отказа: поток открылся, но данные не идут
    # вообще (типично, когда вход занят или сломан в PipeWire).
    deadline = time.time() + FIRST_DATA_TIMEOUT
    while not audio and time.time() < deadline:
        time.sleep(0.1)
    if not audio:
        stream.close()
        print("[✗] Микрофон не отдаёт данные — вход занят другим приложением или")
        print("    PipeWire не может его открыть. Попробуйте:")
        print("    kill $(pgrep -f transcribe.py)   # если висит прошлый запуск")
        print("    journalctl --user -b | grep -iE 'pipewire|alsa'")
        return None

    th = None
    if sys.stdout.isatty():
        th = threading.Thread(target=indicator, daemon=True)
        th.start()
    try:
        if background:
            # Фоновый режим: стоп по STOP_FLAG (второе нажатие хоткея),
            # по таймауту MAX_RECORD_SEC или по тишине (silence_stop).
            # stdin не читаем.
            while True:
                if os.path.exists(STOP_FLAG):
                    break
                if total_samples / RECORD_RATE >= MAX_RECORD_SEC:
                    break
                if silence_stop > 0 and time.time() - last_sound_ts > silence_stop:
                    print(f"\n[i] Тишина {silence_stop:.0f}с — останавливаю запись.")
                    break
                time.sleep(0.1)
        else:
            while True:
                try:
                    input()
                except EOFError:
                    raise
                if not audio:
                    continue
                seconds = total_samples / RECORD_RATE
                if seconds < MIN_RECORD_SEC:
                    if th:
                        sys.stdout.write("\r" + " " * 70 + "\r")
                        sys.stdout.flush()
                    print(f"[i] Запись {seconds:.1f}с — похоже на случайный Enter, "
                          f"продолжаю (Enter — стоп).")
                    continue
                break
    except KeyboardInterrupt:
        print("\nВыход.")
        return None
    except EOFError:
        print("\nstdin закрыт — выход.")
        return None
    finally:
        stop_indicator.set()
        try:
            stream.stop()
        finally:
            stream.close()

    if not audio:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(audio).flatten()



def _open_stream(callback, device=None, timeout=OPEN_TIMEOUT):
    """Открывает микрофон в отдельном потоке: если устройство занято,
    PortAudio может висеть на open бесконечно — таймаут превращает это
    в понятную ошибку вместо «зависшего» скрипта."""
    result = {}

    def worker():
        try:
            result["stream"] = sd.InputStream(samplerate=RECORD_RATE, channels=1,
                                               dtype="float32", callback=callback,
                                               device=device)
        except Exception as e:
            result["error"] = e

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout)
    if "stream" in result:
        return result["stream"]
    if "error" in result:
        raise result["error"]
    raise RuntimeError(
        f"микрофон не отвечает за {timeout:.0f}с — устройство занято другим "
        f"приложением или PipeWire не может открыть вход. Проверьте:\n"
        f"  ps aux | grep -iE 'transcribe|arecord|parec'   # висит ли старый запуск\n"
        f"  journalctl --user -b | grep -iE 'pipewire|alsa'")




# Ошибки конфигурации устройства: повтором не лечатся (неверное имя в
# MIC_DEVICE/--device или дубль устройства на Windows). Для них — сразу
# понятное сообщение с подсказками, без ретраев и raw traceback.
DEVICE_CONFIG_ERRS = ("No input device matching", "Multiple input devices found")


def _device_error(e, device):
    return (f"устройство захвата не найдено: {device!r} ({e}).\n"
            f"Список устройств: --list-devices; закрепить вход: "
            f"--device \"<имя из списка>\".\n"
            f"Если имя задано в .env (MIC_DEVICE) — оно могло остаться с "
            f"другой машины: очистите строку, тогда auto выберет системный вход.")


def open_microphone(callback, device=None, attempts=3, wait_s=1.5):
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            return _open_stream(callback, device=device)
        except Exception as e:
            last_err = e
            if any(m in str(e) for m in DEVICE_CONFIG_ERRS):
                raise ValueError(_device_error(e, device)) from e
            # Честная причина вместо догадки «занят»: ошибка PortAudio/ALSA
            # бывает и без занятого устройства (первый open после простоя),
            # а повторная попытка часто проходит.
            print(f"[i] Микрофон не открылся ({attempt}/{attempts}): {e} — жду {wait_s}с…")
            time.sleep(wait_s)
    raise last_err


import audio as _audio  # noqa: E402 — форвардеры (патчи-совместимость)

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
