# AZ1: Cloudflare Tunnel, 30.10.2026

Рабочий публичный вход: `az1.funsociety.dev:443`, VLESS/XHTTP/TLS,
SNI `az1.funsociety.dev`, path `/obfuscator-xhttp-az1`, mode `packet-up`, ALPN h2.
UUID сохранён; профиль AZ1 обновлён в действующей подписке на DE1.

Двухуровневое имя `az1.obfuscator.funsociety.dev` не покрывается бесплатным
Universal SSL для зоны funsociety.dev. Его исходная A-запись восстановлена.
Новый короткий hostname имеет proxied CNAME на именованный tunnel.

## Цепочка

Телефон (существующий XHTTP-клиент) -> Cloudflare TLS edge -> QUIC tunnel ->
cloudflared на AZ1 -> nginx 127.0.0.1:18080 -> Xray 127.0.0.1:8445 -> интернет AZ1.
Cloudflare завершает внешний TLS; это HTTP reverse proxy, а не прозрачный TCP.
На сервере XHTTP mode=auto разрешает packet-up и прежний stream-up.
Старый DE1 relay сохранён для сравнения/отката, не является новым входом AZ1.
MTProto:8888 и его DNS не изменены, работают только на DE1. MTProto через Cloudflare не публикуется.

## Сервис и файлы

- cloudflared 2026.10.6 arm64, SHA256
  `0ae0e179475b2c77651a718d2b376e0151f4fca5954702a84f02843a4d5fcac0`.
- systemd `obfuscator-cloudflared.service`: enabled, Restart=always.
- `/etc/cloudflared/az1.token`: root-only 0600, не выводить в журналы.
- `/etc/nginx/sites-available/obfuscator-cloudflare`, loopback-only :18080.
- исходник origin: `Subscriptions/config/nginx-az1-tunnel.conf`.
- installer: `Subscriptions/scripts/install-az1-cloudflare-tunnel.sh`.
- Старые `obfuscator-vpn-ddns.timer` и `obfuscator-ddns.timer` выключены:
  их нельзя включать для нового tunnel hostname.
- Cloudflare API state и исходные DNS-записи сохранены в игнорируемом `.secrets/`.
- Серверные исходные конфиги сохранены в `/var/backups/obfuscator-cloudflare-*`.

## Проверки

Первичные проверки с DE2 и AZ1: по 10 новых Xray-процессов на маршрут,
запрос HTTPS generate_204 через SOCKS/XHTTP до gstatic. Медиана полного запроса:
AZ1 CF 597 мс (10/10), DE1 relay 1098 мс (8/10);
DE2 CF 615 мс (10/10), DE1 relay 738 мс (9/10).
Это не ping и не гарантия для мобильной сети в РФ.
Дополнительно verify-vpn из AZ1: 20/20 запросов к двум HTTPS-целям.
Первый дополнительный долгоживущий тест имел один неудачный старт;
последующие 30/30 запросов прошли. Speed.cloudflare.com вернул 403,
поэтому длительную передачу проверяем собственным временным файлом.
Краткий тест не доказывает многосуточную стабильность.

Расширенная проверка DE2: 49/50 новых соединений, медиана 493 мс,
максимум успешного запроса 1505 мс. Длительная загрузка собственного файла
12 000 000 байт с ограничением 100 KiB/s оборвалась: curl 92, HTTP 200,
10 649 600 байт за 104.45 с. После неё 27/30 запросов успешны.
stream-up не прошёл, в том числе отдельный опыт с noGRPCHeader.
Оставлен packet-up. Пилот работает, но критерий надёжности длительных сессий
не пройден; нельзя представлять его как стабильную замену прямого входа.
Временный тестовый файл и location удалены. Сервис tunnel перезапущен
для проверки восстановления. Численные результаты:
`Subscriptions/snapshot/cloudflare-az1-2026-10-30.json`.

## Эксплуатация и откат

`systemctl status obfuscator-cloudflared`,
`journalctl -u obfuscator-cloudflared --since '-10 minutes'`.
Публичный probe `https://az1.funsociety.dev/.well-known/obfuscator-node`
должен вернуть `obfuscator-az1`, затем проверять именно авторизованный XHTTP.

При откате сначала вернуть профиль AZ1 в реестре подписки из сохранённой копии,
затем остановить tunnel и удалить только новый CNAME. MTProto DNS/порт не менять.
Старый origin и reverse SSH в DE1 сохранены. Native Xray config при необходимости
восстанавливается из серверной резервной копии с валидацией перед restart.
Для полного восстановления старого DNS-поведения вернуть исходное состояние timers;
на новом tunnel hostname динамический A-DDNS не нужен.
