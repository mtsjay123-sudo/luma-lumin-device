import unittest,tempfile,time,threading,json,urllib.request,urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from luma.memory.store import Store
from luma.agent.runtime import Agent
from luma.integrations.providers import OutcomeUnknown,Providers
from luma.control.server import make_server

class FakeProviders:
    def __init__(self):self.env={};self.calls=0;self.fail=False
    def sms(self,args):
        self.calls+=1;time.sleep(.01)
        if self.fail:raise OutcomeUnknown('Check provider before retrying')
        return {'message_id':'fixture-only','summary':'Fixture accepted'}

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=Store(self.root/'state.db',self.root/'state.key');self.providers=FakeProviders();self.now=1788782400
        self.agent=Agent(store=self.store,providers=self.providers,use_model=False,now=lambda:self.now)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def test_encrypted_memory_survives_reopen(self):
        self.agent.chat('remember I prefer the private violet bicycle');self.assertNotIn(b'private violet',self.store.db_path.read_bytes());self.store.close();self.store=Store(self.root/'state.db',self.root/'state.key');self.assertIn('private violet',self.store.recall('bicycle')[0]['text'])
    def test_missing_key_never_silently_resets_memory(self):
        self.agent.chat('remember a preference');self.store.key_path.unlink()
        with self.assertRaises(RuntimeError):Store(self.root/'state.db',self.root/'state.key')
    def test_payment_secrets_are_rejected(self):
        for text in ['remember card number: 4111111111111111','remember password: secret']:
            with self.assertRaises(ValueError):self.agent.chat(text)
        self.assertEqual(self.store.all('memory'),[])
    def test_sms_disabled_until_explicitly_enabled(self):
        result=self.agent.chat('text +19195550123: Fixture only')
        self.assertEqual(result['state'],'draft')
        self.assertEqual(result['message_draft']['to'],'+19195550123')
        with self.assertRaises(ValueError):self.agent.propose('sms.send',{'to':'+19195550123','body':'Fixture only'})
        self.assertEqual(self.providers.calls,0)
    def draft(self):self.agent.set_message_route('twilio');return self.agent.chat('text +19195550123: Fixture only')
    def test_sms_requires_correct_confirmation_and_only_executes_once(self):
        d=self.draft();self.assertEqual(self.providers.calls,0)
        with self.assertRaises(ValueError):self.agent.confirm(d['action'],'wrong')
        def confirm():
            try:return self.agent.confirm(d['action'],d['confirm_token'])
            except ValueError:return None
        with ThreadPoolExecutor(2) as pool:list(pool.map(lambda _:confirm(),range(2)))
        self.assertEqual(self.providers.calls,1)
        with self.assertRaises(ValueError):self.agent.confirm(d['action'],d['confirm_token'])
    def test_unknown_outcome_is_not_retried(self):
        d=self.draft();self.providers.fail=True;r=self.agent.confirm(d['action'],d['confirm_token']);self.assertEqual(r['state'],'unknown')
        with self.assertRaises(ValueError):self.agent.confirm(d['action'],d['confirm_token'])
        self.assertEqual(self.providers.calls,1)
    def test_expired_or_cancelled_actions_do_not_send(self):
        d=self.draft();self.now+=601
        with self.assertRaises(ValueError):self.agent.confirm(d['action'],d['confirm_token'])
        d=self.draft();self.agent.cancel(d['action'])
        with self.assertRaises(ValueError):self.agent.confirm(d['action'],d['confirm_token'])
        self.assertEqual(self.providers.calls,0)
    def test_consent_rechecked_on_confirmation(self):
        d=self.draft();self.agent.enable('sms',False)
        with self.assertRaises(ValueError):self.agent.confirm(d['action'],d['confirm_token'])
        self.assertEqual(self.providers.calls,0)
    def test_kids_mode_cannot_send_or_recall_adult_memory(self):
        self.agent.chat('remember adult private detail');self.agent.set_mode('kids')
        for text in ['recall private','text +19195550123: no']:
            with self.assertRaises(ValueError):self.agent.chat(text)
        self.assertEqual(self.providers.calls,0)
    def test_tasks_persist_and_reminders_honor_hush_and_coalescing(self):
        self.agent.chat('remind me in 1 minute to check the oven');self.now+=65;self.agent.hush();self.assertIsNone(self.agent.tick());self.now+=1801
        r=self.agent.tick();self.assertIsNotNone(r);self.assertIn('oven',r['text']);self.assertIsNone(self.agent.tick())
    def test_model_cannot_name_an_unregistered_tool(self):
        self.agent.use_model=True;self.agent.planner=lambda *args:{'type':'tool','name':'sms.confirm_all','arguments':{}}
        self.assertIn("No action was taken",self.agent.chat('Do an unauthorized action')["text"])
        self.assertEqual(self.providers.calls,0)
    def test_explanation_cannot_create_a_model_invented_reminder(self):
        self.agent.use_model=True;self.store.set_setting('deliberate',False);self.store.set_setting('think_first',False)
        self.agent.planner=lambda *args:{'type':'tool','name':'tasks.create','arguments':{'title':'unrequested','due':'2026-10-01T12:00:00-04:00'}}
        self.assertIn('No action was taken',self.agent.chat('Explain how a reminder can help me')['text']);self.assertEqual(self.store.all('task'),[])
    def test_conceptual_explanation_has_no_tools_and_returns_prose(self):
        self.agent.use_model=True
        def planner(history,memories,tools,mode):
            self.assertEqual(tools,{})
            return {'type':'reply','text':'A reminder makes a future intention visible when it matters.'}
        self.agent.planner=planner
        self.assertIn('future intention',self.agent.chat('Explain how reminders help')['text'])
        self.assertEqual(self.store.all('action'),[])
    def test_natural_message_plan_resolves_named_contact_without_sending(self):
        self.agent.contacts.save({'name':'Mom','phone':'+19195550123'})
        self.agent.use_model=True
        self.agent.planner=lambda *args:{'type':'tool','name':'messages.prepare','arguments':{'recipient':'my mom','body':'Could you pick up the groceries while you are out?'}}
        result=self.agent.chat('Hey Luma, can you text my mom to pick up the groceries while she is out?')
        self.assertEqual(result['state'],'draft');self.assertEqual(result['message_draft']['to'],'+19195550123');self.assertEqual(self.providers.calls,0)
    def test_personality_persists_and_rejects_unknown_preferences(self):
        profile={'name':'Amiri','tone':'playful','language_style':'contemporary','verbosity':'brief'}
        self.agent.set_profile(profile);self.assertEqual(self.agent.profile,profile)
        with self.assertRaises(ValueError):self.agent.set_profile({**profile,'tone':'unrestricted'})
    def test_past_reminder_is_rejected(self):
        with self.assertRaises(ValueError):self.agent.propose('tasks.create',{'title':'old','due':'2024-01-01T12:00:00Z'})
        self.assertEqual(self.store.all('task'),[])
    def test_checkout_is_a_handoff_and_makes_no_request(self):
        p=Providers(env={'LUMA_MERCHANTS_JSON':'{"grocer":"https://example.com/shop"}'},request=lambda *a,**kw:self.fail('must not send request'))
        r=p.checkout({'merchant':'grocer','items':'apples','budget_cents':1500});self.assertTrue(r['handoff']);self.assertIn('No order has been placed',r['summary'])

