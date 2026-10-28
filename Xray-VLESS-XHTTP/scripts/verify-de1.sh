#!/usr/bin/env bash
# Authenticate through the public DE1 XHTTP route without exporting client secrets.
set -euo pipefail
[[ $EUID -eq 0 && $(hostname -s) == obfuscator-de1 ]]
image=ghcr.io/xtls/xray-core@sha256:592ec4d11f656db95598d01e76dbcc6e002d67360b96a5436500a938230f52c7
probe=obfuscator-xhttp-probe-$$
file=$(mktemp /opt/xray/.probe-XXXX.json)
cleanup() { docker stop "$probe" >/dev/null 2>&1 || true; rm -f "$file"; }
trap cleanup EXIT
install -m644 /etc/obfuscator-xhttp/client.json "$file"
docker run --rm -d --name "$probe" --network host -v "$file":/etc/xray/config.json:ro "$image" run -c /etc/xray/config.json >/dev/null
for attempt in {1..5}; do
 sleep 1
 if curl -fsS --max-time 20 --proxy socks5h://127.0.0.1:1081 https://api.ipify.org; then echo;exit 0;fi
done
exit 1
