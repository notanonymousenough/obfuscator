# Короткие runbooks

Команды CLI — из корня проекта. На узлах нужны существующие idle root tmux-панели `0:0.0`, открытые оператором через sudo. Постоянного NOPASSWD нет. Не работать в панели одновременно с CLI.

## Клиент и скрытый DE2

```sh
python3 Subscriptions/cli.py add alice
python3 Subscriptions/cli.py links alice
python3 Subscriptions/cli.py disable alice
python3 Subscriptions/cli.py enable alice
python3 Subscriptions/cli.py grant-de2 alice
python3 Subscriptions/cli.py revoke-de2 alice
```

`add` печатает Subscription URL для Happ и HTTPS Telegram URL. `grant-de2` печатает отдельный URI, но не включает DE2 в подписку. `disable` удаляет только управляемые ключи; старые x-ui клиенты остаются.

## Сменить ключи / ссылку

`rotate-link alice` отзывает старые URL, но не уже импортированные ключи. `rotate-vpn alice` меняет UUID: обновить подписку. `rotate-mtp alice` меняет MTProto secret: снова открыть Telegram URL. Для полного отзыва — сначала `disable`, затем необходимые ротации и `enable`.

## Поменять Cloudflare токен

На AZ1 заменить `/home/deploy/cloudflare.ini`, chmod600. Поддерживаются ключи `cloudflare_api_token` и `dns_cloudflare_api_token`. В root tmux:

```sh
python3 /home/deploy/obfuscator-subscriptions/scripts/import-cloudflare.py /home/deploy/cloudflare.ini
systemctl start obfuscator-vpn-ddns
certbot renew --dry-run
```

Нормализованные `/etc/obfuscator/cloudflare.token` и `cloudflare.ini` — root0600, используются DDNS и Certbot. DE1 имеет отдельный `/etc/letsencrypt/cloudflare.ini`; менять отдельно root0600. Токену нужны Zone Read + DNS Edit для funsociety.dev. Не печатать токен в лог или git.

## DDNS / CGNAT

AZ1 root: `systemctl start obfuscator-vpn-ddns; journalctl -u obfuscator-vpn-ddns -n 15`. `direct` — DE1 проверил публичный IP443, TLS и идентификатор AZ1. `relay` — DNS ведёт через DE1. Проброс портов и MAC reservation не снимают CGNAT. TTL120, у клиентов возможны дополнительные кеши. Оба AZ1 hostname выбирают direct/relay одним DDNS; старый static timer отключён.

## Статус / сертификат

DE1: `systemctl status haproxy nginx obfuscator-subscriptions obfuscator-telemt xray-docker`.
AZ1: `systemctl status haproxy nginx obfuscator-vpn obfuscator-mtp obfuscator-telemt obfuscator-az1-tunnel obfuscator-vpn-ddns.timer`.
DE2: `systemctl status xray-docker nginx`.

`curl -fsS https://obfuscator.funsociety.dev/healthz` — delivery. `python3 Subscriptions/cli.py baseline` — сохранение старых ключей. На узлах `certbot renew --dry-run` — тест продления, nginx reload делает deploy-hook. Автопродление разнесено: DE1 00:20/12:20 UTC, AZ1 03:20/15:20 UTC, jitter10мин. Не запускать параллельно вручную выдачу сертификатов для mtp на DE1/AZ1: DNS challenge общий.

## Выключить новый MTProto

На **обоих** DE1/AZ1 `systemctl stop obfuscator-telemt`; вернуть `start`. Для остановки после reboot `disable --now`, вернуть `enable --now`. Старый DE1:8888 и AZ1 mtg отдельны, эти команды их не отключают.

## Ошибка / reboot

При timeout посмотреть `tmux capture-pane -p -t 0:0.0`; не повторять вслепую, пока старая команда выполняется. После reboot обычные сервисы работают без tmux; чтобы менять клиентов, открыть root tmux заново. Исправить доступ и повторить `python3 Subscriptions/cli.py sync`. `pending_sync=True` — применение не завершено.

## Backup / откат

`.secrets/clients.json` (0600, каталог0700) сохранить в зашифрованную копию. На узлах `/etc/obfuscator-managed/owned.json` — принадлежность новых ключей агенту; сохранять вместе с действующими конфигами. Не удалять owned.json: потеряется возможность корректного отзыва.

`/var/lib/obfuscator-managed/backups` — private исходные x-ui DB и конфиги, последующие VPN snapshots. Секреты не экспортируются в git. Legacy baseline содержит хеши.

AZ1 ingress rollback: stop haproxy, вернуть `/etc/obfuscator/mtg.toml.pre-subscriptions` в mtg.toml, restart obfuscator-mtp. DE1 rollback: вернуть `/etc/haproxy/haproxy.cfg.pre-subscriptions`, validate `haproxy -c -f /etc/haproxy/haproxy.cfg`, reload. Новые сервисные имена при этом перестанут работать. Старую x-ui DB не восстанавливать поверх действующей ради отката подписок.

## Проверки без раскрытия секретов

`python3 Subscriptions/scripts/verify-delivery.py` — owner subscription/redirect/скрытый DE2. `verify-vpn.py` — реальный HTTPS через три выданных owner узла из AZ1. `verify-mtp.py` и `verify-mtp.py --via az1`/`--via de1` — FakeTLS HMAC-аутентификация. Это не проверка Telegram DC/сообщений. Для отозванного verification: `verify-delivery.py verification --revoked`, `verify-mtp.py verification --via az1 --rejected`, `verify-vpn.py verification --rejected`.

`verify-pool.sh` запускать через root-tmux на DE1: временно исключает по одному backend, проверяет HMAC и в finally возвращает оба. Проводить в согласованное окно — новые подключения кратковременно идут только через оставшийся backend.

[Прямой вход AZ1:443, CGNAT и что запросить у провайдера](az1-public-ingress.md).

## Повторная проверка таймаутов релея

`python3 Subscriptions/scripts/verify-vpn.py --nodes az1 --attempts 40 --timeout 7` —40 новых TLS/H2 сессий из Баку/AZ1, две независимые HTTPS204 цели. `--from-node de2` — независимый источник. В HAProxy на обоих слоях сохранять условие полного SNI перед `set-var(sess.route_sni)`; без него можно получить неправильный default backend/сертификат. При обновлении не заменять условную запись SNI без полного теста.

AZ1 пока закреплён за DE1: `/etc/obfuscator/az1-ddns.json` содержит `ingress_mode=relay`. `auto` включать только явным решением после появления прямого входа; оба hostname обновляются одним timer.
