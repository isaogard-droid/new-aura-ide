---
type: Reference
title: "fedora-warm-colors: extras (тёмная тема, шрифты)"
description: "Дополнение к скиллу-на-полке fedora-warm-colors: references/windows-look-extras.md"
date: 2026-08-16
tags: [skill-notes, fedora]
source: skills/fedora-warm-colors/references/windows-look-extras.md (перенесено 16.08.2026)
status: stable
---

# fedora-warm-colors: extras (тёмная тема, шрифты)

Дополнение к Howto-посту `fedora-warm-colors.md` (вынесено из-за лимита 300 строк).

# Fedora → Windows 11 look: расширенные шаги (extra)
Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->


Подробности «как на Windows» сверх ядра тёплого отображения (SKILL.md §1-4:
Night Light, VCGT-гамма, монитор, проверка). Читать, когда задача требует
Windows-лука: тёмная тема, шрифты, иконки, курсоры, звуки, расширения,
терминалы, passwordless sudo.

## 1. Dark theme — force ALL apps dark (GNOME 42+)

### 1a. Base: GTK3/GTK4 + GNOME apps (system-wide via gsettings)

```bash
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
sudo dnf install -y adw-gtk3-theme    # package is adw-gtk3-theme, NOT adw-gtk3
gsettings set org.gnome.desktop.interface gtk-theme 'adw-gtk3-dark'
```
Covers: all native GNOME apps + most RPM GTK3/GTK4 apps (Files, Text Editor, Nautilus, etc.).

### 1b. Qt apps (Kate, Telegram, Dolphin, qBittorrent, VLC, etc.)

Qt does NOT read gsettings — it needs the platform theme var (ArchWiki:
`QT_QPA_PLATFORMTHEME=gtk3` makes Qt render with the active GTK theme = dark):

```bash
mkdir -p ~/.config/environment.d
printf 'QT_QPA_PLATFORMTHEME=gtk3\n' > ~/.config/environment.d/qt-dark.conf
```
- Applied by systemd at LOGIN — user must log out/in (or reboot) for it to take effect.
- Works for RPM Qt apps (kate, telegram-desktop). Check: `printenv QT_QPA_PLATFORMTHEME`
  after relogin shows `gtk3`.
- Flatpak Qt apps (Dolphin flatpak, qBittorrent flatpak): env vars do NOT cross the
  sandbox, but Qt 6.5+ reads `prefer-dark` via the XDG Settings portal automatically —
  they darken on their own after relogin.

### 1c. LibreOffice (own theme mechanism, ignores gsettings)

- LO 24.8+ follows the system theme automatically when using the GTK backend
  (RPM `libreoffice-gtk3`/`libreoffice-gtk4` installed on Fedora).
- If still light: Сервис → Параметры → Персонализация → Цветовая схема → **Автоматически**
  (Tools → Options → Personalization → Color scheme → Automatic).
- Force the GTK4 backend (draws with current GTK theme): `SAL_USE_VCLPLUGIN=gtk4 libreoffice`
  (also add to ~/.config/environment.d/ to persist).

### 1d. Browsers (Firefox, Brave, Chromium — incl. flatpaks)

- Firefox / Chromium / Brave follow the system `prefers-color-scheme` → GNOME
  already reports dark, so they go dark with zero config.
- Brave stays light anyway → `brave://flags` → "Force Dark Mode for Web Contents" → Enabled.
- Firefox extra hardening (about:config): `widget.content.allow-gtk-dark-theme` = true,
  `ui.systemUsesDarkTheme` = 1.

### 1e. Electron apps (VS Code, Slack, Discord, etc.)

- Follow the system color scheme via Chromium → dark automatically with prefer-dark.
- VS Code: `"workbench.colorTheme": "Default Dark Modern"` in settings.json if needed.

### Verification (after relogin)

```bash
printenv QT_QPA_PLATFORMTHEME        # expect gtk3
gsettings get org.gnome.desktop.interface color-scheme   # expect 'prefer-dark'
gsettings get org.gnome.desktop.interface gtk-theme      # expect 'adw-gtk3-dark'
```
Rollback: delete ~/.config/environment.d/qt-dark.conf + relogin; reset gsettings keys.

## 2. Soft font rendering like ClearType (GNOME 47+ moved the keys)

```bash
gsettings set org.gnome.desktop.interface font-rendering 'manual'
gsettings set org.gnome.desktop.interface font-antialiasing 'rgba'   # subpixel, ClearType-style
gsettings set org.gnome.desktop.interface font-hinting 'slight'      # soft
gsettings set org.gnome.desktop.interface font-rgba-order 'rgb'
```

Plus user fontconfig (fallback layer respected by GTK/Pango/FreeType):