class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();r=Path(self.temp.name);self.store=Store(r/'db',r/'key');self.agent=Agent(store=self.store,providers=FakeProviders(),use_model=False);self.server=make_server(self.agent,0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.base='http://127.0.0.1:'+str(self.server.server_port)
        with urllib.request.urlopen(self.base) as response:self.cookie=response.headers['Set-Cookie'].split(';')[0];self.assertIn('HttpOnly',response.headers['Set-Cookie'])
    def tearDown(self):self.server.agent_stop.set();self.server.shutdown();self.server.server_close();self.store.close();self.temp.cleanup()
    def request(self,path,data=None,headers=None):
        h={'Cookie':self.cookie,'Origin':self.base,'Content-Type':'application/json',**(headers or {})};req=urllib.request.Request(self.base+path,data=None if data is None else json.dumps(data).encode(),headers=h)
        return urllib.request.urlopen(req)
    def test_profile_photo_is_kept_small_and_served_back(self):
        import base64, io
        from PIL import Image
        buf=io.BytesIO();Image.new('RGB',(64,64),(200,120,90)).save(buf,'JPEG');photo='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
        with self.request('/api/photo',{'photo':photo}) as r:self.assertTrue(json.load(r)['photo'])
        with self.request('/api/photo') as r:self.assertEqual(r.read(),buf.getvalue())
        with self.request('/api/home') as r:self.assertTrue(json.load(r)['profile']['photo'])
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/photo',{'photo':'data:image/png;base64,iVBORw0KGgo='})
        self.assertEqual(e.exception.code,400)
        with self.request('/api/profile',{'name':'Sam'}) as r:self.assertEqual(json.load(r)['profile']['name'],'Sam')
        with self.request('/api/photo',{'photo':''}) as r:self.assertEqual(json.load(r)['photo'],'')
    def test_talking_in_the_window_turns_speech_into_text_locally(self):
        import sys, types
        heard=[]
        fake=types.ModuleType('luma.audio.stt')
        fake.transcribe_clip=lambda data,suffix: heard.append((len(data),suffix)) or 'what is on my calendar today'
        old=sys.modules.get('luma.audio.stt');sys.modules['luma.audio.stt']=fake
        try:
            req=urllib.request.Request(self.base+'/api/listen',data=b'\x1aE\xdf\xa3'+b'0'*5000,headers={'Cookie':self.cookie,'Origin':self.base,'Content-Type':'audio/webm;codecs=opus'})
            with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['text'],'what is on my calendar today')
            self.assertEqual(heard,[(5004,'.webm')])
            req=urllib.request.Request(self.base+'/api/listen',data=b'x'*10,headers={'Cookie':self.cookie,'Origin':self.base,'Content-Type':'text/plain'})
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
            self.assertEqual(e.exception.code,415)
        finally:
            if old is None: sys.modules.pop('luma.audio.stt',None)
            else: sys.modules['luma.audio.stt']=old
    def test_sharing_a_photo_goes_to_the_local_vision_and_rejects_non_images(self):
        seen=[]
        self.agent.see=lambda image,question='',thread='main': seen.append((len(image),question,thread)) or {'text':'I see a cat.','section':'vision'}
        req=urllib.request.Request(self.base+'/api/see?q=what%20is%20this&thread=main',data=b'\xff\xd8\xff'+b'0'*500,headers={'Cookie':self.cookie,'Origin':self.base,'Content-Type':'image/jpeg'})
        with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['text'],'I see a cat.')
        self.assertEqual(seen,[(503,'what is this','main')])
        bad=urllib.request.Request(self.base+'/api/see',data=b'hello',headers={'Cookie':self.cookie,'Origin':self.base,'Content-Type':'text/plain'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(bad)
        self.assertEqual(e.exception.code,415)
    def test_control_persists_memory_and_blocks_cross_origin(self):
        with self.request('/api/chat',{'text':'remember I like tea'}) as r:self.assertEqual(r.status,200)
        with self.request('/api/state') as r:self.assertEqual(json.load(r)['memories'][0]['text'],'I like tea')
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/chat',{'text':'remember attack'},{'Origin':'https://untrusted.example'})
        self.assertEqual(e.exception.code,403)
    def test_no_session_cannot_read_private_memory(self):
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.base+'/api/state')
        self.assertEqual(e.exception.code,401)
    def test_host_header_rebinding_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/state',headers={'Host':'untrusted.example'})
        self.assertEqual(e.exception.code,403)

if __name__=='__main__':unittest.main()
