#!/usr/bin/python3
"""Root-owned, stdin JSON-only reconciler. Legacy clients are never owned/removed."""
import datetime,socket,time,hashlib,json,os,pathlib,re,shutil,sqlite3,subprocess,sys,tempfile,uuid,urllib.parse
ROOT=pathlib.Path('/etc/obfuscator-managed'); BACK=pathlib.Path('/var/lib/obfuscator-managed/backups')
NODE={'obfuscator-de1':'de1','obfuscator-de2':'de2','obfuscator-az1':'az1'}
def atomic(path,data,mode=None):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 old=path.stat() if path.exists() else None
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.obfuscator-')
 try:
  with os.fdopen(fd,'w') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(name,mode if mode is not None else old.st_mode&0o777 if old else 0o600)
  if old:os.chown(name,old.st_uid,old.st_gid)
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=150)
 if p.returncode:raise RuntimeError('Command failed: '+args[0]+' '+args[1]+' (see local service logs)')
 return p.stdout
def vpn_path(node):return pathlib.Path('/etc/obfuscator-vpn/config.json' if node=='az1' else '/opt/xray/config.json')
def identities(node):
 out={'xui':[],'vpn':[],'mtp':[]}
 db=pathlib.Path('/etc/x-ui/x-ui.db')
 if db.exists():
  con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
  for (settings,) in con.execute('SELECT settings FROM inbounds'):
   d=json.loads(settings or '{}')
   for c in d.get('clients',[]):
    for k in ('id','secret','password'):
     if c.get(k):out['xui'].append(hashlib.sha256((k+':'+str(c[k])).encode()).hexdigest())
  con.close()
 p=vpn_path(node)
 if p.exists():
  for b in json.loads(p.read_text()).get('inbounds',[]):
   for c in b.get('settings',{}).get('clients',[]):
    if c.get('id'):out['vpn'].append(hashlib.sha256(c['id'].encode()).hexdigest())
 p=pathlib.Path('/etc/obfuscator/mtg.toml')
 if p.exists():
  import tomllib
  out['mtp']=[hashlib.sha256(tomllib.loads(p.read_text())['secret'].encode()).hexdigest()]
 return {k:sorted(set(v)) for k,v in out.items()}
def baseline(node):
 ROOT.mkdir(mode=0o700,parents=True,exist_ok=True);BACK.mkdir(mode=0o700,parents=True,exist_ok=True)
 base=ROOT/'legacy-baseline.json'
 if not base.exists():
  atomic(base,json.dumps(identities(node)),0o600)
  dest=BACK/('initial-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));dest.mkdir(mode=0o700)
  for p in [vpn_path(node),pathlib.Path('/etc/obfuscator/mtg.toml'),pathlib.Path('/etc/haproxy/haproxy.cfg')]:
   if p.exists():shutil.copy2(p,dest/(p.name+'.'+p.parent.name));os.chmod(dest/(p.name+'.'+p.parent.name),0o600)
  db=pathlib.Path('/etc/x-ui/x-ui.db')
  if db.exists():
   src=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True);target=sqlite3.connect(str(dest/'x-ui.db'));src.backup(target);target.close();src.close();os.chmod(dest/'x-ui.db',0o600)
 return json.loads(base.read_text())
def verify_legacy(node):
 expected=baseline(node);now=identities(node)
 for k,v in expected.items():
  if not set(v).issubset(now[k]):raise RuntimeError('Legacy preservation check failed: '+k)
 return {k:len(v) for k,v in expected.items()}
def telemt(clients,node):
 if node=='de2':return
 p=pathlib.Path('/etc/obfuscator-telemt/config.toml')
 head=pathlib.Path('/etc/obfuscator-telemt/base.toml').read_text()
 content=head+'\n[access.users]\n'+''.join(f'{c["name"]} = "{c["mtp"]}"\n' for c in clients)
 if not clients:content+='reserved_disabled = "'+('0'*32)+'"\n\n[access.user_enabled]\nreserved_disabled = false\n'
 if not p.exists() or p.read_text()!=content:
  prior=p.read_text() if p.exists() else None
  atomic(p,content,0o640);shutil.chown(p,user='root',group='obftelemt')
  try:
   run(['systemctl','restart','obfuscator-telemt'])
   for attempt in range(40):
    try:
     with socket.create_connection(('127.0.0.1',8446),timeout=.5):break
    except OSError:time.sleep(.25)
   else:raise RuntimeError('Telemt listener not ready')
  except Exception:
   if prior is not None:atomic(p,prior,0o640);run(['systemctl','restart','obfuscator-telemt'])
   raise
 else:run(['systemctl','is-active','obfuscator-telemt'])
