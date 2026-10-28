# Клиенты и ключи

До завершения миграции `Control/ctl.py` разрешает чтение, а изменения отклоняет. Для рабочих клиентов использовать `Subscriptions/cli.py`. Панель содержит проверенные копии, не текущие счётчики рабочего VPN.

После успешной миграции открыть SSH-туннель (`Control/scripts/open-ui.sh`). В UI раздел «Клиенты»: имя, статус, привязанные inbounds, трафик, ограничения и последняя активность. Старые клиенты присутствуют под прежними именами либо `legacy-vless-<узел>-<номер>`; управляемый owner — `obf-owner`. Не удалять старые строки и отключённые Reality inbounds при уборке.

```sh
python3 Control/ctl.py list
python3 Control/ctl.py add phone
python3 Control/ctl.py links phone
python3 Control/ctl.py disable phone
python3 Control/ctl.py enable phone
python3 Control/ctl.py grant-de2 phone
python3 Control/ctl.py revoke-de2 phone
python3 Control/ctl.py rotate-vpn phone
python3 Control/ctl.py rotate-mtp phone
python3 Control/ctl.py rotate-link phone
```

`links` намеренно печатает секретные URL; не копировать вывод в Git, тикеты и публичные логи. `list` их не печатает. Отдельный DE2 URI выдаётся через `links` только после grant; общая подписка всегда скрывает DE2.

Для нового клиента в UI привязать VLESS `obf-vpn-de1`, `obf-vpn-az1`, MTProto **оба** `obf-mtp-de1` и `obf-mtp-az1`. DE2 добавляется только вручную. UUID — индивидуальный; MTProto secret — `ee` + 32 hex случайного ключа + hex домена `mtp.funsociety.dev`. CLI генерирует это автоматически. Отключение клиента глобальное; удаление только одной MTProto-привязки не заменяет отключение.

Канонические ссылки: `https://obfuscator.funsociety.dev/s/<subId>` и `https://mtp.funsociety.dev/mtp/<subId>`. Использовать их вместо встроенного локального порта подписок 2096. Подписку обновить в Happ после смены UUID; уже импортированный профиль не исчезнет при одном лишь отзыве URL — для отзыва VPN нужен disable или rotate-vpn. Ротация ссылки отдельно меняет только URL подписки.

Сначала смотреть состояние node-sync, затем результат клиента: online узла означает доступность управляющего API, но не доказывает доступность VPN из РФ. У новой панели счётчики рабочего трафика начнут заполняться после переключения; старые счётчики другого процесса не переносятся как новые.
