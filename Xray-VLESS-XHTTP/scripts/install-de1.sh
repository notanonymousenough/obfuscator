#!/usr/bin/env bash
# DE1: retain x-ui/MTProto 8888; HAProxy routes AZ1 SNI and DE1 XHTTP.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export DEBIAN_FRONTEND=noninteractive LC_ALL=C
[[ $EUID -eq 0 ]]
[[ $(hostname -s) == obfuscator-de1 ]] || { echo "Wrong host; expected obfuscator-de1" >&2; exit 1; }
base=$(cd "$(dirname "$0")/.." && pwd)
apt-get update
apt-get install -y docker.io docker-compose-v2 nginx haproxy
systemctl enable --now docker
install -d -m700 /opt/xray /etc/obfuscator-xhttp
install -d -m755 /var/www/decoy /var/www/acme
python3 - "$base" <<'PY'
import json,pathlib,secrets,sys,uuid,urllib.parse
base=pathlib.Path(sys.argv[1]);p=pathlib.Path('/opt/xray/config.json')
if not p.exists():
 s=(base/'config/server.json.example').read_text().replace('__CLIENT_UUID__',str(uuid.uuid4())).replace('__XHTTP_PATH__','/'+secrets.token_urlsafe(24))
 d=json.loads(s);d['inbounds'][0]['port']=8445;p.write_text(json.dumps(d,indent=2)+'\n');p.chmod(0o644)
d=json.loads(p.read_text());b=d['inbounds'][0];client=b['settings']['clients'][0]['id'];path=b['streamSettings']['xhttpSettings']['path'];domain='de1.obfuscator.funsociety.dev'
s=(base/'config/client.json.example').read_text().replace('__CLIENT_UUID__',client).replace('__XHTTP_PATH__',path).replace('__DOMAIN__',domain)
c=json.loads(s);c['inbounds'][0]['port']=1081
f=pathlib.Path('/etc/obfuscator-xhttp/client.json');f.write_text(json.dumps(c,indent=2)+'\n');f.chmod(0o600)
query=urllib.parse.urlencode({'encryption':'none','security':'tls','sni':domain,'alpn':'h2','fp':'chrome','type':'xhttp','path':path,'mode':'stream-up'})
f=pathlib.Path('/etc/obfuscator-xhttp/client-link.txt');f.write_text('vless://'+client+'@'+domain+':443?'+query+'#DE1-XHTTP\n');f.chmod(0o600)
s=(base/'config/nginx.conf.example').read_text().replace('__DOMAIN__',domain).replace('__XHTTP_PATH__',path)
s=s.replace('listen 443 ssl http2;','listen 127.0.0.1:8444 ssl http2;').replace('    listen [::]:443 ssl http2;\n','').replace('127.0.0.1:8443','127.0.0.1:8445')
s=s.replace('    return 301 https://$host$request_uri;', '    location /.well-known/acme-challenge/ { root /var/www/acme; }\n    location / { return 301 https://$host$request_uri; }')
f=pathlib.Path('/etc/nginx/sites-available/obfuscator-de1');f.write_text(s);f.chmod(0o600)
PY
install -m600 "$base/config/docker-compose.pinned.yml" /opt/xray/docker-compose.yml
install -m644 "$base/systemd/xray-docker.service" /etc/systemd/system/
printf '%s\n' '<!doctype html><html><head><title>Service</title></head><body>Service online</body></html>' > /var/www/decoy/index.html
ln -sfn /etc/nginx/sites-available/obfuscator-de1 /etc/nginx/sites-enabled/obfuscator-de1
rm -f /etc/nginx/sites-enabled/default
openssl x509 -checkend 86400 -noout -in /etc/letsencrypt/live/de1.obfuscator.funsociety.dev/cert.pem
nginx -t
systemctl enable --now nginx
systemctl reload nginx
install -d -m755 /etc/letsencrypt/renewal-hooks/deploy
install -m755 "$base/scripts/reload-nginx-after-renewal.sh" /etc/letsencrypt/renewal-hooks/deploy/obfuscator-nginx
cd /opt/xray
docker compose pull
docker compose run --rm --no-deps xray run -test -c /etc/xray/config.json
systemctl daemon-reload
systemctl enable --now xray-docker
# Preflight before touching public ingress.
install -m644 "$base/config/haproxy-de1.cfg" /etc/haproxy/haproxy.cfg
haproxy -c -f /etc/haproxy/haproxy.cfg
ufw allow 80/tcp comment 'ACME and HTTPS redirect'
ufw allow 443/tcp comment 'MTProto AZ1 and XHTTP DE1'
systemctl disable --now obfuscator-az1-relay.socket
systemctl stop obfuscator-az1-relay.service
if ! systemctl restart haproxy; then
  systemctl enable --now obfuscator-az1-relay.socket
  echo 'HAProxy failed; previous MTProto-only relay restored' >&2
  exit 1
fi
systemctl enable haproxy certbot.timer
echo 'DE1 SNI ingress active. Private client data remains in /etc/obfuscator-xhttp.'