def reconcile(node,payload):
 clients=payload.get('clients',[])
 if len({c['name'] for c in clients})!=len(clients) or len({c['uuid'] for c in clients})!=len(clients):raise ValueError('Duplicate managed identity')
 if len(clients)>500:raise ValueError('Too many clients')
 for c in clients:
  if not re.fullmatch(r'[a-z][a-z0-9_-]{0,47}',c['name']):raise ValueError('Invalid client name')
  uuid.UUID(c['uuid'])
  if not re.fullmatch('[0-9a-f]{32}',c['mtp']):raise ValueError('Invalid MTProto secret')
 previous=ROOT/'owned.json';old=json.loads(previous.read_text()) if previous.exists() else []
 path=vpn_path(node);cfg=json.loads(path.read_text());inbound=next(b for b in cfg['inbounds'] if b['protocol']=='vless')
 old_ids={c['uuid'] for c in old};desired={c['uuid'] for c in clients}
 current=inbound['settings']['clients'];unmanaged=[c for c in current if c.get('id') not in old_ids]
 if desired & {c.get('id') for c in unmanaged}:raise ValueError('Managed UUID collides with a legacy client')
 new=unmanaged+[{'id':c['uuid'],'email':'managed-'+c['name']} for c in clients]
 if current!=new:
  prior=path.read_text();inbound['settings']['clients']=new
  stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');atomic(BACK/(stamp+'-'+node+'-vpn.json'),prior,0o600)
  atomic(path,json.dumps(cfg,indent=2)+'\n')
  try:
   if node=='az1':run(['/usr/local/bin/xray','run','-test','-c',str(path)]);run(['systemctl','restart','obfuscator-vpn'])
   else:run(['systemctl','restart','xray-docker'])
  except Exception:
   atomic(path,prior);run(['systemctl','restart','obfuscator-vpn' if node=='az1' else 'xray-docker']);raise
 atomic(previous,json.dumps(clients,indent=2)+'\n',0o600)
 telemt(clients,node)
 stream=inbound['streamSettings'];domain={'de1':'de1.obfuscator.funsociety.dev','de2':'de2.obfuscator.funsociety.dev','az1':'vpn-az1.obfuscator.funsociety.dev'}[node]
 q=urllib.parse.urlencode({'encryption':'none','security':'tls','sni':domain,'alpn':'h2','fp':'chrome','type':'xhttp','path':stream['xhttpSettings']['path'],'mode':'stream-up'})
 links={c['name']:'vless://'+c['uuid']+'@'+domain+':443?'+q+'#'+node.upper() for c in clients}
 return {'node':node,'links':links,'legacy_preserved':verify_legacy(node),'managed_count':len(clients)}
def main():
 if os.geteuid()!=0:raise PermissionError('Root required')
 node=NODE.get(os.uname().nodename.split('.')[0]);assert node
 data=json.loads(sys.stdin.read(2_000_000));action=data.get('action');baseline(node)
 if action=='baseline':return {'node':node,'legacy_preserved':verify_legacy(node)}
 if action in ('reconcile','portal') and pathlib.Path('/etc/obfuscator-control/managed').exists():
  raise RuntimeError('3x-ui owns the client registry; use Control/ctl.py or the panel')
 if action=='reconcile':return reconcile(node,data)
 if action=='control-enroll' and node=='de1':
  nodes=data['nodes'];assert set(nodes)=={'de2','az1'}
  for name,cfg in nodes.items():
   assert cfg['node']==name and cfg['scope']=='node-sync' and cfg['basePath']=='/control-node/'
   assert re.fullmatch(r'[A-Za-z0-9_-]{20,200}',cfg['apiToken'])
   assert cfg['bridge_public_key'].startswith('ssh-ed25519 ')
  atomic('/etc/obfuscator-control/enrollment.json',json.dumps(nodes)+'\n',0o600)
  return {'stored_nodes':len(nodes)}
 if action=='control-export':
  info=json.loads(pathlib.Path('/etc/obfuscator-control/access.json').read_text())
  public=pathlib.Path('/etc/obfuscator-control/tunnel/id_ed25519.pub')
  if public.exists():info['bridge_public_key']=public.read_text().strip()
  if node!='de1':info.pop('password',None);info.pop('username',None)
  return info
 if action=='control-bootstrap':
  clients=data['clients']
  for c in clients:
   assert re.fullmatch(r'[a-z][a-z0-9_-]{0,47}',c['name']);uuid.UUID(c['uuid'])
   assert re.fullmatch('[0-9a-f]{32}',c['mtp']);assert re.fullmatch(r'[A-Za-z0-9_-]{32,100}',c['token'])
  atomic('/etc/obfuscator-control/bootstrap-clients.json',json.dumps(clients)+'\n',0o600)
  return {'stored':len(clients)}
 if action=='configure-ddns' and node=='az1':
  token=data['publisher_token'];assert re.fullmatch(r'[A-Za-z0-9_-]{43}',token)
  atomic('/etc/obfuscator/az1-publisher.token',token+'\n',0o600)
  config=pathlib.Path('/etc/obfuscator/az1-ddns.json');cfg=json.loads(config.read_text()) if config.exists() else {}
  cfg.update({'publisher_token_file':'/etc/obfuscator/az1-publisher.token','relay_ipv4':'159.89.12.205'});cfg.setdefault('ingress_mode','relay')
  atomic(config,json.dumps(cfg)+'\n',0o600)
  return {'configured':True}
 if action=='portal' and node=='de1':
  body=data['data'];assert isinstance(body['clients'],dict)
  atomic('/var/lib/obfuscator-subscriptions/data.json',json.dumps(body,indent=2)+'\n',0o640);shutil.chown('/var/lib/obfuscator-subscriptions/data.json',user='root',group='obfsub')
  return {'published':len(body['clients'])}
 raise ValueError('Unknown action')
if __name__=='__main__':
 try:print(json.dumps(main()))
 except Exception as e:print(json.dumps({'error':str(e)}));sys.exit(1)
