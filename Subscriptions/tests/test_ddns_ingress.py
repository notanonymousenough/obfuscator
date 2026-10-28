import contextlib,importlib.util,io,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
SCRIPTS=pathlib.Path(__file__).resolve().parents[1]/'scripts';sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('ddns_ingress',SCRIPTS/'ddns-az1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DDNSIngress(unittest.TestCase):
 def run_case(self,reachable,unavailable=False):
  with tempfile.TemporaryDirectory() as td:
   d=pathlib.Path(td);(d/'token').write_text('test-only-publisher');(d/'config').write_text(json.dumps({'publisher_token_file':str(d/'token'),'relay_ipv4':'159.89.12.205'}))
   fake=lambda:contextlib.nullcontext(io.BytesIO(json.dumps({'reachable':reachable}).encode()))
   with patch.object(m,'CONFIG',d/'config'),patch.object(m,'public_ipv4',return_value='185.146.112.151'),patch.object(m.urllib.request,'urlopen',side_effect=OSError('probe unavailable') if unavailable else lambda *a,**k:fake()),patch.object(m,'sync') as sync,contextlib.redirect_stdout(io.StringIO()):
    m.main();calls=sync.call_args_list
   self.assertEqual({c.args[0]['name'] for c in calls},set(m.NAMES))
   self.assertEqual(len(calls),2)
   for c in calls:self.assertEqual(c.args[0]['ipv4'],'185.146.112.151' if reachable and not unavailable else '159.89.12.205')
 def test_reachable_publishes_both_direct_names(self):self.run_case(True)
 def test_unreachable_keeps_both_relay_names(self):self.run_case(False)
 def test_probe_error_cannot_publish_unverified_public_ip(self):self.run_case(True,True)
