---
type: Howto
title: dolphin-windows-theme
description: "Make the Dolphin file manager (flatpak on GNOME/Fedora) look like Windows 11 File Explorer — dark gray #1F1F1F background, white text, blue #0078D4 selection. Use when the user say"
date: 2026-08-16
tags: [skill-notes, fedora, kde, theme, dolphin]
source: skills/dolphin-windows-theme/ (перенесено 16.08.2026)
status: stable
---

# dolphin-windows-theme — скилл-на-полке (Howto)

Перенесено из `skills/dolphin-windows-theme/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже — дословно.

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# Dolphin (flatpak) → Windows 11 Dark theme

Проверено на Fedora 44 + GNOME Wayland, Dolphin 26.04.3 (flatpak, fedora-remote, runtime org.fedoraproject.KDE6Platform). Результат: тёмный фон как в проводнике Windows 11, белый текст, синее выделение #0078D4.

## Почему Dolphin не темнеет (корневые причины, проверены)

1. **Песочница flatpak**: внутри sandbox `XDG_CONFIG_HOME=$HOME/.var/app/<appid>/config`, а НЕ `~/.config`. Хостовый `~/.config/kdeglobals` flatpak-приложение не читает — оно читает `~/.var/app/<appid>/config/kdeglobals`.
2. **На GNOME KDE-платформенный тем не загружен** (в Plasma его подхватывает Qt сам). Без него kdeglobals игнорируется вообще, а «тёмность» даёт только portal color-scheme (Qt `styleHints()->colorScheme()`), при этом палитра остаётся Breeze-дефолтной. Включить KDE-тем: `QT_QPA_PLATFORMTHEME=kde`.
3. **В рантайме нет adwaita-qt**: у org.fedoraproject.KDE6Platform только стиль `breeze6.so` (проверено: `ls .../lib64/qt6/plugins/styles/`). Flathub-расширение `org.kde.KStyle.Adwaita` подходит только рантайму `org.kde.Platform` — для fedora-рантайма бесполезно.
4. Приложение может при выходе перезаписать свой kdeglobals пустым файлом (наблюдалось: 0 байт, права 444). Защита — `chmod 444` после записи.

## Диагностика (2 минуты)

```bash
flatpak info org.kde.dolphin | grep -E "Среда|Runtime"          # какой рантайм
flatpak run --command=env org.kde.dolphin | grep XDG_CONFIG_HOME # куда реально пишет конфиг
ls -la ~/.var/app/org.kde.dolphin/config/kdeglobals              # пустой/отсутствует = проблема
```

## Шаги (готовая процедура — скрипт ниже)

1. **Скрипт**: `bash scripts/apply-windows11-dark.sh [app_id]` (по умолчанию `org.kde.dolphin`). Он:
   - пишет палитру Windows 11 Dark в хостовый `~/.config/kdeglobals` + `~/.local/share/color-schemes/Windows11Dark.colors` (для нативных KDE-приложений) и в песочные пути `~/.var/app/<appid>/config/kdeglobals` + `~/.var/app/<appid>/data/color-schemes/`;
   - `chmod 444` песочному kdeglobals (защита от обнуления);
   - ставит flatpak overrides: `QT_QPA_PLATFORMTHEME=kde`, `--filesystem=xdg-config/kdeglobals:ro`, `--filesystem=xdg-data/color-schemes:ro`.
2. **Шрифт Segoe UI** (проверить): `fc-list | grep -ci segoe` — если 0, поставить `segoe-ui-linux` (у пользователя уже стоит; в kdeglobals: `font=Segoe UI,11,...`).
3. **Иконки** Fluent-dark: `ls ~/.local/share/icons/Fluent-dark/index.theme` (у пользователя стоят; ключ `[Icons] Theme=Fluent-dark` уже в kdeglobals).
4. **Полный перезапуск приложения** — старое окно держит кэш темы: закрыть ВСЕ окна, `pkill -f dolphin` при необходимости, открыть заново.



---

*Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.***
Палитра (Windows 11 dark canon): Window `#1F1F1F`, View `#202020`, Button `#2D2D2D`, Tooltip `#2B2B2B`, текст `#FFFFFF` (inactive `#C9C9C9`), Selection/Focus/Decoration `#0078D4`, Alternate-строки на 6–7 единиц светлее фона.

## Проверка без возможности видеть экран (агент без vision)

