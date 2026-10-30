#!/usr/bin/python3
"""Subscription delivery, not a public administration API. No request-path logging."""
import argparse,base64,hashlib,hmac,html,http.server,ipaddress,json,pathlib,re,socket,ssl,urllib.parse
DATA=pathlib.Path('/var/lib/obfuscator-subscriptions/data.json')
def response_for(data,host,path):
 uri=urllib.parse.urlsplit(path);parts=uri.path.strip('/').split('/')
 if uri.path=='/healthz':return 200,{'Content-Type':'text/plain'},b'ok\n'
 if uri.path=='/':
  message='Use your personal Telegram link.' if host=='mtp.funsociety.dev' else 'Use your personal subscription link in Happ or another compatible client.'
  return 200,{'Content-Type':'text/html; charset=utf-8'},('<!doctype html><title>Obfuscator</title><h1>Obfuscator</h1><p>'+message+'</p>').encode()
 if len(parts)!=2 or parts[0] not in ('s','mtp'):return 404,{},b'Not found\n'
 token=parts[1]
 if not re.fullmatch(r'[A-Za-z0-9_-]{12,100}',token):return 404,{},b'Not found\n'
 client=data.get('clients',{}).get(hashlib.sha256(token.encode()).hexdigest())
 if not client or not client.get('enabled'):return 404,{},b'Not found\n'
 if parts[0]=='mtp':
  if host!='mtp.funsociety.dev':return 404,{},b'Not found\n'
  if not client.get('mtp'):return 404,{},b'Not found\n'
  secret='ee'+client['mtp']+'mtp.funsociety.dev'.encode().hex()
  link='tg://proxy?'+urllib.parse.urlencode({'server':'mtp.funsociety.dev','port':443,'secret':secret})
  return 302,{'Location':link},b''
 if host!='obfuscator.funsociety.dev':return 404,{},b'Not found\n'
 # DE2 is NEVER included in the default subscription, even for authorized recipients.
 links=[client['links'][n] for n in ('de1','az1') if client['links'].get(n)]
 body=('\n'.join(links)+'\n').encode();fmt=urllib.parse.parse_qs(uri.query).get('format',['base64'])[0]
 if fmt not in ('plain','base64'):return 400,{},b'Unsupported format\n'
 if fmt=='base64':body=base64.b64encode(body)
 return 200,{'Content-Type':'text/plain; charset=utf-8','profile-title':'base64:'+base64.b64encode(b'Obfuscator').decode(),'profile-update-interval':'1','profile-web-page-url':'https://obfuscator.funsociety.dev/'},body
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def data(self):return json.loads(DATA.read_text())
 def send(self,status,headers,body):
  self.send_response(status)
  for k,v in headers.items():self.send_header(k,v)
  self.send_header('Cache-Control','private, no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(body)));self.end_headers()
  if self.command!='HEAD':self.wfile.write(body)
 def do_GET(self):
  try:
   host=self.headers.get('Host','').split(':')[0].lower();self.send(*response_for(self.data(),host,self.path))
  except Exception:self.send(503,{},b'Service unavailable\n')
 do_HEAD=do_GET
 def do_POST(self):
  try:
   d=self.data();provided=self.headers.get('Authorization','').removeprefix('Bearer ')
   if self.path!='/internal/az1-reachability' or not hmac.compare_digest(hashlib.sha256(provided.encode()).hexdigest(),d.get('publisher_hash','')):
    return self.send(404,{},b'Not found\n')
   n=int(self.headers.get('Content-Length','0'));assert 0<n<256
   ip=str(ipaddress.IPv4Address(json.loads(self.rfile.read(n))['ipv4']));assert ipaddress.ip_address(ip).is_global
   reachable=False
   try:
    with socket.create_connection((ip,443),timeout=4) as s:
     with ssl.create_default_context().wrap_socket(s,server_hostname='az1.obfuscator.funsociety.dev') as t:
      t.settimeout(4);t.sendall(b'GET /.well-known/obfuscator-node HTTP/1.1\r\nHost: az1.obfuscator.funsociety.dev\r\nConnection: close\r\n\r\n');buf=b''
      while len(buf)<8192:
       block=t.recv(4096)
       if not block:break
       buf+=block
      reachable=buf.endswith(b'obfuscator-az1\n') and b'200 OK' in buf.split(b'\r\n',1)[0]
   except (OSError,ssl.SSLError):pass
   self.send(200,{'Content-Type':'application/json'},json.dumps({'reachable':reachable}).encode())
  except Exception:self.send(400,{},b'Invalid request\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=9080);a=p.parse_args()
 http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
