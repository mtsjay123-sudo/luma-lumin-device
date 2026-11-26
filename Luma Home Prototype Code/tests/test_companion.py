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

    def test_phone_can_turn_the_mic_off_but_not_on(self):
        self.pair();self.agent.set_muted(False)
        with self.request('/api/setting',{'key':'muted','value':True}) as r:self.assertEqual(r.status,200)
        self.assertTrue(self.agent.muted)
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/setting',{'key':'muted','value':False})
        self.assertEqual(e.exception.code,403);self.assertIn('at home',json.load(e.exception)['error'])
        self.assertTrue(self.agent.muted)
    def test_phone_can_start_a_nap_and_end_one_but_not_switch_naps_off(self):
        # A nap asked for from the phone is the same nap as one asked for out loud: nothing started until the time's up,
        # and it only ever makes Luma quieter. The off switch is a setting, and settings are changed at home.
        from luma.agent import nap
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/setting',{'key':'nap','value':True})
        self.assertIn(e.exception.code,(401,403));self.assertFalse(nap.napping(self.agent))   # a stranger on the Wi-Fi can't (an unpaired POST is a 403)
        self.pair()
        with self.request('/api/setting',{'key':'nap','value':True}) as r:self.assertEqual(r.status,200)
        self.assertTrue(nap.napping(self.agent))
        with self.request('/api/today') as r:day=json.load(r)
        self.assertGreater(day['device']['napping_until'],self.agent.clock());self.assertTrue(day['device']['naps'])
        with self.request('/api/setting',{'key':'nap','value':False}) as r:self.assertEqual(r.status,200)
        self.assertFalse(nap.napping(self.agent))
        with self.request('/api/today') as r:self.assertEqual(json.load(r)['device']['napping_until'],0)
        with self.request('/api/setting',{'key':'nap','value':45}) as r:self.assertEqual(r.status,200)
        self.assertAlmostEqual(nap.until(self.agent)-self.agent.clock(),45*60,delta=5)
        for wrong in (0,-5,181,'20',2.5,None):
            with self.assertRaises(urllib.error.HTTPError):self.request('/api/setting',{'key':'nap','value':wrong})
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/setting',{'key':'naps','value':False})
        self.assertEqual(e.exception.code,403);self.assertTrue(nap.napping(self.agent))
        self.agent.store.set_setting('naps',False);nap.wake(self.agent)   # switched off at home: the phone is told so, and nothing naps
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/setting',{'key':'nap','value':True})
        self.assertEqual(e.exception.code,409);self.assertIn('switched off',json.load(e.exception)['error']);self.assertFalse(nap.napping(self.agent))
    def test_the_phone_app_and_its_today_call(self):
        with self.request('/phone/') as r:
            page=r.read().decode();self.assertIn('phone.js',page);self.assertIsNone(r.headers.get('Set-Cookie'))
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/today')
        self.assertEqual(e.exception.code,401)
        self.pair();self.store.put('memory',{'text':"Mom's birthday is June 3"})
        with self.request('/api/today') as r:
            today=json.load(r)
        self.assertEqual(today['memory']['recent'][0]['kind'],'Dates')
        self.assertGreater(today['device']['storage']['total'],0)
        self.assertIn(today['device']['mic'],{'on','off'})

    def test_the_ring_of_the_day_is_times_only(self):
        # The phone draws today as a ring of 48 dots round Luma, lit where they talked. It's given the half hours and
        # nothing else: no word of what was said, nothing from another day, and nothing at all in kids mode.
        from datetime import datetime
        from luma.control import today as day
        self.pair()
        self.assertEqual(day.talked(self.agent),[])
        midnight=datetime.fromtimestamp(self.agent.clock(),self.agent.zone).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        self.agent.transcripts['main']=[{'role':'user','text':'my secret plan','at':midnight+9*3600+60},{'role':'luma','text':'ok','at':midnight+9*3600+90},
                                        {'role':'user','text':'later','at':midnight+13*3600+31*60},{'role':'user','text':'yesterday','at':midnight-600},{'role':'user','text':'no time'}]
        self.assertEqual(day.talked(self.agent),[18,27])
        with self.request('/api/today') as r:raw=r.read().decode()
        self.assertEqual(json.loads(raw)['talked'],[18,27])
        self.assertEqual(day.compact(self.agent)['talked'],[18,27])             # the same through the relay, away from home
        self.agent.set_mode('kids')
        self.assertNotIn('talked',day.payload(self.agent))
        page=(Path(__file__).resolve().parents[1]/'src'/'luma'/'control'/'web'/'phone'/'phone.js').read_text()
        self.assertIn('renderDay(today.talked, today.zone)',page)

    def test_the_passcode_is_chosen_and_reset_from_the_paired_phone_and_never_sent_back(self):
        # Always on, and locked to its people (luma.agent.who): the phrase is chosen, changed and reset in the app, and
        # nothing the phone is sent holds it. A weak one is refused with a sentence. Not in kids mode.
        import urllib.error
        from luma.agent import who
        self.pair()
        with self.request('/api/who',{'action':'choose','phrase':'blue kettle tuesday'}) as r:raw=r.read().decode()
        self.assertTrue(json.loads(raw)['who']['people'][0]['passcode'])
        self.assertNotIn('kettle',raw)
        with self.request('/api/who',{'action':'greeting','line':'wtw bro'}) as r:self.assertEqual(json.loads(r.read())['who']['people'][0]['greeting'],'Wtw bro')
        with self.request('/api/who',{'action':'lock'}) as r:self.assertTrue(json.loads(r.read())['who']['locked'])
        self.assertTrue(self.agent.chat('what is on my list',channel='room').get('locked'))
        with self.request('/api/today') as r:today=r.read().decode()
        self.assertTrue(json.loads(today)['device']['who']['locked'])
        self.assertNotIn('kettle',today)
        with self.request('/api/who',{'action':'unlock'}) as r:self.assertFalse(json.loads(r.read())['who']['locked'])
        with self.assertRaises(urllib.error.HTTPError) as weak:self.request('/api/who',{'action':'choose','phrase':'hello'})
        self.assertIn('two or three words',json.loads(weak.exception.read())['error'])
        with self.request('/api/who',{'action':'reset'}) as r:self.assertFalse(json.loads(r.read())['who']['people'][0]['passcode'])
        self.assertFalse(who.enabled(self.agent))
        self.agent.set_mode('kids')
        with self.assertRaises(urllib.error.HTTPError) as kids:self.request('/api/who',{'action':'choose','phrase':'blue kettle tuesday'})
        self.assertIn(kids.exception.code,{400,403})
        self.assertFalse(who.enabled(self.agent))

    def test_the_second_step_of_a_sign_in_comes_from_the_paired_phone_and_no_password_is_ever_sent_back(self):
        # With the owner's yes, Luma does it (luma.agent.yeses): a sign-in is typed into the app once and sealed; the
        # phone's Confirm is the second step; nothing the phone is sent holds the password; an unpaired phone gets nothing.
        import urllib.error
        from luma.agent import yeses
        typed=[]
        class Browser:
            def describe(self,ref): return {'type':'password','label':'Password'}
            def read(self): return {'title':'Sign in','url':'https://www.chase.com/login'}
            def type(self,ref,text,submit=False,expected_label=None): typed.append(text); return self.read()
        with self.assertRaises(urllib.error.HTTPError) as stranger:self.request('/api/yes',{'action':'signin','site':'chase.com','user':'x','secret':'y'})
        self.assertIn(stranger.exception.code,{401,403})
        self.pair()
        with self.request('/api/yes',{'action':'signin','site':'https://www.chase.com/login','user':'jay01','secret':'correct-horse-battery','label':'my bank'}) as r:raw=r.read().decode()
        self.assertEqual(json.loads(raw)['yes']['signins'][0]['site'],'chase.com')
        self.assertNotIn('correct-horse',raw)
        self.agent._browser=Browser();self.agent.enable('browser',True)
        self.store.set_setting('browser_page','Sign in — https://www.chase.com/login')
        self.agent.chat('log me in to my bank')
        asked=self.agent.propose('browser.type',{'ref':2,'text':'x','submit':False})
        with self.request('/api/today') as r:today=r.read().decode()
        self.assertEqual(json.loads(today)['device']['yes']['waiting'][0]['id'],asked['waiting'])
        self.assertNotIn('correct-horse',today)
        self.assertEqual(typed,[])
        with self.request('/api/yes',{'action':'confirm','id':asked['waiting']}) as r:done=r.read().decode()
        self.assertEqual(typed,['correct-horse-battery'])
        self.assertIn('typed your password on chase.com',done)
        self.assertNotIn('correct-horse',done)
        with self.request('/api/yes') as r:self.assertNotIn('correct-horse',r.read().decode())
        with self.assertRaises(urllib.error.HTTPError) as again:self.request('/api/yes',{'action':'confirm','id':asked['waiting']})   # used once
        self.assertEqual(again.exception.code,400)
        with self.request('/api/yes',{'action':'forget_signin','id':json.loads(raw)['yes']['signins'][0]['id']}) as r:self.assertEqual(json.load(r)['yes']['signins'],[])

    def test_luma_on_its_stage_says_only_what_is_true(self):
        # The line under Luma on the phone is its state in its own words. A nap never says it can't hear (anything said
        # wakes it); mic off says so plainly; it never calls itself an AI or an assistant.
        web=Path(__file__).resolve().parents[1]/'src'/'luma'/'control'/'web'/'phone'
        js,page=(web/'phone.js').read_text(),(web/'index.html').read_text()
        for line in ('"Napping. Say anything and I\'m up."','"Here, and listening."','"Here. My mic is off, so I can\'t hear the room."','"I can\'t be reached right now."'):
            self.assertIn(line,js)
        for part in ('id="stage"','id="luma-body"','id="day"','id="here"','id="hello"','id="ask-text"','id="state"'):self.assertIn(part,page)
        here=js[js.index('$("here").textContent'):];here=here[:here.index(';')]
        for word in ('AI','assistant','program','asleep',"can't hear you"):self.assertNotIn(word,here)

    def test_the_storage_screen_from_a_paired_phone(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/storage')
        self.assertEqual(e.exception.code,401)                                  # not paired: nothing about what's kept
        self.pair()
        self.store.put('chat',{'thread':'t1','title':'Trip ideas','log':[{'role':'user','text':'x'*40000,'at':1}]})
        with self.request('/api/storage') as r:page=json.load(r)
        self.assertEqual(page['state'],'ok');self.assertTrue(page['health']['ok'])
        self.assertIn('chats',[k['key'] for k in page['kinds']])
        chat=next(b for b in page['biggest'] if b['kind']=='chat')
        self.assertEqual(chat['title'],'Trip ideas')
        with self.request('/api/storage/remove',{'kind':'chat','id':chat['id']}) as r:done=json.load(r)
        self.assertGreater(done['freed_bytes'],30000)
        self.assertIsNone(self.store.get('chat',chat['id']))
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/storage/remove',{'kind':'memory','id':'x'})
        self.assertEqual(e.exception.code,400)
        with self.request('/api/storage/repair',{}) as r:self.assertTrue(json.load(r)['ok'])
        self.agent.set_mode('kids')
        with self.request('/api/storage') as r:self.assertEqual(json.load(r),{'kids':True})
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/storage/remove',{'kind':'chat','id':'x'})
        self.assertIn(e.exception.code,(400,403))                               # refused in kids mode, by the gate every personal control sits behind

    def test_whats_marked_hidden_is_hidden_on_the_phone(self):
        # A row is a flex box, and a class's display used to beat the hidden attribute: "Super Intelligence …" showed for everyone.
        with self.request('/phone/phone.css') as r:css=r.read().decode()
        self.assertIn('[hidden] { display: none !important; }',css)
        with self.request('/phone/') as r:page=r.read().decode()
        self.assertIn('id="plus-row" hidden',page)
        self.assertIn('id="plan-row" hidden',page)  # the plan row is there, and shows only when there's a plan to show

if __name__=='__main__':unittest.main()
