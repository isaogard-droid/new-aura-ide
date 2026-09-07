# 2026-08-17 VPN vs прокси: что видит провайдер, режимы vpn-gui

## Вопрос

Для проекта vpn-gui: (1) использует ли VPN-режим тот же TUN, что и прокси-режим
(план: свой VPS + Xray VLESS+Reality); (2) «VPN = фулл анонимность» — правда ли;
(3) видит ли провайдер что-то при работе через SOCKS5-прокси; (4) должны ли
режимы VPN и Прокси быть раздельными, без фоллбэков друг на друга.

## План / под-вопросы

1. Что видит ISP при VPN (метаданные, содержимое, DNS, fingerprint протокола).
2. Что видит ISP при SOCKS5-прокси (шифруется ли SOCKS5, SNI, DNS, X-Forwarded-For).
3. VLESS+Reality: что видит DPI/провайдер, чем отличается от OpenVPN/WireGuard.
4. VPN ≠ анонимность: fingerprint браузера, платёж, correlation-атаки.
5. Один TUN-интерфейс vs несколько: конфликты, паттерн sing-box.
6. Kill switch / fail-closed: что делает индустрия при падении туннеля.
7. Сверка с кодом vpn-gui: apply_mode, parse_share_link, killswitch.

## Источники

Первоисточники и независимые обзоры, загружены через Camoufox 17.08.2026
(12 поисков + 5 батчей; ниже — успешно загруженные, 34 шт.).

### ISP + VPN (что видит/не видит)

- nordvpn.com/blog/can-isp-see-vpn/ — ISP видит: факт VPN, IP сервера, протокол,
  время, объём. Не видит: сайты, содержимое, DNS (в туннеле).
- howtogeek.com/isp-knows-vpn-use/ — VPN-сигнатура (равномерные пакеты), DNS-leak
  как главная утечка, ISP может трекать расписание подключений.
- surfshark.com/blog/can-isp-see-vpn — таблица «видит/не видит»; поисковые запросы
  и загрузки скрыты, факт подключения виден.
- expressvpn.com/blog/vpn-vs-isp-who-can-you-trust/ — без VPN ISP видит домены
  (DNS), с VPN — только туннель; ISP остаётся точкой наблюдения метаданных.
- cyberghostvpn.com/privacyhub/can-isp-see-vpn/ — подтверждает: IP VPN-сервера,
  протокол, метаданные видны; содержимое и домены — нет.
- whatismyip.io/learn/can-my-isp-see-my-vpn — «ISP видит, что трафик идёт в туннель;
  содержимое и конечные домены — обычно нет»; VPN-оператор становится точкой доверия.
- factually.co (metadata ISP + VPN) — сводка: метаданные подключения остаются
  (IP/порт/время/объём); DNS-leak и отсутствие kill switch — реальные экспозиции;
  провайдер VPN, не ISP, видит богаче метаданные при наличии логов.
- cyberfenceplatform.com/blog/can-isp-see-vpn — ISP видит использование VPN и
  протокол, не видит сайты; в США ISP может продавать данные без VPN.

### Прокси (SOCKS5): шифрование и видимость

- security.stackexchange.com/questions/135949 — SOCKS5 не шифрует: «everything is
  plain text»; «anybody able to sniff the connection can see what you are doing»
  (Steffen Ullrich).
- superuser.com/questions/1048861 — прокси обычно не шифрует; может добавлять
  X-Forwarded-For с исходным IP.
- enigmaproxy.net/blog/proxy-encryption-tls-socks5-layers — слои: SOCKS5 не имеет
  собственного шифрования; TLS защищает только внутри своей сессии; SNI виден
  наблюдателю без ECH.
- mullvad.net/en/help/socks5-proxy — «SOCKS5 protocol itself does not include
  encryption»; у Mullvad трафик зашифрован только потому что прокси живёт ВНУТРИ
  туннеля WireGuard (подтверждение: сам по себе SOCKS5 не шифрует).
- geeksforgeeks.org/computer-networks/proxy-vs-vpn-difference/ — прокси маскирует
  IP, не шифрует; VPN шифрует всё.
- cyberfenceplatform.com/blog/vpn-vs-proxy — «на прокси трафик между устройством и
  прокси идёт открытым текстом; ISP видит его»; прокси — приложение-уровень,
  VPN — системный уровень.
- secureguides.com/vpn-vs-proxy-7-steps-to-better-security/ — «Proxy uses none —
  traffic is readable by anyone between you and the proxy server»; прокси-режим
  достаточен только для простого гео-обхода.

### VLESS + Reality

- kovravpn.com/guides/vless-reality-protocol — Reality крадёт реальную TLS-идентичность
  (ClientHello как у браузера, подлинная цепочка сертификатов), активный probing
  возвращает настоящий сайт; OpenVPN/WireGuard — узнаваемые сигнатуры.
- dopplervpn.org/en/blog/vless-reality-explained — «сессия неотличима от HTTPS к
  реальному сайту»; DPI классифицирует по сигнатурам — Reality не даёт сигнатуры.
- plisio.net/cybersecurity/vless-protocol — VLESS не шифрует сам (encryption:none),
  всю конфиденциальность даёт транспорт (TLS 1.3/Reality); единственный протокол,
  который DPI «ещё не победил» (mid-2026); Xray 38.6k stars.
