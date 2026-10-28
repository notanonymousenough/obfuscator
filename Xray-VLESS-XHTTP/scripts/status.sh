#!/usr/bin/env bash
set -u
systemctl --no-pager status xray-docker nginx certbot.timer
cd /opt/xray || exit
sudo docker compose ps
sudo docker compose logs --tail 30 xray
openssl s_client -connect de2.obfuscator.funsociety.dev:443 -servername de2.obfuscator.funsociety.dev -verify_return_error </dev/null
