---
type: Howto
title: disk-formatting
description: "Format, repartition and mount disks/partitions on Fedora Linux (ext4, btrfs, NTFS, FAT32, exFAT). Use when the user asks to format a disk, create a partition, fix a read-only NTFS"
date: 2026-08-16
tags: [skill-notes, fedora, disk, ext4, btrfs]
source: skills/disk-formatting/ (перенесено 16.08.2026)
status: stable
---

# disk-formatting — скилл-на-полке (Howto)

Перенесено из `skills/disk-formatting/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже — дословно.

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->


# Disk formatting on Fedora

Workflow: identify → unmount → format → mount → fstab (if internal) → verify write.

## Safety rules

- **ALWAYS run `lsblk -f` first and confirm the exact device with the user before any destructive command.**
- Reformatting erases ALL data. Warn explicitly and list what the user will lose. Ask for confirmation with the `question` tool when the target holds data.
- Never format a mounted filesystem or the system disk (check `lsblk -f` MOUNTPOINTS: `/`, `/home`, `/boot` are system).
- Double-check that `sdb1` in the plan really is the user's data disk, not the installer stick or another disk with data.
- Use `sudo -n` first; if it fails, use plain `sudo` (user's password prompt).
- After `mkfs`, run `sync`.

## Why a disk can't be written to (check BEFORE reformatting)

Reformatting is the LAST resort, not the first fix. Most "can't create folder" cases have a non-destructive fix:

1. **NTFS mounted read-only** (`mount | grep fuseblk` shows `(ro,...)`, journal shows ntfs-3g "Read-Only"): the volume has a "dirty" flag from Windows fast startup / hibernation / unclean shutdown. Fix WITHOUT data loss:
   - `umount /dev/sdXN` (or `udisksctl unmount -b /dev/sdXN`)
   - `sudo ntfsfix /dev/sdXN` (clears dirty flag, does not touch data)
   - Remount (replug or `udisksctl mount -b /dev/sdXN`) and verify with `touch`.
   - Still read-only? Windows-side fix: disable Fast Startup (powercfg /h off, or Control Panel → Power → Choose what power buttons do), run `chkdsk X: /f`.
2. **vfat/FAT32 small files or old disk** — filesystem fine but size limits (file > 4 GB impossible). Fix: exFAT or NTFS.
3. **ext4 "read-only file system"**: `sudo dmesg | tail` for I/O errors; check SMART `sudo smartctl -a /dev/sdX`. A dying disk must not be reformatted — copy data first.
4. **Permissions**: dirs owned by root (`sudo chown -R $USER:$USER <dir>`).

## Identify the disk

```bash
lsblk -f
# FSTYPE shows current fs, MOUNTPOINT shows if mounted
sudo blkid /dev/sdXN          # exact type/UUID
```

## Unmount

```bash
umount /dev/sdXN               # if automounted under /run/media/...
udisksctl unmount -b /dev/sdXN # alternative
```

## Format

| Goal | Command | Notes |
| --- | --- | --- |
| Fedora data disk | `sudo mkfs.ext4 -F -L DATA /dev/sdXN` | recommended for plain storage |
| Fedora system-ish | `sudo mkfs.btrfs -f -L DATA /dev/sdXN` | snapshot/compression (Fedora root is btrfs) |
| NTFS (Windows compat) | `sudo mkfs.ntfs -f -L DATA /dev/sdXN` | needs `ntfs-3g` package |
| exFAT (USB, >4GB files, cross-platform) | `sudo mkfs.exfat -n DATA /dev/sdXN` | needs `exfatprogs` |
| FAT32 (small USB) | `sudo mkfs.fat -F 32 -n DATA /dev/sdXN` | file size limit 4 GB |

**Permission note**: `mkfs.ext4` without sudo fails with "Отказано в доступе" — always run with sudo.

## Mount + ownership

```bash
sudo mkdir -p /home/$USER/DATA
sudo mount /dev/sdXN /home/$USER/DATA
sudo chown $USER:$USER /home/$USER/DATA
```
Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


Do NOT pass `uid=`/`gid=` to `mount` for ext4 — ext4 rejects unknown options (`Unknown parameter 'uid'`). chown after mount instead. `uid=1000` belongs to FAT/exFAT mounts only.

## Auto-mount at boot (internal disks) — /etc/fstab

```bash
UUID=$(sudo blkid -s UUID -o value /dev/sdXN)
echo "UUID=$UUID /home/$USER/DATA ext4 defaults,noatime,nofail,x-systemd.device-timeout=10 0 2" | sudo tee -a /etc/fstab
```

- `nofail` + `x-systemd.device-timeout=10`: no boot hang if the disk is absent.
- Verify: `grep -v "^#" /etc/fstab | tail`, then `sudo systemctl daemon-reload`.

## Verify write

```bash
mkdir -p /home/$USER/DATA/test && touch /home/$USER/DATA/test/file.txt && echo OK && rm -rf /home/$USER/DATA/test
lsblk -f /dev/sdX
```

## NTFS quirks after formatting

- ntfs-3g (FUSE) automounts via udisks2 under `/run/media/<user>/<UUID>`; if dirty flag set it mounts read-only — see "Why a disk can't be written to".
- `ntfsfix -n` is dry-run check; real fix is `ntfsfix` without `-n`.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
