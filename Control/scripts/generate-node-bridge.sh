#!/bin/bash
set -euo pipefail
node=$(hostname -s)
case "$node" in obfuscator-az1) port=9411; remote=obfuscator-node-az1;; obfuscator-de2) port=9412; remote=obfuscator-node-de2;; *) exit 1;; esac
getent passwd obfpanel >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin obfpanel
chown root:obfpanel /etc/obfuscator-control
chmod 710 /etc/obfuscator-control
install -d -o root -g obfpanel -m750 /etc/obfuscator-control/tunnel
key=/etc/obfuscator-control/tunnel/id_ed25519
if ! test -f "$key"; then ssh-keygen -q -t ed25519 -N '' -C "$remote" -f "$key"; fi
chown root:obfpanel "$key"
chmod 640 "$key"
{ printf '[159.89.12.205]:2222 '; cat /home/deploy/obfuscator-control/config/de1-host-key.pub; } > /etc/obfuscator-control/tunnel/known_hosts
chown root:obfpanel /etc/obfuscator-control/tunnel/known_hosts
chmod 640 /etc/obfuscator-control/tunnel/known_hosts
cat > /etc/systemd/system/obfuscator-panel-bridge.service <<EOF
[Unit]
Description=Private node panel bridge to DE1
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0
[Service]
User=obfpanel
Group=obfpanel
ExecStart=/usr/bin/ssh -F /dev/null -NT -p 2222 -i $key -o BatchMode=yes -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/etc/obfuscator-control/tunnel/known_hosts -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -R 127.0.0.1:$port:127.0.0.1:1337 $remote@159.89.12.205
Restart=always
RestartSec=5
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
printf 'Panel bridge key prepared for %s; public fingerprint: ' "$remote"
ssh-keygen -lf "$key.pub"