- GNOME Wayland блокирует скриншоты агенту: `grim` → «compositor doesn't support», `gdbus org.gnome.Shell.Screenshot` → AccessDenied. Скриншот шлёт пользователь (в чат/Telegram).
- Модель без vision не читает картинки — анализ пикселями через PIL:
  ```python
  from PIL import Image; from collections import Counter
  print(Counter(list(Image.open(path).convert('RGB').getdata())).most_common(6))
  ```
  Сравнивать СТАРЫЙ и НОВЫЙ скриншот: если доминанты идентичны — тема не применилась (окно не перезапущено или конфиг не туда).
- Цвета на скрине сдвинуты гаммой/ICC (у пользователя gnome-gamma-tool) — сравнивай относительные значения до/после, а не с эталоном.
- OCR-фоллбэк: `gpt-cli` (scripts/gpt-ocr.js send) — при кириллическом пути прикрепление отваливается, копируй файл в `/tmp` с ASCII-именем.
Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


## Gotchas

- **`QT_QPA_PLATFORMTHEME=kde` — обязателен**: без него весь kdeglobals игнорируется (на GNOME).
- `cp` в песочный kdeglobals падает с «Отказано в доступе», если файл уже 444 — сначала `chmod 644`.
- Песочный kdeglobals может быть создан приложением пустым (0 байт) — это НЕ значит «тема сброшена», просто KConfig создал файл без ключей; после записи палитры держи его 444.
- Название схемы резолвится по `~/.var/app/<appid>/data/color-schemes/` и рантаймовым каталогам — положить `Windows11Dark.colors` туда же.
- Изменения `~/.config/kdeglobals` (хостовые) касаются и нативных KDE-приложений (Konsole и т.п.) — обычно желаемый побочный эффект.
- Не трогать `dolphinrc` (личные настройки Dolphin живут в песочнице и не влияют на тему окна).

## Available scripts

- `scripts/apply-windows11-dark.sh [app_id]` — идемпотентный установщик (бэкап *.win11bak, запись палитры в host+песочницу, chmod 444, flatpak overrides). Запуск: `bash scripts/apply-windows11-dark.sh`.

## References

- Flatpak theming (GTK/Qt): https://docs.flatpak.org/en/latest/desktop-integration.html
- Гайд «Theme Dolphin (& QT apps) on GNOME»: https://www.reddit.com/r/gnome/comments/11llvso/guide_theme_dolphin_qt_apps_on_gnome/
- Qt dark-mode detection в flatpak (root cause): https://gist.github.com/davidar/ddbe25c7038d7b88e5fddd1272724d8e

Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->

## Скрипт `apply-windows11-dark.sh`

Применяется по инструкции выше (перенесено дословно).

