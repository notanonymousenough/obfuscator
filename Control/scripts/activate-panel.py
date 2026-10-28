#!/usr/bin/python3
"""Install a preflight-validated panel; keep existing databases and private rollback copies."""
import datetime,json,os,pathlib,re,shutil,sqlite3,subprocess,time,urllib.request
P=pathlib.Path
node={'obfuscator-de1':'de1','obfuscator-de2':'de2','obfuscator-az1':'az1'}[os.uname().nodename.split('.')[0]]
release=P('/opt/obfuscator-control/releases/3x-ui-3.11.0');assert (release/'x-ui').exists()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=P('/var/lib/obfuscator-control/backups')/stamp;backup.mkdir(mode=0o700,parents=True)
root=P('/etc/obfuscator-control');root.mkdir(mode=0o700,exist_ok=True);root.chmod(0o710 if (root/"tunnel").exists() else 0o700)
def run(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def backup_db(source,dest):
 if source.exists():
  a=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True);b=sqlite3.connect(str(dest));a.backup(b);b.close();a.close();dest.chmod(0o600)
db=P('/etc/x-ui/x-ui.db');backup_db(db,backup/'x-ui.db')
unit=P('/etc/systemd/system/x-ui.service')
if unit.exists():shutil.copy2(unit,backup/'x-ui.service')
was_active=subprocess.run(['systemctl','is-active','--quiet','x-ui']).returncode==0
was_enabled=subprocess.run(['systemctl','is-enabled','--quiet','x-ui']).returncode==0
(backup/'previous-state.json').write_text(json.dumps({'active':was_active,'enabled':was_enabled}))
app=P('/usr/local/x-ui');previous=P('/usr/local/x-ui.precontrol-'+stamp)
import secrets
password=secrets.token_urlsafe(24);base='/control/' if node=='de1' else '/control-node/'
try:
 subprocess.run(['systemctl','stop','x-ui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if app.exists():app.rename(previous)
 shutil.copytree(release,app)
 P('/etc/x-ui').mkdir(mode=0o700,exist_ok=True)
 env=dict(os.environ,XUI_DB_FOLDER='/etc/x-ui',XUI_BIN_FOLDER='/usr/local/x-ui/bin')
 with (root/'installation.log').open('w') as log:
  os.chmod(log.name,0o600)
  run([str(app/'x-ui'),'setting','-port','1337','-listenIP','127.0.0.1','-webBasePath',base,'-username','operator','-password',password],env=env,stdout=log,stderr=subprocess.STDOUT)
  scope='admin' if node=='de1' else 'node-sync'
  token_output=subprocess.check_output([str(app/'x-ui'),'setting','-getApiToken','-tokenName','obfuscator-control','-tokenScope',scope],env=env,stderr=log,text=True)
 token=re.search(r'^apiToken:\s*(\S+)',token_output,re.M);assert token,'Token generation failed'
 private={'node':node,'apiToken':token.group(1),'scope':scope,'basePath':base,'port':1337,'username':'operator','password':password}
 p=root/'access.json';p.write_text(json.dumps(private,indent=2)+'\n');p.chmod(0o600)
 shutil.copy2('/home/deploy/obfuscator-control/systemd/x-ui.service',unit)
 run(['systemctl','daemon-reload']);run(['systemctl','enable','--now','x-ui'])
 for _ in range(60):
  try:
   req=urllib.request.Request('http://127.0.0.1:1337'+base+'panel/api/inbounds/list',headers={'Authorization':'Bearer '+token.group(1)})
   with urllib.request.urlopen(req,timeout=2) as response:result=json.load(response)
   assert result.get('success'), 'API readiness failed';break
  except Exception:time.sleep(.5)
 else:raise RuntimeError('Panel API not ready')
 db.chmod(0o600)
 # Compare all original id/secret/password values, without exporting them.
 if (backup/'x-ui.db').exists():
  def ids(path):
   c=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);out=set()
   for (settings,) in c.execute('SELECT settings FROM inbounds'):
    for client in json.loads(settings or '{}').get('clients',[]):
     out.update((k,str(client[k])) for k in ['id','secret','password'] if client.get(k))
   c.close();return out
  before=ids(backup/'x-ui.db');assert before.issubset(ids(db)),'Existing credential preservation check failed'
  print('Panel',node,'3.11.0 ready; existing credentials preserved:',len(before))
 else:print('Panel',node,'3.11.0 ready; fresh node database')
except Exception:
 subprocess.run(['systemctl','stop','x-ui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if previous.exists():
  if app.exists():app.rename(P('/usr/local/x-ui.failed-'+stamp))
  previous.rename(app)
 if (backup/'x-ui.db').exists():
  for suffix in ['-wal','-shm']:
   p=P(str(db)+suffix)
   if p.exists():p.rename(backup/p.name)
  shutil.copy2(backup/'x-ui.db',db)
 if (backup/'x-ui.service').exists():shutil.copy2(backup/'x-ui.service',unit)
 subprocess.run(['systemctl','daemon-reload'])
 if was_active:subprocess.run(['systemctl','start','x-ui'])
 if not was_enabled:subprocess.run(['systemctl','disable','x-ui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 raise RuntimeError('Panel activation failed; previous installation restored') from None
