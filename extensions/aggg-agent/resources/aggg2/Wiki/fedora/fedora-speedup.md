---
type: Howto
title: fedora-speedup
description: "Использовать, когда просят ускорить систему/ПК на Linux (Fedora/GNOME): «тормозит», «медленная загрузка», «какие службы отключить», «CachyOS ядро — стоит ли». Покрывает: read-only"
date: 2026-08-16
tags: [skill-notes, fedora, gnome, performance, optimization]
source: skills/fedora-speedup/ (перенесено 16.08.2026)
status: stable
---
# fedora-speedup — скилл-на-полке (Howto)

Перенесено из `skills/fedora-speedup/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке). Инструкция дословно.
# Ускорение Linux-десктопа (Fedora/GNOME): аудит → службы → загрузка → GNOME → ядро

Проверено живьём: загрузка с 45с до ~13с, минус ~300-500МБ RAM, заметно резче
отклик — без потери функциональности. Все шаги обратимы, ничего не ломается
(каждый шаг — с командой отката).

## When to use / when NOT

- **Use:** «ускорить систему», медленная загрузка, тяжёлый интерфейс, вопрос
  «какие службы можно отключить», оценка «стоит ли кастомное ядро».
- **NOT:** настройка zram/свопа → `zram-optimize`; ускорение Firefox →
  `firefox-optimization`; разметка/форматирование дисков → `disk-formatting`;
  серверы (там свои правила — не трогать NetworkManager-wait-online и т.п.).

## Главное правило

**Сначала аудит (read-only), потом правки, потом перезагрузка — владельцем.**
Ничего не менять до того, как собраны факты. Каждую правку показывать
владельцу с ценой и командой отката.

## Workflow

### Шаг 0 — Аудит (read-only, ничего не менять)

```bash
bash scripts/audit.sh          # один запуск — вся картина (см. Available scripts)
```

Или вручную:

```bash
cat /etc/os-release                                   # дистрибутив/версия
systemd-analyze; systemd-analyze blame | head -15     # где время загрузки
systemd-analyze critical-chain | head -12             # кто блокирует кого
systemctl list-unit-files --state=enabled | grep -vE "dbus|getty|systemd-|user@"  # кандидаты
systemctl --failed                                     # упавшие службы
cat /etc/fstab; lsblk -f                               # мёртвые UUID vs реальные диски
free -h; swapon --show                                 # память/своп
systemd-detect-virt                                    # VM или железо
journalctl -b -p err | tail -20                        # ошибки загрузки
```

### Шаг 1 — Загрузка: убрать ожидания

Три типичных пожирателя времени (проверено):

| Виновник | Как найти | Как чинить | Откат |
|---|---|---|---|
| Мёртвый UUID в fstab (диск переформатирован/отключён) | `lsblk -f` vs `cat /etc/fstab`; в journal «timed out waiting for device» | бэкап `cp -a /etc/fstab /etc/fstab.bak-$(date +%Y%m%d)`, удалить/исправить строку; `x-systemd.device-timeout=N` и `nofail` — сдерживают, не лечат | вернуть бэкап |
| `NetworkManager-wait-online.service` (нужен только серверам/сетевым ФС) | `systemd-analyze blame` (обычно 2-10с) | `sudo systemctl mask NetworkManager-wait-online.service` | `unmask` |
| plymouth-заставка (`rhgb` в cmdline) | `blame` → `plymouth-quit-wait.service` | убрать `rhgb quiet` из GRUB cmdline (grubby `--update-kernel`/`--args`) | вернуть аргументы |

### Шаг 2 — Службы: маскировать паразитов (обратимо)

Правило: `sudo systemctl mask --now <unit>` (mask = симлинк на /dev/null —
надёжнее disable, откат `unmask`). Память освобождается **после перезагрузки**.

**Безопасно маскировать на десктопе (проверено):**

| Службы | Что теряешь | Когда НЕ трогать |
|---|---|---|
| `abrtd`, `abrt-journal-core`, `abrt-oops`, `abrt-vmcore`, `abrt-xorg` | авто-детект крашей и уведомления | если владелец сам шлёт багрепорты |
| `ModemManager` | USB 3G/4G-модемы | есть модем |
| `iscsi-onboot`, `iscsi-starter` | iSCSI-хранилища | используется iSCSI |
| `mdmonitor` | мониторинг software RAID | есть mdadm-RAID (`lsblk`) |
| `lvm2-monitor` | события LVM | используется LVM (`lsblk`) |
| `qemu-guest-agent` | агент для ВМ | система — виртуалка (`systemd-detect-virt`) |
| `intel_lpmd` | энергоэффективность ноутбучных SoC | ноутбук |
| `thermald` | термо-демон Intel | ноутбук с боксовым охлаждением; на десктопах часто и так failed |

**По нужде (спросить владельца):** `cups` (принтер), `bluetooth`, `avahi-daemon`
(mDNS/обнаружение устройств).

**НИКОГДА не маскировать:** `akmods` (сборка драйверов), `nvidia-powerd`,
`chronyd`, `crond`, `irqbalance`, `mcelog`, `firewalld`, `auditd`,
`fips-crypto-policy-overlay`, `gdm`, всё `systemd-*` и `user@`.

### Шаг 3 — GNOME: отклик интерфейса

```bash
# анимации off (мгновенный эффект, откат — true)
gsettings set org.gnome.desktop.interface enable-animations false
# посмотреть расширения — каждое = код, грузящий shell
gsettings get org.gnome.shell enabled-extensions
```

- Расширения с динамическим блюром (blur-my-shell и аналоги) — главные
  пожиратели GPU/CPU: перевести на статический блюр или Hack Level 0
  (в настройках расширения; Level 2 отключает clipped redraws — только для
  «красиво любой ценой»).
- `tracker` (файловый индекс): `systemctl --user is-active ...` — если не
  нужен поиск по файлам, выключить в Настройках → Поиск.

### Шаг 4 (опционально) — Кастомное ядро CachyOS x86_64_v3

Честная оценка: **не «+50%», а единицы-десяток % в узких местах** (SIMD:
сжатие, медиа, научка — до 10-20%; повседневное — ~0; BORE-планировщик —
субъективно резче отклик). Для «летала» — сначала шаги 1-3, ядро — последний штрих.

Проверки ДО установки:

```bash
/lib64/ld-linux-x86-64.so.2 --help | grep "x86-64-v3"   # поддержка CPU (нет — НЕ ставить)
mokutil --sb-state                                        # Secure Boot (нет mokutil = обычно выключен)
rpm -qa | grep akmod-nvidia                               # NVIDIA через akmods? (кастомному ядру нужен akmods)
```

Установка (репо — официальный порт команды CachyOS, не левак):

```bash
sudo dnf copr enable bieszczaders/kernel-cachyos -y
sudo dnf install -y kernel-cachyos kernel-cachyos-devel-matched
sudo setsebool -P domain_kernel_load_modules on          # SELinux: загрузка модулей
```

NVIDIA (akmods собирает kmod сам при установке ядра; проверить/дособрать —
**с полной версией ядра**, короткая не находится):

```bash
ls /boot | grep cachyos                                    # точная версия: 7.x.y-cachyosZ.fcN.x86_64
sudo akmods --force --kernels <полная-версия>
rpm -qa | grep kmod-nvidia                                 # kmod для нового ядра = есть
```

Дефолт в GRUB + откат:

```bash
sudo grubby --set-default /boot/vmlinuz-<cachyos-версия>   # старые ядра остаются в меню
sudo grubby --default-kernel                                # проверить
# откат: выбрать старое ядро в меню GRUB при загрузке, затем:
sudo grubby --set-default /boot/vmlinuz-<старое> && sudo dnf remove kernel-cachyos*
```

### Шаг 5 — Проверка после перезагрузки (владелец перезагружается сам)

```bash
systemd-analyze            # сравнить с замером Шага 0
uname -r                   # ядро (если ставили)
nvidia-smi                 # GPU жив (если NVIDIA)
systemctl --failed         # пусто (маски не падают)
```

## Success criteria

- Загрузка быстрее: `systemd-analyze` до/после (типично 45с → 13с с учётом
  таймаутов; ввод пароля LUKS не считается — см. Gotchas).
- `systemctl --failed` пусто; замаскированные `is-enabled` → `masked`.
- RAM: `free -h` — сотни МБ свободнее после ребута.
- Все правки задокументированы владельцу с командами отката.

## Failure modes

| Что идёт не так | Причина | Что делать |
|---|---|---|
| После маски пропало что-то нужное (печать, BT, модем) | замаскировали «по нужде» без вопроса | `unmask` — вернётся мгновенно |
| Не грузится после правки fstab | опечатка в UUID/опциях | в GRUB выбрать rescue/старое ядро, `mount -o remount,rw /`, вернуть `/etc/fstab.bak-*` |
| Новое ядро встало, но нет графики/драйверов | kmod не собрался под новое ядро | загрузиться старым ядром из GRUB, `sudo akmods --force --kernels <полная-версия>` |
| Кастомное ядро не загрузилось вообще | Secure Boot включён / нет поддержки v3 | выбрать старое ядро в GRUB; SB — отключить или подписать ядро (mokutil) |

## Gotchas (собрано из реальных кейсов)

- **«initrd грузится 30-60с» часто = ввод пароля LUKS, не баг.** Проверка:
  `journalctl -b | grep systemd-cryptsetup` — если между «Starting» и
  «Finished» десятки секунд, а cipher выставлен ближе к концу — ждали пароль.
- **`systemd-analyze blame` показывает время АКТИВАЦИИ device-юнитов** (dev-sda1
  «34s» = диск появился на 34-й секунде, а не ждал 34с). Читать вместе с
  `critical-chain` и journal, не по одному числу.
- **UUID в fstab ≠ UUID на диске** после переформатирования (NTFS→ext4 и т.п.):
  сверять `blkid`/`lsblk -f`, не копировать записи из старых конфигов. Симптом:
  «timed out waiting for device» в journal + `x-systemd.device-timeout=N`.
- **thermald на десктопе часто failed сам по себе** (конфликт с ноутбучными
  демонами/кастомными ядрами) — не чинить, маскировать; на ноутбуке — оставить.
- **Secure Boot-проверка без mokutil:** если проприетарный NVIDIA-модуль уже
  работает без подписи — SB выключен, кастомное ядро встанет без возни.
- **akmods требует ПОЛНУЮ версию ядра** (`7.x.y-cachyosZ.fcN.x86_64`), короткая
  (`7.x.y-cachyosZ`) даёт «Could not find files needed to compile modules».
- **Маски не освобождают RAM до перезагрузки** — не ждать эффекта сразу.
- **`mask --now` на failed-службе** оставит её в `--failed` до ребута — это
  остаточное состояние, не ошибка.
- **Канон-эффект ядра:** выигрыш v3 — bimodal (Phoronix: «handful of workloads
  jump, most barely move»); не обещать «+30-50%» от ядра.
- **Репо CachyOS для Fedora убрало prebuilt NVIDIA-драйверы (с 23.02.2026)** —
  нужен akmods/RPMFusion; COPR-ядра = «баги не в Fedora Bugzilla».
- Доступность ссылок и свежесть команд — проверять веб-ресёрчем (первоисточники
  ниже), а не памятью.

## Available scripts

- `scripts/audit.sh` — read-only аудит одним запуском (ОС, загрузка, службы,
  fstab, память, GPU, ошибки). Ничего не меняет. `--help` для справки.

## References

- Общий гайд по оптимизации Fedora: github.com/winterofhell/fedora-optimizations
- Официальный порт ядра: copr.fedorainfracloud.org/coprs/bieszczaders/kernel-cachyos
- Опыт Fedora-сообщества: discussion.fedoraproject.org (темы: clean-up services,
  slow boot after LUKS unlock / dracut-initqueue)
- Бенчи v3: phoronix.com/review/cachyos-x86-64-v3-v4, разбор «Mixed Bag»:
  sunnyflunk.github.io (x86-64-v3 Mixed Bag of Performance)
- systemd-analyze методика: linuxblog.io/systemd-analyze-debug-optimize-linux-boot
- blur-my-shell performance: deepwiki.com/aunetx/blur-my-shell (Performance Considerations)

## Скрипт `audit.sh`

Применяется по инструкции выше (перенесено дословно).

```sh
#!/usr/bin/env bash
# fedora-speedup: read-only аудит системы перед оптимизацией.
# НИЧЕГО не меняет. Запуск: bash scripts/audit.sh
# Универсальный: работает на любом Linux с systemd (Fedora и подобные).
set -uo pipefail

