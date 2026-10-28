#!/bin/bash
set -euo pipefail
case $(hostname -s) in
 obfuscator-de1) hours=00,12;;
 obfuscator-az1) hours=03,15;;
 *) exit 1;;
esac
install -d -m755 /etc/systemd/system/certbot.timer.d
cat > /etc/systemd/system/certbot.timer.d/obfuscator.conf <<EOF
[Timer]
OnCalendar=
OnCalendar=*-*-* $hours:20:00 UTC
RandomizedDelaySec=10min
Persistent=true
EOF
systemctl daemon-reload; systemctl restart certbot.timer
systemctl is-enabled certbot.timer
systemctl list-timers certbot.timer --no-pager
