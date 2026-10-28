#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import datetime,json,pathlib,sqlite3,subprocess
node=subprocess.check_output(['hostname','-s'],text=True).strip()
def call(cmd):return subprocess.run(cmd,capture_output=True,text=True).stdout.strip()
out={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hostname':node,'services':{},'legacy':None}
for unit in ['x-ui','xray-docker','nginx','haproxy','obfuscator-subscriptions','obfuscator-telemt','obfuscator-mtp','obfuscator-vpn','obfuscator-az1-tunnel','obfuscator-vpn-ddns.timer','certbot.timer']:
 out['services'][unit]={'active':call(['systemctl','is-active',unit]),'enabled':call(['systemctl','is-enabled',unit])}
p=subprocess.run(['/usr/local/sbin/obfuscator-node-agent'],input='{"action":"baseline"}',capture_output=True,text=True,check=True);out['legacy']=json.loads(p.stdout)['legacy_preserved']
p=pathlib.Path('/etc/x-ui/x-ui.db')
if p.exists():
 con=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True)
 out['xui_inbounds']=[{'protocol':proto,'port':port,'enabled':bool(enabled),'client_entries':len(json.loads(settings or '{}').get('clients',[]))} for proto,port,enabled,settings in con.execute('SELECT protocol,port,enable,settings FROM inbounds')];con.close()
owned=pathlib.Path('/etc/obfuscator-managed/owned.json');out['managed_clients']=len(json.loads(owned.read_text())) if owned.exists() else 0
out['listener_ports']=call(['ss','-H','-ltn']).splitlines()
print(json.dumps(out,indent=2))
PY
