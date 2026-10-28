#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]]
[[ $(hostname -s) == obfuscator-de1 ]] || { echo "Wrong host; expected obfuscator-de1" >&2; exit 1; }
base=$(cd "$(dirname "$0")/.." && pwd)
public_key=${1:?Public key file required}
ssh-keygen -lf "$public_key" >/dev/null
[[ -x /usr/lib/systemd/systemd-socket-proxyd ]]
getent passwd obfuscator-relay >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin obfuscator-relay
install -d -m755 /etc/ssh/authorized_keys
{ printf 'restrict,port-forwarding,permitlisten="127.0.0.1:9443",permitlisten="127.0.0.1:12222" '; cat "$public_key"; } > /etc/ssh/authorized_keys/obfuscator-relay
chmod 600 /etc/ssh/authorized_keys/obfuscator-relay
chown obfuscator-relay:obfuscator-relay /etc/ssh/authorized_keys/obfuscator-relay
[[ -f /etc/ssh/sshd_config.pre-az1-relay ]] || cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.pre-az1-relay
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/ssh/sshd_config');lines=p.read_text().splitlines()
for i,line in enumerate(lines):
 if line.startswith('AllowUsers ') and 'obfuscator-relay' not in line.split():lines[i]=line+' obfuscator-relay'
p.write_text('\n'.join(lines)+'\n')
PY
cat > /etc/ssh/sshd_config.d/90-obfuscator-relay.conf <<'SSH'
Match User obfuscator-relay
    AuthorizedKeysFile /etc/ssh/authorized_keys/obfuscator-relay
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    AllowTcpForwarding remote
    GatewayPorts no
    PermitListen 127.0.0.1:9443 127.0.0.1:12222
    PermitTTY no
    AllowAgentForwarding no
    X11Forwarding no
    MaxSessions 0
Match all
SSH
sshd -t
systemctl reload ssh
install -m644 "$base/systemd/obfuscator-az1-relay.socket" "$base/systemd/obfuscator-az1-relay.service" /etc/systemd/system/
ufw allow 443/tcp comment 'AZ1 MTProto relay'
systemctl daemon-reload
if systemctl is-active --quiet haproxy && grep -q "backend mtproto_az1" /etc/haproxy/haproxy.cfg; then
  echo "Shared HAProxy ingress already active; standalone socket stays disabled"
else
  systemctl enable --now obfuscator-az1-relay.socket
fi
echo 'DE1 ingress ready; MTProto 8888 unchanged.'
