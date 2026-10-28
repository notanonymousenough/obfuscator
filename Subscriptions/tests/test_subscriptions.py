import base64,hashlib,importlib.util,json,pathlib,tempfile,unittest,uuid
from unittest.mock import patch
BASE=pathlib.Path(__file__).resolve().parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,BASE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
web=module('subscription_web','server.py');agent=module('subscription_agent','node_agent.py')
class Delivery(unittest.TestCase):
 def setUp(self):
  self.token='a'*43;self.data={'clients':{hashlib.sha256(self.token.encode()).hexdigest():{'enabled':True,'mtp':'1'*32,'links':{'de1':'vless://de1','az1':'vless://az1','de2':'vless://HIDDEN'}}}}
 def test_default_subscription_hides_de2(self):
  code,headers,body=web.response_for(self.data,'obfuscator.funsociety.dev','/s/'+self.token)
  self.assertEqual(code,200);plain=base64.b64decode(body);self.assertIn(b'de1',plain);self.assertIn(b'az1',plain);self.assertNotIn(b'HIDDEN',plain)
 def test_plain_and_query_cannot_reveal_de2(self):
  code,_,body=web.response_for(self.data,'obfuscator.funsociety.dev','/s/'+self.token+'?format=plain&include=de2')
  self.assertEqual(code,200);self.assertNotIn(b'HIDDEN',body)
 def test_revoked_and_unknown_return_identical_404(self):
  self.data['clients'][hashlib.sha256(self.token.encode()).hexdigest()]['enabled']=False
  a=web.response_for(self.data,'obfuscator.funsociety.dev','/s/'+self.token)
  b=web.response_for(self.data,'obfuscator.funsociety.dev','/s/'+'b'*43)
  self.assertEqual(a,b);self.assertEqual(a[0],404)
 def test_mtp_stable_domain_with_per_client_secret(self):
  code,h,_=web.response_for(self.data,'mtp.funsociety.dev','/mtp/'+self.token)
  self.assertEqual(code,302);self.assertIn('server=mtp.funsociety.dev',h['Location']);self.assertIn('secret=ee'+'1'*32,h['Location'])
 def test_mtp_host_cannot_deliver_vpn(self):
  self.assertEqual(web.response_for(self.data,'mtp.funsociety.dev','/s/'+self.token)[0],404)
 def test_root_has_no_client_secrets(self):
  code,_,body=web.response_for(self.data,'obfuscator.funsociety.dev','/')
  self.assertEqual(code,200);self.assertNotIn(self.token.encode(),body);self.assertNotIn(b'vless://',body)
 def test_two_clients_have_independent_mtp_secrets(self):
  token2='b'*43;self.data['clients'][hashlib.sha256(token2.encode()).hexdigest()]={'enabled':True,'mtp':'2'*32,'links':{}}
  first=web.response_for(self.data,'mtp.funsociety.dev','/mtp/'+self.token)[1]['Location']
  second=web.response_for(self.data,'mtp.funsociety.dev','/mtp/'+token2)[1]['Location']
  self.assertNotEqual(first,second)
class Preservation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.cfg=self.root/'vpn.json'
  self.legacy=str(uuid.uuid4());self.managed=str(uuid.uuid4())
  self.original={'inbounds':[{'protocol':'vless','settings':{'clients':[{'id':self.legacy,'email':'old-user'}]},'streamSettings':{'xhttpSettings':{'path':'/private-test-path'}}}]}
  self.cfg.write_text(json.dumps(self.original));self.patches=[patch.object(agent,'ROOT',self.root),patch.object(agent,'BACK',self.root),patch.object(agent,'vpn_path',return_value=self.cfg),patch.object(agent,'telemt'),patch.object(agent,'verify_legacy',return_value={'vpn':1}),patch.object(agent,'run',return_value='')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def client(self):return {'name':'alice','uuid':self.managed,'mtp':'2'*32}
 def test_add_and_revoke_keep_legacy_exactly(self):
  agent.reconcile('az1',{'clients':[self.client()]})
  users=json.loads(self.cfg.read_text())['inbounds'][0]['settings']['clients'];self.assertIn(self.original['inbounds'][0]['settings']['clients'][0],users)
  agent.reconcile('az1',{'clients':[]})
  self.assertEqual(json.loads(self.cfg.read_text()),self.original)
 def test_colliding_uuid_is_rejected_without_modification(self):
  c=self.client();c['uuid']=self.legacy
  with self.assertRaises(ValueError):agent.reconcile('az1',{'clients':[c]})
  self.assertEqual(json.loads(self.cfg.read_text()),self.original)
 def test_invalid_name_cannot_become_toml_or_shell(self):
  c=self.client();c['name']='alice\n[malicious]'
  with self.assertRaises(ValueError):agent.reconcile('az1',{'clients':[c]})
  self.assertEqual(json.loads(self.cfg.read_text()),self.original)
 def test_failed_validation_rolls_back_vpn(self):
  with patch.object(agent,'run',side_effect=[RuntimeError('invalid'), '']):
   with self.assertRaises(RuntimeError):agent.reconcile('az1',{'clients':[self.client()]})
  self.assertEqual(json.loads(self.cfg.read_text()),self.original)
if __name__=='__main__':unittest.main()
