"""Small 3x-ui API client. Never include response bodies or credentials in errors."""
import json,pathlib,urllib.request,urllib.error
class Panel:
 def __init__(self,access):
  self.access=access;self.base=access.get('url','http://127.0.0.1:'+str(access.get('port',1337))+access['basePath'])
  self.base=self.base.rstrip('/')+'/panel/api/'
 def call(self,path,data=None):
  headers={'Authorization':'Bearer '+self.access['apiToken']}
  if data is not None:headers['Content-Type']='application/json'
  request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(request,timeout=30) as r:body=json.load(r)
  except urllib.error.HTTPError as e:raise RuntimeError('Panel API '+path.split('/')[0]+' HTTP '+str(e.code)) from None
  if not body.get('success'):raise RuntimeError('Panel API operation rejected: '+path.split('/')[0])
  return body.get('obj')
 def inbounds(self):return self.call('inbounds/list')
