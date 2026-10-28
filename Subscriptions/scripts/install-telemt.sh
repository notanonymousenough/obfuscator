#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
case $(hostname -s) in
 obfuscator-de1) archive=telemt-x86_64-linux-musl.tar.gz; mask=8444; digest=71c1454f79cf755edea0985500629daba553002f9863be754e8e38a418822773;;
 obfuscator-az1) archive=telemt-aarch64-linux-musl.tar.gz; mask=8447; digest=21795430c4165cf964405459714d08eea319edaa5c9027beac4de373c356d84d;;
 *) exit 1;;
esac
printf '%s  %s\n' "$digest" "assets/$archive" | sha256sum -c -
getent passwd obftelemt >/dev/null || useradd --system --home-dir /var/lib/obfuscator-telemt --shell /usr/sbin/nologin obftelemt
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
tar -xzf "assets/$archive" -C "$work"
bin=$(find "$work" -type f -name telemt -print -quit)
install -o root -g root -m755 "$bin" /usr/local/bin/telemt
install -d -o root -g obftelemt -m750 /etc/obfuscator-telemt
sed "s/__MASK_PORT__/$mask/" config/telemt-base.toml > /etc/obfuscator-telemt/base.toml
chmod 640 /etc/obfuscator-telemt/base.toml; chown root:obftelemt /etc/obfuscator-telemt/base.toml
if ! test -f /etc/obfuscator-telemt/config.toml; then
 cat /etc/obfuscator-telemt/base.toml > /etc/obfuscator-telemt/config.toml
 printf '\n[access.users]\nreserved_disabled = "%032d"\n[access.user_enabled]\nreserved_disabled = false\n' 0 >> /etc/obfuscator-telemt/config.toml
 chown root:obftelemt /etc/obfuscator-telemt/config.toml
 chmod 640 /etc/obfuscator-telemt/config.toml
fi
install -m644 systemd/obfuscator-telemt.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now obfuscator-telemt
sleep 2
systemctl is-active obfuscator-telemt
