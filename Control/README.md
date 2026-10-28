# Единое управление Obfuscator

Панель: **3x-ui 3.11.0**, master на DE1, node-sync на AZ1 и DE2.

На 2026-10-28 панель и приватные мосты работают, узлы online. VLESS/XHTTP и MTProto импортированы в изолированные listener-копии и проверены HTTPS/HMAC-тестами. **Переключение публичного трафика и источника подписок ожидает отдельного подтверждения оператора.** До переключения управление рабочими клиентами остаётся в `Subscriptions/cli.py`; изменения в копиях панели не меняют рабочую подписку.

AZ1 обслуживается через DE1. DNS AZ1 указывает на DE1 намеренно: WAN роутера находится за CGNAT. Исправленные HAProxy-правила сохраняют SNI только после получения полного ClientHello. Проверено 100 из 100 HTTPS-запросов через новые Xray-сессии из AZ1/Баку и DE2; отдельной проверки Happ на телефоне ещё нет.

## Доступ

```sh
./Control/scripts/open-ui.sh
```

Оставить процесс SSH работающим и открыть http://127.0.0.1:1337/control/ . Новый логин и пароль находятся в локальном игнорируемом `.secrets/control-access.private.txt`; серверные доступы — в `/etc/obfuscator-control/access.json` (root, 0600).

Публичный адрес https://obfuscator.funsociety.dev/control/ разрешён только для административного IPv4 из `inventory.json`. При VPN, другом адресе или ошибке 403 использовать SSH-туннель. HAProxy передаёт реальный адрес в отдельный nginx listener 8449 через PROXY v2; публичный listener не принимает PROXY-заголовки от клиента. API всех панелей слушают только 127.0.0.1:1337. Узлы подключаются к master по отдельным SSH-мостам; их токены ограничены `node-sync`.

## Кто управляет настройками

| Настройки | Источник |
|---|---|
| Клиенты, UUID, MTProto-секрет, лимиты, включение, статистика | После переключения: 3x-ui на DE1 |
| VLESS/XHTTP и MTProto inbounds на узлах | После переключения: 3x-ui и node-sync |
| Домены, состав узлов, закрытая публикация DE2, IP управления | `Control/inventory.json` и конфиги репозитория |
| nginx, HAProxy, SSH-мосты, systemd, DNS/сертификаты | Скрипты и run-books; root через существующий tmux |
| Подписки и Telegram landing | `Subscriptions/server.py`; после переключения реестр из `Control/delivery.py` |

Панель управляет Xray и клиентами. Системные настройки SSH, Cloudflare и firewall пока меняются через оркестратор/скрипты, а не произвольную root-консоль в браузере. Постоянных sudo-прав не добавлено.

## Схема

```text
Happ -> DE1:443 -> HAProxy(SNI) -> reverse SSH -> AZ1 nginx -> AZ1 Xray
     -> DE1:443 -> DE1 nginx -> DE1 Xray
DE2 private -> DE2 nginx -> DE2 Xray

master DE1 -> 127.0.0.1:9411 / 9412 -> отдельные SSH-мосты -> node API
mtp.funsociety.dev -> HAProxy leastconn -> MTProto DE1 / AZ1
obfuscator.funsociety.dev/s/<token> -> только DE1 + AZ1
```

После переключения `delivery.py` читает нормализованные `clients`/`client_inbounds` и публикует реестр атомарно каждые 2 секунды. UUID и прежние URL-токены сохраняются. DE2 никогда не включается в общую подписку, даже если клиенту выдан частный доступ. MTProto landing выдаётся только при привязке клиента к обоим backend — это нужно для общего балансируемого домена.

## Файлы и команды

```sh
python3 Control/orchestrator.py plan     # схема, без изменений
python3 Control/orchestrator.py status   # нужны SSH-туннель и приватный control.json
python3 Control/orchestrator.py stage    # загрузка кода, без запуска переключения
python3 Control/ctl.py list              # состояния/привязки/байты, без ключей
```

[Переключение и откат](runbooks/migration.md), [клиенты](runbooks/clients.md), [системные операции](runbooks/platform.md).

Версия закреплена и сверяется SHA256 в `scripts/preflight-panel.sh`; бинарные архивы не коммитятся. Исходный проект и API: [3x-ui 3.11.0](https://github.com/MHSanaei/3x-ui/releases/tag/v3.11.0), [multi-node](https://github.com/MHSanaei/3x-ui/blob/main/docs/content/docs/en/operations/multi-node.mdx). Нельзя запускать свежий upstream install-script поверх этой установки без резервной копии и проверки миграции БД.
