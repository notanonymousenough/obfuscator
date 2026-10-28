# Установка узла и восстановление

## Общие условия

64-bit Linux, синхронизированные часы, SSH deploy:2222 через pipe, root tmux `0:0.0`, доступ к DNS API. Базовые SSH hardening/UFW/fail2ban описаны в MTP; сначала проверить вход новым SSH-сеансом, старый не закрывать. На новых узлах закрыть внутренние порты nginx/Xray/Telemt от внешнего доступа (в шаблонах слушают loopback).

Перед любыми изменениями снять **локальный на узле private backup** `/etc/x-ui`, VPN config, HAProxy/nginx/SSH и `/etc/obfuscator*`. SQLite копировать через sqlite backup API или остановленный сервис. Не выгружать DB и секреты в git. `install-agent.sh` сохраняет baseline старых ключей и initial backup; выполнять до изменения legacy-конфигураций.

Копирование без Mac metadata, из корня репозитория:

```sh
COPYFILE_DISABLE=1 tar --no-xattrs --no-fflags --exclude=__pycache__ -czf /tmp/subscriptions.tar.gz -C Subscriptions .
# TARGET: de1.obfuscator.funsociety.dev / de2.obfuscator.funsociety.dev / 192.168.0.194
ssh user@192.168.0.192 "ssh -p 2222 deploy@TARGET 'mkdir -p /home/deploy/obfuscator-subscriptions; tar -xzf - -C /home/deploy/obfuscator-subscriptions'" < /tmp/subscriptions.tar.gz
python3 Subscriptions/scripts/root-tmux.py de1 Subscriptions/scripts/install-agent.sh
```

`root-tmux.py` запускает указанный локальный скрипт в уже открытой root-панели. Использовать только проверенные скрипты. Он не устанавливает sudoers. Исходники staging принадлежат deploy, **исполняемый агент** `/usr/local/sbin/obfuscator-node-agent` — root:root755.

## DE1 — публичный ingress и подписка

Предполагается действующая исходная XHTTP-конфигурация из `Xray-VLESS-XHTTP/`, с сохранёнными UUID, nginx127.0.0.1:8444 и XrayDocker8445. Нужен certbot-dns-cloudflare и root0600 `/etc/letsencrypt/cloudflare.ini`.

1. Скачать Telemt3.5.14 `telemt-x86_64-linux-musl.tar.gz` из официального GitHub release в staging `assets/`. Установщик проверяет SHA256.
2. `install-agent.sh`, затем `install-de1-portal.sh`: service localhost9080, cert SAN obfuscator/mtp, nginx8444 vhost.
3. `install-telemt.sh`: отдельный user obftelemt и loopback8446. До создания клиента используется отключённый placeholder.
4. `enable-de1-ingress.sh`: SNI маршруты и PermitListen9443/12222/9444/9446 для существующей relay key. Сохранённые legacy SNI и DE1 default остаются.
5. `publish-de1-dns.sh`: A DNS-only obfuscator/mtp/vpn-az1 -> DE1. Не запускать после рабочего прямого AZ1 DDNS без намерения временно вернуть relay.

Вызовы через `python3 Subscriptions/scripts/root-tmux.py de1 Subscriptions/scripts/ИМЯ.sh`.

## AZ1 — RPi ARM64

Предполагаются действующий legacy mtg и reverse SSH из MTP, сохранённые ключ/секрет. Если восстанавливаете новый RPi, сначала восстановить эти private файлы и host keys из backup; не генерировать новые секреты существующим клиентам молча.

1. `/home/deploy/cloudflare.ini` с API token600. Staging assets: Telemt ARM64 musl3.5.14 и `Xray-linux-arm64-v8a.zip`26.3.27. SHA256 проверяют установщики.
2. `install-agent.sh` **до** добавления VPN; `install-az1-vpn.sh` нормализует credentials, получает SAN cert vpn-az1/mtp (DNS01), устанавливает native Xray8445 и nginx8444/8447. Этот первоначальный шаблон содержит пустой список новых клиентов; повторный запуск не перезаписывает рабочий config.
3. `install-telemt.sh`, затем `enable-az1-ingress.sh`: apt haproxy, legacy mtg443 -> loopback8448, public443 у HAProxy; старый secret не меняется. Скрипт откатывает handoff listener при ошибке старта.
4. Root tmux снова свободен; на Mac `python3 Subscriptions/cli.py add owner`. Новые ключи применяются на DE1/AZ1.
5. На Mac `python3 Subscriptions/cli.py configure-ddns`, затем `install-ddns.sh` на AZ1. Timer каждые2мин проверяет внешний443 через DE1 и выбирает direct/relay. Reverse SSH остаётся всегда.

Выдачу сертификатов mtp на DE1/AZ1 выполнять **последовательно**, чтобы не конфликтовал общий DNS TXT challenge. Выполнить `configure-renewal-timer.sh` на DE1/AZ1, чтобы разнести автопродление по времени; Certbot timers и nginx reload hooks должны быть enabled.

## DE2 — скрытый существующий XHTTP

Не менять x-ui DB и действующий UUID. Поставить только `install-agent.sh`. Обычная синхронизация оставляет legacy клиентов и не добавляет туда новых без права `de2`. `grant-de2 CLIENT` добавляет управляемый UUID и выдаёт отдельный URI, не публикует узел в основной подписке.

## Совсем новый четвёртый узел

Текущий inventory намеренно фиксирован de1/de2/az1. Новый узел нельзя получить просто переименованием: добавить явное имя/SSH адрес в CLI HOSTS, hostname в NODE агента, domain в URI renderer, выбрать native/Docker config/service mapping, политику видимости в `server.py` (не раскрыть DE2). Затем DNS01/SNI/nginx/XHTTP, baseline, аутентифицированный probe, и лишь после теста включать в subscription list. Для ещё одного MTProto backend — тот же управляемый user secret set, собственный mask nginx, TLS target mtp, защищённый путь до ingress, HAProxy backend check. Старые узлы не переустанавливать.

## Версии, проверка и восстановление

Telemt3.5.14 x86 musl SHA256 `71c1454f79cf755edea0985500629daba553002f9863be754e8e38a418822773`; ARM musl `21795430c4165cf964405459714d08eea319edaa5c9027beac4de373c356d84d`.
Xray26.3.27 ARM zip `4d30283ae614e3057f730f67cd088a42be6fdf91f8639d82cb69e48cde80413c`.
Источник: GitHub releases telemt/telemt и XTLS/Xray-core. Не использовать latest без отдельного обновления/теста.

Проверки: `python3 -m unittest discover -s Subscriptions/tests -v`, CLI baseline, TLS cert, реальный VLESS HTTPS/egress, MTProto mobile test, отключение backend/возврат, отсутствие DE2 в decoded подписке, отдельный URI DE2, test-client disable и отказ старых URL. Стендовый restore включает `.secrets/clients.json`, node owned.json, соответствующие private VPN/Telemt/SSH/Cloudflare configs; затем `sync` и подтверждение baseline. Все сервисы enable, после reboot проверить reverse tunnel и timer. Реальную проверку из РФ отмечать отдельно.
