#!/usr/bin/python3
"""DE1: enroll network-only SSH identities for private panel bridges."""
import json,pathlib,pwd,subprocess,tempfile
P=pathlib.Path
nodes=json.loads(P('/etc/obfuscator-control/enrollment.json').read_text());blocks=[]
for node,port in [('az1',9411),('de2',9412)]:
 user='obfuscator-node-'+node;key=nodes[node]['bridge_public_key']
 try:pw=pwd.getpwnam(user)
 except KeyError:
  subprocess.run(['useradd','--system','--no-create-home','--shell','/usr/sbin/nologin',user],check=True);pw=pwd.getpwnam(user)
 with tempfile.NamedTemporaryFile('w') as f:
  f.write(key+'\n');f.flush();subprocess.run(['ssh-keygen','-lf',f.name],check=True,stdout=subprocess.DEVNULL)
 d=P('/etc/ssh/authorized_keys');d.mkdir(mode=0o755,exist_ok=True)
 p=d/user;p.write_text('restrict,port-forwarding,permitlisten="127.0.0.1:'+str(port)+'" '+key+'\n');p.chmod(0o600)
 import os;os.chown(p,pw.pw_uid,pw.pw_gid)
 blocks.append(f'''Match User {user}
    AuthorizedKeysFile /etc/ssh/authorized_keys/{user}
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    AllowTcpForwarding remote
    GatewayPorts no
    PermitListen 127.0.0.1:{port}
    PermitTTY no
    AllowAgentForwarding no
    X11Forwarding no
    MaxSessions 0
Match all
''')
P('/etc/ssh/sshd_config.d/92-obfuscator-node-bridges.conf').write_text('\n'.join(blocks))
p=P('/etc/ssh/sshd_config');lines=p.read_text().splitlines()
for i,line in enumerate(lines):
 if line.startswith('AllowUsers '):
  names=line.split()[1:]
  for n in nodes:
   user='obfuscator-node-'+n
   if user not in names:names.append(user)
  lines[i]='AllowUsers '+' '.join(names)
p.write_text('\n'.join(lines)+'\n')
subprocess.run(['sshd','-t'],check=True);subprocess.run(['systemctl','reload','ssh'],check=True)
print('Private bridges enrolled; only loopback9411/9412 forwarding, no SSH sessions')
