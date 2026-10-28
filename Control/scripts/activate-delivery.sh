#!/bin/bash
set -euo pipefail
src=/home/deploy/obfuscator-control
backup=/var/lib/obfuscator-control/backups/cutover
install -d -m700 "$backup"
if [ ! -e "$backup/subscription-data.json" ]; then
  install -m600 /var/lib/obfuscator-subscriptions/data.json "$backup/subscription-data.json"
fi
install -d -m755 /usr/local/lib/obfuscator-control
install -m644 "$src/delivery.py" /usr/local/lib/obfuscator-control/delivery.py
install -m644 "$src/systemd/obfuscator-panel-delivery.service" /etc/systemd/system/
# Existing delivery endpoint and its publisher token remain in place.
install -m644 /home/deploy/obfuscator-subscriptions/server.py /usr/local/lib/obfuscator-subscriptions/server.py
python3 /usr/local/lib/obfuscator-control/delivery.py --once
systemctl daemon-reload
systemctl restart obfuscator-subscriptions
systemctl enable --now obfuscator-panel-delivery
systemctl is-active --quiet obfuscator-subscriptions obfuscator-panel-delivery
