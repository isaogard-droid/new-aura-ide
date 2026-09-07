---
type: Howto
title: "singbox-tun"
description: "Системный TUN-туннель всего трафика через SOCKS5-прокси на sing-box (Fedora/Linux): установка из официального репо, валидный конфиг 1.13, автозапуск через systemd, авто-переключение прокси, DNS через прокси, грабли синтаксиса sing-box 1.12-1.13"
date: 2026-08-16
tags: [skill-notes, fedora, sing-box, vpn, proxy, tun]
source: skills/singbox-tun/ (перенесено 16.08.2026)
status: stable
---

# singbox-tun — скилл-на-полке (Howto)

Перенесено из `skills/singbox-tun/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: узкий скилл, не в общем пуле). Полная инструкция ниже.

Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->

# singbox-tun — весь трафик системы через прокси (TUN)

Полный туннель на уровне системы: все приложения (браузер, торренты, мессенджеры)
идут через выбранный прокси. Провайдер видит только IP прокси, DNS-запросы
тоже уходят через прокси (домены не видны).

Схема:

```
Приложения → TUN (sing-tun) → urltest (выбор лучшего прокси) → SOCKS5-прокси → интернет
                                   └─ DNS: tls://1.1.1.1 через прокси (домены скрыты)
```

## Установка (Fedora, официальный репозиторий)

```bash
sudo dnf config-manager addrepo --from-repofile=https://sing-box.app/sing-box.repo
sudo dnf install sing-box          # проверка: sing-box version
```

Пакет уже ставит systemd-юнит `/usr/lib/systemd/system/sing-box.service`
с `AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW` и пользователем `sing-box` —
TUN работает БЕЗ запуска от root и без sudo-хаков.

## Конфиг

Файл: `/etc/sing-box/config.json`. Полный рабочий пример (проверен на
1.13.18) — в code-блоке ниже. Ключевые узлы:

- **inbound**: `tun` (`auto_route: true`, `strict_route: true`, `stack: "system"`) — тянет весь трафик
- **outbounds**: SOCKS5 с `username`/`password` (auth поддерживается!) + `urltest` группа для авто-переключения
- **DNS**: `tls://1.1.1.1` с `detour: "auto"` — резолвинг через прокси
- **route**: `final: "auto"` — весь неподпавший под правила трафик в прокси; локальная сеть (`ip_is_private`) — напрямую (чтобы не ломать принтеры/роутер)

```json
{
  "log": { "level": "info", "timestamp": true },
  "dns": {
    "servers": [
      { "type": "tls", "tag": "remote", "server": "1.1.1.1", "detour": "auto" }
    ]
  },
  "inbounds": [
    {
      "type": "tun",
      "tag": "tun-in",
      "interface_name": "sing-tun",
      "address": ["172.19.0.1/30"],
      "auto_route": true,
      "strict_route": true,
      "stack": "system"
    }
  ],
  "outbounds": [
    {
      "type": "socks",
      "tag": "md1",
      "server": "YOUR_PROXY_IP_1",
      "server_port": YOUR_PROXY_PORT_1,
      "version": "5",
      "username": "YOUR_PROXY_USER",
      "password": "YOUR_PROXY_PASS"
    },
    {
      "type": "socks",
      "tag": "md2",
      "server": "YOUR_PROXY_IP_2",
      "server_port": YOUR_PROXY_PORT_2,
      "version": "5",
      "username": "YOUR_PROXY_USER",
      "password": "YOUR_PROXY_PASS"
    },
    {
      "type": "urltest",
      "tag": "auto",
      "outbounds": ["md1", "md2"],
      "url": "http://www.gstatic.com/generate_204",
      "interval": "1m",
      "tolerance": 50
    }
  ],
  "route": {
    "rules": [
      { "action": "sniff" },
      { "ip_is_private": true, "action": "direct" }
    ],
    "final": "auto",
    "default_domain_resolver": "remote"
  }
}
```

## Запуск и проверка

```bash
sudo systemctl enable --now sing-box
systemctl is-active sing-box                 # active
curl -s https://api.ipify.org                # IP прокси (не твой домашний)
ip link show sing-tun                        # интерфейс поднят
journalctl -u sing-box --no-pager -n 20      # логи, если что-то не так
```

