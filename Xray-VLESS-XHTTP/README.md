# Xray VLESS XHTTP: схема DE2

Название транспорта — **XHTTP**, не XHTCP. Здесь зафиксировано существующее развёртывание DE2 и подготовлены шаблоны восстановления без клиентских секретов. Работа из РФ подтверждена владельцем; в ходе аудита проверялись сервисы, HTTPS и сертификат, но не клиентская VLESS-сессия.

Дополнительно развёрнут [DE1 с совместным SNI-входом XHTTP и MTProto AZ1](DE1.md). DE2 остаётся исходным работающим образцом.

## Текущее состояние 27.10.2026

```text
VLESS/XHTTP клиент → de2.obfuscator.funsociety.dev:443
                  → nginx TLS 1.3 / HTTP2
                  → grpc_pass 127.0.0.1:8443
                  → Xray в Docker, inbound VLESS/XHTTP stream-up
                  → freedom, UseIPv4 → интернет
```

Публичный IPv4: `164.92.246.64`. SSH: `deploy@de2.obfuscator.funsociety.dev:2222` через pipe. На сервере также есть IPv6, но публичной AAAA-записи при аудите не было.

Факты, выгруженные по строгому списку безопасных полей, находятся в [snapshot/de2-public-state-2026-10-27.json](snapshot/de2-public-state-2026-10-27.json). UUID, XHTTP path, ключи и токены не экспортировались. Шаблоны в `config/` — реконструкция проверенной схемы, а не побайтовый backup действующих файлов.

- `/opt/xray/config.json`: один VLESS-клиент, localhost:8443, XHTTP `stream-up`, TLS внутри не используется.
- `/opt/xray/docker-compose.yml`: `ghcr.io/xtls/xray-core:latest`, `network_mode: host`, `restart: always`, read-only mount конфига.
- `/etc/systemd/system/xray-docker.service`: `docker compose up -d`, oneshot+RemainAfterExit, включён.
- `/etc/nginx/sites-available/xray.conf`: внешний TLS, `grpc_pass` на localhost, тайм-ауты 1h, decoy сайт, HTTP→HTTPS redirect.
- Сертификат Let's Encrypt домена DE2 действителен до **02.12.2026 21:03:40 UTC**; certbot.timer активен.
- Старые x-ui и нативный xray.service отключены. На диске остались их файлы и отдельный домашний конфиг: они не являются текущей Docker-конфигурацией.
- IPv4 forwarding включён; BBR/fq активны. Используется netfilter-persistent; UFW-файлы остались, но UFW unit отсутствует.
- Приватные назначения `geoip:private` заблокированы; внешний выход принудительно IPv4.

## Что было сделано ранее

По APT и истории: первоначальная панель x-ui, эксперименты с REALITY, Certbot с Cloudflare DNS plugin, изменения firewall, отдельная установка Xray и ручные запуски. В начале сентября конфигурация была перенесена на Docker с nginx и системным compose unit. В текущей работе живой DE2 не переустанавливается; его работающая схема документируется. Подробности также есть в `../server-audit-2026-10-27.md`.

## Токены и сертификаты

Cloudflare token используется серверной автоматизацией DNS-01 для доказательства владения доменом. Он **не является VLESS UUID** и не передаётся VPN-клиенту. Клиенту нужны адрес, порт, UUID, XHTTP path, режим транспорта и настройки TLS. XHTTP path здесь заменён плейсхолдером, поскольку относится к данным подключения.

На DE2 исторически использовался `/etc/letsencrypt/cloudflare.ini`. Актуальные credentials и параметры renewal надо читать на самом сервере с root, не сохранять в git. В проекте `.cloudflare` и все `secrets/` игнорируются.

Права токена: Zone/DNS Edit и Zone Read для нужной зоны. Credentials mode 0600 root:root. Сертификат получают, например:

```sh
sudo certbot certonly --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  --dns-cloudflare-propagation-seconds 60 \
  --cert-name de2.obfuscator.funsociety.dev \
  -d de2.obfuscator.funsociety.dev
```

Наличие certbot.timer не гарантирует, что nginx загрузит обновлённый сертификат. При аудите каталог `renewal-hooks/deploy` был пуст. Подготовлен `scripts/reload-nginx-after-renewal.sh`; перед установкой надо проверить, не задан ли эквивалентный deploy hook в renewal-конфиге. Установка hook на DE2 пока не выполнялась. Проверка: `certbot renew --dry-run` и `nginx -t`.

## Шаблоны и восстановление

```sh
python3 scripts/render.py --output secrets/new-deployment
```

Создаст новый UUID и path и запишет приватные файлы mode 0600. Можно явно передать существующие значения через `--uuid` и `--path`, но не следует помещать секреты в shell history. По умолчанию создаются **новые** данные подключения, которые не работают с действующим DE2 до изменения сервера. Для воспроизведения старых клиентов следует восстановить прежние значения из защищённого server-side backup.

Порядок развёртывания на новом сервере:

1. Установить Docker Engine/Compose из официального репозитория и nginx, Certbot, Cloudflare DNS plugin. Настроить SSH/firewall. Этот комплект не переустанавливает Docker на действующем DE2 автоматически.
2. Настроить DNS и сертификат. Создать `/opt/xray`; установить отрендеренные `config.json` и `docker-compose.yml`, права конфигурации 0640 или строже с учётом UID контейнера.
3. Установить nginx-конфигурацию и decoy сайт. Убедиться, что nginx слушает 443, а Xray — только localhost:8443; один и тот же port не должен занимать старый x-ui/Xray.
4. Установить unit из `systemd/`, выполнить `systemctl daemon-reload`, `systemctl enable --now xray-docker nginx certbot.timer`.
5. Проверить `docker compose ps`, логи, `nginx -t`, TLS, затем реальный клиент.

Текущий image tag — `latest`; проверенный работающий Xray — **26.3.27 Custom**, digest `ghcr.io/xtls/xray-core@sha256:592ec4d11f656db95598d01e76dbcc6e002d67360b96a5436500a938230f52c7`. ID контейнера совпал с ID локального образа. Для строго воспроизводимого восстановления используйте этот digest. Не выполнять `docker compose pull` при обычном перезапуске сервиса: это может незаметно изменить версию.

## Управление

```sh
sudo systemctl stop xray-docker       # compose down
sudo systemctl start xray-docker      # compose up -d
sudo systemctl disable --now xray-docker
sudo systemctl enable --now xray-docker
cd /opt/xray
sudo docker compose ps
sudo docker compose logs --tail 50 xray
```

После изменения `config.json` перезапустить контейнер через `sudo docker compose restart xray`. Сам `systemctl reload xray-docker` не предусмотрен.

## Клиенты, MTProto и звонки

`config/client.json.example` — локальный Xray SOCKS5 на **127.0.0.1:1080**. Для использования с текущим DE2 подставить его действующий UUID/path. Этот SOCKS нельзя без аутентификации выставлять на внешний интерфейс.

Для будущего chaining AZ1: mtg использует этот локальный SOCKS как исходящий маршрут. Вход клиент→AZ1 остаётся MTProto и звонки этим не добавляются.

Для звонков на телефоне нужен либо поддерживаемый Telegram SOCKS5, либо приложение VPN/TUN с VLESS/XHTTP и поддержкой UDP. Запуск локального SOCKS на Raspberry Pi не маршрутизирует звонки телефона автоматически. Сначала проверяется клиентский туннель, затем двусторонний звук/видео на реальном звонке.
