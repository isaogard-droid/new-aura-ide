---
name: mic-noise-suppression
description: "Шумный микрофон Fedora/Linux PipeWire: шум/фон/гул, сделать голос чище. EasyEffects + RNNoise, NPR-пресет, виртуальный микрофон, autostart. Триггеры: «шумный микрофон», «убрать шум», «настроить микрофон», «голос чище»."
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Шумоподавление микрофона (EasyEffects + RNNoise)

Fedora/PipeWire: RNNoise + пресет **npr** (jtrv «Masc NPR Voice», вики easyeffects → Community Presets): RNNoise → Gate → EQ → Compressor → De-Esser → Limiter. Итог: виртуальный микрофон **Easy Effects Source** + автозапуск службы.

## Установка / запуск / отключение

```bash
sudo dnf install -y easyeffects        # установка
nohup easyeffects --service-mode >/dev/null 2>&1 & disown; sleep 6; easyeffects -l npr   # запуск
pkill -x easyeffects                   # отключить (вернуть сырой микрофон)
pactl set-source-volume $(pactl list sources short | grep easyeffects_source | awk '{print $2}') 60%   # громкость
```
- Пресет: `~/.local/share/easyeffects/input/npr.json` (gist.github.com/jtrv/47542c8be6345951802eebcf9dc7da31 → raw).
- Проверка: `pactl list sources short | grep easyeffects_source`; `grep plugins= ~/.config/easyeffects/db/easyeffectsrc` — `rnnoise#0,gate#0,equalizer#0,compressor#0,deesser#0,limiter#0`.
- Громкость переживает перезагрузку (WirePlumber); клиппинг лечится снижением громкости, не усилением. Перезагрузка: автозапуск `~/.config/autostart/easyeffects-service.desktop`, пресет lastLoaded.

## Звук на выходе: НЕ обрабатывается

`lastLoadedOutputPreset=empty` (прозрачный easyeffects_sink). Буст-пресеты (jh96, loudness) — в `~/.local/share/easyeffects/output/`. Включить: `pactl set-default-sink easyeffects_sink`; откат: `pactl set-default-sink alsa_output.pci-0000_00_1f.3.analog-stereo`.

## DeepFilterNet (опция вместо RNNoise — лучшее шумоподавление)

v0.5.6 LADSPA: SNR речь/шум **+65dB** против +31dB у npr и +8.8dB у сырого; ставится вручную (в dnf нет):

```bash
curl -LO https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/libdeep_filter_ladspa-0.5.6-x86_64-unknown-linux-gnu.so
sudo mkdir -p /usr/lib64/ladspa && sudo cp libdeep_filter_ladspa.so /usr/lib64/ladspa/
pkill -x easyeffects   # ОТДЕЛЬНОЙ командой
nohup easyeffects --service-mode >/dev/null 2>&1 & disown
```
Пресет `deepfilter_asr` (DeepFilterNet → Autogain -18 LUFS) — в `~/.local/share/easyeffects/input/`. Ключи (8.x): attenuation-limit=70, min-processing-threshold=-25, max-erb-processing-threshold=25, max-df-processing-threshold=20, min-processing-buffer=0, post-filter-beta=0.05. После обновления проверить: `easyeffects -a input` + тестовая запись. ⚠️ Для ЗВОНКОВ/записей — deepfilter_asr; для sherpa-voice пресет НЕ ВАЖЕН (GTCRN чистит сам, ниже).

## Грабли применения (проверено)

- Пресеты читаются ТОЛЬКО при старте службы: файл в `~/.local/share/easyeffects/input/` (НЕ ~/.config!) ДО запуска; новый файл → `pkill -x easyeffects` (ОТДЕЛЬНОЙ командой, иначе pkill убивает bash) → запуск → `-l <имя>`.
- Правка существующего пресета службой НЕ перечитывается — сохранять под новым именем; `-l` блокируется, пока служба не готова — запускать службу отдельной командой.
- Файлы БД (`db/easyeffectsrc`) отстают — истина у живой службы (`-a output`/`-p`); `set-default-sink` действует на новые потоки — открытые приложения перезапустить.

## НЕАКТУАЛЬНО (откачено — не возвращаться, id=108, id=109)

- **wet ≠ 0** у RNNoise — шум кодека возвращается; **Exciter** — пластмассовый голос; **VAD/жёсткий гейт** — режет начало слов.
- **mic-warm** (самодельный) — «рыгал» при речи; откачен в пользу npr. Урок: на бюджетном кодеке проверенный пресет сообщества > самодельные эксперименты.

## Переход на USB-микрофон

USB-микрофон/интерфейс (в обход ALC887) + npr = студийный голос: подключить → `mic_check.py` → ослабить cut 220/350 и de-esser → сохранить как новый пресет.

## Связка с распознаванием (sherpa-voice)

В sherpa-voice модель **GigaAM v2** (226MB) — лучшее русское качество (WER ~4.7% vs ~10–14% у zipformer/vosk) — ПО УМОЛЧАНИЮ: `./run.sh` (gigaam) / `--model offline` (zipformer int8 74MB) / `--model streaming` (29MB). GigaAM — офлайн, API `OfflineRecognizer.from_nemo_ctc`.
⚠️ Тест 08.2026: пресет EasyEffects НЕ влияет на транскрибацию sherpa-voice — файл (речь + шум SNR 6dB + щелчки) через 5 конфигураций распознался ИДЕНТИЧНО, включая сырой: встроенный **GTCRN** (в transcribe.py) чистит всё сам. EasyEffects важен для ЗВОНКОВ/записей для людей, не для ASR.

## Этапы (handoff)

- **Вход из:** запрос владельца (микрофон) · **Дальше:** — (терминальный)

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