show_help() {
  cat <<'EOF'
usage: bash scripts/audit.sh [--help]

Read-only аудит для ускорения Linux-десктопа (Fedora/GNOME и подобные):
ОС, время загрузки, медленные unit-ы, enabled-службы (кандидаты на маску),
упавшие службы, fstab vs реальные диски, память/своп, GPU, ошибки загрузки.

Ничего не меняет; привилегий не требует (sudo — только если есть, для GPU).
См. SKILL.md — разделы «Шаг 0» и «Gotchas» (как читать вывод).
EOF
}

[[ "${1:-}" == "--help" || "${1:-}" == "-h" ]] && { show_help; exit 0; }

sec() { printf '\n===== %s =====\n' "$1"; }

sec "ОС"
grep -E "^PRETTY_NAME" /etc/os-release 2>/dev/null || cat /etc/fedora-release 2>/dev/null

sec "ЗАГРУЗКА (общая)"
systemd-analyze 2>/dev/null || echo "systemd-analyze недоступен"

sec "ЗАГРУЗКА (blame, топ-12)"
systemd-analyze blame 2>/dev/null | head -12

sec "ЗАГРУЗКА (critical-chain)"
systemd-analyze critical-chain 2>/dev/null | head -12

sec "СЛУЖБЫ: enabled (кандидаты на маску)"
systemctl list-unit-files --state=enabled --no-pager 2>/dev/null \
  | grep -vE "dbus|getty|systemd-|user@|remote-fs" | awk '{print $1}' | sort | head -60

