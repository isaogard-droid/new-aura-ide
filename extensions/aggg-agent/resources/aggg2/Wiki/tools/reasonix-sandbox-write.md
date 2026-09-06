---
type: Howto
title: "reasonix-sandbox-write"
description: "Фикс ошибки «Файловая система доступна только для чтения» при записи вне воркспейса в Reasonix: песочница (bubblewrap) монтирует внешние диски read-only даже при rw-диске; решение — allow_write в config.toml + перезапуск сессии"
date: 2026-08-16
tags: [skill-notes, tools, reasonix, sandbox, linux]
source: skills/reasonix-sandbox-write/ (перенесено 16.08.2026)
status: stable
---

# reasonix-sandbox-write — скилл-на-полке (Howto)

Перенесено из `skills/reasonix-sandbox-write/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->

# Reasonix: запись в проект вне рабочей папки

Применимо к Reasonix (`~/.reasonix/config.toml`), Linux + bubblewrap.

## Симптом

- `write_file` / `edit_file` падает с:
  `path "..." is outside the writable roots (writes are confined to /home/...; write inside the workspace or a configured allow_write root)`
- `touch` / `echo > file` в bash падает с: `Файловая система доступна только для чтения`
- При этом `mount` на хосте показывает диск как `rw` — и пользователь его перемонтировал, а писать всё равно нельзя.

## Диагноз (в 30 секунд)

Смотри mountinfo **изнутри песочницы** — суперблок и опции монтирования разные:

```bash
grep " <точка монтирования диска> " /proc/self/mountinfo
# 1408 1401 8:17 / /run/media/<user>/DATA ro,nosuid,nodev,relatime master:908 - ext4 /dev/sdb1 rw,seclabel,errors=remount-ro
#                                     ^^ mount options (ro!)          суперблок ^^ (rw)
# Точку монтирования брать из реального mountinfo (пример на Linux:
# /run/media/<user>/DATA — на другой машине/ОС путь другой)
```

Ключ: **опции монтирования `ro`, суперблок `rw`** — это не диск, это песочница
(Reasonix, `bash = "enforce"` → bubblewrap на Linux) наложила read-only поверх
живого диска. Писать разрешено только в `workspace_root` (по умолчанию cwd) +
`allow_write`. Всё остальное песочница монтирует `ro`.

**Не иди по ложному следу:** не перемонтируй диск (`sudo mount -o remount,rw`),
не fsck, не «диск сдох» — это нормальное поведение песочницы, если путь не в
списке разрешённых. Сначала проверь mountinfo, потом правь конфиг Reasonix.

## Решение

1. В `~/.reasonix/config.toml` в секции `[sandbox]` добавить путь в `allow_write`:

```toml
[sandbox]
allow_write = ["<точка монтирования диска>"]   # универсально: вся точка монтирования
```

   - Универсальный вариант: указывать **всю точку монтирования диска**
     (например `/run/media/<user>/DATA`), а не один проект — покрывает все
     проекты на диске и не требует правок на каждый новый путь.
   - Точечный вариант: `["<точка монтирования>/AGGG2.0/projects/sherpa-voice"]`.

2. **Перезапустить сессию Reasonix** (`/new` или новый сеанс). Песочница
   создаётся ОДИН раз при старте сессии — mount зафиксирован на весь её
   жизненный цикл, текущая сессия новый конфиг не подхватит.

3. Проверить (путь — реальный, из `mountinfo`/`findmnt` вашей машины):

```bash
touch <точка монтирования>/AGGG2.0/projects/sherpa-voice/.write_test && rm <точка монтирования>/AGGG2.0/projects/sherpa-voice/.write_test
```

   В mountinfo появляется второй rw-биндинг поверх ro:
   `1475 1457 8:17 / /run/media/<user>/DATA rw,...` — это признак, что всё сработало.

## Что не трогать

- `bash = "off"` — снимает песочницу целиком; обычно не нужно, достаточно
  расширить `allow_write`.
- `workspace_root = "/"` — открывает запись во всю систему; избыточно для
  работы с одним диском данных.
- `forbid_read` — не про запись, оставить как есть.

---

*Принадлежит и разработано: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, новая — ещё лучше.***

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
