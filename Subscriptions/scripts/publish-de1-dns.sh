#!/bin/bash
set -euo pipefail
cd /home/deploy/obfuscator-subscriptions
python3 - <<'PY'
import pathlib,sys,tempfile,os
sys.path.insert(0,'scripts')
from cloudflare_dns import sync
values={}
for line in pathlib.Path('/etc/letsencrypt/cloudflare.ini').read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1);values[k.strip()]=v.strip()
fd,name=tempfile.mkstemp()
try:
 with os.fdopen(fd,'w') as f:f.write(values['dns_cloudflare_api_token'])
 for domain in ['obfuscator.funsociety.dev','mtp.funsociety.dev','vpn-az1.obfuscator.funsociety.dev']:
  sync({'zone':'funsociety.dev','name':domain,'token_file':name,'ipv4':'159.89.12.205','ingress_confirmed':True},True)
finally:os.unlink(name)
PY