sec "СЛУЖБЫ: упавшие"
systemctl --failed --no-pager 2>/dev/null | head -10

sec "FSTAB (сверять UUID с lsblk -f!)"
grep -vE "^#|^$" /etc/fstab 2>/dev/null

sec "ДИСКИ (lsblk -f)"
lsblk -f 2>/dev/null | head -14

sec "ПАМЯТЬ"
free -h | head -2
swapon --show 2>/dev/null
echo "swappiness=$(cat /proc/sys/vm/swappiness 2>/dev/null) page-cluster=$(cat /proc/sys/vm/page-cluster 2>/dev/null)"

sec "ВИРТУАЛКА?"
systemd-detect-virt 2>/dev/null || echo "неизвестно"

sec "CPU/GPU"
lspci 2>/dev/null | grep -iE "vga|3d|display" || echo "lspci недоступен"
sudo -n true 2>/dev/null && nvidia-smi --query-gpu=name,driver_version --format=csv 2>/dev/null

sec "ПОДДЕРЖКА x86_64_v3 (для кастомного ядра)"
/lib64/ld-linux-x86-64.so.2 --help 2>/dev/null | grep -E "x86-64-v[23]" || echo "проверить вручную"

sec "ОШИБКИ ЗАГРУЗКИ (journal, tail)"
journalctl -b -p err --no-pager 2>/dev/null | tail -15 || echo "journalctl недоступен"

sec "ТАЙМАУТЫ УСТРОЙСТВ (journal)"
journalctl -b --no-pager 2>/dev/null | grep -iE "timed out|waiting for device" | head -5 \
  || echo "таймаутов не найдено"

sec "LUKS (если есть): сколько ждали пароль"
journalctl -b --no-pager 2>/dev/null | grep -E "systemd-cryptsetup@.*(Starting|Finished)" | head -4 \
  || echo "LUKS не используется или журнал недоступен"

sec "GNOME: расширения (каждое = нагрузка)"
gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "не GNOME"

sec "ИТОГ"
echo "Дальше — SKILL.md: Шаг 1 (таймауты), Шаг 2 (маски служб), Шаг 3 (GNOME)."
echo "НИЧЕГО НЕ МЕНЯТЬ без согласования с владельцем; каждая правка — с откатом."
```
