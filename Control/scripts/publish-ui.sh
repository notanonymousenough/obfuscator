#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-control
python3 - <<'PY'
import json,ipaddress,pathlib
cfg=json.loads(pathlib.Path('inventory.json').read_text())
p=pathlib.Path('/etc/nginx/snippets/obfuscator-control-allow.conf')
text=''.join('allow '+str(ipaddress.ip_network(v,strict=True))+';\n' for v in cfg['admin_allow_ipv4'])+'allow 127.0.0.1;\nallow ::1;\ndeny all;\n';p.write_text(text);p.chmod(0o644)
PY
install -m644 config/nginx-http.conf /etc/nginx/conf.d/obfuscator-control.conf
install -m644 config/nginx-portal.conf /etc/nginx/sites-available/obfuscator-control
ln -sfn /etc/nginx/sites-available/obfuscator-control /etc/nginx/sites-enabled/obfuscator-control
nginx -t; systemctl reload nginx
haproxy -c -f /home/deploy/obfuscator-subscriptions/config/haproxy-de1.cfg
install -m644 /home/deploy/obfuscator-subscriptions/config/haproxy-de1.cfg /etc/haproxy/haproxy.cfg
systemctl reload haproxy
sleep 1
curl -fsS --max-time 8 --resolve obfuscator.funsociety.dev:443:127.0.0.1 https://obfuscator.funsociety.dev/control/ -o /dev/null -w 'Restricted UI HTTP %{http_code}\n'
