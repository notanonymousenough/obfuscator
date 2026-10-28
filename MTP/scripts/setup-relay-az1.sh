#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]]
[[ $(hostname -s) == obfuscator-az1 ]] || { echo "Wrong host; expected obfuscator-az1" >&2; exit 1; }
base=$(cd "$(dirname "$0")/.." && pwd)
getent passwd mtptunnel >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin mtptunnel
install -d -m750 -o root -g mtptunnel /etc/obfuscator-tunnel
if [[ ! -f /etc/obfuscator-tunnel/id_ed25519 ]]; then
  ssh-keygen -q -t ed25519 -N '' -C az1-reverse-tunnel -f /etc/obfuscator-tunnel/id_ed25519
fi
chown root:mtptunnel /etc/obfuscator-tunnel/id_ed25519
chmod 640 /etc/obfuscator-tunnel/id_ed25519
awk '{print "[159.89.12.205]:2222 " $1 " " $2}' "$base/relay/de1-host-key.pub" > /etc/obfuscator-tunnel/known_hosts
chmod 644 /etc/obfuscator-tunnel/known_hosts
install -d -m755 /home/deploy/obfuscator-staging
install -m644 /etc/obfuscator-tunnel/id_ed25519.pub /home/deploy/obfuscator-staging/az1-tunnel.pub
install -m644 "$base/systemd/obfuscator-az1-tunnel.service" /etc/systemd/system/
systemctl daemon-reload
echo 'AZ1 tunnel prepared; install public key on DE1 before starting.'
