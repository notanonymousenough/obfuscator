#!/usr/bin/python3
"""Normalize a local Cloudflare INI without printing credentials."""
import os,pathlib,sys
source=pathlib.Path(sys.argv[1]);values={}
for line in source.read_text().splitlines():
 if '=' in line and not line.lstrip().startswith(('#',';')):
  k,v=line.split('=',1);values[k.strip()]=v.strip().strip('"\'')
token=values.get('dns_cloudflare_api_token') or values.get('cloudflare_api_token')
if not token or any(c.isspace() for c in token):raise SystemExit('Missing or malformed API token')
os.chmod(source,0o600)
d=pathlib.Path('/etc/obfuscator');d.mkdir(mode=0o750,exist_ok=True)
for name,content in [('cloudflare.token',token+'\n'),('cloudflare.ini','dns_cloudflare_api_token = '+token+'\n')]:
 p=d/name
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'w') as f:f.write(content)
 os.chmod(p,0o600);os.chown(p,0,0)
print('Cloudflare credentials normalized; all credential files mode 0600')
