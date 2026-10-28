#!/usr/bin/env python3
"""Check delivery without printing private URLs, credentials, or response bodies."""
import argparse,base64,json,pathlib,urllib.request,urllib.error
p=argparse.ArgumentParser();p.add_argument('client',nargs='?',default='owner');p.add_argument('--revoked',action='store_true');a=p.parse_args()
c=json.loads((pathlib.Path(__file__).resolve().parents[2]/'.secrets/clients.json').read_text())['clients'][a.client]
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None
op=urllib.request.build_opener(NoRedirect)
def get(url):
 try:return op.open(url,timeout=20)
 except urllib.error.HTTPError as e:return e
v=get('https://obfuscator.funsociety.dev/s/'+c['token']);t=get('https://mtp.funsociety.dev/mtp/'+c['token'])
if a.revoked:assert v.code==404 and t.code==404, (v.code,t.code);print('revoked: VPN and Telegram URLs both 404')
else:
 assert v.code==200;raw=base64.b64decode(v.read()).decode();lines=raw.strip().splitlines()
 assert len(lines)==2 and all(x.startswith('vless://') for x in lines)
 assert '#DE1' in raw and '#AZ1' in raw and '#DE2' not in raw and 'de2.obfuscator' not in raw
 assert t.code==302 and 'server=mtp.funsociety.dev' in t.headers['Location'] and 'secret=ee'+c['mtp'] in t.headers['Location']
 assert v.headers['Cache-Control']=='private, no-store'
 print('delivery: 2 VLESS nodes DE1/AZ1; DE2 hidden; personal MTProto redirect valid')
