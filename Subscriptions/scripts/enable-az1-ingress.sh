#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq haproxy
haproxy -c -f config/haproxy-az1.cfg
# Preserve existing secret; change only its listener and ingress ownership.
cp -an /etc/obfuscator/mtg.toml /etc/obfuscator/mtg.toml.pre-subscriptions
python3 - <<'PY'
import pathlib,re
p=pathlib.Path('/etc/obfuscator/mtg.toml');s=p.read_text();s,n=re.subn(r'(?m)^bind-to\s*=.*$', 'bind-to = "127.0.0.1:8448"',s);assert n==1;p.write_text(s)
PY
install -m644 config/haproxy-az1.cfg /etc/haproxy/haproxy.cfg
# There is a brief handoff of TCP 443. On any failed start restore the original listener.
if ! systemctl restart obfuscator-mtp || ! systemctl restart haproxy; then
 systemctl stop haproxy
 cp -a /etc/obfuscator/mtg.toml.pre-subscriptions /etc/obfuscator/mtg.toml
 systemctl restart obfuscator-mtp
 exit 1
fi
systemctl enable haproxy
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/systemd/system/obfuscator-az1-tunnel.service');s=p.read_text()
if '127.0.0.1:9444' not in s:
 s=s.replace(' obfuscator-relay@',' -R 127.0.0.1:9444:127.0.0.1:8444 -R 127.0.0.1:9446:127.0.0.1:8446 obfuscator-relay@');p.write_text(s)
PY
systemctl daemon-reload; systemctl restart obfuscator-az1-tunnel
systemctl is-active obfuscator-mtp haproxy obfuscator-telemt obfuscator-vpn obfuscator-az1-tunnel
