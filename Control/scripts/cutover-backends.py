#!/usr/bin/python3
"""One-node transactional traffic adoption; public tests precede old-service shutdown.
Run only after the operator approves the production cutover. Rollback is also
available as a standalone action for a multi-node coordinator.
"""
import copy,json,os,pathlib,shutil,socket,subprocess,sys,tempfile,time
from importlib.machinery import SourceFileLoader
P=pathlib.Path;base=P('/home/deploy/obfuscator-control');Panel=SourceFileLoader('control_api',str(base/'api.py')).load_module().Panel
node={'obfuscator-de1':'de1','obfuscator-de2':'de2','obfuscator-az1':'az1'}[os.uname().nodename.split('.')[0]]
api=Panel(json.loads(P('/etc/obfuscator-control/access.json').read_text()))
old_service='obfuscator-vpn' if node=='az1' else 'xray-docker'
domain={'de1':'de1.obfuscator.funsociety.dev','de2':'de2.obfuscator.funsociety.dev','az1':'az1.funsociety.dev'}[node]
backup=P('/var/lib/obfuscator-control/backups/cutover');backup.mkdir(mode=0o700,parents=True,exist_ok=True);statefile=backup/'state.json'
def active(unit):return subprocess.run(['systemctl','is-active','--quiet',unit]).returncode==0
def enabled(unit):return subprocess.run(['systemctl','is-enabled','--quiet',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
def command(*args):subprocess.run(list(args),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def write_state(s):statefile.write_text(json.dumps(s,indent=2)+'\n');statefile.chmod(0o600)
def inbound(tag):return next(b for b in api.inbounds() if b['tag']==tag)
def parsed(v):return json.loads(v) if isinstance(v,str) else v
def public_probe():
 b=inbound('obf-vpn-'+node);user=next(c for c in json.loads(P('/etc/obfuscator-control/bootstrap-clients.json').read_text()) if c['enabled'])
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 stream=copy.deepcopy(parsed(b['streamSettings']));stream.update({'security':'tls','tlsSettings':{'serverName':domain,'fingerprint':'chrome','alpn':['h2']}})
 cfg={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':port,'protocol':'socks','settings':{'auth':'noauth'}}],'outbounds':[{'protocol':'vless','settings':{'vnext':[{'address':domain,'port':443,'users':[{'id':user['uuid'],'encryption':'none'}]}]},'streamSettings':stream}]}
 with tempfile.TemporaryDirectory(prefix='obf-cutover-') as d:
  p=P(d)/'client.json';p.write_text(json.dumps(cfg));p.chmod(0o600)
  binary=next(P('/usr/local/x-ui/bin').glob('xray-linux-*'));proc=subprocess.Popen([str(binary),'run','-c',str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for _ in range(100):
    try:
     with socket.create_connection(('127.0.0.1',port),timeout=.1):break
    except OSError:time.sleep(.05)
   for target in ['https://cp.cloudflare.com/generate_204','https://www.gstatic.com/generate_204']:
    r=subprocess.run(['curl','-fsS','--max-time','7','--proxy','socks5h://127.0.0.1:'+str(port),'-o','/dev/null','-w','%{http_code}',target],capture_output=True,text=True)
    if r.returncode or r.stdout!='204':raise RuntimeError('Authenticated public VPN smoke test failed')
  finally:proc.terminate();proc.wait(timeout=5)
 print(node,'public TLS/VLESS/XHTTP smoke passed',flush=True)
def rollback(s):
 if s['vpn_active']:command('systemctl','start',old_service)
 if s['vpn_enabled']:command('systemctl','enable',old_service)
 else:command('systemctl','disable',old_service)
 for item in s['nginx']:shutil.copy2(item['backup'],item['path'])
 command('nginx','-t');command('systemctl','reload','nginx')
 if s.get('mtp'):
  api.call('inbounds/update/'+str(s['mtp']['id']),s['mtp']);api.call('server/restartXrayService',{})
  if s['mtp_active']:command('systemctl','start','obfuscator-telemt')
  if s['mtp_enabled']:command('systemctl','enable','obfuscator-telemt')
  else:command('systemctl','disable','obfuscator-telemt')
 marker=P('/etc/obfuscator-control/managed')
 if marker.exists():marker.unlink()
 s['phase']='rolled_back';write_state(s);print(node,'previous route/services restored',flush=True)
def apply():
 if P('/etc/obfuscator-control/managed').exists():print(node,'already managed');return
 # Fail before changing routing if clients changed since the adoption snapshot.
 source=P('/etc/obfuscator-vpn/config.json' if node=='az1' else '/opt/xray/config.json')
 old=next(b for b in json.loads(source.read_text())['inbounds'] if b['protocol']=='vless')
 current={c['id'] for c in old['settings']['clients']}
 cloned={c['id'] for c in parsed(inbound('obf-vpn-'+node)['settings'])['clients'] if c.get('enable',True)}
 if current!=cloned:raise RuntimeError('Live clients changed after adoption; refresh the panel snapshot before cutover')
 if node!='de2':
  import tomllib
  old_mtp=set(tomllib.loads(P('/etc/obfuscator-telemt/config.toml').read_text()).get('access',{}).get('users',{}).values())
  new_mtp={c['secret'][2:34] for c in parsed(inbound('obf-mtp-'+node)['settings'])['clients'] if c.get('enable',True)}
  if old_mtp!=new_mtp:raise RuntimeError('Live MTProto clients changed after adoption; refresh before cutover')
 s={'node':node,'phase':'prepared','vpn_active':active(old_service),'vpn_enabled':enabled(old_service),'nginx':[],'mtp':None,'mtp_active':False,'mtp_enabled':False}
 old_port=8443 if node=='de2' else 8445
 for link in P('/etc/nginx/sites-enabled').iterdir():
  p=link.resolve();text=p.read_text();needle='grpc_pass grpc://127.0.0.1:'+str(old_port)+';'
  if domain in text and needle in text:
   dest=backup/(p.name+'.original');shutil.copy2(p,dest);s['nginx'].append({'path':str(p),'backup':str(dest)})
 if not s['nginx']:raise RuntimeError('Expected old ingress not found; nothing changed')
 if node!='de2':s.update({'mtp':inbound('obf-mtp-'+node),'mtp_active':active('obfuscator-telemt'),'mtp_enabled':enabled('obfuscator-telemt')})
 write_state(s)
 try:
  if s['mtp']:
   command('systemctl','stop','obfuscator-telemt');new=copy.deepcopy(s['mtp']);new['port']=8446
   api.call('inbounds/update/'+str(new['id']),new);api.call('server/restartXrayService',{})
   sys.path.insert(0,'/home/deploy/obfuscator-subscriptions');from mtp_probe import authenticate
   key=next(c['mtp'] for c in json.loads(P('/etc/obfuscator-control/bootstrap-clients.json').read_text()) if c['enabled'])
   for attempt in range(20):
    try:
     if not authenticate(key,'127.0.0.1',8446):raise RuntimeError('HMAC mismatch')
     break
    except Exception:
     if attempt==19:raise RuntimeError('Production MTProto HMAC failed') from None
     time.sleep(.25)
  for item in s['nginx']:
   p=P(item['path']);p.write_text(p.read_text().replace('grpc_pass grpc://127.0.0.1:'+str(old_port)+';','grpc_pass grpc://127.0.0.1:8545;'))
  command('nginx','-t');command('systemctl','reload','nginx');time.sleep(.5)
  # These public tests are INSIDE the rollback boundary, before stopping old VPN.
  public_probe();s['phase']='public_verified';write_state(s)
  command('systemctl','stop',old_service);public_probe()
  command('systemctl','disable',old_service)
  if s['mtp']:command('systemctl','disable','obfuscator-telemt')
  P('/etc/obfuscator-control/managed').write_text('3x-ui authoritative; old JSON configs are rollback copies\n')
  command('install','-m755','-o','root','-g','root','/home/deploy/obfuscator-subscriptions/node_agent.py','/usr/local/sbin/obfuscator-node-agent')
  s['phase']='complete';write_state(s);print(node,'panel ownership committed',flush=True)
 except Exception:
  rollback(s);raise RuntimeError('Cutover failed; automatically rolled back including public smoke-test failure') from None
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='rollback':
  if statefile.exists():rollback(json.loads(statefile.read_text()))
  else:print(node,'no cutover state; nothing to roll back')
 elif len(sys.argv)>1 and sys.argv[1]=='apply':apply()
 else:raise SystemExit('Use apply or rollback')
