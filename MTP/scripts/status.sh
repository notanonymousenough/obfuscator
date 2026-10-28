#!/usr/bin/env bash
set -u
systemctl --no-pager --full status obfuscator-mtp.service nginx.service certbot.timer obfuscator-ddns.timer
ss -lnt '( sport = :443 or sport = :2222 or sport = :8443 )'
/usr/local/bin/mtg doctor /etc/obfuscator/mtg.toml
