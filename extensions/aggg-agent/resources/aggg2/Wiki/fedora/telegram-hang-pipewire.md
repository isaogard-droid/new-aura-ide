---
type: Howto
title: "telegram-hang-pipewire"
description: "Telegram Desktop завис после пересоздания аудио-устройства (PipeWire/EasyEffects): процесс жив, окно не рисует, новые запуски ждут ответа от зависшего инстанса вечно. Симптомы, диагноз по логам, лечение kill + запуск заново."
date: 2026-08-17
tags: [fedora, telegram, pipewire, easyeffects, audio, debug]
status: stable
---

# Telegram Desktop завис на аудио — новые запуски «не работают»

Поймано живьём 17.08.2026 на Fedora 44 (telegram-desktop 7.0.6). Инцидент разобран по протоколу debug-incident-protocol: факты → лог → корень → один фикс.

## Симптомы

- Иконка Telegram не открывает окно: кликаешь — ничего не происходит.
- В `ps` висит **два** процесса `/usr/bin/Telegram`: старый (часы, 1.4 ГБ RAM) и новый (только что запущенный).
- В journalctl: `dbus-broker-launch: Activation request for 'org.telegram.desktop' failed`.

## Корень

1. Главный инстанс **завис**: его лог (`~/.local/share/TelegramDesktop/log.txt`) обрывается на
   `Audio Info: recreating audio device...` / `Closing audio playback device.` — сразу после
   пересоздания аудио-устройства (у нас — перезапуск PipeWire с виртуальными Easy Effects
   Sink/Source). UI-поток мёртв, но процесс жив, окно не рисует.
2. Telegram Desktop — **single-instance**: новый запуск подключается к зависшему через
   локальный сокет, шлёт «show command» и ждёт ответа. Зависший не отвечает →
   `log_start*.txt` обрывается на «Show command written, waiting response...» → окно не появляется.

Вывод: «не запускается» = симптом. Настоящий корень — зависший единственный инстанс,
который блокирует все новые запуски.

## Диагноз за минуту

```bash
ps aux | grep "[T]elegram"                          # сколько процессов, какой старый
head ~/.local/share/TelegramDesktop/log_start0.txt  # «waiting response...» = клиент зависшего инстанса
tail ~/.local/share/TelegramDesktop/log.txt         # обрыв на аудио = завис на пересоздании устройства
```

## Лечение

```bash
kill <PID старого> <PID нового>   # или pkill -f "[T]elegram"
/usr/bin/Telegram &                # один свежий запуск
```

Признак, что всё починилось: в новом логе `Socket connect error 0, starting server and app...`
(стал главным инстансом, а не клиентом зависшего).

## Профилактика

- Это грабли PipeWire: после рестарта аудио-сервера (EasyEffects autostart, смена устройств)
  Telegram может повеситься на пересоздании аудио-устройства. Лечится тем же kill + запуском.
- Системного фикса не найдено (рестарт аудио не откатывается из приложения).
