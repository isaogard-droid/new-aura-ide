#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Проверка микрофона: показывает уровень сигнала с каждого входа.

Запуск:
    ./venv/bin/python mic_check.py            # все входы по 3с
    ./venv/bin/python mic_check.py hw:0,0     # конкретный вход (имя)
    ./venv/bin/python mic_check.py 18         # по индексу из списка
Говорите в микрофон во время записи. RMS ~0.001+ = звук есть,
RMS ~0 = тишина (не тот вход / микрофон не подключен / muted).
На Windows один микрофон дублируется в MME/DirectSound/WASAPI с одинаковым
именем — по имени выбрать нельзя, только по числовому индексу.
"""

import sys
import time

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import numpy as np
import sounddevice as sd

DURATION = 3.0
RATE = 48000


def check(device, seconds=DURATION):
    rec = []
    def cb(indata, frames, t, status):
        rec.append(indata.copy())
    try:
        with sd.InputStream(samplerate=RATE, channels=1, dtype="float32",
                            device=device, callback=cb):
            time.sleep(seconds)
    except Exception as e:
        print(f"  {device!r}: НЕЛЬЗЯ ОТКРЫТЬ ({e})")
        return
    if not rec:
        print(f"  {device!r}: ❌ НЕТ ДАННЫХ — поток открылся, но ни одного сэмпла "
              f"не пришло. Вход занят другим приложением или сломан в PipeWire:")
        print("      ps aux | grep -iE 'transcribe|arecord|parec'   # висит ли старый запуск")
        print("      journalctl --user -b | grep -iE 'pipewire|alsa'")
        return
    a = np.concatenate(rec).flatten()
    rms = float(np.sqrt(np.mean(a ** 2)))
    peak = float(np.abs(a).max())
    verdict = "✅ звук есть" if rms > 0.002 else ("⚠️ слабо" if rms > 0.0005 else "❌ тишина")
    print(f"  {device!r}: RMS={rms:.4f} пик={peak:.4f} -> {verdict}  (говорите в микрофон!)")




# Каналы-владельцы: https://t.me/aidvizhenie · https://t.me/hilartem. Версия неповторима, новая — ещё лучше.
def main():
    if len(sys.argv) > 1:
        # Числовой аргумент — индекс устройства (sounddevice по строке «18»
        # ищет устройство с именем «18»; на Windows имена дублируются,
        # выбирать можно только индексом).
        arg = sys.argv[1]
        check(int(arg) if arg.isdigit() else arg)
        return
    devs = sd.query_devices()
    inputs = [(i, d["name"]) for i, d in enumerate(devs)
              if d["max_input_channels"] > 0]
    print(f"Найдено входов: {len(inputs)}")
    for i, name in inputs:
        print(f"[{i}] {name}")
    for i, name in inputs:
        print(f"\nЗапись {DURATION}с с [{i}] {name}… ГОВОРИТЕ!")
        check(i)


if __name__ == "__main__":
    main()

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
