#!/usr/bin/env python3
"""Fresh-session authenticated VPN tests. Never print client keys or private URLs."""
import argparse,base64,json,pathlib,shlex,subprocess,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[2]
def config_for(link,user):
 u=urllib.parse.urlsplit(link);q=urllib.parse.parse_qs(u.query)
 return {'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':0,'protocol':'socks','settings':{'auth':'noauth','udp':True}}],'outbounds':[{'protocol':'vless','settings':{'vnext':[{'address':u.hostname,'port':u.port,'users':[{'id':user,'encryption':'none'}]}]},'streamSettings':{'network':'xhttp','security':'tls','tlsSettings':{'serverName':q['sni'][0],'fingerprint':q.get('fp',['chrome'])[0],'alpn':['h2']},'xhttpSettings':{'path':q['path'][0],'mode':'stream-up'}}}]}
def main():
 p=argparse.ArgumentParser();p.add_argument('client',nargs='?',default='owner');p.add_argument('--rejected',action='store_true');p.add_argument('--nodes',nargs='+',choices=['de1','de2','az1'],default=['de1','de2','az1']);p.add_argument('--from-node',choices=['az1','de2'],default='az1');p.add_argument('--attempts',type=int,default=1);p.add_argument('--timeout',type=int,default=7);a=p.parse_args()
 if not 1<=a.attempts<=100 or not 1<=a.timeout<=30:p.error('attempts 1..100; timeout 1..30')
 s=json.loads((ROOT/'.secrets/clients.json').read_text());owner=s['clients']['owner'];client=s['clients'][a.client]
 configs={n:config_for(owner['links'][n],client['uuid']) for n in a.nodes if not (a.rejected and n=='de2' and not client.get('de2'))}
 payload={'configs':configs,'attempts':a.attempts,'timeout':a.timeout,'rejected':a.rejected}
 # Every attempt starts a fresh Xray process, rather than reusing a warm TLS/H2 pool.
 remote=r'''
import base64,json,pathlib,socket,subprocess,tempfile,time
p=json.loads(base64.b64decode(PAYLOAD));failures=0;total=0
for node,cfg in p['configs'].items():
 for attempt in range(p['attempts']):
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  cfg['inbounds'][0]['port']=port
  with tempfile.TemporaryDirectory(prefix='obf-vpn-check-') as d:
   path=pathlib.Path(d)/'config.json';path.write_text(json.dumps(cfg));path.chmod(0o600)
   proc=subprocess.Popen(['/usr/local/bin/xray','run','-c',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   try:
    for _ in range(100):
     try:
      with socket.create_connection(('127.0.0.1',port),timeout=.1):break
     except OSError:
      if proc.poll() is not None:raise RuntimeError('Xray exited before readiness')
      time.sleep(.05)
    for url in ['https://cp.cloudflare.com/generate_204','https://www.gstatic.com/generate_204']:
     total+=1
     r=subprocess.run(['curl','-fsS','--max-time',str(p['timeout']),'--proxy','socks5h://127.0.0.1:'+str(port),'-o','/dev/null','-w','%{http_code} %{time_total}',url],capture_output=True,text=True)
     ok=r.returncode!=0 if p['rejected'] else r.returncode==0 and r.stdout.startswith('204 ')
     failures+=not ok
     print(node+' session='+str(attempt+1)+' target='+url.split('/')[2]+' '+('OK' if ok else 'FAIL')+' curl='+str(r.returncode)+' '+r.stdout,flush=True)
   finally:proc.terminate();proc.wait(timeout=5)
print('SUMMARY checks='+str(total)+' failures='+str(failures),flush=True)
raise SystemExit(1 if failures else 0)
'''.replace('PAYLOAD',repr(base64.b64encode(json.dumps(payload).encode()).decode()))
 host={'az1':'192.168.0.194','de2':'de2.obfuscator.funsociety.dev'}[a.from_node]
 inner=shlex.join(['ssh','-o','BatchMode=yes','-p','2222','deploy@'+host,'python3 -c '+shlex.quote(remote)])
 return subprocess.run(['ssh','-o','BatchMode=yes','user@192.168.0.192',inner]).returncode
if __name__=='__main__':raise SystemExit(main())
