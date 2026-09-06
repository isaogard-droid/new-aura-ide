---
type: Howto
title: zram-optimize
description: "Optimize zram compressed swap on any Linux (Fedora/Arch/CachyOS/RHEL with systemd-zram-generator, Ubuntu with zram-tools). Use when the user says 'настрой zram', 'сжатый своп', 'ка"
date: 2026-08-16
tags: [skill-notes, fedora, zram, swap, memory]
source: skills/zram-optimize/ (перенесено 16.08.2026)
status: stable
---

# zram-optimize — скилл-на-полке (Howto)

Перенесено из `skills/zram-optimize/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже — дословно.

Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->

# zram swap optimization (universal)

Проверено: Fedora 44 (systemd-zram-generator, 16G RAM). Работает на любом systemd-Linux. Результат: zram RAM/2 на zstd (~3.4:1), swappiness 150, page-cluster 0 — холодные страницы жмутся в RAM, свободная память идёт под page cache.

## Формула размера (главное)

```
zram-size (MB) = RAM (MB) / 2
```

| RAM | zram-size | пример |
|---|---|---|
| 8G | 4096 | ноутбук |
| 16G | 8192 | этот стенд, VPS 16GB |
| 32G | 16384 | ПК-референс (CachyOS) |
| 64G | 32768 | (кап дефолта Fedora — 8192, больше — только явным конфигом) |

- **Реальная память при полном заполнении** ≈ zram-size / ratio: zstd ~3.37 → 8192MB ≈ 2.4G реальных (lzo-rle 2.74, lz4 2.63 — benchmark r/Fedora).
- Fedora-дефолт (zram-generator-defaults): `zram-size = min(ram, 8192)` → для ≤16G это и есть RAM/2, но с **lzo-rle**.
- Десктоп/ноутбук — RAM/2. VPS/сервер с большим RAM — RAM/2 тоже норм, при нехватке CPU можно RAM/4.

## Значения (и почему)

| Параметр | Значение | Обоснование |
|---|---|---|
| `compression-algorithm` | `zstd` | ratio 3.37 против 2.74 у lzo-rle (+~20% памяти); медленнее на декомпрессии, но читает меньше. lz4 — если CPU совсем слабый (быстрее, ratio 2.63) |
| `vm.swappiness` | `150` (до 180) | kernel docs: для in-memory swap (zram/zswap) разрешены значения >100; «random I/O быстрее NVMe в 10+ раз» → ядро охотно сбрасывает anon-страницы в сжатый zram, RAM освобождается под кэш. CachyOS-референс использует 150, kernel maintainers рекомендуют 180 |
| `vm.page-cluster` | `0` | дефолт 3 — это swap-readahead с 2005 года для дисков. Для zram: читать по одной странице (ChromeOS по умолчанию, практика Android). Для zstd выигрыш в латентности, readahead не даёт выигрыша |
| `swap-priority` | `100` | выше дискового swap (обычно -2/10) — zram используется первым |

## Шаги (готовый скрипт — ниже)

1. `bash scripts/apply-zram.sh [--dry-run] [zram_size_mb]` — определяет механизм (zram-generator vs zram-tools), считает размер по формуле RAM/2, пишет конфиг + sysctl, применяет sysctl сразу. Требует sudo.
2. Если zram не включён вообще: поставить `systemd-zram-generator` (dnf/pacman) или `zram-tools` (apt) — скрипт сам скажет, чего не хватает.
3. **Перезагрузка** для смены размера/алгоритма (генератор пересоздаёт /dev/zram0 на старте).
4. Проверка: `zramctl` (алгоритм/размер/использование), `swapon --show`, `cat /proc/sys/vm/swappiness /proc/sys/vm/page-cluster`, `free -h`.

## Безопасность применения (важно)

- **НЕ перезапускать zram на живой системе**, если в swap есть данные и свободной RAM мало: `swapoff` втянет 2G+ обратно в RAM → OOM-килл. Алгоритм/размер меняются только ребутом.
- sysctl (swappiness/page-cluster) применяются **мгновенно** — `sysctl -w` или `sysctl --system` после записи файла в /etc/sysctl.d/.
- swappiness 150 НЕ для дискового swap (только zram/zswap — там это катастрофа: дисковый thrash).
- page-cluster 0 НЕ для дискового swap (потеря readahead на HDD/SSD).
Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


## Диагностика текущего состояния

```bash
zramctl                    # алгоритм/размер/использование
swapon --show              # swap-устройства, приоритеты
cat /proc/sys/vm/swappiness /proc/sys/vm/page-cluster
cat /etc/systemd/zram-generator.conf /usr/lib/systemd/zram-generator.conf 2>/dev/null
```

Частая картина на Fedora: zram есть (дефолт, lzo-rle, min(ram,8192)), но swappiness=10 и page-cluster=3 — параметры для дискового swap, zram недожат.

## Когда НЕ использовать

- Машина с дисковым swap и без zram → другое решение (swappiness 10, page-cluster 3).
- Слабое CPU + очень нагруженная память (VPS 1 vCPU): zstd съедает CPU — рассмотреть lz4.
- Есть zswap с активным дисковым spill → swappiness 50-100, не 150.

## Available scripts

- `scripts/apply-zram.sh [--dry-run] [zram_size_mb]` — идемпотентный установщик: RAM/2-формула, zstd, swappiness 150, page-cluster 0, поддержка zram-generator и zram-tools, --dry-run.

## References

- Kernel docs (zram, swappiness >100 для in-memory swap, page-cluster): https://docs.kernel.org/admin-guide/blockdev/zram.html и https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html
- ArchWiki Zram (высокий swappiness для zram — идеален): https://wiki.archlinux.org/title/Zram
- Benchmark алгоритмов + page-cluster (zstd 3.37, lz4 2.63, lzo-rle 2.74): https://www.reddit.com/r/Fedora/comments/mzun99/new_zram_tuning_benchmarks/
- zram-generator конфиг: https://github.com/systemd/zram-generator
- Ubuntu zram-tools (/etc/default/zramswap): https://github.com/oerv/ecryptfs-utils  (zram-tools: /usr/bin/zramswap, ALGO/PERCENT/PRIORITY)

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->

## Скрипт `apply-zram.sh`

Применяется по инструкции выше (перенесено дословно).

```sh
#!/usr/bin/env bash
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Universal zram swap optimization (systemd + zram-generator; Ubuntu: zram-tools).
# Idempotent, non-interactive, agent-safe. Needs root (sudo).
# Usage:
#   bash scripts/apply-zram.sh [--dry-run] [zram_size_mb]
#   ZRAM_SIZE_MB=8192 bash scripts/apply-zram.sh     # явный размер
set -u

