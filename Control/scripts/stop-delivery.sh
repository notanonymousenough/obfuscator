#!/bin/bash
set -euo pipefail
systemctl disable --now obfuscator-panel-delivery.service 2>/dev/null || true
backup=/var/lib/obfuscator-control/backups/cutover/subscription-data.json
if [ -e "$backup" ]; then
  install -m640 -o root -g obfsub "$backup" /var/lib/obfuscator-subscriptions/data.json
fi
