#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
python3 scripts/import-cloudflare.py /home/deploy/cloudflare.ini
certbot certonly --non-interactive --agree-tos --register-unsafely-without-email --dns-cloudflare --dns-cloudflare-credentials /etc/obfuscator/cloudflare.ini --dns-cloudflare-propagation-seconds 90 --cert-name obfuscator-az1-vpn -d vpn-az1.obfuscator.funsociety.dev -d mtp.funsociety.dev
printf '%s\n' '4d30283ae614e3057f730f67cd088a42be6fdf91f8639d82cb69e48cde80413c  assets/Xray-linux-arm64-v8a.zip' | sha256sum -c -
python3 - <<'PY'
import zipfile,pathlib,os
p=pathlib.Path('/usr/local/bin/xray')
with zipfile.ZipFile('assets/Xray-linux-arm64-v8a.zip') as z:p.write_bytes(z.read('xray'))
p.chmod(0o755)
PY
getent passwd obfvpn >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin obfvpn
install -d -o root -g obfvpn -m750 /etc/obfuscator-vpn
if ! test -f /etc/obfuscator-vpn/config.json; then install -o root -g obfvpn -m640 config/az1-vpn.json /etc/obfuscator-vpn/config.json; fi
/usr/local/bin/xray run -test -c /etc/obfuscator-vpn/config.json
install -m644 systemd/obfuscator-vpn.service /etc/systemd/system/
install -m644 config/nginx-az1.conf /etc/nginx/sites-available/obfuscator-vpn
ln -sfn /etc/nginx/sites-available/obfuscator-vpn /etc/nginx/sites-enabled/obfuscator-vpn
nginx -t; systemctl reload nginx
systemctl daemon-reload; systemctl enable --now obfuscator-vpn
ufw allow 80/tcp
systemctl is-active obfuscator-vpn nginx
