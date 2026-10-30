#!/usr/bin/python3
"""Publish direct AZ1 only after an external TLS identity probe; retain DE1 fallback."""
import json,pathlib,urllib.request
from cloudflare_dns import public_ipv4,sync
NAMES=('az1.obfuscator.funsociety.dev',)
CONFIG=pathlib.Path('/etc/obfuscator/az1-ddns.json')
def main():
 cfg=json.loads(CONFIG.read_text());mode=cfg.get('ingress_mode','auto');reachable=False;ip=None
 if mode=='relay':selected=cfg['relay_ipv4']
 elif mode=='auto':
  ip=public_ipv4()
  try:
   key=pathlib.Path(cfg['publisher_token_file']).read_text().strip()
   req=urllib.request.Request('https://obfuscator.funsociety.dev/internal/az1-reachability',data=json.dumps({'ipv4':ip}).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=15) as r:reachable=json.load(r)['reachable'] is True
  except Exception:raise RuntimeError('External probe unavailable; DNS left unchanged') from None
  selected=ip if reachable else cfg['relay_ipv4']
 else:raise ValueError('ingress_mode must be relay or auto')
 for name in NAMES:
  sync({'zone':'funsociety.dev','name':name,'token_file':'/etc/obfuscator/cloudflare.token','ipv4':selected,'ingress_confirmed':True},True)
 print('AZ1 ingress='+('direct' if reachable else 'relay')+'; mode='+mode+'; observed IPv4='+str(ip))
if __name__=='__main__':main()
