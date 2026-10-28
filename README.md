# Obfuscator

Исходные схемы проекта (актуальный слой подписок описан ниже):

- [MTP](MTP/README.md): самостоятельный MTProto FakeTLS на AZ1 без x-ui; пакеты, установка, systemd, SSH2222, DNS-01 сертификат и DDNS. [Фактическое состояние AZ1](MTP/DEPLOYMENT.md).
- [Xray VLESS XHTTP](Xray-VLESS-XHTTP/README.md): описание работающего DE2, безопасный снимок параметров, конфигурационные шаблоны, Docker Compose, systemd и клиент.

AZ1 опубликован через [релей DE1](MTP/RELAY.md) в обход CGNAT. На DE1 дополнительно развёрнут [VLESS/XHTTP с общим SNI-входом](Xray-VLESS-XHTTP/DE1.md). DE2 сохраняет действующее развёртывание. MTProto сам по себе не переносит аудио/видео звонков Telegram; для звонков рассматривается SOCKS5 либо VPN/TUN.

[Исходный аудит трёх серверов](server-audit-2026-10-27.md) фиксирует состояние до настройки AZ1. Текущее состояние AZ1 описано отдельно и заменяет первоначальные выводы о нём.

`.cloudflare`, резервная копия Tenda и приватные каталоги `secrets/` исключены из git. Рабочие клиентские UUID, секреты MTProto и закрытые ключи не включены в шаблоны.

[План развития: балансировка, специальные выходы, pipe и UI](docs/development-plan-2026-10-28.md) — исследование и дорожная карта от 28.10.2026.

## Подписки и клиенты (28.10.2026)

Актуальный слой: [Subscriptions](Subscriptions/README.md). Две публичные точки: `obfuscator.funsociety.dev` (персональная подписка DE1/AZ1) и `mtp.funsociety.dev` (MTProto DE1/AZ1 с общим адресом и отдельными секретами клиентов). DE2 скрыт и выдаётся отдельно. Старые клиенты остаются. Отдельных AI/Realtime/Payments профилей нет.

[Короткие операции](Subscriptions/runbooks/operations/README.md) · [Установка и восстановление](Subscriptions/runbooks/installation/README.md). Файлы MTP/Xray описывают исходные развёртывания; изменения ingress и новые управляемые клиенты описаны в Subscriptions.

## Единая панель и оркестратор

[Control](Control/README.md): 3x-ui 3.11.0 на DE1 с подключёнными узлами AZ1/DE2, приватными SSH-мостами, CLI и процедурой принятия рабочих backend. Панель установлена; переключение публичного трафика и подписок пока ожидает подтверждения. Исправление SNI-релея уже работает в production: [результат 100 HTTPS-проверок](Subscriptions/snapshot/relay-acceptance-2026-10-28.json).
