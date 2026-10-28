#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]] || { echo 'Run as root'; exit 1; }
domain=$(cat /etc/obfuscator/domain)
[[ -s /etc/obfuscator/cloudflare.token ]] || { echo 'Missing root-only Cloudflare token'; exit 1; }
umask 077
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/obfuscator/cloudflare.token');v=p.read_text().strip()
if not v or any(c.isspace() for c in v):raise SystemExit('Expected raw Cloudflare API token')
Path('/etc/obfuscator/cloudflare.ini').write_text('dns_cloudflare_api_token = '+v+'\n')
PY
# DNS-01 works behind CGNAT. No self-signed fallback or exposed HTTP challenge.
certbot certonly --non-interactive --agree-tos --register-unsafely-without-email \
  --dns-cloudflare --dns-cloudflare-credentials /etc/obfuscator/cloudflare.ini \
  --dns-cloudflare-propagation-seconds 60 --cert-name "$domain" -d "$domain" --keep-until-expiring
cat > /etc/nginx/sites-available/obfuscator-mtp <<EOF
server {
    listen 127.0.0.1:8443 ssl;
    server_name $domain;
    ssl_certificate /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /var/www/obfuscator;
    access_log off;
    location / { try_files \$uri /index.html; }
}
EOF
ln -sfn /etc/nginx/sites-available/obfuscator-mtp /etc/nginx/sites-enabled/obfuscator-mtp
rm -f /etc/nginx/sites-enabled/default
nginx -t
install -d -m 755 /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/obfuscator-nginx <<'EOF'
#!/bin/sh
set -eu
/usr/sbin/nginx -t
/bin/systemctl reload nginx
EOF
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/obfuscator-nginx
systemctl enable --now nginx.service
systemctl reload nginx.service
systemctl enable --now certbot.timer
systemctl enable --now obfuscator-mtp.service
echo 'TLS fallback and MTProto enabled. Public ingress still requires a public address or relay.'
