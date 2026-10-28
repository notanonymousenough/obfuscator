#!/usr/bin/env bash
# Stage both ports, verify a NEW connection on 2222, then call finalize.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]] || { echo 'Run as root'; exit 1; }
mode=${1:-stage}
state=/var/lib/obfuscator/ssh
conf=/etc/ssh/sshd_config.d/00-obfuscator.conf
install -d -m 700 "$state"
restart_ssh() {
  /usr/sbin/sshd -t
  systemctl daemon-reload
  if systemctl is-active --quiet ssh.socket; then systemctl restart ssh.socket; fi
  systemctl restart ssh.service
}
case "$mode" in
  rollback)
    cp -a "$state/sshd_config.original" /etc/ssh/sshd_config
    if [[ -e "$state/had-dropin" ]]; then cp -a "$state/dropin.original" "$conf"; else rm -f "$conf"; fi
    rm -f /etc/systemd/system/ssh.socket.d/obfuscator.conf
    restart_ssh
    exit 0;;
  commit)
    systemctl stop obfuscator-ssh-rollback.timer 2>/dev/null || true
    if [[ -f "$state/finalized" ]]; then ufw delete allow 22/tcp >/dev/null 2>&1 || true; fi
    echo 'SSH rollback cancelled after independent verification.'
    exit 0;;
  stage|finalize) ;;
  *) echo 'Usage: setup-ssh.sh stage|finalize|commit|rollback'; exit 2;;
esac
if [[ ! -f "$state/sshd_config.original" ]]; then
  cp -a /etc/ssh/sshd_config "$state/sshd_config.original"
  if [[ -e "$conf" ]]; then cp -a "$conf" "$state/dropin.original"; touch "$state/had-dropin"; fi
fi
# Do not leave an old explicit Port directive active in addition to the managed one.
sed -i -E 's/^([[:space:]]*Port[[:space:]]+.*)$/# Obfuscator managed: \1/' /etc/ssh/sshd_config
systemctl stop obfuscator-ssh-rollback.timer 2>/dev/null || true
systemctl reset-failed obfuscator-ssh-rollback.service 2>/dev/null || true
systemd-run --unit=obfuscator-ssh-rollback --on-active=5m /usr/local/lib/obfuscator/setup-ssh.sh rollback
{
  echo 'Port 2222'
  [[ "$mode" != stage ]] || echo 'Port 22'
  printf '%s\n' 'PermitRootLogin no' 'PasswordAuthentication no' 'KbdInteractiveAuthentication no' 'PubkeyAuthentication yes' 'AllowUsers deploy'
} > "$conf"
if systemctl is-enabled --quiet ssh.socket 2>/dev/null; then
  install -d /etc/systemd/system/ssh.socket.d
  {
    printf '[Socket]\nListenStream=\nListenStream=2222\n'
    [[ "$mode" != stage ]] || echo 'ListenStream=22'
  } > /etc/systemd/system/ssh.socket.d/obfuscator.conf
fi
ufw allow 2222/tcp comment 'Obfuscator SSH' >/dev/null
[[ "$mode" != stage ]] || ufw allow 22/tcp comment 'Temporary SSH migration' >/dev/null
restart_ssh
if [[ "$mode" == finalize ]]; then touch "$state/finalized"; else rm -f "$state/finalized"; fi
echo "SSH $mode applied. Verify a NEW connection on 2222, then commit within 5 minutes."
