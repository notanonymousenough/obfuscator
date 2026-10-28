#!/usr/bin/env python3
"""Inventory-based platform coordinator. Root operations use existing root tmux only."""
import argparse,io,json,pathlib,shlex,subprocess,sys,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
INVENTORY=json.loads((ROOT/'Control/inventory.json').read_text())
ORDER=['de2','az1','de1']
def remote(node,command,data=None):
 inner=shlex.join(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-p','2222','deploy@'+INVENTORY['nodes'][node]['ssh'],command])
 subprocess.run(['ssh','-o','BatchMode=yes','user@192.168.0.192',inner],input=data,check=True)
def root(node,script):
 subprocess.run([sys.executable,str(ROOT/'Subscriptions/scripts/root-tmux.py'),node,str(ROOT/'Control/scripts'/script)],check=True)
def stage():
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w:gz') as tar:
  for folder,target in [('Control','obfuscator-control'),('Subscriptions','obfuscator-subscriptions')]:
   for p in sorted((ROOT/folder).rglob('*')):
    rel=p.relative_to(ROOT/folder)
    if not p.is_file() or any(x in ('assets','__pycache__','secrets') or x.startswith('.') for x in rel.parts) or '.private.' in p.name or p.suffix=='.pyc':continue
    tar.add(p,arcname=str(pathlib.Path(target)/rel),recursive=False)
 for node in ORDER:
  remote(node,'umask 077; tar -xzf - -C /home/deploy',buf.getvalue());print(node,'source staged',flush=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','status','stage','cutover','rollback']);a=p.parse_args()
 if a.action=='plan':
  print('Panel 3x-ui '+INVENTORY['panel_version']+' on DE1; nodes AZ1/DE2 through scoped SSH bridges.')
  print('AZ1 ingress=DE1 relay. Public subscriptions=DE1/AZ1. DE2=private grants only.')
  print('stage uploads tracked source, excluding credentials and binaries. cutover switches DE2, AZ1, DE1 with public authenticated tests and rollback.')
  print('Production cutover requires operator approval; it has not been performed by plan/stage.');return
 if a.action=='status':subprocess.run([sys.executable,str(ROOT/'Control/ctl.py'),'status'],check=True);return
 if a.action=='stage':stage();return
 if a.action=='rollback':
  root('de1','stop-delivery.sh')
  for node in reversed(ORDER):root(node,'rollback-backends.sh')
  print('Restored migration-time services. Reconcile any later UI client changes before using old client management.');return
 attempted=[]
 try:
  for node in ORDER:
   attempted.append(node);root(node,'cutover-backends.sh')
  root('de1','activate-delivery.sh')
 except Exception:
  root('de1','stop-delivery.sh')
  for node in reversed(attempted):
   try:root(node,'rollback-backends.sh')
   except Exception:print(node,'ROLLBACK NEEDS MANUAL INSPECTION',file=sys.stderr)
  raise RuntimeError('Global adoption failed; rollback attempted on every touched node') from None
 statefile=ROOT/'.secrets/control.json';state=json.loads(statefile.read_text());state['mode']='active';statefile.write_text(json.dumps(state,indent=2)+'\n');statefile.chmod(0o600)
 print('Panel is authoritative. Use Control/ctl.py and UI for client operations.')
if __name__=='__main__':
 try:main()
 except Exception as e:print('ERROR:',str(e),file=sys.stderr);sys.exit(1)
