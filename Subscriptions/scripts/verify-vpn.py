#!/usr/bin/env python3
"""Authenticated end-to-end VPN smoke tests from AZ1, without exporting legacy secrets."""
import argparse,base64,json,pathlib,shlex,subprocess,urllib.parse
p=argparse.ArgumentParser();p.add_argument('client',nargs='?',default='owner');p.add_argument('--rejected',action='store_true');a=p.parse_args()
s=json.loads((pathlib.Path(__file__).resolve().parents[2]/'.secrets/clients.json').read_text());links=s['clients']['owner']['links']
configs={}
for node,link in links.items():
 if a.rejected and node=='de2' and not s['clients'][a.client].get('de2'):continue
 u=urllib.parse.urlsplit(link);q=urllib.parse.parse_qs(u.query)
 configs[node]={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':0,'protocol':'socks','settings':{'auth':'noauth','udp':True}}],'outbounds':[{'protocol':'vless','settings':{'vnext':[{'address':u.hostname,'port':u.port,'users':[{'id':s['clients'][a.client]['uuid'],'encryption':'none'}]}]},'streamSettings':{'network':'xhttp','security':'tls','tlsSettings':{'serverName':q['sni'][0],'fingerprint':'chrome','alpn':['h2']},'xhttpSettings':{'path':q['path'][0],'mode':'stream-up'}}}]}
remote=r'''
import argparse,base64,json,pathlib,socket,subprocess,tempfile,time
configs=json.loads(base64.b64decode(PAYLOAD));failed=False
for name,cfg in configs.items():
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 cfg['inbounds'][0]['port']=port
 with tempfile.TemporaryDirectory(prefix='obf-probe-') as d:
  path=pathlib.Path(d)/'config.json';path.write_text(json.dumps(cfg));path.chmod(0o600)
  p=subprocess.Popen(['/usr/local/bin/xray','run','-c',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   time.sleep(1)
   r=subprocess.run(['curl','-fsS','--max-time','10' if REJECTED else '25','--proxy','socks5h://127.0.0.1:'+str(port),'https://api.ipify.org'],capture_output=True,text=True)
   if REJECTED:
    if r.returncode:print(name+': revoked VLESS key rejected')
    else:print(name+': FAIL revoked VLESS key accepted');failed=True
   elif r.returncode:print(name+': FAIL curl='+str(r.returncode));failed=True
   else:print(name+': HTTPS through VLESS/XHTTP OK; egress='+r.stdout.strip())
  finally:p.terminate();p.wait(timeout=5)
raise SystemExit(1 if failed else 0)
'''.replace('REJECTED',repr(a.rejected)).replace('PAYLOAD',repr(base64.b64encode(json.dumps(configs).encode()).decode()))
cmd='python3 -c '+shlex.quote(remote)
inner=shlex.join(['ssh','-o','BatchMode=yes','-p','2222','deploy@192.168.0.194',cmd])
p=subprocess.run(['ssh','-o','BatchMode=yes','user@192.168.0.192',inner]);raise SystemExit(p.returncode)
