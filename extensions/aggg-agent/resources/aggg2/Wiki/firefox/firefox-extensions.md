---
type: Howto
title: firefox-extensions
description: "Проверенный набор расширений Firefox для буста и защиты зрения: YourCodecs (YouTube H.264, когда GPU не умеет VP9/AV1), uBlock Origin, Dark Background and Light Text, тема RedDarkM"
date: 2026-08-16
tags: [skill-notes, firefox, extensions, video, codecs]
source: skills/firefox-extensions/ (перенесено 16.08.2026)
status: stable
---

# firefox-extensions — скилл-на-полке (Howto)

Перенесено из `skills/firefox-extensions/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже — дословно.

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->


# Firefox extensions: boost + eye protection bundle

Проверено 2026-08-10 (машина: Fedora 44, NVIDIA GTX 1660 SUPER, RPM Firefox 153).
Два назначения: **буст** (скорость, меньше CPU/RAM) и **зрение** (тёмный режим).

## Установка — ТОЛЬКО кнопкой на AMO (GOTCHA)

Самый надёжный путь — кнопка «Add to Firefox» на addons.mozilla.org
(юзер сам, или открыть страницу через `xdg-open`).

Что НЕ работает (проверено на Fedora 44, Firefox 153):
- **Sideload xpi в папку профиля** (`extensions/{id}.xpi`) — Firefox игнорирует,
  `extensions.json` не обновляется. Не тратить время.
- **policies.json** (`/usr/lib64/firefox/distribution/` или `/etc/firefox/policies/`,
  `ExtensionSettings` c `normal_installed`/`force_installed`) — не сработал.
- `firefox --install-extension` — флага нет в --help (не подтверждён).

## Набор (для буста и зрения)

### YourCodecs — буст видео (обязателен для NVIDIA без VP9/AV1)
- Что: форк h264ify (0.2.0, 2024, MIT), выборочно блокирует AVC/VP8/VP9/AV1
  на YouTube. Нужен, когда GPU не умеет VP9/AV1 (1660 SUPER: VP9/AV1 нет в
  NVDEC — проверено vainfo) — YouTube по умолчанию шлёт VP9, и Firefox
  декодирует его процессором → тормоза на стримах.
- Ссылка: https://addons.mozilla.org/en-US/firefox/addon/your-codecs/
- ID: `{08146168-5720-4ebb-b6cb-e85b4f9c5d45}`
- После установки — **Ctrl+F5** на YouTube (иначе старый формат держится).
- Грабли: заблокировать ВСЕ кодеки разом = «Ваш браузер не может воспроизвести
  видео» (так и задумано); для принудительного AV1 — VP9 и AV1 не блокировать.
- Не брать оригинальный h264ify (1.1.0, 2019, не обновляется) — YourCodecs
  свежее и гибче.

### uBlock Origin — буст (реклама/трекеры)
- Что: самый лёгкий эффективный блокировщик, 10.5M юзеров, recommended,
  1.73.0. Меньше рекламы/трекеров = меньше CPU, RAM, трафика — главный
  «буст» скорости браузера.
- Ссылка: https://addons.mozilla.org/ru/firefox/addon/ublock-origin/
- ID: `uBlock0@raymondhill.net`
- Уже установлен в профиле юзера (1.73.0) — не дублировать.

### Dark Background and Light Text — зрение (тёмный режим)
- Что: 0.7.6, инвертирует/затемняет страницы. Юзер держит СПЕЦИАЛЬНО для
  тёмного режима — **НЕ удалять** (проверено: удалённый xpi Firefox
  восстанавливает с AMO).
- Ссылка: https://addons.mozilla.org/ru/firefox/addon/dark-background-light-text/
- ID: `jid1-QoFqdK4qzUfGWQ@jetpack`
- Грабли: при двух тёмных расширениях одновременно (это + Dark Reader) —
  двойная фильтрация, заметный CPU на видео-страницах. Если тормозит —
  оставить ОДНО (юзер предпочитает это, Dark Reader — на его выбор).
Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


### RedDarkMode — тема (визуал, не расширение)
- Что: ТЕМА Firefox (не extension!): «Dark mode with red highlights» от
  K1ll8H0T, 1.0, 2021 (не обновляется), 547 юзеров, 7.5 КБ. Чисто визуальная —
  на производительность не влияет.
- Ссылка: https://addons.mozilla.org/ru/firefox/addon/reddarkmode/

## Проверка результата

- YourCodecs: YouTube → Ctrl+F5 → `nvidia-smi` при просмотре: decode > 0
  (не 5% idle как до лечения).
- uBlock: «пингвин»-панель показывает счётчик заблокированных запросов.
- Тёмный режим: страницы тёмные, видео не «выгорает» — как юзер любит.

## References

- Находки ресёрча: research.db (findings id=65 — диагностика медленного
  Firefox, id=68 — чек расширений, id=69 — полный кейс).
- Аппаратное декодирование/VA-API — скилл `firefox-optimization`.
- AMO-страницы расширений — ссылки выше (первоисточник).




---

*Авторство и разработка: https://t.me/aidvizhenie · https://t.me/hilartem. Версия уникальна — и это не предел.***

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
