#!/usr/bin/python3
"""Host-local adoption. Existing private configurations never leave their node."""
import json,os,pathlib,secrets,socket,subprocess,sys,tempfile,time,copy
from api import Panel
P=pathlib.Path
node={'obfuscator-de1':'de1','obfuscator-de2':'de2','obfuscator-az1':'az1'}[os.uname().nodename.split('.')[0]]
access=json.loads(P('/etc/obfuscator-control/access.json').read_text());api=Panel(access)
managed=json.loads(P('/etc/obfuscator-control/bootstrap-clients.json').read_text());byid={c['uuid']:c for c in managed}
source=P('/etc/obfuscator-vpn/config.json' if node=='az1' else '/opt/xray/config.json')
def parsed(value):return json.loads(value) if isinstance(value,str) else value
def existing(tag):return next((b for b in api.inbounds() if b['tag']==tag),None)
def add_vpn():
 tag='obf-vpn-'+node
 if existing(tag):print(node,'VPN already adopted');return
 original=next(b for b in json.loads(source.read_text())['inbounds'] if b['protocol']=='vless')
 clients=[]
 for n,c in enumerate(original['settings']['clients'],1):
  c=copy.deepcopy(c);m=byid.get(c['id'])
  c.update({'email':'obf-'+m['name'] if m else 'legacy-vless-'+node+'-'+str(n),'enable':True,'expiryTime':0,'totalGB':0,'subId':m['token'] if m else secrets.token_urlsafe(32)})
  if m:c['secret']='ee'+m['mtp']+'mtp.funsociety.dev'.encode().hex()
  clients.append(c)
 settings=copy.deepcopy(original['settings']);settings['clients']=clients
 inbound={'tag':tag,'remark':node.upper()+' · VLESS/XHTTP'+(' · private' if node=='de2' else ''),'listen':'127.0.0.1','port':8545,'protocol':'vless','settings':json.dumps(settings),'streamSettings':json.dumps(original['streamSettings']),'sniffing':json.dumps({'enabled':False}),'enable':True,'excludeFromSub':node=='de2','shareAddrStrategy':'custom','shareAddr':{'de1':'de1.obfuscator.funsociety.dev','de2':'de2.obfuscator.funsociety.dev','az1':'vpn-az1.obfuscator.funsociety.dev'}[node]}
 api.call('inbounds/add',inbound);api.call('server/restartXrayService',{})
 print(node,'VPN cloned into panel; legacy listener preserved')
def add_mtp():
 if node=='de2':return
 tag='obf-mtp-'+node
 if existing(tag):print(node,'MTProto already adopted');return
 clients=[]
 for c in managed:
  if c['enabled']:clients.append({'id':c['uuid'],'email':'obf-'+c['name'],'subId':c['token'],'secret':'ee'+c['mtp']+'mtp.funsociety.dev'.encode().hex(),'enable':True,'totalGB':0,'expiryTime':0})
 settings={'clients':clients,'preferIp':'prefer-ipv4','domainFronting':{'ip':'127.0.0.1','port':8444 if node=='de1' else 8447,'proxyProtocol':False}}
 api.call('inbounds/add',{'tag':tag,'remark':node.upper()+' · MTProto shared endpoint','listen':'127.0.0.1','port':8546,'protocol':'mtproto','settings':json.dumps(settings),'streamSettings':'{}','sniffing':'{}','enable':True,'excludeFromSub':True,'shareAddrStrategy':'custom','shareAddr':'mtp.funsociety.dev'})
 api.call('server/restartXrayService',{});print(node,'MTProto clone prepared')
def probe_vpn():
 inbound=existing('obf-vpn-'+node);settings=parsed(inbound['settings']);client=settings['clients'][0]
 port=0
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 cfg={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':port,'protocol':'socks','settings':{'auth':'noauth'}}],'outbounds':[{'protocol':'vless','settings':{'vnext':[{'address':'127.0.0.1','port':8545,'users':[{'id':client['id'],'encryption':'none'}]}]},'streamSettings':parsed(inbound['streamSettings'])}]}
 binary=next(P('/usr/local/x-ui/bin').glob('xray-linux-*'))
 with tempfile.TemporaryDirectory(prefix='obf-panel-probe-') as d:
  f=P(d)/'client.json';f.write_text(json.dumps(cfg));f.chmod(0o600)
  p=subprocess.Popen([str(binary),'run','-c',str(f)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   time.sleep(1)
   r=subprocess.run(['curl','-fsS','--max-time','10','--proxy','socks5h://127.0.0.1:'+str(port),'-o','/dev/null','-w','%{http_code}','https://www.gstatic.com/generate_204'],capture_output=True,text=True)
   assert r.returncode==0 and r.stdout=='204','Panel VPN clone failed authenticated HTTPS test'
  finally:p.terminate();p.wait(timeout=5)
 print(node,'panel VPN clone: authenticated HTTPS204 OK')
 if node!='de2':
  sys.path.insert(0,'/home/deploy/obfuscator-subscriptions')
  from mtp_probe import authenticate
  key=next(c['mtp'] for c in managed if c['enabled'])
  assert authenticate(key,'127.0.0.1',8546),'Panel MTProto clone HMAC failed'
  print(node,'panel MTProto clone: HMAC verified')
if __name__=='__main__':
 if sys.argv[1]=='adopt':add_vpn();add_mtp();probe_vpn()
 elif sys.argv[1]=='probe':probe_vpn()
 else:raise SystemExit('Unknown task')
