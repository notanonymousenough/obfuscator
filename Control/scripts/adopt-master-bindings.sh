#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import datetime,json,pathlib,sqlite3,time
path=pathlib.Path('/etc/x-ui/x-ui.db')
backup=pathlib.Path('/var/lib/obfuscator-control/backups')/('bindings-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.db')
a=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);b=sqlite3.connect(str(backup));a.backup(b);b.close();a.close();backup.chmod(0o600)
con=sqlite3.connect(path,timeout=10);con.row_factory=sqlite3.Row;con.execute('BEGIN IMMEDIATE')
try:
 count=0
 for inbound in list(con.execute("SELECT id,tag,settings FROM inbounds WHERE tag LIKE 'obf-%'")):
  for wire in json.loads(inbound['settings']).get('clients',[]):
   row=con.execute('SELECT * FROM clients WHERE email=?',(wire['email'],)).fetchone()
   if not row:raise RuntimeError('Missing canonical identity; refusing partial adoption')
   if (wire.get('id') and wire['id']!=row['uuid']) or wire.get('subId')!=row['sub_id'] or (wire.get('secret') and wire['secret']!=row['secret']):raise RuntimeError('Identity mismatch; refusing to merge clients')
   result=con.execute('INSERT OR IGNORE INTO client_inbounds(client_id,inbound_id,flow_override,created_at) VALUES(?,?,?,?)',(row['id'],inbound['id'],wire.get('flow',''),int(time.time()*1000)));count+=result.rowcount
 con.commit();print('Verified matching identity attachments added:',count)
except Exception:
 con.rollback();raise
finally:con.close()
PY
