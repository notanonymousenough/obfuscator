#!/usr/bin/env python3
"""Collect only newly generated panel credentials; bootstrap managed identities via root tmux."""
import importlib.util,json,os,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('obf_cli',ROOT/'Subscriptions/cli.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
registry=json.loads((ROOT/'.secrets/clients.json').read_text())
state={'version':1,'mode':'bootstrap','nodes':{}}
for node in ['de1','de2','az1']:
 state['nodes'][node]=cli.agent(node,{'action':'control-export'})
 clients=[dict(c,name=name) for name,c in registry['clients'].items() if node!='de2' or c.get('de2')]
 cli.agent(node,{'action':'control-bootstrap','clients':clients})
p=ROOT/'.secrets/control.json';fd,tmp=tempfile.mkstemp(dir=p.parent)
with os.fdopen(fd,'w') as f:json.dump(state,f,indent=2);f.write('\n')
os.chmod(tmp,0o600);os.replace(tmp,p)
access=state['nodes']['de1'];text='URL: https://obfuscator.funsociety.dev/control/\nUsername: '+access['username']+'\nPassword: '+access['password']+'\n\nAccess is restricted to the Baku management network. SSH-local UI is also available.\n'
p=ROOT/'.secrets/control-access.private.txt';p.write_text(text);p.chmod(0o600)
print('New panel credentials stored privately; managed-client bootstrap delivered to three nodes')