DRY=0
[ "${1:-}" = "--dry-run" ] && { DRY=1; shift; }
ZRAM_MB="${1:-}"
[ -z "$ZRAM_MB" ] && ZRAM_MB="${ZRAM_SIZE_MB:-}"

say()  { printf '[zram] %s\n' "$*"; }
run()  { say "> $*"; [ "$DRY" -eq 0 ] && "$@"; }

# --- RAM ----------------------------------------------------------------
MEM_KB=$(awk '/^MemTotal/{print $2}' /proc/meminfo)
MEM_MB=$((MEM_KB / 1024))
if [ -z "$ZRAM_MB" ]; then
  ZRAM_MB=$((MEM_MB / 2))     # формула: RAM/2
  # cap как у Fedora-дефолта: min(ram/2, 8192) для <=16G; для >16G разрешаем RAM/2
fi
say "RAM: ${MEM_MB}MB ($((MEM_MB / 1024))G) → zram-size = ${ZRAM_MB}MB ($((ZRAM_MB / 1024))G)"
say "Реальная память при полном заполнении ≈ ${ZRAM_MB}MB / 3.4 (zstd) ≈ $((ZRAM_MB * 100 / 340))MB"

# --- какой механизм на дистрибутиве --------------------------------------
if systemctl list-unit-files 2>/dev/null | grep -q '^systemd-zram-setup@'; then
  MODE=zram-generator
elif [ -x /usr/bin/zramswap ] || [ -f /etc/default/zramswap ]; then
  MODE=zram-tools
else
  MODE=unknown
fi
say "механизм: $MODE"

# --- 1. конфиг zram ------------------------------------------------------
case "$MODE" in
  zram-generator)
    run sudo tee /etc/systemd/zram-generator.conf >/dev/null <<EOF
# zram: RAM/2, zstd (сжатие ~3.4:1 против 2.7 у lzo-rle), приоритет выше дискового swap
[zram0]
zram-size = $ZRAM_MB
compression-algorithm = zstd
swap-priority = 100
EOF
    say "Применится при ПЕРЕЗАГРУЗКЕ (размер/алгоритм). Живой перезапуск zram опасен при занятом swap (OOM) — не делать при низкой free RAM."
    ;;
  zram-tools)
    run sudo tee /etc/default/zramswap >/dev/null <<EOF
ALGO=zstd
PERCENT=50
PRIORITY=100
EOF
    say "Применится при перезапуске службы zramswap (systemctl restart zramswap)."
    ;;
  *)
    say "не найден ни zram-generator, ни zram-tools. Установи: dnf install systemd-zram-generator (Fedora) / pacman -S zram-generator (Arch) / apt install zram-tools (Ubuntu)."
    ;;
esac

# --- 2. sysctl (применяется СРАЗУ) ---------------------------------------
run sudo tee /etc/sysctl.d/99-zram-vm.conf >/dev/null <<'EOF'
# zram-оптимизации: высокая swappiness (сжатый своп в RAM быстрее диска —
# ядро разрешает >100 для in-memory swap), чтение по одной странице
vm.swappiness = 150
vm.page-cluster = 0
EOF
if [ "$DRY" -eq 0 ]; then
  sudo sysctl -w vm.swappiness=150 vm.page-cluster=0
fi

# --- 3. проверка ----------------------------------------------------------
say "проверка: zramctl; cat /proc/sys/vm/swappiness /proc/sys/vm/page-cluster"
if [ "$DRY" -eq 0 ]; then
  zramctl || true
  printf 'swappiness=%s page-cluster=%s\n' "$(cat /proc/sys/vm/swappiness)" "$(cat /proc/sys/vm/page-cluster)"
fi
say "готово. swappiness/page-cluster работают сразу; алгоритм zstd — после ребута."


# Создано и поддерживается: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая новая версия — уникальная и лучшая.

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
```
