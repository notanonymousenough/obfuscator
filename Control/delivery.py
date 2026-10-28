#!/usr/bin/python3
"""Read the normalized 3x-ui registry and publish filtered subscription delivery atomically."""
import argparse,hashlib,json,os,pathlib,re,sqlite3,tempfile,time,urllib.parse
DB=pathlib.Path('/etc/x-ui/x-ui.db');DATA=pathlib.Path('/var/lib/obfuscator-subscriptions/data.json')
DOMAINS={'de1':'de1.obfuscator.funsociety.dev','de2':'de2.obfuscator.funsociety.dev','az1':'vpn-az1.obfuscator.funsociety.dev'}
def make_link(node,user,stream):
 q=urllib.parse.urlencode({'encryption':'none','security':'tls','sni':DOMAINS[node],'alpn':'h2','fp':'chrome','type':'xhttp','path':stream['xhttpSettings']['path'],'mode':'stream-up'})
 return 'vless://'+user+'@'+DOMAINS[node]+':443?'+q+'#'+node.upper()
def collect(con,now_ms=None):
 now_ms=now_ms or int(time.time()*1000);con.row_factory=sqlite3.Row;out={};mtp_nodes={}
 # clients + client_inbounds are authoritative. settings.clients can contain old UUIDs.
 rows=con.execute('''SELECT c.id AS cid,c.email,c.sub_id,c.uuid,c.secret,c.enable AS client_enable,c.expiry_time,
 i.tag,i.protocol,i.stream_settings,i.enable AS inbound_enable
 FROM clients c JOIN client_inbounds ci ON ci.client_id=c.id JOIN inbounds i ON i.id=ci.inbound_id
 WHERE i.tag LIKE 'obf-vpn-%' OR i.tag LIKE 'obf-mtp-%' ''')
 for r in rows:
  token=r['sub_id']
  if not token or not re.fullmatch(r'[A-Za-z0-9_-]{12,100}',token):continue
  key=hashlib.sha256(token.encode()).hexdigest()
  client=out.setdefault(key,{'enabled':bool(r['client_enable']) and (r['expiry_time']<=0 or r['expiry_time']>now_ms),'mtp':None,'links':{}})
  if not client['enabled'] or not r['inbound_enable']:continue
  node=r['tag'].rsplit('-',1)[-1]
  if node not in DOMAINS:continue
  if r['protocol']=='vless' and r['tag']=='obf-vpn-'+node and r['uuid']:
   client['links'][node]=make_link(node,r['uuid'],json.loads(r['stream_settings']))
  elif r['protocol']=='mtproto' and r['tag']=='obf-mtp-'+node:
   secret=r['secret'] or ''
   if re.fullmatch('ee[0-9a-f]{32}'+re.escape('mtp.funsociety.dev'.encode().hex()),secret):
    client['mtp']=secret[2:34];mtp_nodes.setdefault(key,set()).add(node)
 # A leastconn pool needs the same identity on both backends. Fail closed on partial bindings.
 for key,client in out.items():
  if mtp_nodes.get(key)!= {'de1','az1'}:client['mtp']=None
 return out
def publish():
 with sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True,timeout=5) as con:
  con.execute('BEGIN');clients=collect(con)
 old=json.loads(DATA.read_text());new=dict(old,clients=clients)
 if old==new:return
 original=DATA.stat();fd,name=tempfile.mkstemp(dir=DATA.parent,prefix='.panel-delivery-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(new,f);f.write('\n');f.flush();os.fsync(f.fileno())
  os.chmod(name,0o640);os.chown(name,original.st_uid,original.st_gid);os.replace(name,DATA)
 finally:
  if os.path.exists(name):os.unlink(name)
 print('Subscription registry synchronized from panel; clients='+str(len(clients)),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');a=p.parse_args()
 while True:
  try:publish()
  except Exception as e:
   # Keep last known good delivery and avoid logging client data on error.
   print('Delivery sync failed: '+type(e).__name__,flush=True)
   if a.once:raise
  if a.once:return
  time.sleep(2)
if __name__=='__main__':main()
