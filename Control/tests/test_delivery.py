import hashlib,importlib.util,json,pathlib,sqlite3,unittest,uuid,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('control_delivery',ROOT/'delivery.py');delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)
spec=importlib.util.spec_from_file_location('subscription_server',ROOT.parent/'Subscriptions/server.py');web=importlib.util.module_from_spec(spec);spec.loader.exec_module(web)
class Delivery(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:');self.user=str(uuid.uuid4());self.token='t'*43
  self.db.executescript('''CREATE TABLE clients(id INTEGER,email TEXT,sub_id TEXT,uuid TEXT,secret TEXT,enable INTEGER,expiry_time INTEGER);CREATE TABLE client_inbounds(client_id INTEGER,inbound_id INTEGER);CREATE TABLE inbounds(id INTEGER,tag TEXT,protocol TEXT,stream_settings TEXT,enable INTEGER);''')
  self.db.execute('INSERT INTO clients VALUES(1,?,?,?,?,1,0)',('obf-owner',self.token,self.user,'ee'+'a'*32+'mtp.funsociety.dev'.encode().hex()))
  for i,node in enumerate(['de1','de2','az1'],1):
   self.db.execute('INSERT INTO inbounds VALUES(?,?,?,?,1)',(i,'obf-vpn-'+node,'vless',json.dumps({'xhttpSettings':{'path':'/unchanged'}})));self.db.execute('INSERT INTO client_inbounds VALUES(1,?)',(i,))
  self.db.execute('INSERT INTO inbounds VALUES(4,?,?,?,1)',('obf-mtp-de1','mtproto','{}'));self.db.execute('INSERT INTO client_inbounds VALUES(1,4)')
  self.db.execute('INSERT INTO inbounds VALUES(5,?,?,?,1)',('obf-mtp-az1','mtproto','{}'));self.db.execute('INSERT INTO client_inbounds VALUES(1,5)')
 def tearDown(self):self.db.close()
 def data(self):return {'clients':delivery.collect(self.db,now_ms=1000)}
 def test_existing_token_and_uuid_are_preserved(self):
  c=self.data()['clients'][hashlib.sha256(self.token.encode()).hexdigest()]
  self.assertIn(self.user,c['links']['az1']);self.assertEqual(c['mtp'],'a'*32)
 def test_de2_hidden_even_when_client_attached(self):
  code,_,body=web.response_for(self.data(),'obfuscator.funsociety.dev','/s/'+self.token+'?format=plain');self.assertEqual(code,200);self.assertNotIn(b'de2.obfuscator',body);self.assertIn(b'#AZ1',body)
 def test_panel_disable_revokes_delivery(self):
  self.db.execute('UPDATE clients SET enable=0');self.assertEqual(web.response_for(self.data(),'obfuscator.funsociety.dev','/s/'+self.token)[0],404)
 def test_normalized_uuid_rotation_changes_published_key(self):
  new=str(uuid.uuid4());self.db.execute('UPDATE clients SET uuid=?',(new,));c=next(iter(self.data()['clients'].values()));self.assertIn(new,c['links']['de1']);self.assertNotIn(self.user,c['links']['de1'])
 def test_detaching_de2_removes_only_private_link(self):
  self.db.execute('DELETE FROM client_inbounds WHERE inbound_id=2');c=next(iter(self.data()['clients'].values()));self.assertNotIn('de2',c['links']);self.assertEqual(set(c['links']),{'de1','az1'})
 def test_expired_client_denied(self):
  self.db.execute('UPDATE clients SET expiry_time=999');self.assertFalse(next(iter(self.data()['clients'].values()))['enabled'])
 def test_no_mtp_attachment_does_not_generate_bogus_link(self):
  self.db.execute('DELETE FROM client_inbounds WHERE inbound_id IN (4,5)');self.assertEqual(web.response_for(self.data(),'mtp.funsociety.dev','/mtp/'+self.token)[0],404)
 def test_new_panel_token_format_supported(self):
  short='p'*16;self.db.execute('UPDATE clients SET sub_id=?',(short,));self.assertEqual(web.response_for(self.data(),'obfuscator.funsociety.dev','/s/'+short)[0],200)

 def test_partial_mtp_binding_is_not_published(self):
  self.db.execute('DELETE FROM client_inbounds WHERE inbound_id=5');self.assertIsNone(next(iter(self.data()['clients'].values()))['mtp'])

 def test_relative_expiry_before_first_use_can_fetch_subscription(self):
  self.db.execute('UPDATE clients SET expiry_time=-86400000');self.assertTrue(next(iter(self.data()['clients'].values()))['enabled'])