Проверка «открывается ли сайт» — ТОЛЬКО через Camoufox (антидетект-браузер),
не curl: curl даёт ложные 403 (TLS-фингерпринт).

## Грабли sing-box 1.12–1.13 (проверено на практике, 08.2026)

| Проблема | Симптом | Решение |
|---|---|---|
| Legacy DNS-серверы | `legacy DNS servers is deprecated... remove in 1.14` | Новый формат: `{"type": "tls", "tag": "x", "server": "1.1.1.1", "detour": "auto"}` вместо `address: "tls://..."` |
| `route.default_outbound` удалён | `unknown field "default_outbound"` | Поле называется **`final`**: `"route": {"final": "auto"}` |
| `direct`/`block` не outbounds | `detour to an empty direct outbound makes no sense` | В 1.11+ это **rule actions**, не outbounds: `{"ip_is_private": true, "action": "direct"}`; из `outbounds` их убрать |
| `sniff` в inbound удалён | `legacy inbound fields are deprecated... removed in 1.13` | Sniff — в route rules: `{"action": "sniff"}` первой записью |
| Нет domain resolver | `missing route.default_domain_resolver... deprecated` | `"route": {"default_domain_resolver": "remote"}` (тег DNS-сервера) |
| DNS-правило по outbound deprecated | `outbound DNS rule item is deprecated` | Просто убрать — весь DNS идёт в `remote` через прокси (даже лучше для приватности) |

Общий принцип: sing-box активно чистит legacy-поля — после установки новой версии
сначала `sing-box check -c /etc/sing-box/config.json`, чинить по `migration` из
доки (sing-box.sagernet.org/migration), а не «на глаз».

## Что важно знать про прокси/VPN (из опыта)

- SOCKS5 с авторизацией: расширения Chrome (FoxyProxy) НЕ умеют auth (в `chrome.proxy`
  API нет полей username/password — доки Chromium) — Firefox умеет. sing-box умеет
  (`username`/`password` в socks-outbound) — поэтому TUN-подход универсален.
- Дата-центр-прокси (NL/ES и т.п.) видны сайтам как «подозрительный IP»:
  HDrezka отдаёт «ERROR 105 — подозрительная активность... если используете VPN —
  смените его». Для пиратских киносайтов нужен чистый (не-дата-центр, не-ЕС) IP —
  молдавский VPS (напр. ServPrivate MD-S, AlexHost — ~$7.50/мес 1 Gbps).
- urltest сам выбирает быстрый прокси (url `http://www.gstatic.com/generate_204`,
  интервал 1м, tolerance 50мс) — можно добавлять сколько угодно прокси/серверов,
  в т.ч. свой VPS (VLESS outbound), и туннель сам выберет лучший.
- Kill-switch: `final: "auto"` + отсутствие direct-outbound для внешнего трафика —
  если прокси упали, соединения не утекают мимо (локальная сеть при этом жива).

## Управление (скрипт `vpnctl`)

`vpnctl` (в AGGG2.0/scripts/, симлинк в ~/.local/bin) — управление вкл/выкл,
автозапуском и сменой прокси через Clash API (мгновенно, без рестарта):

```bash
vpnctl status               # сервис, TUN, активная прокси, внешний IP, автозапуск
vpnctl on | off             # включить/выключить туннель
vpnctl autostart on|off     # автозапуск при старте системы
vpnctl proxy md1|md2|best   # сменить прокси на лету (best = авто-выбор)
vpnctl ip                   # внешний IP через туннель
vpnctl logs [N]             # логи
```

Для этого в конфиге: `experimental.clash_api` (127.0.0.1:9090, secret в
/etc/sing-box/secret, chmod 600) + `selector` "auto" [md1, md2, best(urltest)]
вместо голого urltest — selector позволяет принудительный выбор без рестарта.

## Управление (systemctl, если скрипта нет)

```bash
sudo systemctl stop sing-box    # выключить туннель (трафик пойдёт напрямую)
sudo systemctl restart sing-box # применить новый конфиг
sudo systemctl disable sing-box # убрать из автозапуска
```

aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
