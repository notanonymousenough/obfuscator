#!/usr/bin/env python3
"""Unified panel client registry. Run open-ui.sh first; secrets print only with links."""
import argparse,json,pathlib,re,secrets,sys,uuid,urllib.parse
from api import Panel
from delivery import make_link
ROOT=pathlib.Path(__file__).resolve().parents[1]
def secret():return 'ee'+secrets.token_hex(16)+'mtp.funsociety.dev'.encode().hex()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('action',choices=['status','list','links','add','enable','disable','grant-de2','revoke-de2','rotate-vpn','rotate-mtp','rotate-link'])
 p.add_argument('name',nargs='?');p.add_argument('--de2',action='store_true');a=p.parse_args()
 state=json.loads((ROOT/'.secrets/control.json').read_text());access=dict(state['nodes']['de1'],url='http://127.0.0.1:1337/control/')
 api=Panel(access);inbounds=api.inbounds();ids={b['tag']:b['id'] for b in inbounds}
 if a.action=='status':
  print('Authority:',state['mode'])
  for n in api.call('nodes/list') or []:print(n['name'],'enabled='+str(n.get('enable')), 'online='+str(n.get('online',n.get('status','unknown'))))
  print('Inbounds:',len(inbounds));return
 clients=api.call('clients/list') or []
 if a.action=='list':
  for c in clients:
   traffic=c.get('traffic') or {};print(c['email'],'enabled='+str(c['enable']),'bindings='+','.join(map(str,c.get('inboundIds',[]))),'used_bytes='+str(traffic.get('up',0)+traffic.get('down',0)))
  return
 if not a.name or not re.fullmatch('[a-z][a-z0-9_-]{0,47}',a.name):p.error('Use a lowercase managed client name')
 email='obf-'+a.name;client=next((c for c in clients if c['email']==email),None)
 if a.action=='links':
  if not client:p.error('Client does not exist')
  token=client['subId'];print('Subscription: https://obfuscator.funsociety.dev/s/'+token);print('MTProto: https://mtp.funsociety.dev/mtp/'+token)
  if ids['obf-vpn-de2'] in client.get('inboundIds',[]):
   stream=next(b['streamSettings'] for b in inbounds if b['tag']=='obf-vpn-de2');stream=json.loads(stream) if isinstance(stream,str) else stream
   print('DE2 private:',make_link('de2',client['uuid'],stream))
  return
 if state['mode']!='active':p.error('Panel is in bootstrap mode; production cutover is pending. Use the existing Subscriptions CLI for production clients.')
 if a.action=='add':
  if client:p.error('Client already exists')
  tags=['obf-vpn-de1','obf-vpn-az1','obf-mtp-de1','obf-mtp-az1']+(['obf-vpn-de2'] if a.de2 else [])
  api.call('clients/add',{'client':{'email':email,'id':str(uuid.uuid4()),'secret':secret(),'subId':secrets.token_urlsafe(32),'enable':True,'expiryTime':0,'totalGB':0},'inboundIds':[ids[t] for t in tags]})
 else:
  if not client:p.error('Client does not exist')
  path='clients/'+email
  if a.action in ('grant-de2','revoke-de2'):
   api.call(path+('/attach' if a.action=='grant-de2' else '/detach'),{'inboundIds':[ids['obf-vpn-de2']]})
  else:
   update=dict(client);update['id']=update.pop('uuid');update.pop('traffic',None);update.pop('inboundIds',None)
   if a.action in ('enable','disable'):update['enable']=a.action=='enable'
   elif a.action=='rotate-vpn':update['id']=str(uuid.uuid4())
   elif a.action=='rotate-mtp':update['secret']=secret()
   elif a.action=='rotate-link':update['subId']=secrets.token_urlsafe(32)
   api.call('clients/update/'+urllib.parse.quote(email,safe=''),update)
 print('Panel updated. Check node synchronization in UI; use links to display private connection links.')
if __name__=='__main__':
 try:main()
 except Exception as e:print('ERROR:',str(e),file=sys.stderr);sys.exit(1)
