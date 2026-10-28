#!/usr/bin/python3
import json,pathlib,time
from importlib.machinery import SourceFileLoader
base=pathlib.Path('/home/deploy/obfuscator-control')
Panel=SourceFileLoader('control_api',str(base/'api.py')).load_module().Panel
api=Panel(json.loads(pathlib.Path('/etc/obfuscator-control/access.json').read_text()))
nodes=json.loads(pathlib.Path('/etc/obfuscator-control/enrollment.json').read_text())
current=api.call('nodes/list') or []
# Tree API roots contain ordinary node views; preserve any existing unrelated entries.
for node,port in [('az1',9411),('de2',9412)]:
 if any(n.get('name')==node.upper() for n in current):print(node,'already enrolled');continue
 cfg=nodes[node]
 request={'name':node.upper(),'remark':'Obfuscator '+node.upper(),'scheme':'http','address':'127.0.0.1','port':port,'basePath':cfg['basePath'],'apiToken':cfg['apiToken'],'enable':True,'allowPrivateAddress':True,'tlsVerifyMode':'verify','inboundSyncMode':'selected','inboundTags':['obf-vpn-'+node]+(['obf-mtp-'+node] if node=='az1' else [])}
 for _ in range(20):
  try:api.call('nodes/add',request);print(node,'enrolled over private SSH bridge');break
  except RuntimeError:time.sleep(1)
 else:raise RuntimeError('Node '+node+' bridge/API not ready')
