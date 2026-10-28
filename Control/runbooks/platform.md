# Системные операции

## Сменить административный IP

Оставить открытым SSH-доступ. В `Control/inventory.json` заменить `admin_allow_ipv4` точным внешним CIDR, обычно `/32`. `python3 Control/orchestrator.py stage`, затем `python3 Subscriptions/scripts/root-tmux.py de1 Control/scripts/publish-ui.sh`. Проверить UI из разрешённой сети и отказ 403 из DE2. Не открывать панель всему Интернету ради устранения 403; SSH-local доступ работает независимо от ACL.

## Перезапустить управляющий мост

На AZ1/DE2 через root tmux: `systemctl restart obfuscator-panel-bridge`; проверить `systemctl is-active obfuscator-panel-bridge`, затем online в master. Мост управляет только панелью; рабочий обратный туннель AZ1 — отдельный сервис, его перезапускать не нужно. При отказе после chmod проверить проход к `/etc/obfuscator-control/tunnel` для группы `obfpanel`: родитель 0710, tunnel 0750, ключ 0640 root:obfpanel.

## Обновить 3x-ui

Сначала изучить upstream release/migrations, закрепить новую версию и SHA256 обеих архитектур. Создать приватный SQLite backup через SQLite backup API, проверить миграцию на копии и сохранность старых UUID/secret/password на узле. Обновлять узлы последовательно, затем master. `activate-panel.py` — bootstrap с генерацией новых доступов, **не** повседневный updater; повторный запуск потребует обновления node enrollment и локальных доступов. Не запускать его при обычном рестарте.

## Новый сервер

1. Настроить deploy SSH:2222, ключи, firewall и root tmux по существующим run-books Subscriptions; определить публичную адресацию и доступность 443 снаружи.
2. Добавить узел в inventory и явную схему ingress. Текущие install/adopt-скрипты проверяют имена de1/de2/az1: сначала расширить allowlist/hostname mapping и протестировать, затем запускать. Нельзя выдать текущий трёхузловой bootstrap за универсальный installer.
3. Загрузить закреплённый архив архитектуры; проверить SHA256; установить локальную панель API 127.0.0.1 и отдельный node-sync token. Создать ограниченный SSH-мост с выделенным ключом, пользователем и permitlisten.
4. Импортировать backend с сохранением существующих ключей, проверить отдельный listener и публичный TLS-маршрут, записать host overrides: публичные домен/443/TLS. Добавить node master с selected tags, не импортируя произвольные legacy inbounds.
5. Добавить узел в delivery и тесты только согласно политике выдачи. Сначала отдельный тестовый клиент, затем публичная подписка. Новая страна/узел не означает автоматически новый профиль для AI/Payments.

## Cloudflare и сертификаты

Действующие инструкции: `Subscriptions/runbooks/operations/` и `MTP/DEPLOYMENT.md`. В relay-режиме `ingress_mode=relay` для AZ1; DNS намеренно указывает DE1. Не включать старый DDNS, перезаписывающий relay адрес. Токен Cloudflare хранится root-only на AZ1; его и `cloudflare.ini` не коммитить. Панель не хранит Cloudflare-токен и не управляет certbot.
