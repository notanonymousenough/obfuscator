import importlib.util,pathlib,tempfile,unittest,json
from unittest.mock import patch
s=importlib.util.spec_from_file_location('ddns',pathlib.Path(__file__).resolve().parents[1]/'scripts/cloudflare_dns.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class DnsSafety(unittest.TestCase):
 def test_discovery_disagreement_does_not_publish(self):
  with patch.object(m,'fetch',side_effect=[b'8.8.8.8',b'1.1.1.1']):
   with self.assertRaises(ValueError):m.public_ipv4()
 def test_apply_requires_ingress_confirmation(self):
  with self.assertRaises(ValueError):m.sync({},True)
 def test_cgnat_discovery_rejected(self):
  with patch.object(m,'fetch',return_value=b'100.66.95.154'):
   with self.assertRaises(ValueError):m.public_ipv4()
 def test_multiple_records_never_overwritten(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'token';p.write_text('fake-test-token')
   responses=[json.dumps({'success':True,'result':[{'id':'zone'}]}).encode(),json.dumps({'success':True,'result':[{'id':'a'},{'id':'b'}]}).encode()]
   with patch.object(m,'fetch',side_effect=responses) as f:
    with self.assertRaises(ValueError):m.sync({'zone':'example.com','name':'a.example.com','token_file':str(p),'ipv4':'8.8.8.8','ingress_confirmed':True},True)
    self.assertEqual(f.call_count,2)
 def test_read_only_default_does_not_write(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'token';p.write_text('fake-test-token')
   responses=[json.dumps({'success':True,'result':[{'id':'zone'}]}).encode(),json.dumps({'success':True,'result':[]}).encode()]
   with patch.object(m,'fetch',side_effect=responses) as f:
    m.sync({'zone':'example.com','name':'a.example.com','token_file':str(p),'ipv4':'8.8.8.8'})
    self.assertEqual(f.call_count,2)
if __name__=='__main__':unittest.main()
