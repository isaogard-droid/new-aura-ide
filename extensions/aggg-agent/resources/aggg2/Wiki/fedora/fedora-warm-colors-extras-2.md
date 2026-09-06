---
type: Reference
title: "fedora-warm-colors: extras-2 (sudo, терминалы)"
description: "Дополнение к скиллу-на-полке fedora-warm-colors: references/windows-look-extras-2.md"
date: 2026-08-16
tags: [skill-notes, fedora]
source: skills/fedora-warm-colors/references/windows-look-extras-2.md (перенесено 16.08.2026)
status: stable
---

# fedora-warm-colors: extras-2 (sudo, терминалы)

Дополнение к Howto-посту `fedora-warm-colors.md` (вынесено из-за лимита 300 строк).

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie

AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Windows-look extras, часть 2 (sudo + терминалы + rollback)

Вынесено из `windows-look-extras.md` (механическая резка god-файла, docs/canon/FILE-SIZE.md).


## 5. Passwordless sudo (user-enabled 2026-08-06)

The user explicitly asked to disable the sudo password prompt for the local user
(`$USER`), so the whole setup can run non-interactively:

```bash
echo "$USER ALL=(ALL) NOPASSWD: ALL" > /tmp/opencode/sudoers-nopasswd
sudo install -m 0440 /tmp/opencode/sudoers-nopasswd /etc/sudoers.d/opencode-nopasswd
rm /tmp/opencode/sudoers-nopasswd
sudo -n true && echo OK   # verify: no password prompt
```

- Rollback: `sudo rm /etc/sudoers.d/opencode-nopasswd` (password required again).
- Security note: this makes every command `sudo`-able by the user without a prompt;
  if the account password was ever shared/typed in a terminal, recommend
  `passwd` to rotate it. Do NOT hardcode any password in this file.
- sudoers.d files must be mode 0440 and owned by root (hence `install -m 0440`).

## 6. Terminals: Alacritty + WezTerm, Cascadia Mono (Windows Terminal look, 2026-08-06)

User asked for the two recommended terminals and "Cascadia Mono like on Windows".

Installed:
```bash
sudo dnf install -y alacritty        # 0.17.0, in Fedora 44 repos
# wezterm NOT in Fedora repos (any version) — official RPM from GitHub releases:
curl -sL -o /tmp/wezterm.rpm https://github.com/wez/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203_110809_5046fc22-1.fedora39.x86_64.rpm
sudo dnf install -y /tmp/wezterm.rpm   # fedora39 build works on 44; ~121 MiB
```
GOTCHAS:
- WezTerm: original author @wez stepped back in early 2024 (last release tag
  20240203-110809-5046fc22). The repo is NOT archived and NOT forked — it is still
  actively developed by community maintainers in the SAME repo
  (`https://github.com/wezterm/wezterm`, pushed 2026-08-05), but no new tagged
  releases are cut, so the GitHub releases page only has up to `fedora39` RPMs.
  The `20240203` RPM is therefore the newest installable release. Query via
  `curl -sL https://api.github.com/repos/wezterm/wezterm/releases/latest` (tag
  `20240203-110809-5046fc22`; the RPM filename uses `20240203_110809_5046fc22` —
  underscore). There is no wezterm COPR repo either (404).
  Nightly/dev builds: build from source (`cargo build`) if newer is required.
- Fedora's `cascadia-code-fonts` package ships ONLY "Cascadia Code" (with ligatures) —
  there is NO "Cascadia Mono" family in it. The Mono variant (Windows Terminal
  default) must be installed separately from the official release:
  ```bash
  curl -sL -o /tmp/cascadia.zip https://github.com/microsoft/cascadia-code/releases/download/v2404.23/CascadiaCode-2404.23.zip
  unzip -o -q /tmp/cascadia.zip -d /tmp/cascadia
  mkdir -p ~/.local/share/fonts/cascadia-mono
  cp /tmp/cascadia/ttf/CascadiaMono.ttf /tmp/cascadia/ttf/CascadiaMonoItalic.ttf /tmp/cascadia/ttf/CascadiaMonoPL.ttf /tmp/cascadia/ttf/CascadiaMonoPLItalic.ttf ~/.local/share/fonts/cascadia-mono/
  fc-cache -f ~/.local/share/fonts/cascadia-mono
  ```
  (zip is ~150 MB; the 9-byte "Not Found" response = wrong URL, same trick as Bibata.)

Configs (Windows Terminal Dark look: bg `#0c0c0c`, fg `#cccccc`, WT palette):
- Alacritty: `~/.config/alacritty/alacritty.toml` (0.17 = TOML format; font
  `Cascadia Mono` normal/bold/italic, size 12, WT Dark palette).
- WezTerm: `~/.config/wezterm/wezterm.lua` — `color_scheme = "Windows Terminal Dark"`,
  `font = wezterm.font("Cascadia Mono")`, font_size 12.
- GOTCHA: wezterm has NO `background = "<color>"` config key (that's a Vec for
  gradients) — it errors with "Cannot convert String to Vec"; the bg color comes
  from the color_scheme.
- Font verify: `wezterm ls-fonts` (shows resolved "Cascadia Mono"); alacritty config
  validates on launch (`timeout 3 alacritty`, exit 0).
- Alacritty hotkeys: `Ctrl+Shift+-`/`=` zoom, `Ctrl+Shift+C/V` copy/paste, `F11` fullscreen.

## Rollback (Windows-look parts)

- Cursors: `gsettings set org.gnome.desktop.interface cursor-theme 'Bibata-Modern-Classic'`
  (or default) and delete `~/.local/share/icons/win11-aero`.
- Sounds: `gsettings set org.gnome.desktop.sound theme-name 'freedesktop'` (or default)
  and delete `~/.local/share/sounds/win11`.
- Extensions: `gsettings reset-recursively org.gnome.shell.extensions.dash-to-panel` (and
  arcmenu / blur-my-shell / ding), disable via the gdbus call, then delete the dirs under
  `/usr/share/gnome-shell/extensions/` (sudo), and remove the combined
  `~/.local/share/glib-2.0/schemas/` compiled file (it only carries extension schemas).
- Dark theme: delete `~/.config/environment.d/qt-dark.conf` + relogin; reset gsettings keys.
- Sudo: `sudo rm /etc/sudoers.d/opencode-nopasswd`.

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
