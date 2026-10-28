#!/usr/bin/env bash
# Installs local AZ1 components. Public ingress and DNS are configured separately.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]] || { echo 'Run as root'; exit 1; }
[[ $(uname -m) == aarch64 ]] || { echo 'This bundle is pinned for Linux ARM64'; exit 1; }
base=$(cd -- "$(dirname -- "$0")/.." && pwd)
domain=${1:-az1.obfuscator.funsociety.dev}
[[ "$domain" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || exit 2
(cd "$base/dist" && sha256sum -c SHA256SUMS)
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates nginx certbot python3-certbot-dns-cloudflare ufw fail2ban unattended-upgrades
getent passwd mtg >/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin mtg
install -d -m 750 -o root -g mtg /etc/obfuscator
install -d -m 755 /usr/local/lib/obfuscator /var/lib/obfuscator /var/www/obfuscator
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
tar -xzf "$base/dist/mtg-2.2.8-linux-arm64.tar.gz" -C "$scratch"
install -m 755 "$scratch/mtg-2.2.8-linux-arm64/mtg" /usr/local/bin/mtg
install -d -m 755 /usr/local/share/doc/mtg
install -m 644 "$scratch/mtg-2.2.8-linux-arm64/LICENSE" /usr/local/share/doc/mtg/LICENSE
for f in "$base"/scripts/*.sh "$base"/scripts/*.py; do install -m 755 "$f" /usr/local/lib/obfuscator/; done
if [[ ! -e /etc/obfuscator/mtg.toml ]]; then
  python3 - "$base/config/mtg.toml.example" "$domain" <<'PY'
import pathlib,secrets,sys,os
secret='ee'+secrets.token_hex(16)+sys.argv[2].encode().hex()
p=pathlib.Path('/etc/obfuscator/mtg.toml')
p.write_text(pathlib.Path(sys.argv[1]).read_text().replace('__GENERATED_EE_SECRET__',secret))
os.chmod(p,0o640)
PY
fi
chown root:mtg /etc/obfuscator/mtg.toml
chmod 640 /etc/obfuscator/mtg.toml
printf '%s\n' "$domain" > /etc/obfuscator/domain
chmod 644 /etc/obfuscator/domain
printf '%s\n' '<!doctype html><html><head><title>Service</title></head><body><h1>Service online</h1></body></html>' > /var/www/obfuscator/index.html
install -m 644 "$base/systemd/obfuscator-mtp.service" /etc/systemd/system/
install -m 644 "$base/systemd/obfuscator-ddns.service" "$base/systemd/obfuscator-ddns.timer" /etc/systemd/system/
cat > /etc/fail2ban/jail.d/obfuscator-sshd.local <<'EOF'
[sshd]
enabled = true
backend = systemd
port = 2222
maxretry = 5
findtime = 10m
bantime = 1h
EOF
cat > /etc/sysctl.d/90-obfuscator.conf <<'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
EOF
modprobe tcp_bbr || true
sysctl -p /etc/sysctl.d/90-obfuscator.conf || true
ufw allow 22/tcp comment 'Temporary SSH migration'
ufw allow 2222/tcp comment 'Obfuscator SSH'
ufw allow 443/tcp comment 'MTProto FakeTLS'
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
systemctl enable --now fail2ban.service
systemctl enable --now systemd-timesyncd.service
systemctl enable certbot.timer
systemctl daemon-reload
# MTP is enabled/started by configure-tls.sh only after a real certificate exists.
echo 'Installed. Next: stage SSH, configure DNS credentials and TLS, verify ingress.'
