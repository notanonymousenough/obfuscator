#!/usr/bin/env python3
"""Operator CLI. Private state stays under ignored .secrets/ with mode 0600."""
import argparse,fcntl,base64,hashlib,json,os,pathlib,re,secrets,shlex,subprocess,sys,tempfile,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'.secrets/clients.json'
HOSTS={'de1':'de1.obfuscator.funsociety.dev','de2':'de2.obfuscator.funsociety.dev','az1':'192.168.0.194'}
def save(s):
 STATE.parent.mkdir(mode=0o700,exist_ok=True);os.chmod(STATE.parent,0o700)
 fd,n=tempfile.mkstemp(dir=STATE.parent)
 with os.fdopen(fd,'w') as f:json.dump(s,f,indent=2);f.write('\n')
 os.chmod(n,0o600);os.replace(n,STATE)
def agent(node,payload):
 # Existing root tmux session is required. No persistent sudo grant is installed.
 request=base64.b64encode(json.dumps(payload).encode()).decode()
 remote = r"""
import base64,json,os,pathlib,shlex,subprocess,tempfile,time
base=pathlib.Path.home()/'.obfuscator-requests';base.mkdir(mode=0o700,exist_ok=True)
d=pathlib.Path(tempfile.mkdtemp(dir=base));(d/'input').write_bytes(base64.b64decode(REQUEST))
try:
 panes=subprocess.check_output(['tmux','list-panes','-a','-F','#{session_name}:#{window_index}.#{pane_index} #{pane_current_command}'],text=True)
 targets=[line.split()[0] for line in panes.splitlines() if line.split()[-1] in ('sudo','su','bash','zsh')]
 if len(targets)!=1:raise RuntimeError('Exactly one idle root tmux pane is required')
 q=shlex.quote
 command='/usr/local/sbin/obfuscator-node-agent < '+q(str(d/'input'))+' > '+q(str(d/'output'))+'; chmod 644 '+q(str(d/'output'))+'; touch '+q(str(d/'done'))
 subprocess.run(['tmux','send-keys','-t',targets[0],'-l',command],check=True)
 subprocess.run(['tmux','send-keys','-t',targets[0],'Enter'],check=True)
 for _ in range(360):
  if (d/'done').exists():break
  time.sleep(0.5)
 else:raise RuntimeError('Root tmux command timed out; inspect pane before retry')
 result=json.loads((d/'output').read_text())
 if 'error' in result:raise RuntimeError(result['error'])
 print(json.dumps(result))
finally:
 for f in d.iterdir():f.unlink()
 d.rmdir()
""".replace('REQUEST',repr(request))
 cmd='python3 -c '+shlex.quote(remote)
 inner=shlex.join(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-p','2222','deploy@'+HOSTS[node],cmd])
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','user@192.168.0.192',inner],text=True,capture_output=True,timeout=220)
 if p.returncode:raise RuntimeError(node+': '+p.stderr.strip())
 return json.loads(p.stdout)
def portal(s):
 clients={}
 for name,c in s['clients'].items():
  clients[hashlib.sha256(c['token'].encode()).hexdigest()]={'enabled':c['enabled'] and c.get('provisioned',False),'mtp':c['mtp'],'links':c.get('links',{})}
 return agent('de1',{'action':'portal','data':{'publisher_hash':hashlib.sha256(s['publisher_token'].encode()).hexdigest(),'clients':clients}})
def sync(s):
 # Revoke subscription URLs before touching backend state; publish additions only after success.
 portal(s)
 for n in ('de2','az1','de1'):
  clients=[{'name':name,'uuid':c['uuid'],'mtp':c['mtp']} for name,c in s['clients'].items() if c['enabled'] and (n!='de2' or c.get('de2'))]
  result=agent(n,{'action':'reconcile','clients':clients})
  for name,c in s['clients'].items():
   c.setdefault('links',{}).pop(n,None)
   if name in result['links']:c['links'][n]=result['links'][name]
  save(s);print(n+': managed='+str(result['managed_count'])+', legacy preserved='+json.dumps(result['legacy_preserved']))
 
 for c in s['clients'].values():c['provisioned']=True
 portal(s);s['pending']=False;save(s)
def links(name,c):
 print(name+(' [enabled]' if c['enabled'] else ' [disabled]'))
 print('Subscription: https://obfuscator.funsociety.dev/s/'+c['token'])
 print('Telegram: https://mtp.funsociety.dev/mtp/'+c['token'])
 if c.get('de2') and c.get('links',{}).get('de2'):print('DE2 private: '+c['links']['de2'])
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['add','list','links','disable','enable','grant-de2','revoke-de2','rotate-vpn','rotate-mtp','rotate-link','sync','baseline','configure-ddns']);p.add_argument('name',nargs='?');p.add_argument('--de2',action='store_true');a=p.parse_args()
 s=json.loads(STATE.read_text()) if STATE.exists() else {'version':1,'publisher_token':secrets.token_urlsafe(32),'clients':{},'pending':False}
 if not STATE.exists():save(s)
 if a.action=='baseline':
  for n in HOSTS:print(json.dumps(agent(n,{'action':'baseline'})))
  return
 if a.action=='configure-ddns':
  agent('az1',{'action':'configure-ddns','publisher_token':s['publisher_token']});print('AZ1 DDNS publisher configured');return
 if a.action=='list':
  for name,c in s['clients'].items():print(name,'enabled='+str(c['enabled']),'de2='+str(c.get('de2',False)))
  print('pending_sync='+str(s.get('pending',False)));return
 if a.action=='sync':sync(s);return
 if not a.name or not re.fullmatch(r'[a-z][a-z0-9_-]{0,47}',a.name):p.error('Use a lowercase client name')
 if a.action=='add':
  if a.name in s['clients']:p.error('Client exists; use enable or rotate')
  s['clients'][a.name]={'uuid':str(uuid.uuid4()),'mtp':secrets.token_hex(16),'token':secrets.token_urlsafe(32),'enabled':True,'de2':a.de2,'links':{}}
 elif a.name not in s['clients']:p.error('Unknown client')
 c=s['clients'][a.name]
 if a.action=='links':links(a.name,c);return
 if a.action in ('disable','enable'):c['enabled']=a.action=='enable'
 elif a.action in ('grant-de2','revoke-de2'):c['de2']=a.action=='grant-de2'
 elif a.action=='rotate-vpn':c['uuid']=str(uuid.uuid4())
 elif a.action=='rotate-mtp':c['mtp']=secrets.token_hex(16)
 elif a.action=='rotate-link':c['token']=secrets.token_urlsafe(32)
 c['provisioned']=False
 s['pending']=True;save(s);sync(s);links(a.name,c)
if __name__=='__main__':
 try:
  STATE.parent.mkdir(mode=0o700,exist_ok=True)
  with (STATE.parent/'operation.lock').open('w') as lock:
   os.chmod(lock.name,0o600);fcntl.flock(lock,fcntl.LOCK_EX);main()
 except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
