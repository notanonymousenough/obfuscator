#!/usr/bin/env python3
"""Render a NEW private bundle; does not change DE2 or export its credentials."""
import argparse,json,os,pathlib,re,secrets,uuid
p=argparse.ArgumentParser()
p.add_argument('--domain',default='de2.obfuscator.funsociety.dev')
p.add_argument('--uuid',dest='client_uuid',help='Existing ID supplied explicitly, otherwise generate a new ID')
p.add_argument('--path',dest='xhttp_path',help='Existing path supplied explicitly, otherwise generate a new path')
p.add_argument('--output',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]/'secrets/rendered')
a=p.parse_args()
if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',a.domain):p.error('Invalid DNS name')
client=str(uuid.UUID(a.client_uuid)) if a.client_uuid else str(uuid.uuid4())
path=a.xhttp_path or '/'+secrets.token_urlsafe(24)
if not re.fullmatch(r'/[A-Za-z0-9/_-]+',path):p.error('Invalid XHTTP path')
a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
os.chmod(a.output,0o700)
root=pathlib.Path(__file__).resolve().parents[1]
for source,target in [('server.json.example','config.json'),('client.json.example','client.json'),('nginx.conf.example','nginx.conf'),('docker-compose.yml','docker-compose.yml')]:
 s=(root/'config'/source).read_text()
 for k,v in {'__DOMAIN__':a.domain,'__CLIENT_UUID__':client,'__XHTTP_PATH__':path}.items():s=s.replace(k,v)
 if target.endswith('.json'):json.loads(s)
 f=a.output/target;f.write_text(s);f.chmod(0o600)
print('Private bundle rendered:',a.output)
print('New credentials do not authorize access to existing DE2 until installed there.')