`~/.config/fontconfig/fonts.conf`:
```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <match target="font">
    <edit name="antialias" mode="assign"><bool>true</bool></edit>
    <edit name="hinting" mode="assign"><bool>true</bool></edit>
    <edit name="hintstyle" mode="assign"><const>hintslight</const></edit>
    <edit name="lcdfilter" mode="assign"><const>lcddefault</const></edit>
    <edit name="rgba" mode="assign"><const>rgb</const></edit>
    <edit name="embeddedbitmap" mode="assign"><bool>false</bool></edit>
  </match>
</fontconfig>
```

Note: `hintfull` + subpixel = sharp Windows look; `hintslight` = softer.
Changes apply after relogin/restarting apps.

## 3. Windows fonts: Segoe UI + Cascadia Mono

```bash
git clone --depth 1 https://github.com/mrbvrz/segoe-ui-linux ~/segoe-ui-linux
mkdir -p ~/.local/share/fonts/Microsoft/TrueType/SegoeUI
cp ~/segoe-ui-linux/font/*.ttf ~/.local/share/fonts/Microsoft/TrueType/SegoeUI/
fc-cache -f ~/.local/share/fonts/Microsoft/TrueType/SegoeUI
gsettings set org.gnome.desktop.interface font-name 'Segoe UI 11'
gsettings set org.gnome.desktop.interface document-font-name 'Segoe UI 12'
```
No sudo needed (user-level install). Proprietary Microsoft font — user's own machine,
user choice; alternative: install from an existing Windows partition.
Repo also contains `seguiemj.ttf` (emoji) + `seguisym.ttf` — copy them too if wanted.

Monospace = Windows 11 terminal font (needs sudo, Fedora package):
```bash
sudo dnf install cascadia-code-fonts
gsettings set org.gnome.desktop.interface monospace-font-name 'Cascadia Mono 11'
```

## 4. Windows 11 look: icons, cursors, taskbar, start menu, desktop

Icons (Fluent, user-level, no sudo):
```bash
git clone --depth 1 https://github.com/vinceliuice/Fluent-icon-theme ~/Fluent-icon-theme
~/Fluent-icon-theme/install.sh          # installs Fluent, Fluent-light, Fluent-dark
gsettings set org.gnome.desktop.interface icon-theme 'Fluent-dark'
```

### REAL Windows 11 cursors (win11-aero)
Authentic Windows .cur/.ani files from `Microtribute/win11-aero-left-cursors`
(real aero_arrow/aero_link/aero_working etc.); libXcursor loads .cur/.ani natively:
- Download: `curl -sL -o /tmp/win11cur.tar.gz https://codeload.github.com/Microtribute/win11-aero-left-cursors/tar.gz/refs/heads/main` (≈344 KB)
- Extract ONLY the normal-size files (skip `_l` left-handed / `_xl` XL) into
  `~/.local/share/icons/win11-aero/` + write `cursor.theme`:
  `[Icon Theme] Name=win11-aero Comment=Windows 11 Aero cursors Directories=. [.] Size=32 Type=Fixed`
- Symlink X cursor names → files (default/left_ptr→aero_arrow, pointer/hand2→aero_link,
  help→aero_helpsel, move→aero_move, watch/wait→aero_working.ani, progress→aero_busy.ani,
  crosshair/cell→aero_pen, not-allowed/no-drop→aero_unavail, ew/ns/nesw/nwse-resize→aero_*).
- The repo has NO text I-beam — generate one (Win11 aero_beam style) and compile with
  `xcursorgen` (install first: `sudo dnf install xcursorgen`):
  `magick -size 24x24 xc:none -fill black -draw "roundrectangle 7,3 17,6 2,2" -draw "roundrectangle 7,18 17,21 2,2" -draw "roundrectangle 9,3 15,21 2,2" -fill white -draw "roundrectangle 9,4 15,20 2,2" -draw "roundrectangle 8,4 16,5 1,1" -draw "roundrectangle 8,19 16,20 1,1" beam.png`
  then `xcursorgen` with config `24 12 12 beam.png` → `text`, symlink `xterm`/`ibeam`.
- Enable: `gsettings set org.gnome.desktop.interface cursor-theme 'win11-aero'`
  (cursor-size 24). Fallback: `Bibata-Modern-Classic` (Windows-like arrow, same install pattern).

### Base settings
```bash
gsettings set org.gnome.desktop.wm.preferences button-layout 'appmenu:minimize,maximize,close'  # min/max/close on the right, like Windows
gsettings set org.gnome.desktop.interface accent-color 'blue'      # Win11 default accent (GNOME 47+; closest to #0078d4)
gsettings set org.gnome.desktop.interface clock-format '24h'
gsettings set org.gnome.desktop.interface clock-show-date true
gsettings set org.gnome.desktop.interface text-scaling-factor 1.1  # 110% — readable; Win11@1080p often uses 125%
gsettings set org.gnome.desktop.interface cursor-size 24           # matches Win11 default
```