```sh
#!/usr/bin/env bash
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Dolphin (flatpak) → Windows 11 Dark theme: palette + flatpak overrides.
# Idempotent, non-interactive, agent-safe. Run: bash scripts/apply-windows11-dark.sh [app_id]
set -u

APP="${1:-org.kde.dolphin}"
HOST_CONF="$HOME/.config/kdeglobals"
HOST_SCHEMES="$HOME/.local/share/color-schemes"
SANDBOX_CONF="$HOME/.var/app/$APP/config"
SANDBOX_DATA="$HOME/.var/app/$APP/data"

say()  { printf '[win11-dark] %s\n' "$*"; }
die()  { say "ERROR: $*"; exit 1; }

[ -d "$SANDBOX_CONF" ] || die "sandbox config dir not found: $SANDBOX_CONF (проверь, что $APP установлен через flatpak)"

# ---------------------------------------------------------------------------
say "backup старых файлов (если есть и ещё не бэкаплены)"
[ -f "$HOST_CONF" ]   && [ ! -f "$HOST_CONF.win11bak" ]   && cp -a "$HOST_CONF" "$HOST_CONF.win11bak"
[ -f "$SANDBOX_CONF/kdeglobals" ] && [ ! -f "$SANDBOX_CONF/kdeglobals.win11bak" ] && cp -a "$SANDBOX_CONF/kdeglobals" "$SANDBOX_CONF/kdeglobals.win11bak"

# ---------------------------------------------------------------------------
write_kdeglobals() { # $1 = файл
cat > "$1" <<'EOF'
[General]
ColorScheme=Windows11Dark
Name=Windows11Dark
ColorSchemeHash=17f4d46d42a1723d493e19f6dcac1413
shadeSortColumn=true
font=Segoe UI,11,-1,5,50,0,0,0,0,0
menuFont=Segoe UI,11,-1,5,50,0,0,0,0,0
toolBarFont=Segoe UI,10,-1,5,50,0,0,0,0,0
smallestReadableFont=Segoe UI,9,-1,5,50,0,0,0,0,0

[KDE]
LookAndFeelPackage=org.kde.breezedark.desktop

[Icons]
Theme=Fluent-dark

[ColorEffects:Disabled]
Color=56,56,56
ColorAmount=0.2
ColorEffect=0
ContrastAmount=0.65
ContrastEffect=1
IntensityAmount=0.1
IntensityEffect=2

[ColorEffects:Inactive]
ChangeSelectionColor=true
Color=112,111,110
ColorAmount=0.025
ColorEffect=2
ContrastAmount=0.1
ContrastEffect=2
Enable=false
IntensityAmount=0
IntensityEffect=0

[Colors:Window]
BackgroundNormal=31,31,31
BackgroundAlternate=38,38,38
BackgroundSelected=0,120,212
ForegroundNormal=255,255,255
ForegroundInactive=201,201,201
ForegroundActive=255,255,255
ForegroundLink=108,180,238
ForegroundVisited=157,120,255
DecorationFocus=0,120,212
DecorationHover=0,120,212
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


[Colors:View]
BackgroundNormal=32,32,32
BackgroundAlternate=39,39,39
BackgroundSelected=0,120,212
ForegroundNormal=255,255,255
ForegroundInactive=201,201,201
ForegroundActive=255,255,255
ForegroundLink=108,180,238
ForegroundVisited=157,120,255
DecorationFocus=0,120,212
DecorationHover=0,120,212

[Colors:Button]
BackgroundNormal=45,45,45
BackgroundAlternate=45,45,45
BackgroundSelected=0,120,212
ForegroundNormal=255,255,255
ForegroundInactive=201,201,201
ForegroundActive=255,255,255
ForegroundLink=108,180,238
ForegroundVisited=157,120,255
DecorationFocus=0,120,212
DecorationHover=0,120,212

[Colors:Selection]
BackgroundNormal=0,120,212
BackgroundAlternate=0,120,212
BackgroundSelected=0,120,212
ForegroundNormal=255,255,255
ForegroundInactive=230,230,230
ForegroundActive=255,255,255
ForegroundLink=108,180,238
ForegroundVisited=157,120,255
DecorationFocus=0,120,212
DecorationHover=0,120,212

[Colors:Tooltip]
BackgroundNormal=43,43,43
BackgroundAlternate=43,43,43
BackgroundSelected=0,120,212
ForegroundNormal=255,255,255
ForegroundInactive=201,201,201
ForegroundActive=255,255,255
ForegroundLink=108,180,238
ForegroundVisited=157,120,255
DecorationFocus=0,120,212
DecorationHover=0,120,212

[Colors:Complementary]
BackgroundNormal=31,31,31
BackgroundAlternate=38,38,38
BackgroundSelected=0,120,212
ForegroundNormal=255,255,255
ForegroundInactive=201,201,201
ForegroundActive=255,255,255
ForegroundLink=108,180,238
ForegroundVisited=157,120,255
DecorationFocus=0,120,212
DecorationHover=0,120,212
EOF
}

# host (для нативных KDE-приложений) + песочница (куда реально смотрит flatpak-приложение)
write_kdeglobals "$HOST_CONF"
sed -n '/^\[ColorEffects/,$p' "$HOST_CONF" > "$HOST_SCHEMES/Windows11Dark.colors" || die "не смог записать схему"

mkdir -p "$SANDBOX_CONF" "$SANDBOX_DATA/color-schemes" "$HOST_SCHEMES"
chmod 644 "$SANDBOX_CONF/kdeglobals" 2>/dev/null || true   # песочный файл может быть 444/пустой
write_kdeglobals "$SANDBOX_CONF/kdeglobals"
sed -n '/^\[ColorEffects/,$p' "$SANDBOX_CONF/kdeglobals" > "$SANDBOX_DATA/color-schemes/Windows11Dark.colors"

# защита от перезаписи/обнуления приложением (наблюдалось: 0-байтовый 444 файл)
chmod 444 "$SANDBOX_CONF/kdeglobals"

# ---------------------------------------------------------------------------
say "flatpak overrides: QT_QPA_PLATFORMTHEME=kde (KDE-платформенный тем читает kdeglobals)"
flatpak override --user --env=QT_QPA_PLATFORMTHEME=kde "$APP"
flatpak override --user --filesystem=xdg-config/kdeglobals:ro --filesystem=xdg-data/color-schemes:ro "$APP"

say "готово. Полностью закрой $APP и открой заново (старое окно держит кэш темы)."
say "Схема: фон #1F1F1F/#202020, текст #FFFFFF, акцент #0078D4 (Windows 11 Dark), шрифт Segoe UI, иконки Fluent-dark."


# Разработано для https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, дальше — ещё лучше.

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
```
