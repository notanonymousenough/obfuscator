#!/usr/bin/env python3
"""Verify FakeTLS HMAC authentication (not Telegram messaging/upstream) with a managed secret.
Protocol reference: telemt/telemt 3.5.14 src/protocol/tls.rs.
"""
import argparse,base64,hashlib,hmac,json,pathlib,shlex,socket,ssl,struct,subprocess,time
p=argparse.ArgumentParser();p.add_argument('client',nargs='?',default='owner');p.add_argument('--via',choices=['de1','az1']);p.add_argument('--rejected',action='store_true');a=p.parse_args()
s=json.loads((pathlib.Path(__file__).resolve().parents[2]/'.secrets/clients.json').read_text());key=s['clients'][a.client]['mtp']
source=(pathlib.Path(__file__).resolve().parents[1]/'mtp_probe.py').read_text()
host,port=('127.0.0.1',8446) if a.via else ('mtp.funsociety.dev',443)
probe=source+'\nvalid=authenticate('+repr(key)+','+repr(host)+','+str(port)+')\nassert valid != '+repr(a.rejected)+', "Unexpected FakeTLS authentication result"\nprint("FakeTLS authentication result verified")\n'

if a.via:
 host={'de1':'de1.obfuscator.funsociety.dev','az1':'192.168.0.194'}[a.via]
 inner=shlex.join(['ssh','-o','BatchMode=yes','-p','2222','deploy@'+host,'python3 -c '+shlex.quote(probe)])
 r=subprocess.run(['ssh','-o','BatchMode=yes','user@192.168.0.192',inner]);raise SystemExit(r.returncode)
exec(probe)