### Win11 GTK theme + adw-gtk3
GOTCHAS:
- `B00merang-Project/Windows-11` repo NO LONGER EXISTS (404 on GitHub). The
  Win11-style Fluent theme is **B00merang-Project/Windows-10-Fluent-Dark**.
- `git clone` of GitHub repos may prompt for credentials — use curl tarballs instead:
  `curl -sL -o /tmp/w10.tar.gz https://github.com/B00merang-Project/Windows-10-Fluent-Dark/archive/refs/heads/master.tar.gz`
- Install user-level, no sudo:
```bash
mkdir -p ~/.themes && tar -xzf /tmp/w10.tar.gz -C ~/.themes && mv ~/.themes/Windows-10-Fluent-Dark-master ~/.themes/Windows-10-Fluent-Dark
gsettings set org.gnome.desktop.interface gtk-theme 'Windows-10-Fluent-Dark'
```
- It ships gtk-2.0/3.0/4.0 + metacity; applies to GTK3 apps; libadwaita (GTK4) apps
  stay GNOME-dark (libadwaita barely themes anyway).
- adw-gtk3 alternative (system-wide): `sudo dnf install adw-gtk3-theme`, then
  `gsettings set ... gtk-theme 'adw-gtk3-dark'` for a coherent GNOME look.

### Black / warm wallpaper
```bash
# plain black (no image):
gsettings set org.gnome.desktop.background picture-uri-dark ''
gsettings set org.gnome.desktop.background picture-uri ''
gsettings set org.gnome.desktop.background color-shading-type 'solid'
gsettings set org.gnome.desktop.background primary-color '#000000'
gsettings set org.gnome.desktop.background secondary-color '#000000'
Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


# or a warm dark gradient (ImageMagick, no network):
magick -size 1920x1080 gradient:'#4a3524'-'#120d09' -colorspace sRGB +noise Gaussian -attenuate 0.1 -blur 0x2 -quality 90 ~/Pictures/warm-dark.jpg
gsettings set org.gnome.desktop.background picture-uri-dark 'file:///home/$USER/Pictures/warm-dark.jpg'
gsettings set org.gnome.desktop.background picture-uri 'file:///home/$USER/Pictures/warm-dark.jpg'
gsettings set org.gnome.desktop.background picture-options 'zoom'
```
(JPEG q90 ≈ 300 KB; PNG is 9–14 MB, avoid.)

### Windows 11 system sounds
Win11 sound scheme as a GNOME sound theme (user-level, no sudo):
- Download: `curl -sL -o /tmp/winsounds.tar.gz https://codeload.github.com/MCPlayer2015/all-windows-sounds/tar.gz/refs/heads/main`
  (106 MB — whole repo, ALL Windows versions; strip the rest).
- Extract only the Win11 folder:
  `mkdir -p ~/.local/share/sounds/win11 && tar -xzf /tmp/winsounds.tar.gz -C ~/.local/share/sounds/win11 --strip-components=2 'all-windows-sounds-main/(2021) Windows 11/*'`
- Create `index.theme`: `[Sound Theme] Name=win11 Directories=. [.]`
- Symlink GNOME event ids → Win11 wavs (e.g. `ln -sf "Windows Notify.wav" dialog-information.wav`):
  dialog-error→Windows Error, dialog-information→Windows Notify, dialog-question→Notify System Generic,
  dialog-warning→Windows Exclamation, bell-window-system→Windows Notify, window-attached→Foreground,
  window-detached→Background, window-restore→Windows Restore, window-minimize→Windows Minimize,
  button-pressed/released→Menu Command, button-toggle-*→Windows Notify, service/desktop-login→Windows Logon,
  logout→Logoff Sound, device-added→Hardware Insert, device-removed→Hardware Remove,
  battery-low→Battery Low, battery-full→Notify System Generic, power-unplug-battery→Battery Critical,
  complete→chimes, trash-empty→Windows Recycle, message-new-instant→Notify Messaging, alarm→Alarm01.
- Enable: `gsettings set org.gnome.desktop.sound theme-name 'win11'` (+ `event-sounds true`).

### Extensions: Dash to Panel + ArcMenu + Blur my Shell + DING
IMPORTANT gotchas:
- Get the zip version matching the shell: `https://extensions.gnome.org/extension-info/?uuid=<uuid>&shell_version=<N>`
  (shell 50 → dash-to-panel@jderose9.github.com v73, arcmenu@arcmenu.com v69.2,
  blur-my-shell@aunetx v72, ding@rastersoft.com v92).
  Download `https://extensions.gnome.org/download-extension/<uuid>.shell-extension.zip?version_tag=<pk>`.
