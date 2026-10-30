#!/usr/bin/env python3
"""Run a reviewed local root script through the operator's existing tmux pane."""
import argparse,base64,pathlib,shlex,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('node',choices=['de1','de2','az1']);p.add_argument('script');a=p.parse_args()
host={'de1':'de1.obfuscator.funsociety.dev','de2':'de2.obfuscator.funsociety.dev','az1':'192.168.0.194'}[a.node]
script=base64.b64encode(pathlib.Path(a.script).read_bytes()).decode()
remote=r'''
import base64,pathlib,shlex,subprocess,tempfile,time
base=pathlib.Path.home()/'obfuscator-subscriptions';base.mkdir(exist_ok=True)
d=pathlib.Path(tempfile.mkdtemp(prefix='root-',dir=base));(d/'script').write_bytes(base64.b64decode(SCRIPT))
q=shlex.quote
cmd='umask 022; bash '+q(str(d/'script'))+' > '+q(str(d/'log'))+' 2>&1; echo $? > '+q(str(d/'status'))
subprocess.run(['tmux','send-keys','-t','0:0.0','-l',cmd],check=True);subprocess.run(['tmux','send-keys','-t','0:0.0','Enter'],check=True)
for _ in range(1200):
 if (d/'status').exists():break
 time.sleep(.5)
else:raise RuntimeError('Timed out; inspect tmux before retry')
print((d/'log').read_text());raise SystemExit(int((d/'status').read_text()))
'''.replace('SCRIPT',repr(script))
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-p','2222','deploy@'+host,'python3 -c '+shlex.quote(remote)]);sys.exit(r.returncode)
