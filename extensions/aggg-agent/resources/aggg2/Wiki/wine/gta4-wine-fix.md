---
type: Howto
title: gta4-wine-fix
description: "Плейбук починки GTA IV (репак/Complete Edition) под Wine: RGL-ошибка, FusionFix, DXVK, шейдеры, windowed. Диагностика + проверенные фиксы."
date: 2026-08-16
tags: [skill-notes, wine, gaming, gta, dxvk]
source: skills/gta4-wine-fix/ (перенесено 16.08.2026)
status: stable
---

# gta4-wine-fix — скилл-на-полке (Howto)

Перенесено из `skills/gta4-wine-fix/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже — дословно.

Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->


# Починка GTA IV (репак / Complete Edition) под Wine — проверенный плейбук

Проверено на практике (Fedora, wine-staging 11 wow64, NVIDIA GTX 1660 SUPER, проприетарный драйвер, префикс `~/.wine`, игра в `~/DATA/Games/Grand Theft Auto IV`).

> **Как читать этот плейбук.** Запуск GTA IV — цепочка слоёв:
> `Launcher → GTAIV.exe → ASI loader (dinput8) → FusionFix → d3d9 wrapper → DXVK → Wine Vulkan → NVIDIA driver`.
> Каждая исправленная ошибка открывает следующую — «чиню одно, вылезает другое» это норма, а не регресс.
> Раздел 1 — **инварианты** (что доказать; долгоживущая методика). Разделы 2–4 — **реализации текущей версии** (могут устареть: Wine, DXVK, FusionFix, репаки меняются).

---

## 1. ИНВАРИАНТЫ — что нужно доказать (методика, не зависит от версий)

Диагностика всегда сводится к доказательству четырёх фактов о РЕАЛЬНОМ состоянии, а не о предполагаемом:

| # | Инвариант | Как доказать (не косвенно, а напрямую) |
|---|---|---|
| 1 | **Какой exe запускается** | Лог запуска/процессы: `GTAIV.exe` (игра) ≠ `PlayGTAIV.exe`/`Launcher.exe` (bootstrap-редиректор RGL). Если запущен редиректор — RGL-ошибка неизбежна без установленного RGL |
| 2 | **Какая DLL реально загружена** | `WINEDEBUG=+loaddll wine GTAIV.exe 2>&1 \| grep -iE "d3d9\|dinput8\|vulkan"` — искать `Loaded L"D:\Games\...\d3d9.dll" ... native` (локальная из папки игры), а не `system32`. «Мод установлен» ≠ «мод активен» |
| 3 | **Какой рендерер активен** | В логе есть `wined3d_*` fixme/err → рендер на wined3d (не DXVK). DXVK-лог начинается с `info: DXVK: vX.Y.Z` |
| 4 | **Какой GPU выбрал DXVK** | Строка `info: Device : NVIDIA GeForce ...` в логе = ВЕСЬ стек работает (Vulkan есть, ICD найден, 32-bit Vulkan есть, DXVK загружен, драйвер отвечает). Сильнее, чем vulkaninfo/lsmod — проверяется именно тот стек, которым пользуется игра. `llvmpipe` = GPU не виден |

**Порядок диагностики всегда сверху вниз** (по цепочке слоёв): пока не доказан предыдущий инвариант, чинить следующий слой бессмысленно (игра до него не доходит).

---

## 2. РЕАЛИЗАЦИИ (текущая версия — может измениться)

### 2.1 Диагностика по сообщению об ошибке

| Симптом | Источник | Фикс |
|---|---|---|
| «Unable to locate the Rockstar Games Launcher, please verify your game data» | `PlayGTAIV.exe`/`Launcher.exe` — «Rockstar Games Launcher Redirector»: ищут RGL по пути `\Rockstar Games\Launcher\Launcher.exe` и реестру `SOFTWARE\WOW6432Node\Rockstar Games\Launcher` | Запускать **GTAIV.exe напрямую** (RGL не проверяет). Не играть через PlayGTAIV/Launcher |
| Краш/чёрный экран, в логе `wined3d_get_format` / `context_choose_pixel_format` | Рендер ушёл на wined3d вместо DXVK | Включить DXVK: `d3d9.cfg` → `[MAIN] API=1` |
| `err:d3dcompiler:assemble_shader Asm reading failed` | Wine'шный d3dcompiler_43 не понимает asm-шейдеры FusionFix | `winetricks -q d3dcompiler_43` (native Microsoft DLL) + оверрайд `d3dcompiler_43=n` |
| `info: Device not reset` (DXVK), краш при переходе в fullscreen | Потеря Vulkan-устройства при переключении режима | Оконный режим: `-windowed` в `commandline.txt` |
| GPU не используется (в логе llvmpipe/lavapipe, нет «Device : NVIDIA») | Нет `/dev/dri` в песочнице ИЛИ нет 32-bit Vulkan-стека | Проверить: `vulkan-loader.i686`, `nvidia_icd.i686.json`, `/usr/lib/libvulkan.so.1`; вне песочницы с GPU |
Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


### 2.2 Стек файлов (минимум для рабочего запуска)

- **`d3d9.cfg`** (папка игры, от FusionFix-враппера):
  ```
  [MAIN]
  API=1
  ```
  Враппер НЕ автоматический: `API=1` → грузит `vulkan.dll` (DXVK 32-bit из папки игры); `API=0`/пусто → системный wined3d (краш). Пустой конфиг = DXVK «установлен», но никто его не загрузил.
- **`commandline.txt`** (папка игры; GTA IV читает его автоматически):
  ```
  -norestrictions
  -nomemrestrict
  -windowed
  ```
  `-norestrictions -nomemrestrict` — официальный фикс Rockstar для GPU >2GB VRAM.
- **`start.sh`**:
  ```bash
  export WINEDEBUG=-all
  export WINEDLLOVERRIDES="dinput8=n,b;d3d9=n,b;d3d11=n,b;dxgi=n,b;d3dcompiler_43=n;winedbg.exe=d"
  wine GTAIV.exe "$@" 2>&1 | tee ~/gtaiv_user.log
  ```
  `dinput8=n,b` — ASI-loader FusionFix; `d3d9=n,b` — враппер из папки игры; `winedbg.exe=d` — из Lutris-скрипта.
- **`~/.wine/user.reg`**: `"Version"="win7"` в `[Software\\Wine]` (Windows 7 режим).

### 2.3 Установка FusionFix (обязательно для CE)

1. Скачать: `https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/releases/latest/download/GTAIV.EFLC.FusionFix.zip`
2. Распаковать в корень игры (где GTAIV.exe). Должны появиться: `dinput8.dll` (ASI loader), `d3d9.dll` (враппер), `vulkan.dll` (DXVK 32-bit), `plugins/GTAIV.EFLC.FusionFix.asi`.
3. Проверить, что `vulkan.dll` — это DXVK: `strings vulkan.dll | grep -i dxvk` (должен найтись).
4. `winetricks -q d3dcompiler_43` (нужно для компиляции шейдеров FusionFix).
5. d3dx9_43 — проверить `winetricks -q d3dx9_43` при необходимости.

---

## 3. Диагностические приёмы (реализация инвариантов)

1. **UTF-16 строки бинарников** — искать сообщения/пути проверки: `strings -e l GTAIV.exe | grep -i "rockstar games launcher"`. Обычный `strings` (ASCII) НЕ найдёт — в Windows exe строки UTF-16LE. «Ничего не найдено» может означать только предел инструмента, а не отсутствие данных.
2. **Какие DLL реально грузятся** (инвариант 2): см. раздел 1.
3. **GPU подтверждение** (инвариант 4): строка `info: Device : NVIDIA GeForce ...` в логе DXVK.
4. **Лог запуска всегда в файл**: `wine GTAIV.exe ... > ~/gtaiv_user.log 2>&1`.
5. Песочница агента (bwrap) не имеет `/dev/dri` → DXVK там падает на lavapipe, игра «висит» при компиляции шейдеров — **это нерепрезентативно**, финальную проверку делает пользователь на хосте (инвариант 4 доказывается ТОЛЬКО на хосте).

---

## 4. Паттерны (по AGGG)

| Паттерн | Правило | Гард |
|---|---|---|
| Сообщение ошибки ≠ в том файле, что кажется | «Unable to locate…» — в PlayGTAIV.exe (редиректор), «Please run GTA IV using…» — в GTAIV.exe | strings -e l по ВСЕМ exe, не только главному |
| Пустой поиск ≠ нет данных | Строки Windows-бинарников UTF-16, ASCII-поиск пуст | strings -e l (UTF-16LE) всегда для .exe/.dll |
| «Установил мод» ≠ «мод активен» | FusionFix может быть распакован, но DXVK выключен (пустой d3d9.cfg) → wined3d → краш | проверить loaddll-лог и d3d9.cfg API=1 |
| Ошибка после фикса = следующий слой, не регресс | Каждый фикс открывает следующую ошибку (RGL → wined3d → шейдеры → fullscreen) | идти по слоям, лог после КАЖДОГО изменения |
| Скилл не должен гадать о GPU | В песочнице без /dev/dri DXVK всегда на software | проверка GPU — только логом на хосте пользователя («Device : NVIDIA…») |
| Запуск .sh двойным кликом ≠ запуск | GNOME открывает .sh в редакторе | делать .desktop ярлык: `Exec=/path/launch.sh`, `Terminal=true`, `chmod +x`, `gio set ... metadata::trusted true` |
| Инвариант важнее симптома | Симптом «DXVK вроде работает» лжёт; состояние системы доказывается логом (+loaddll, Device : NVIDIA) | каждый шаг: сформулировать инвариант → доказать его логом → только потом чинить следующий слой |
| Конкретные реализации устаревают | API=1, d3dcompiler_43, -windowed привязаны к текущим Wine/DXVK/FusionFix/репаку | при новом сбое возвращаться к инвариантам (раздел 1), а не к конкретным фиксам |

---

## 5. План Б (если CE не заводится вообще)

- **GTA IV Downgrader v2.2** (ClonkAndre): `https://github.com/ClonkAndre/GTAIVDowngrader/releases/download/v2.2/IVDowngrader.v2.2.zip` — даунгрейд до 1.0.8.0/1.0.7.0: версии без RGL и Social Club, GTAIV.exe запускается напрямую. In-place обхода RGL-проверки CE НЕ существует (редиректор исполняет реальный RGL с online-auth; dummy-файл/реестр не работают).
- FusionFix для даунгрейда: нужен Legacy Addon.
- GOG-версии GTA IV нет (игра только Steam/RGL).




---

*Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.***

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->
