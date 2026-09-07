import http.cookiejar
import json
import ssl
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.control.server import make_server
from luma.control.pairing import ensure_local_certificate

class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();path=Path(self.temp.name)
        self.store=Store(path/'state.db',path/'key');self.agent=Agent(store=self.store,use_model=False)
        self.owner=make_server(self.agent,0);self.ctx=self.owner.control_context
        self.phone=make_server(self.agent,0,context=self.ctx,phone_host='127.0.0.1')
        cert,key=ensure_local_certificate(path/'tls','192.168.10.10')
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert,key);self.phone.socket=tls.wrap_socket(self.phone.socket,server_side=True)
        self.tls_client=ssl.create_default_context(cafile=str(cert))
        for server in [self.owner,self.phone]:threading.Thread(target=server.serve_forever,daemon=True).start()
        self.base=f'https://127.0.0.1:{self.phone.server_port}'
        self.client=urllib.request.build_opener(urllib.request.HTTPSHandler(context=self.tls_client),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def tearDown(self):
        self.ctx.stop.set()
        for server in [self.owner,self.phone]:server.shutdown();server.server_close()
        self.store.close();self.temp.cleanup()
    def request(self,path,data=None,headers=None):
        request=urllib.request.Request(self.base+path,data=None if data is None else json.dumps(data).encode(),headers={'Origin':self.base,'Content-Type':'application/json',**(headers or {})})
        return self.client.open(request)
    def pair(self):
        invite=self.ctx.pairing.create_invite()
        with self.request('/api/phone/pair',{'token':invite['token'],'name':'Fixture phone'}) as r:
            self.assertIn('Secure',r.headers['Set-Cookie']);self.assertIn('HttpOnly',r.headers['Set-Cookie']);return json.load(r)['device']
    def test_phone_page_never_grants_owner_cookie_or_private_records(self):
        with self.request('/') as r:self.assertIsNone(r.headers.get('Set-Cookie'))
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/state')
        self.assertEqual(error.exception.code,401)
    def test_pair_over_tls_and_revoke_immediately(self):
        device=self.pair()
        with self.request('/api/state') as r:self.assertEqual(json.load(r)['viewer'],'phone')
        self.ctx.pairing.revoke(device['id'])
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/state')
        self.assertEqual(error.exception.code,401)
    def test_phone_cannot_issue_invites_or_enable_microphone(self):
        self.pair()
        for path,data in [('/api/phone/invite',{}),('/api/setting',{'key':'muted','value':False})]:
            with self.assertRaises(urllib.error.HTTPError) as e:self.request(path,data)
            self.assertEqual(e.exception.code,403)
        self.assertTrue(self.agent.muted)
    def test_pairing_requires_origin_and_rejects_forwarded_identity(self):
        invite=self.ctx.pairing.create_invite()
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/phone/pair',{'token':invite['token'],'name':'no'}, {'Origin':'https://evil.example','X-Forwarded-For':'127.0.0.1'})
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/state',headers={'Cookie':'luma_owner='+self.ctx.owner_session})
        self.assertEqual(e.exception.code,401)
    def test_phone_can_draft_contact_message_without_sending(self):
        self.pair();self.agent.contacts.save({'name':'Mom','phone':'+19195550123'})
        with self.request('/api/messages/prepare',{'recipient':'my mom','body':'Fixture groceries'}) as r:self.assertEqual(json.load(r)['state'],'draft')
        self.assertEqual(self.store.all('action'),[])
    def test_phone_does_not_enable_integrations_in_kids_mode(self):
        self.pair();self.agent.set_mode('kids')
        with self.assertRaises(urllib.error.HTTPError):self.request('/api/messages/prepare',{'recipient':'+19195550123','body':'blocked'})
        with self.request('/api/state') as r:
            state=json.load(r);self.assertEqual(state['contacts'],[]);self.assertEqual(state['events'],[])

if __name__=='__main__':unittest.main()
