# Публичный вход AZ1 через DE1

Выбран владельцем 27.10.2026 из-за CGNAT в Азербайджане.

```text
Telegram / TLS SNI az1.obfuscator.funsociety.dev
  → DNS A 159.89.12.205 (DE1), TCP 443
  → HAProxy SNI router (TLS не завершает)
  → DE1 127.0.0.1:9443
  → обратный SSH-туннель, инициированный AZ1
  → AZ1 127.0.0.1:443, mtg
  → Telegram DC

SSH с pipe → DE1:2222 → DE1 127.0.0.1:12222 → AZ1:2222
```

На том же DE1:443 имя `de1.obfuscator.funsociety.dev` ведёт в отдельный XHTTP: nginx localhost:8444 → Xray localhost:8445. Поэтому порт 443 обслуживает HAProxy, а не прежний standalone `obfuscator-az1-relay.socket`. Старый socket оставлен как вариант отката, но выключен. Не включать его одновременно с HAProxy.

## Компоненты и ограничения

- На AZ1: `obfuscator-az1-tunnel.service`, пользователь `mtptunnel`; закрытый ключ `/etc/obfuscator-tunnel/id_ed25519` mode 0640 root:mtptunnel, родительский каталог 0750. Ключ не выносился с AZ1.
- На DE1: пользователь `obfuscator-relay`, только key authentication, `MaxSessions 0`, без shell/PTY/agent/X11. Разрешены исключительно reverse listeners `127.0.0.1:9443` и `127.0.0.1:12222`; `GatewayPorts no`, `AllowTcpForwarding remote`.
- Публичный SSH DE1 остался на 2222 для deploy. Доступ к AZ1 через релей требует SSH-конфигурации: обычный `ssh deploy@az1... -p2222` без неё попадёт на DE1, поскольку DNS обоих имён одинаковый.
- Host key DE1 закреплён в AZ1 known_hosts и проверен через существующий доверенный SSH-доступ. `StrictHostKeyChecking=yes`; автоматического принятия нового ключа нет.
- При разрыве SSH используются keepalive 15s/3 и `Restart=always` с паузой 5s. `ExitOnForwardFailure` не позволяет считать сервис рабочим, если reverse ports заняты.
- HAProxy TCP/SNI routing не завершает TLS, не знает secret MTProto и не читает содержимое Telegram. Сертификат AZ1 остаётся и продлевается на AZ1.
- DDNS на AZ1 публикует **статический адрес релея 159.89.12.205**, а не внешний CGNAT IP. Конфиг `/etc/obfuscator/dns.json`, timer `obfuscator-ddns.timer`, `ingress_confirmed=true`. Cloudflare — DNS-only.
- `public-ipv4` mtg задаётся как адрес публичного входа DE1; это нужно для ссылок и SNI/DNS диагностики, а не IP интерфейса Raspberry Pi.

Релей решает входящий CGNAT. AZ1 остаётся точкой выполнения mtg и прямого выхода в Telegram; перенос исходящего трафика на DE2 пока не включён. Выключенный Raspberry Pi, его интернет или DE1 делают этот маршрут недоступным. Для независимого AZ1 нужен публичный IP провайдера либо другая публичная точка входа.

## Восстановление установки

1. На AZ1 из полного bundle `MTP` выполнить `scripts/setup-relay-az1.sh` от root. При повторном запуске ключ сохраняется.
2. Передать на DE1 **только** файл `id_ed25519.pub` (копия лежит в AZ1 staging `az1-tunnel.pub`). Установить аккаунт и ограничения скриптом `scripts/setup-relay-de1.sh PUBLIC_KEY_FILE`.
3. Для совместного XHTTP/MTProto входа выполнить `../Xray-VLESS-XHTTP/scripts/install-de1.sh`; он заменяет standalone socket на HAProxy. `setup-relay-de1.sh` распознаёт уже работающий shared HAProxy и не включает standalone socket поверх него.
4. На AZ1: `systemctl enable --now obfuscator-az1-tunnel`.
5. После внешнего TLS-теста установить `config/dns-relay.json.example` как `/etc/obfuscator/dns.json`, применить `cloudflare_dns.py --apply` и включить timer.

## Управление и доступ

На AZ1:

```sh
systemctl status obfuscator-az1-tunnel obfuscator-mtp
systemctl restart obfuscator-az1-tunnel
journalctl -u obfuscator-az1-tunnel -n 50 --no-pager
/usr/local/lib/obfuscator/access.py  # приватная Telegram-ссылка с публичным доменом
```

На DE1:

```sh
systemctl status haproxy
ss -lnt '( sport = :443 or sport = :9443 or sport = :12222 )'
```

На pipe уже установлен `/home/user/obfuscator/ssh-via-relay.conf`:

```sh
ssh -F /home/user/obfuscator/ssh-via-relay.conf az1.obfuscator.funsociety.dev
```

С локального компьютера:

```sh
ssh -t user@192.168.0.192 'ssh -t -F /home/user/obfuscator/ssh-via-relay.conf az1.obfuscator.funsociety.dev'
```

Секреты не нужны на DE1 для MTProto-релея; приватный ключ туннеля, сертификат AZ1 и MTProto secret восстанавливаются из защищённой копии самого AZ1, не из публичных шаблонов.
