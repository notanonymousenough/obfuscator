# MTP: самостоятельный MTProto-сервис AZ1

Цель: Raspberry Pi без x-ui, с `mtg` FakeTLS на TCP 443, SSH 2222, systemd, настоящим TLS fallback, автоматическим продлением сертификата и подготовленным DDNS.

## Состояние и границы

Актуальный результат установки записывается в [DEPLOYMENT.md](DEPLOYMENT.md). Наличие файлов в этой папке само по себе не означает завершённое развёртывание.

В резервной копии Tenda от 27.10.2026 WAN IPv4 — `100.66.95.154`, внешний адрес AZ1 — `185.146.112.151`: подключение за CGNAT. Публичного IPv6 на AZ1 не обнаружено. Обычный port forwarding не устраняет NAT провайдера. Домен **не направляется на общий адрес CGNAT**; после выбора релея он направлен на DE1.

**Выбран и настроен вариант с DE1:** [RELAY.md](RELAY.md). DNS ведёт на DE1, обратный туннель доставляет TCP в AZ1. Описание CGNAT выше остаётся актуальным, но внешний вход теперь обеспечивается релеем.

Варианты публичного доступа:

1. Публичный IPv4 у провайдера (динамический допустим): DHCP reservation для Raspberry Pi, TCP 443 и 2222 на его LAN-адрес, затем включение DDNS.
2. Публичный IPv6: адрес и firewall должны быть доступны с клиентской сети; требуется отдельная настройка AAAA. Текущий DDNS управляет только A.
3. Публичный сервер-релей и постоянный исходящий туннель от AZ1. Выбран и настроен DE1. Свой DDNS в такой схеме должен публиковать адрес релея, а не CGNAT AZ1.

## Звонки Telegram

