#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
cp -an /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.pre-subscriptions
haproxy -c -f config/haproxy-de1.cfg
install -m644 config/haproxy-de1.cfg /etc/haproxy/haproxy.cfg
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/ssh/sshd_config.d/90-obfuscator-relay.conf');s=p.read_text();s=s.replace('PermitListen 127.0.0.1:9443 127.0.0.1:12222','PermitListen 127.0.0.1:9443 127.0.0.1:12222 127.0.0.1:9444 127.0.0.1:9446');p.write_text(s)
p=Path('/etc/ssh/authorized_keys/obfuscator-relay');s=p.read_text();marker='permitlisten="127.0.0.1:9446"'
if marker not in s:s=s.replace('permitlisten="127.0.0.1:9443"','permitlisten="127.0.0.1:9443",permitlisten="127.0.0.1:9444",permitlisten="127.0.0.1:9446"');p.write_text(s)
PY
sshd -t; systemctl reload ssh
systemctl reload haproxy
systemctl is-active haproxy obfuscator-telemt obfuscator-subscriptions