- GNOME 45+ queues user-installed extensions for GUI approval; `gnome-extensions enable` fails with
  "not found". Bypass: install as SYSTEM extension (needs sudo) into `/usr/share/gnome-shell/extensions/`.
- After copying as root, FIX perms + SELinux: files may end up 600 root:root and get `usr_t`
  mislabels — run `sudo restorecon -R` and `sudo chmod -R a+rX` on both dirs.
- Compile schemas after install: `sudo glib-compile-schemas /usr/share/gnome-shell/extensions/<uuid>/schemas/`.
- **gsettings CLI does NOT see extension schemas** (they're not in its search path) —
  "Schema does not exist" errors. Fix: copy all `*.xml` from the extensions' schemas/
  into `~/.local/share/glib-2.0/schemas/` and run `glib-compile-schemas` there. Only
  needed to configure via CLI; the shell itself reads the extension's own schemas dir.
- GNOME 50 moved the D-Bus interface: it's `org.gnome.Shell` at object path `/org/gnome/Shell`
  (NOT `/org/gnome/Shell/Extensions`). Enable via:
  `gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Extensions.EnableExtension <uuid>`
- gnome-shell only scans extension dirs at STARTUP: new system extensions require a log out/in.
- Extension state check: `gnome-extensions info <uuid>` → `Состояние:`
  (INITIALIZED = scanned, not yet enabled; ACTIVE = running).

Win11-style config:
Dash to Panel:
```bash
gsettings set org.gnome.shell.extensions.dash-to-panel panel-size 48
gsettings set org.gnome.shell.extensions.dash-to-panel panel-positions '{"0":"BOTTOM"}'
gsettings set org.gnome.shell.extensions.dash-to-panel dot-style-focused 'METRO'      # Win11 underline
gsettings set org.gnome.shell.extensions.dash-to-panel dot-style-unfocused 'SOLID'
gsettings set org.gnome.shell.extensions.dash-to-panel dot-size 3
gsettings set org.gnome.shell.extensions.dash-to-panel dot-color-1 '#0078d4'          # Windows accent blue
gsettings set org.gnome.shell.extensions.dash-to-panel show-activities-button false
gsettings set org.gnome.shell.extensions.dash-to-panel hot-keys true                  # Super+1..9
gsettings set org.gnome.shell.extensions.dash-to-panel taskbar-locked true
```

ArcMenu (v69.2 — `position-in-panel` enum is capitalized: 'Left'):
```bash
gsettings set org.gnome.shell.extensions.arcmenu menu-layout 'windows'
gsettings set org.gnome.shell.extensions.arcmenu position-in-panel 'Left'
gsettings set org.gnome.shell.extensions.arcmenu arcmenu-hotkey "['Super_L']"         # Super opens the menu
gsettings set org.gnome.shell.extensions.arcmenu override-menu-theme true
gsettings set org.gnome.shell.extensions.arcmenu menu-background-color 'rgba(48,48,49,0.98)'
gsettings set org.gnome.shell.extensions.arcmenu windows-show-frequent-apps true
gsettings set org.gnome.shell.extensions.arcmenu windows-show-pinned-apps true
```

Blur my Shell (v72 — key names differ from old docs: `blur`, `static-blur`, NOT blur-enabled):
```bash
gsettings set org.gnome.shell.extensions.blur-my-shell.panel blur true
gsettings set org.gnome.shell.extensions.blur-my-shell.panel static-blur true
gsettings set org.gnome.shell.extensions.blur-my-shell.panel corner-radius 16
```

Desktop Icons NG / DING (desktop icons, Windows-style):
```bash
gsettings set org.gnome.shell.extensions.ding icon-size 'standard'
gsettings set org.gnome.shell.extensions.ding start-corner 'top-left'
gsettings set org.gnome.shell.extensions.ding show-home true
gsettings set org.gnome.shell.extensions.ding show-trash true
gsettings set org.gnome.shell.extensions.ding arrangeorder 'NAME'
gsettings set org.gnome.shell.extensions.ding keep-arranged false
```


---

## 5–6 (sudo, терминалы) и Rollback — вынесены в `windows-look-extras-2.md` (резка god-файла, docs/canon/FILE-SIZE.md)

- Dark theme: delete `~/.config/environment.d/qt-dark.conf` + relogin; reset gsettings keys.
- Sudo: `sudo rm /etc/sudoers.d/opencode-nopasswd`.

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
