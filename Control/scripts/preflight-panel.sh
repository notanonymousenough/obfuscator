#!/bin/bash
set -euo pipefail
root=/opt/obfuscator-control/releases/3x-ui-3.11.0
staging=/home/deploy/obfuscator-control
case $(uname -m) in
x86_64) archive=x-ui-linux-amd64.tar.gz; digest=0ddfa4702f595442e2962acd81addc768fdacaa4ff2672c971a0463dae744916;;
aarch64) archive=x-ui-linux-arm64.tar.gz; digest=f50b4c30fd919d018f2f4c3d8db53a4ca027503d581328727770afb116a79d90;;
*) exit 1;;esac
printf '%s  %s\n' "$digest" "$staging/assets/$archive" | sha256sum -c -
install -d -m755 "$root"
tar -xzf "$staging/assets/$archive" --strip-components=1 -C "$root"
chown -R root:root "$root"
install -d -m700 /var/lib/obfuscator-control/preflight-db
python3 - <<'PY'
import pathlib,sqlite3
source=pathlib.Path('/etc/x-ui/x-ui.db');dest=pathlib.Path('/var/lib/obfuscator-control/preflight-db/x-ui.db')
if source.exists():
 a=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True);b=sqlite3.connect(str(dest));a.backup(b);b.close();a.close();dest.chmod(0o600)
print('Private migration copy ready')
PY
# Migrations run only against the isolated copy; no new service/listener is started.
XUI_DB_FOLDER=/var/lib/obfuscator-control/preflight-db XUI_BIN_FOLDER="$root/bin" "$root/x-ui" setting -getListen > /var/lib/obfuscator-control/preflight-db/migration.log 2>&1
python3 - <<'PY'
import sqlite3,json,pathlib
original=pathlib.Path('/etc/x-ui/x-ui.db');new=pathlib.Path('/var/lib/obfuscator-control/preflight-db/x-ui.db')
def identities(path):
 out=set();con=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
 for proto,settings in con.execute('SELECT protocol,settings FROM inbounds'):
  d=json.loads(settings or '{}')
  for c in d.get('clients',[]):
   for k in ['id','secret','password']:
    if c.get(k):out.add((k,str(c[k])))
 con.close();return out
if original.exists():
 before=identities(original);after=identities(new)
 assert before.issubset(after),'Migration changed an existing credential'
 print('3x-ui migration copy: preserved credential entries',len(before))
else:print('3x-ui new node database preflight passed')
PY
"$root/x-ui" -v