- core-tutorial.argsment.com/singbox/reality — точная структура sing-box outbound:
  tls.reality = {enabled, public_key, short_id}; fingerprint — в tls.utls; uTLS
  почти обязателен для Reality (иначе Go-fingerprint выдаёт туннель).
- sing-box.sagernet.org/configuration/outbound/vless/ — официальная спека vless
  outbound (flow xtls-rprx-vision, tls, transport).

### VPN ≠ анонимность

- purevpn.com/blog/does-a-vpn-prevent-browser-fingerprinting/ — fingerprint
  идентифицирует с точностью до 99% даже за VPN; VPN не трогает атрибуты браузера.
- vpncritic.com/vpns-do-not-guarantee-online-anonymity/ — canvas/WebGL/fonts
  стабильны 85-92% при смене IP (исследование 2026); correlation-атаки масштабируются
  (RevealNet, IEEE 2025); WebRTC и SNI — утечки, не закрытые VPN.
- factually.co (metadata) — VPN-оператор — новая точка доверия: при логах видит
  то, что раньше видел ISP.

### TUN, режимы, kill switch, fail-closed

- deepwiki.com/SagerNet/sing-box/4.1-tun-interface-and-transparent-proxying — один
  TUN-инбаунд перехватывает системный трафик; выбранный outbound определяет выход
  (TUN — не «один сервер», а точка входа).
- sing-box.sagernet.org/configuration/inbound/tun/ — официальная спека tun
  (auto_route, dns_mode hijack).
- singbox-internals.hidandelion.com/protocols/groups.html — selector: ручной
  выбор, НЕТ автоматического failover между outbound (urltest — по латентности);
  при падении выбранного outbound соединения рвутся, но не «перетекают» на другие.
- hiddify/hiddify-app issue #2232 — 2 TUN-клиента/нестабильный TUN на Linux:
  конфликт роутинга, DNS-падения; на десктопе дефолт — systemProxy, не TUN.
- caffeineproject.itch.io (fail-closed proxy) — fail-closed (отказ обслуживать
  трафик при недоступности выхода) = тот же уровень защиты, что kill switch.
- vpncritic.com/vpn-kill-switch-failures-explained/ — kill switch может «казаться
  активным» и пропускать трафик; важен fail-closed и тест при обрыве.
- qalvpn.com/blog/vpn-kill-switch-guide/ — «objective is fail-closed, not best
  effort»; частичные правила/гонки = окна утечки; статус в UI + тесты обрыва.
- cybershieldtips.com (kill switch guide 2026) — без kill switch после обрыва ОС
  молча возвращается на прямую связь — реальный IP утекает; kill switch это
  предотвращает.
- comparitech.com + nordvpn.com + wundertech.net + scalefusion.com (split vs full
  tunnel) — full tunnel = весь трафик в туннель (дефолт «серьёзных» VPN), split =
  выборочный; для защиты от провайдера — full.
- deepwiki.com/SagerNet/sing-box/3.3-outbound-configuration — outbound-архитектура
  sing-box (типы, detour, цепочки).

### Отсеянное и почему

- Reddit r/VPN, r/VPNHacks — заблокированы для ботов (network security block),
  факты продублированы StackExchange/обзорами.
- gist.github.com/im-Qarch (hiddify TUN-конфликт) — не загрузился; вывод по
  конфликту TUN подтверждён issue #2232 (первоисточник).
- premier VPN/runvpn/duduvpn/fiery.host (vless-reality обзоры) — маркетинговые
  пересказы, взяты 3 независимых технических (kovravpn, dopplervpn, plisio).
- Спека sing-box shared/tls обрезалась в выдаче — структура reality подтверждена
  core-tutorial (по option/tls.go, pinned v1.13.15) — первоисточник кода.

## Выводы

- **Один TUN:** в vpn-gui один sing-box держит один `sing-tun`; режимы меняют
  только `route.final` (выход). Поднятие VPS Xray = новый vless outbound, второй
  TUN не нужен и вреден (конфликты роутинга, issue #2232).
- **VPN ≠ фулл анонимность.** VPN (даже VLESS+Reality на своём VPS) скрывает
  от ПРОВАЙДЕРА: тот видит лишь IP сервера + объём + время, DPI — обычный HTTPS.
  Анонимность не достигается: VPS-провайдер видит весь трафик и платёж,
  fingerprint браузера стабилен 85-92%, correlation-атаки реальны (RevealNet 2025).
- **Прокси — провайдер видит:** факт подключения к прокси, IP прокси, объём,
  время; при HTTPS — SNI/домены (TLS сквозь прокси, ECH редок); при HTTP —
  содержимое целиком; DNS вне туннеля — домены. Владелец прокси видит всё
  (вплоть до X-Forwarded-For). Ответ на вопрос юзера: ДА, видит.
- **Режимы раздельны — уже так:** proxy → final=auto (фоллбэк только между
  прокси, не на direct), vpn → final=строго vpn_tag, DNS detour туда же; kill
  switch nftables fail-closed (policy drop); selector не делает авто-failover.
  Это соответствует индустрии (fail-closed — QAL, caffeineproject).
- **Найдено в коде:** parse_share_link не парсил pbk/sid/fp из vless://reality —
  ссылка добавилась бы, но не подключилась. Исправлено в этой задаче.

- findings: id=780 (вердикты), id=781 (пробел reality-парсинга).
