#!/usr/bin/python3
"""Set public host metadata for loopback-only cloned inbounds; no routing change."""
import json,pathlib
from importlib.machinery import SourceFileLoader
base=pathlib.Path('/home/deploy/obfuscator-control')
Panel=SourceFileLoader('control_api',str(base/'api.py')).load_module().Panel
api=Panel(json.loads(pathlib.Path('/etc/obfuscator-control/access.json').read_text()))
hosts=api.call('hosts/raw') or []
for b in api.inbounds():
 tag=b['tag']
 if not tag.startswith(('obf-vpn-','obf-mtp-')):continue
 node=tag.rsplit('-',1)[-1];mtp=tag.startswith('obf-mtp-')
 domain='mtp.funsociety.dev' if mtp else {'de1':'de1.obfuscator.funsociety.dev','de2':'de2.obfuscator.funsociety.dev','az1':'vpn-az1.obfuscator.funsociety.dev'}[node]
 settings=b['streamSettings'];settings=json.loads(settings) if isinstance(settings,str) else settings
 group={'inboundIds':[b['id']],'hosts':[domain],'remark':'Obfuscator '+tag,'port':443,'security':'same' if mtp else 'tls','sni':domain,'alpn':[] if mtp else ['h2'],'fingerprint':'' if mtp else 'chrome','path':'' if mtp else settings['xhttpSettings']['path']}
 old=next((h for h in hosts if h.get('remark')==group['remark']),None)
 if old:group['groupId']=old['groupId'];api.call('hosts/update/'+old['groupId'],group)
 else:api.call('hosts/add',group)
 print(tag,'public host/port metadata configured')
