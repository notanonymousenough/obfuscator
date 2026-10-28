"""Managed MTProto FakeTLS HMAC probe; no Telegram account/session required.
Reference: telemt/telemt 3.5.14 src/protocol/tls.rs. This checks authentication,
not MTProto message delivery or Telegram DC reachability.
"""
import hashlib,hmac,socket,ssl,struct,time
def authenticate(key_hex,host,port=443):
 key=bytes.fromhex(key_hex)
 ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
 ctx.minimum_version=ssl.TLSVersion.TLSv1_3;ctx.set_alpn_protocols(['h2','http/1.1'])
 incoming=ssl.MemoryBIO();outgoing=ssl.MemoryBIO();tls=ctx.wrap_bio(incoming,outgoing,server_side=False,server_hostname='mtp.funsociety.dev')
 try:tls.do_handshake()
 except ssl.SSLWantReadError:pass
 hello=bytearray(outgoing.read());hello[11:43]=bytes(32)
 digest=bytearray(hmac.new(key,hello,hashlib.sha256).digest());stamp=struct.pack('<I',int(time.time()))
 for i in range(4):digest[28+i]^=stamp[i]
 hello[11:43]=digest
 with socket.create_connection((host,port),timeout=10) as sock:
  sock.sendall(hello);buf=bytearray(sock.recv(65536));sock.settimeout(1.5)
  while len(buf)<65536:
   try:
    block=sock.recv(65536)
    if not block:break
    buf.extend(block)
   except socket.timeout:break
 assert len(buf)>43,'Missing server handshake'
 actual=bytes(buf[11:43]);buf[11:43]=bytes(32)
 # TLS front profiles can append optional records. Check complete record prefixes only.
 valid=False;end=0
 while end+5<=len(buf):
  end+=5+int.from_bytes(buf[end+3:end+5],'big')
  if end>len(buf):break
  expected=hmac.new(key,bytes(digest)+buf[:end],hashlib.sha256).digest()
  if hmac.compare_digest(actual,expected):valid=True;break
 return valid