MTProto проксирует сообщения и медиа, но не является каналом передачи звука/видео звонка. В текущем официальном Telegram iOS галочка «Использовать для звонков» показывается только для SOCKS5: [исходник](https://github.com/TelegramMessenger/Telegram-iOS/blob/master/submodules/SettingsUI/Sources/Data%20and%20Storage/ProxyListSettingsController.swift#L311-L314). Поддержка конкретного мобильного клиента проверяется отдельно; один mtg её не добавляет.

Для звонков возможен совместимый SOCKS5 в самом Telegram либо VPN/TUN-клиент с поддержкой UDP поверх DE2 VLESS/XHTTP. SOCKS5 без маскировки не следует считать заменой FakeTLS для прохода DPI. Входящий MTProto нельзя превратить в VPN для звонков, изменив только его исходящий маршрут.

## Схема на AZ1

```text
Telegram → AZ1 TCP 443 → mtg → Telegram DC
                        └─ неавторизованный TLS → nginx 127.0.0.1:8443
                                                    └─ сертификат собственного домена
Certbot DNS-01 → Cloudflare TXT → Let's Encrypt → nginx reload
systemd timer → Cloudflare A (только после настройки публичного входа)
```

mtg закреплён на **v2.2.8**, Linux ARM64, без ARMv9-специфичных инструкций. Бинарный архив лежит в `dist/`, SHA256 — в `dist/SHA256SUMS`; лицензия содержится в архиве и устанавливается на сервер. Источник: [официальный релиз](https://github.com/9seconds/mtg/releases/tag/v2.2.8). Автообновления бинарника нет: обновление выполняется контролируемо с новой версией и SHA256.

## Установка

Для Debian/Raspberry Pi OS ARM64. Запуск от root. Установка меняет UFW, fail2ban, nginx, sysctl и добавляет systemd units. Перенос SSH выполняется отдельным скриптом.

```sh
cd MTP
sudo bash scripts/install.sh az1.obfuscator.funsociety.dev
sudo bash /usr/local/lib/obfuscator/setup-ssh.sh stage
```

Из ДРУГОЙ сессии проверить новый вход на 2222. Затем выполнить `setup-ssh.sh commit`, `setup-ssh.sh finalize`, вновь проверить вход и снова `setup-ssh.sh commit`. Для этапов stage/finalize ставится пятиминутный таймер отката. Старое соединение и root tmux нужно сохранить до завершения проверки. Не выполнять reboot до commit.

Секреты не передаются как параметры команд. Cloudflare raw API token устанавливается локально на сервере в `/etc/obfuscator/cloudflare.token`, mode **0600 root:root**. Каталог `/etc/obfuscator` — root:mtg 0750; mtg не может прочитать токен. Требуются ограниченные нужной зоной права DNS Edit и Zone Read. Один и тот же токен может применяться к DDNS и DNS-01; его не нужно выдавать клиентам Telegram.

```sh
sudo bash /usr/local/lib/obfuscator/configure-tls.sh
```

Этот шаг преобразует токен в отдельный root-only `cloudflare.ini`, получает сертификат через DNS-01 и включает nginx, mtg и certbot.timer. DNS-01 работает и за CGNAT. ACME-аккаунт изначально регистрируется без e-mail; при желании добавьте контакт через `certbot update_account --email ...`.

Сертификат нужен HTTPS fallback, который увидит обычный TLS-клиент. mtg обрабатывает FakeTLS и пересылает не прошедшие аутентификацию подключения на локальный nginx. Нельзя указать собственный публичный домен как fallback без localhost override: получится петля.

## DDNS

Шаблон — `config/dns.json.example`, устанавливается вручную в `/etc/obfuscator/dns.json` после решения о публичном доступе. Перед применением нужно явно установить `ingress_confirmed: true`; по умолчанию запись не изменяется. `ipv4: "auto"` допустим для прямого публичного IPv4. Для релея указывается его IP. Cloudflare запись должна быть **DNS-only**, обычный HTTP proxy Cloudflare не обслуживает произвольный MTProto TCP.

```sh
sudo /usr/local/lib/obfuscator/cloudflare_dns.py --config /etc/obfuscator/dns.json
# Только после проверки показанного изменения и реальной входящей доступности:
sudo /usr/local/lib/obfuscator/cloudflare_dns.py --config /etc/obfuscator/dns.json --apply
sudo systemctl enable --now obfuscator-ddns.timer
```

Скрипт изменяет только одну A-запись. Не удаляет AAAA/другие записи, не печатает токен, отказывается от публикации непубличного адреса и при расхождении двух внешних IP-проверок. Наблюдаемый внешний IP **не является доказательством отсутствия CGNAT** — это проверяется по WAN роутера.

## Управление

```sh
sudo systemctl stop obfuscator-mtp       # выключить сейчас
sudo systemctl start obfuscator-mtp      # включить сейчас
sudo systemctl disable --now obfuscator-mtp  # выключить и убрать автозапуск
sudo systemctl enable --now obfuscator-mtp   # вернуть автозапуск
sudo systemctl status obfuscator-mtp
sudo journalctl -u obfuscator-mtp -n 50 --no-pager
sudo /usr/local/bin/mtg doctor /etc/obfuscator/mtg.toml
sudo /usr/local/lib/obfuscator/access.py --server 192.168.0.194  # локальная проверка
sudo /usr/local/lib/obfuscator/access.py  # вывод приватной tg:// ссылки; не в публичные логи
```

`Restart=on-failure` восстанавливает процесс после сбоя, но ручной `systemctl stop` оставляет его выключенным. Стабильный secret хранится в `/etc/obfuscator/mtg.toml`; повторная установка не генерирует его заново. Восстановление самого оборудования/карты памяти требует резервной копии этого файла, настроек и секретов Cloudflare. При физическом отключении питания Raspberry Pi доступность обеспечивается только после его возвращения в сеть; «всегда доступен» при выключенном устройстве требует резервного узла.

На текущем AZ1 публичные DoH endpoints не завершили TLS handshake; системный DNS работает. Поэтому mtg использует системный резолвер (`[network].dns = ""`), а не недоступный DoH.

## Проверки и обновления

- Подключение SSH новым процессом на 2222, проверка отказа password/root и закрытия 22.
- `nginx -t`, `systemctl is-active`, `mtg doctor`; TLS-проверка `openssl s_client -connect IP:443 -servername az1.obfuscator.funsociety.dev -verify_return_error`.
- `certbot renew --dry-run`, таймер и deploy hook; nginx перезагружает сертификат без перезапуска mtg.
- Проверка реального Telegram-клиента по LAN, затем извне, затем из РФ. Открытый TCP-порт и корректный сертификат не заменяют проверку MTProto-сессии.
- При обновлении mtg сначала сохранить прежний бинарник, проверить новый архив и конфиг, заменить бинарник и перезапустить сервис; при неудаче вернуть прежний. Не использовать `curl | bash` и `latest` без проверки.

## На будущее: исходящий путь через DE2

[mtg поддерживает SOCKS5 chaining](https://github.com/9seconds/mtg/blob/v2.2.8/example.config.toml). Схема: `mtg → SOCKS5 127.0.0.1:1080 → Xray VLESS/XHTTP → DE2 → Telegram`. В `mtg.toml` меняется `[network].proxies` на единственный `socks5://127.0.0.1:1080` без пустой строки (пустая строка разрешила бы прямой обход). Клиентский шаблон лежит в соседней папке `Xray-VLESS-XHTTP`. Пока этот исходящий туннель не включён. Он не решает вход через CGNAT и не добавляет звонки к MTProto.
