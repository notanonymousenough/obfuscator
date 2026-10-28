# Прямой внешний вход AZ1:443

Проверено 28.10.2026 через **живой Tenda API**, а не только старый backup:

- WAN Tenda `100.66.95.154/20`, gateway `100.66.80.1`.
- Общий внешний IPv4 `185.146.112.151`, RIPE network `AG-TELECOM-FTTB`.
- Forward80/443 ->192.168.0.194 с соответствующими внутренними портами, protocol both, source All — верен.
- DHCP reservation192.168.0.194 ->b8:27:eb:ce:89:2b — верен.
- IPv6 выключен на Tenda; на RPi только link-local IPv6, публичного маршрута нет.
- С DE2 внешний185.146.112.151:443 даёт timeout; за время контролируемого запроса RPi получил **0 SYN** от DE2 на443. Через DE1 relay TLS identity AZ1 доступна.
- NAT-PMP address query и PCP ANNOUNCE не получили ответов ни от Tenda, ни от carrier gateway. Mapping запросы не создавались.

`100.64.0.0/10` — shared address space CGNAT ([RFC6598](https://www.rfc-editor.org/rfc/rfc6598)). Проброс на Tenda не создаёт проброс на NAT провайдера. Cloudflare DNS-only не является средством NAT traversal. Обычный Cloudflare HTTP proxy не открывает произвольный TCP MTProto вход за CGNAT.

## Что запросить у провайдера

> Нужен публичный (real/white) IPv4 на WAN моего роутера вместо адреса100.66.95.154 за CGNAT, с разрешёнными входящими TCP80 и TCP443. Динамический публичный адрес подходит — DDNS настроен. Если выделение адреса невозможно, можете ли вы сделать входящий mapping TCP443 и TCP80 на мой WAN? Подтвердите доступность и стоимость до подключения услуги.

По RIPE/DNS сеть относится к AG Telecom/KATV1. Контакт провайдера проверить по договору; официальный сайт [KATV1](https://katv1.az/) указывает сервисный номер(012)127. Наличие услуги/цена не подтверждены; запрос оператору не отправлялся.

## После изменения провайдером

1. Проверить WAN в Tenda: публичный IPv4 вместо100.64/10 (либо согласованный mapping провайдера). Не вписывать вручную общий185.146.112.151 как static WAN: адрес вам не выделен.
2. Убедиться, что DHCP reservation и forward80/443 сохранились. RPi `haproxy` слушает0.0.0.0:443, UFW разрешает443.
3. Получить новый внешний IP с RPi (`curl -4 https://api.ipify.org`). С DE2 проверить `curl --resolve vpn-az1.obfuscator.funsociety.dev:443:PUBLIC_IP https://vpn-az1.obfuscator.funsociety.dev/.well-known/obfuscator-node` — нужен валидный TLS и тело `obfuscator-az1`.
4. На AZ1 root: `systemctl start obfuscator-vpn-ddns`, `journalctl -u obfuscator-vpn-ddns -n 12`. Только после успешной внешней TLS identity-проверки DDNS выберет direct.
5. Единый DDNS обновляет **оба** A DNS-only имени: `az1.obfuscator.funsociety.dev` и `vpn-az1.obfuscator.funsociety.dev`. Старый static `obfuscator-ddns.timer` отключён, чтобы не перезаписать direct адрес DE1-адресом. При подтверждённой внешним probe недоступности оба имени возвращаются на relay. Если недоступен сам probe API на DE1, DNS остаётся прежним: сбой DE1 не должен увести исправный direct AZ1 на сломанный relay.
6. Reverse SSH оставляется включённым. SSH извне по-прежнему доступен через сохранённый DE1 reverse12222; проброса внешнего2222 на Tenda нет. MTProto secret/клиентские UUID при смене IP не меняются.
7. Обновить подписку/переподключить Happ, повторить HTTPS/UDP тест и тест из РФ. Учитывать DNS TTL120 и кеш телефона.

Необходимое внешнее условие — действие провайдера. Локальные изменения firewall, DDNS, сертификата или VPN не могут сами выделить публичный IPv4 или открыть чужой carrier NAT.
