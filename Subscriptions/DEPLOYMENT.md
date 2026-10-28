# Фактическое развёртывание 28.10.2026

Рабочая ветка: `codex/subscriptions-client-management`.

## Результат

- `obfuscator.funsociety.dev` DNS-only A 159.89.12.205, nginx TLS -> delivery127.0.0.1:9080. Персональная base64 VLESS подписка **DE1 + AZ1**, update interval1час.
- `mtp.funsociety.dev` DNS-only A 159.89.12.205 -> HAProxy leastconn -> Telemt DE1:8446 / AZ1 через reverse9446. У клиента общий secret для двух backend. HTTPS Telegram landing работает через mask nginx обоих backend; AZ1 пересылает его в DE1 portal с проверкой TLS chain.
- `vpn-az1.obfuscator.funsociety.dev` -> сейчас DE1 relay9444 -> nginx AZ18444 -> Xray8445. DDNS наблюдает публичный185.146.112.151, но внешний TLS443 не проходит; выбран relay. Это не доказательство отсутствия проброса: вероятен сохранившийся CGNAT/ограничение провайдера.
- AZ1 public443 теперь HAProxy: старый az1 SNI -> прежний mtg на127.0.0.1:8448 (secret сохранён), новый VPN SNI -> nginx8444, mtp SNI -> Telemt8446. Старый reverse9443->AZ1:443 и SSHreverse12222 сохранены.
- Новые reverse-порты DE19444->AZ18444, DE19446->AZ18446. SSH2222 и сохранённый tunnel key не менялись.
- DE2 работает отдельно, выдаётся owner через private VLESS URI; в subscription его нет даже для owner с правом DE2.
- Создан `owner` с независимыми VPN UUID, MTProto secret и bearer URL. Private данные в `.secrets/clients.json` и `.secrets/owner-links.private.txt`, вне git. Тестовый `verification` создан и отозван; он остаётся disabled в реестре как запись проверки.

## Сохранность старого

Контроль исходных уникальных credential hashes (это **не** количество клиентов): DE1 x-ui21/VPN1, DE2 x-ui3/VPN1, AZ1 mtg1. После применения все исходные хеши присутствуют. x-ui DB не редактировались. DE1 legacy MTProto8888 остаётся активным; disabled VLESS inbounds в x-ui не включались. DE2 x-ui по-прежнему disabled. На AZ1 x-ui не устанавливался.

Private исходные backup на каждом узле `/var/lib/obfuscator-managed/backups/initial-*`; в git только шаблоны и sanitized [snapshots](snapshot/).

## Проверки

- Unit: 11 tests подписки/видимость DE2/отзыв/сохранность legacy/rollback + 5 DNS tests — passed.
- Реальный HTTPS через новые VLESS/XHTTP ключи из AZ1: DE1 egress159.89.12.205, DE2 egress164.92.246.64, AZ1 egress185.146.112.151 — passed.
- Проверка подписки: ровно2 URI DE1/AZ1; DE2 отсутствует; персональный Telegram redirect содержит правильный secret — passed.
- FakeTLS HMAC-аутентификация owner через публичный mtp443 и оба backend отдельно — passed. Это проверка secret/TLS, **не** отправка Telegram-сообщений через Telegram DC.
- Отключение DE1 backend в HAProxy -> авторизация через AZ1; отключение AZ1 -> через DE1; оба backend восстановлены — passed. Обычные TCP health checks с fall3/rise2, не end-to-end Telegram health.
- Тестовый клиент отозван: VPN и Telegram landing404, старый MTProto secret отвергается обоими backend, старый VLESS UUID не пропускает HTTPS через DE1/AZ1 — passed.
- TLS сертификаты новых имён действуют до26.01.2027. Certbot dry-run новых сертификатов DE1 portal и AZ1 VPN/mtp — оба passed.
- Certbot timer enabled: DE1 00:20/12:20UTC, AZ1 03:20/15:20UTC, jitter10мин; nginx reload deploy hook сохранён.
- Проверки из РФ, импорт конкретной версии Happ на телефоне, сообщения/медиа Telegram и UDP/звонки через VPN **ещё не выполнены**.

## Ограничения

DE1 пока единая публичная точка для подписки, MTProto и резервного AZ1. Балансировка backend не устраняет отказ/блокировку самого DE1 IP. Смена клиента перезапускает Xray/Telemt при изменении config, возможен краткий обрыв текущих соединений. Распределённые изменения не атомарны; CLI хранит pending и поддерживает повтор `sync`.

Все рабочие сервисы включены через systemd; root tmux нужен только оператору для изменения конфигураций/клиентов. После reboot оператор должен заново открыть root tmux, чтобы использовать CLI; сам VPN, delivery, DDNS и tunnel от этого не зависят. Постоянных sudoers-grants нет.
