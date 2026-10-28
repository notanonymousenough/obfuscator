#!/bin/bash
set -euo pipefail
mkdir -p /home/deploy/obfuscator-subscriptions/assets
cd /home/deploy/obfuscator-subscriptions/assets
case $(uname -m) in
 x86_64) name=telemt-x86_64-linux-musl.tar.gz; digest=71c1454f79cf755edea0985500629daba553002f9863be754e8e38a418822773;;
 aarch64) name=telemt-aarch64-linux-musl.tar.gz; digest=21795430c4165cf964405459714d08eea319edaa5c9027beac4de373c356d84d;;
 *) echo 'Unsupported architecture'; exit 1;;
esac
curl -fsSL --retry 2 --max-time 180 "https://github.com/telemt/telemt/releases/download/3.5.14/$name" -o "$name"
printf '%s  %s\n' "$digest" "$name" | sha256sum -c -
if [ "$(uname -m)" = aarch64 ]; then
 curl -fsSL --retry 2 --max-time 180 https://github.com/XTLS/Xray-core/releases/download/v26.3.27/Xray-linux-arm64-v8a.zip -o Xray-linux-arm64-v8a.zip
 printf '%s\n' '4d30283ae614e3057f730f67cd088a42be6fdf91f8639d82cb69e48cde80413c  Xray-linux-arm64-v8a.zip' | sha256sum -c -
fi
