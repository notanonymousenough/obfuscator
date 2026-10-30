#!/bin/bash
set -euo pipefail
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup=/var/backups/obfuscator-cloudflare-$stamp
install -d -m700 "$backup"
cp -a /etc/obfuscator-vpn/config.json "$backup/xray.json"
cp -a /etc/haproxy/haproxy.cfg "$backup/haproxy.cfg"
systemctl is-enabled obfuscator-vpn-ddns.timer > "$backup/ddns-enabled" || true
curl -fL --retry 2 --max-time 180 https://github.com/cloudflare/cloudflared/releases/download/2026.10.6/cloudflared-linux-arm64 -o /tmp/obf-cloudflared
printf '%s\n' '0ae0e179475b2c77651a718d2b376e0151f4fca5954702a84f02843a4d5fcac0  /tmp/obf-cloudflared' | sha256sum -c -
install -m755 /tmp/obf-cloudflared /usr/local/bin/cloudflared
rm /tmp/obf-cloudflared
install -d -m700 /etc/cloudflared
install -m600 /home/deploy/.obf-cfd-token /etc/cloudflared/az1.token
rm /home/deploy/.obf-cfd-token
python3 - <<'PY'
import pathlib,json
p=pathlib.Path('/etc/obfuscator-vpn/config.json');d=json.loads(p.read_text())
for b in d['inbounds']:
 if b['protocol']=='vless':b['streamSettings']['xhttpSettings']['mode']='auto'
p.write_text(json.dumps(d,indent=2)+'\n')
PY
/usr/local/bin/xray run -test -c /etc/obfuscator-vpn/config.json
install -m644 /home/deploy/obfuscator-subscriptions/config/nginx-az1-tunnel.conf /etc/nginx/sites-available/obfuscator-cloudflare
ln -sfn /etc/nginx/sites-available/obfuscator-cloudflare /etc/nginx/sites-enabled/obfuscator-cloudflare
nginx -t
systemctl restart obfuscator-vpn
systemctl reload nginx
cat > /etc/systemd/system/obfuscator-cloudflared.service <<'EOF'
[Unit]
Description=Cloudflare XHTTP ingress for AZ1
Wants=network-online.target
After=network-online.target nginx.service obfuscator-vpn.service
StartLimitIntervalSec=0
[Service]
ExecStart=/usr/local/bin/cloudflared --no-autoupdate tunnel run --token-file /etc/cloudflared/az1.token
Restart=always
RestartSec=5
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now obfuscator-cloudflared
curl -fsS http://127.0.0.1:18080/.well-known/obfuscator-node
systemctl is-active obfuscator-cloudflared
# A tunnel CNAME must never be overwritten by the former direct/DE1 DDNS.
systemctl disable --now obfuscator-vpn-ddns.timer
systemctl stop obfuscator-vpn-ddns.service
systemctl disable --now obfuscator-ddns.timer 2>/dev/null || true
