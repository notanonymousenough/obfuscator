#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
getent passwd obfsub >/dev/null || useradd --system --home-dir /var/lib/obfuscator-subscriptions --shell /usr/sbin/nologin obfsub
install -d -o root -g obfsub -m750 /var/lib/obfuscator-subscriptions
install -d -m755 /usr/local/lib/obfuscator-subscriptions
install -m755 server.py /usr/local/lib/obfuscator-subscriptions/server.py
if ! test -f /var/lib/obfuscator-subscriptions/data.json; then
 printf '{"clients":{}}\n' > /var/lib/obfuscator-subscriptions/data.json
 chown root:obfsub /var/lib/obfuscator-subscriptions/data.json; chmod 640 /var/lib/obfuscator-subscriptions/data.json
fi
install -m644 systemd/obfuscator-subscriptions.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable --now obfuscator-subscriptions
certbot certonly --non-interactive --agree-tos --register-unsafely-without-email --dns-cloudflare --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini --dns-cloudflare-propagation-seconds 30 --cert-name obfuscator-portal -d obfuscator.funsociety.dev -d mtp.funsociety.dev
install -m644 config/nginx-portal.conf /etc/nginx/sites-available/obfuscator-portal
ln -sfn /etc/nginx/sites-available/obfuscator-portal /etc/nginx/sites-enabled/obfuscator-portal
nginx -t; systemctl reload nginx
curl -fsS -H 'Host: obfuscator.funsociety.dev' http://127.0.0.1:9080/healthz
