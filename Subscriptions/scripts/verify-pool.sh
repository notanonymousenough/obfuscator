#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
python3 - <<'PY'
import json,socket,time
from mtp_probe import authenticate
clients=json.load(open('/etc/obfuscator-managed/owned.json'))
key=next(c['mtp'] for c in clients if c['name']=='owner')
def command(text):
 with socket.socket(socket.AF_UNIX) as s:
  s.connect('/run/haproxy/admin.sock');s.sendall((text+'\n').encode());s.shutdown(socket.SHUT_WR);s.recv(4096)
try:
 for disabled,active in [('de1','az1'),('az1','de1')]:
  command('enable server mtproto_pool/'+active)
  command('disable server mtproto_pool/'+disabled)
  assert authenticate(key,'127.0.0.1',443)
  print('MTProto pool: '+disabled+' disabled; authenticated through '+active)
finally:
 for name in ['de1','az1']:command('enable server mtproto_pool/'+name)
print('MTProto pool: both backends restored')
PY
