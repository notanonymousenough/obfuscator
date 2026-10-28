# DE1: совместный вход MTProto AZ1 + VLESS/XHTTP

Развёрнут 27.10.2026 по запросу владельца. Существующий MTProto DE1:8888 под x-ui сохраняется. Новый XHTTP работает отдельно от x-ui.

```text
DE1 0.0.0.0:443 — HAProxy, TCP/SNI
  az1.obfuscator.funsociety.dev → 127.0.0.1:9443 → reverse SSH → mtg AZ1
  de1.obfuscator.funsociety.dev (и default) → nginx 127.0.0.1:8444 TLS
                                         → Xray 127.0.0.1:8445 VLESS/XHTTP stream-up
                                         → прямой IPv4-выход DE1
```

## Файлы и сервисы

- `scripts/install-de1.sh`: воспроизводимая установка с предварительной проверкой nginx, Xray и HAProxy; при неудачном старте HAProxy возвращает прежний standalone MTProto socket.
- `config/haproxy-de1.cfg` → `/etc/haproxy/haproxy.cfg`.
- Xray в Docker, `/opt/xray/config.json` и `docker-compose.yml`. Каталог `/opt/xray` mode 0700: локальные пользователи не могут прочитать UUID/path, хотя bind-mounted config внутри контейнера читается его непривилегированным UID.
- `/etc/nginx/sites-available/obfuscator-de1` mode 0600: TLS/nginx и приватный XHTTP path.
- `/etc/obfuscator-xhttp/client-link.txt` и `client.json` mode 0600, каталог 0700. Созданы отдельные от DE2 UUID и path. В репозиторий и вывод инструментов они не выгружались.
- `xray-docker.service`, `nginx.service`, `haproxy.service`, `certbot.timer` — автозапуск.
- Образ Xray закреплён на digest работающего DE2: `ghcr.io/xtls/xray-core@sha256:592ec4d11f656db95598d01e76dbcc6e002d67360b96a5436500a938230f52c7`, версия 26.3.27 Custom.
- SSH DE1 остаётся 2222. UFW: 443 общий TLS, 80 HTTP redirect/ACME; прежние правила существующего MTProto не удалялись.

Сертификат DE1 уже существовал, действителен до **29.11.2026 22:05:15 UTC**. Он используется новым nginx. Добавлен deploy hook для reload nginx. Тест `certbot renew --dry-run` для DE1 прошёл успешно. Файл credentials остаётся на DE1, его значение не выносится.

## Управление

```sh
systemctl status haproxy nginx xray-docker
systemctl stop xray-docker   # выключить только XHTTP; MTProto AZ1 остаётся
systemctl start xray-docker
haproxy -c -f /etc/haproxy/haproxy.cfg
nginx -t
cd /opt/xray && docker compose logs --tail 50 xray
cat /etc/obfuscator-xhttp/client-link.txt  # root; приватная ссылка для клиента
```

Остановка HAProxy выключает оба новых внешних маршрута на 443; старый MTProto 8888 от него не зависит. Остановка туннеля AZ1 выключает только маршрут домена AZ1. Параметры старых отключённых VLESS-входов x-ui не следует включать на 443/8444/8445 поверх новой схемы.

Схема не делает оба публичных сервиса независимыми: общий DE1 IP остаётся общей точкой отказа и потенциальной IP-блокировки. Прохождение из РФ проверяется отдельно.

## Итог проверки

- С независимого DE2 оба домена на DE1:443 получили доверенный TLS 1.3 и HTTP 200; SAN соответствует выбранному SNI.
- Настоящий Xray-клиент с созданным UUID/path, запущенный на DE1, прошёл публичный HAProxy → nginx → VLESS/XHTTP маршрут. Запрос через SOCKS получил внешний IP **159.89.12.205**. Приватные параметры не выносились с сервера; временный клиентский контейнер и его конфиг удалены.
- `certbot renew --dry-run --cert-name de1.obfuscator.funsociety.dev` — успешно.
- `sshd -T` подтвердил ограничения туннельного пользователя; обратный SSH AZ1 восстановился после принудительного завершения процесса.
- systemd failed units отсутствуют. Старый MTProto 8888 продолжает слушать.
- Вход из РФ, реальный мобильный MTProto-клиент и звонки пока не проверены. Для повторного локального XHTTP-теста есть `scripts/verify-de1.sh`.
