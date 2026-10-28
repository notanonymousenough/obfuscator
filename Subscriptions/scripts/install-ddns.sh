#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
install -d -m755 /usr/local/lib/obfuscator-subscriptions
install -m755 scripts/ddns-az1.py scripts/cloudflare_dns.py /usr/local/lib/obfuscator-subscriptions/
install -m644 systemd/obfuscator-vpn-ddns.service systemd/obfuscator-vpn-ddns.timer /etc/systemd/system/
test -s /etc/obfuscator/az1-publisher.token
systemctl daemon-reload; systemctl enable --now obfuscator-vpn-ddns.timer
systemctl start obfuscator-vpn-ddns
journalctl -u obfuscator-vpn-ddns -n 8 --no-pager
