"""Local owner controls and an opt-in, paired HTTPS phone companion."""
from __future__ import annotations
import base64
import os
import json
import secrets
import ssl
import subprocess
import threading
import re
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import quote_plus, urlsplit
from luma.control.pairing import PairingManager, ensure_local_certificate, private_ipv4
from luma.integrations.phone_app import PhoneApp

ROOT = Path(__file__).parent / 'web'

def lan_addresses():
    """Read local interfaces only. Never infer a publicly reachable device URL."""
    import re
    try:
        import shutil
        if shutil.which('ip'):
            output = subprocess.run(['ip','-j','-4','address','show'], capture_output=True, text=True, timeout=3).stdout
            addresses = [a.get('local','') for i in json.loads(output) for a in i.get('addr_info',[]) if a.get('family') == 'inet']
        else:
            output = subprocess.run(['/sbin/ifconfig'], capture_output=True, text=True, timeout=3).stdout
            addresses = re.findall(r'\binet (\d+\.\d+\.\d+\.\d+)', output)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        addresses = []
    result = []
    for address in addresses:
        try: address = str(private_ipv4(address))
        except ValueError: continue
        if address not in result: result.append(address)
    return result

class ControlContext:
    def __init__(self, agent):
        self.agent = agent
        self.events = deque(maxlen=30)
        self.stop = threading.Event()
        self.pairing = PairingManager(agent.store)
        self.phone_server = None
        self.phone_origin = None
        self.owner_session = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.limits = {}
        self.phone_app = PhoneApp(agent)
        agent.on_result = self.publish

    def publish(self, result):
        result.setdefault('event_id', secrets.token_hex(8))
        self.events.append({'created': time.time(), 'result': result})

    def say(self, text, cancel_event=None):
        event = cancel_event or self.agent.new_turn()
        def play():
            try:
                from luma.orchestrator import speak
                speak(text, self.agent, cancel_event=event, allow_muted=True)
            except Exception as error:
                self.publish({'text':'Voice could not play: ' + str(error)[:250]})
        threading.Thread(target=play, daemon=True).start()

    recording = None  # a Teach session in Luma's browser, while the owner shows Luma a task

    def allowed(self, key, count, seconds=60):
        now = time.monotonic()
        with self.lock:
            self.limits = {k: v for k, v in self.limits.items() if now-v[0] < seconds}
            start, used = self.limits.get(key, (now, 0))
            self.limits[key] = (start, used+1)
            return used < count

    def start_phone(self, host, port=8096):
        host = str(private_ipv4(host))
        if host not in lan_addresses(): raise ValueError('Connect this Mac to your home Wi-Fi first, then choose its local address.')
        with self.lock:
            if self.phone_server: return self.phone_origin
            cert, key = ensure_local_certificate(self.agent.store.db_path.parent / 'phone-tls', host)
            server = make_server(self.agent, port, context=self, phone_host=host)
            try:
                tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                tls.minimum_version = ssl.TLSVersion.TLSv1_2
                tls.load_cert_chain(cert, key)
                server.socket = tls.wrap_socket(server.socket, server_side=True)
            except Exception:
                server.server_close(); raise
            self.phone_origin = f'https://{host}:{server.server_port}'
            self.phone_server = server
            threading.Thread(target=server.serve_forever, daemon=True).start()
            return self.phone_origin


def home_payload(agent, owner=True):
    """Everything the Luma Desktop home screen shows, in one request."""
    now = agent.clock()
    approvals = []
    for row in agent.store.all('action', 40):
        if row.get('state') != 'pending' or row.get('expires', 0) < now: continue
        item = {k: v for k, v in row.items() if k != 'approval_hash'}
        token = agent.approval_tokens.get(row['id'])
        if owner and token: item['confirm_token'] = token[0]
        approvals.append(item)
    learned = [m for m in agent.store.all('memory', 60) if m.get('source') in {'feedback', 'noticed_in_conversation', 'explicit_user_request'}][:8]
    helpers = agent.helpers.list()
    return {
        'today': agent.today(),
        'cards': agent.feed.list(40),
        'approvals': approvals,
        'helpers': helpers,
        'ideas': agent.ideas(),
        'activity': agent.activity.view(),
        'threads': agent.thread_list(),
        'rules': agent.rules.all(),
        'learned': learned,
        'connections': {
            'mail': agent.mail.status(),
            'calendar': agent.calendar.status(),
            'browser': {'on': agent.integration_on('browser'), 'available': agent._browser_available()},
            'texting': {'route': agent.message_route, 'enabled': agent.store.setting('integration:sms', False)},
            'phone_app': None,
            'apps': agent.connectors.list() if owner else [],
            'app_presets': agent.connectors.presets(),
        },
        'profile': {'name': agent.profile.get('name') or '', 'photo': str(agent.store.setting('owner_photo_at', '') or '')},
        'taught': agent.taught.list() if owner and agent.mode != 'kids' else [],
        'model': {'on': agent.use_model},
    }


def make_server(agent, port=8095, *, context=None, phone_host=None):
    root_context = context is None
    ctx = context or ControlContext(agent)
    companion = phone_host is not None

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, *args): pass

        def authorities(self):
            port = self.server.server_port
            return {f'{phone_host}:{port}'} if companion else {f'127.0.0.1:{port}', f'localhost:{port}'}

        def valid_host(self): return self.headers.get('Host') in self.authorities()

        def valid_origin(self):
            scheme = 'https' if companion else 'http'
            return self.headers.get('Origin') in {f'{scheme}://{a}' for a in self.authorities()}

        def authenticated(self):
            cookies = SimpleCookie()
            try: cookies.load(self.headers.get('Cookie', ''))
            except Exception: return False
            token = cookies.get('luma_phone' if companion else 'luma_owner')
            if not token: return False
            return bool(ctx.pairing.authenticate(token.value)) if companion else secrets.compare_digest(token.value, ctx.owner_session)

        def send(self, data, status=200, kind='application/json', *, owner_cookie=False, phone_token=None):
            encoded = json.dumps(data, ensure_ascii=False).encode() if kind=='application/json' else data
            self.send_response(status)
            for k, v in {'Content-Type':kind, 'Content-Length':str(len(encoded)), 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer', 'X-Frame-Options':'DENY', 'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items(): self.send_header(k,v)
            if owner_cookie: self.send_header('Set-Cookie',f'luma_owner={ctx.owner_session}; HttpOnly; SameSite=Strict; Path=/')
            if phone_token: self.send_header('Set-Cookie',f'luma_phone={phone_token}; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000; Path=/')
            self.end_headers()
            self.wfile.write(encoded)

        def redirect(self, location):
            self.send_response(302)
            self.send_header('Location', location)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_GET(self):
            if not self.valid_host(): return self.send({'error':'Invalid device host'},403)
            path = urlsplit(self.path).path
            static = {'/':('index.html','text/html'), '/app.js':('app.js','text/javascript'), '/companion.js':('companion.js','text/javascript'), '/style.css':('style.css','text/css'),
                      '/desktop/':('desktop/index.html','text/html'), '/desktop/desktop.js':('desktop/desktop.js','text/javascript'), '/desktop/desktop.css':('desktop/desktop.css','text/css')}
            if path=='/desktop': return self.redirect('/desktop/')
            if path=='/desktop/logo':
                # Drop your own logo at web/desktop/brand/logo.png and Luma Desktop uses it everywhere.
                custom = ROOT/'desktop'/'brand'/'logo.png'
                if custom.is_file(): return self.send(custom.read_bytes(),kind='image/png')
                svg = ROOT/'desktop'/'brand'/'logo.svg'
                if svg.is_file(): return self.send(svg.read_bytes(),kind='image/svg+xml')
                return self.send((ROOT/'desktop'/'mascot.svg').read_bytes(),kind='image/svg+xml')
            if re.fullmatch(r'/desktop/characters/[a-z-]{2,30}\.png', path) and (ROOT/path.removeprefix('/')).is_file():
                return self.send((ROOT/path.removeprefix('/')).read_bytes(),kind='image/png')
            if path in {'/desktop/fonts/geist.woff2','/desktop/fonts/instrument-serif.woff2','/desktop/fonts/instrument-serif-italic.woff2'}:
                return self.send((ROOT/path.removeprefix('/')).read_bytes(),kind='font/woff2')
            if path in static and not (companion and path.startswith('/desktop/')):
                file, kind = static[path]
                return self.send((ROOT/file).read_bytes(),kind=kind+'; charset=utf-8',owner_cookie=path in {'/','/desktop/'} and not companion)
            if path=='/api/session': return self.send({'viewer':'phone' if companion else 'owner', 'paired':self.authenticated()})
            if not self.authenticated(): return self.send({'error':'Pair this phone from the Mac, or reopen the local owner controls.'},401)
            if path.startswith('/files/'):
                row = agent.store.get('file', path[len('/files/'):])
                files = (agent.files_dir).resolve()
                target = Path(row['path']).resolve() if row else None
                if not row or files not in target.parents or not target.is_file(): return self.send({'error':'File not found'},404)
                data = target.read_bytes()
                self.send_response(200)
                kind = 'application/vnd.openxmlformats-officedocument.presentationml.presentation' if target.suffix == '.pptx' else 'application/octet-stream'
                safe = ''.join(c for c in row['name'] if c.isalnum() or c in '-_.') or 'luma-file'
                for k, v in {'Content-Type': kind, 'Content-Length': str(len(data)), 'Content-Disposition': f'attachment; filename="{safe}"',
                             'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}.items(): self.send_header(k, v)
                self.end_headers()
                return self.wfile.write(data)
            if path=='/api/activity':
                return self.send({'activity':agent.activity.view(),'recent':agent.activity.recent[:5]})
            if path=='/api/activity/shot':
                image=agent.activity.image()
                if not image: return self.send({'error':'No picture yet'},404)
                return self.send(image,kind='image/jpeg')
            if path=='/api/photo':
                photo=agent.store.setting('owner_photo','')
                if not photo: return self.send({'error':'No photo yet'},404)
                return self.send(base64.b64decode(photo),kind='image/jpeg')
            if path=='/api/browser/frame':
                # What Luma's browser shows right now, for the browser view in Luma's window.
                if companion or agent.mode=='kids': return self.send({'error':'Open the browser on the Mac.'},403)
                if not agent.integration_on('browser') or not agent.browser: return self.send({'frame':None})
                try: return self.send({'frame':agent.browser.frame()})
                except Exception as error: return self.send({'frame':None,'error':str(error)[:200]})
            if path=='/api/home':
                if agent.mode=='kids': return self.send({'kids':True,'today':agent.today(),'ideas':[],'cards':[],'approvals':[]})
                payload=home_payload(agent, owner=not companion)
                payload['connections']['phone_app']=ctx.phone_app.status() if not companion else None
                payload['events']=list(ctx.events)[-20:]
                payload['status']=agent.status()
                return self.send(payload)
            if path.startswith('/api/threads/'):
                ident=path[len('/api/threads/'):]
                if ident not in agent.transcripts: return self.send({'error':'That chat is gone.'},404)
                return self.send({'id':ident,'title':agent.thread_titles.get(ident),'messages':agent.transcripts[ident]})
            if path=='/api/state':
                adult = agent.mode!='kids'
                actions = [{k:v for k,v in r.items() if k!='approval_hash'} for r in agent.store.all('action',30)] if adult else []
                return self.send({'viewer':'phone' if companion else 'owner', 'status':agent.status(), 'household':{'timers':agent.household.timers(mode=agent.mode),'records':agent.household.records(mode=agent.mode),'recipes':agent.household.recipes(mode=agent.mode),'briefing':agent.household.briefing(mode=agent.mode)}, 'workflows':agent.workflows.list() if adult else [], 'local_grocery_lists':agent.store.all('grocery_list',20) if adult else [], 'memories':agent.store.all('memory',40) if adult else [], 'contacts':agent.contacts.list() if adult else [], 'message_drafts':agent.store.all('phone_draft',20) if adult else [], 'sms_receipts':agent.store.all('sms_receipt',30) if adult else [], 'grocery_receipts':agent.store.all('grocery_receipt',15) if adult else [], 'tasks':agent._run('tasks.list',{})['tasks'], 'routines':[r for r in agent.store.all('routine') if r.get('mode','friend')==agent.mode], 'actions':actions, 'events':list(ctx.events)[-20:] if adult else [], 'booking_services':agent.bookings.services() if adult else [], 'files':[{'id':f['id'],'name':f['name'],'url':'/files/'+f['id'],'kind':f.get('kind'),'title':f.get('title'),'slides':f.get('slides'),'theme':f.get('theme'),'outline':f.get('outline'),'created':f.get('created')} for f in agent.store.all('file',20)] if adult else [], 'phone':{'origin':ctx.phone_origin, 'addresses':lan_addresses() if not companion and not ctx.phone_origin else [], 'devices':ctx.pairing.list_devices() if not companion and adult else []}, 'phone_app':ctx.phone_app.status() if adult and not companion else None})
            return self.send({'error':'Not found'},404)

        def do_POST(self):
            if not self.valid_host() or not self.valid_origin(): return self.send({'error':'Device origin required'},403)
            path = urlsplit(self.path).path
            pairing = companion and path=='/api/phone/pair'
            if not pairing and not self.authenticated(): return self.send({'error':'Unauthorized device request'},403)
            # Driving the browser by hand is many small requests, so it has its own, larger allowance.
            driving = path=='/api/browser/drive'
            bucket, allowance = ('pair',10) if pairing else ('drive',900) if driving else ('request',90)
            if not ctx.allowed((bucket, self.client_address[0]), allowance): return self.send({'error':'Too many requests. Wait one minute.'},429)
            if path=='/api/listen':
                # A short recording from Luma's window becomes text, right here on this computer.
                if companion: return self.send({'error':'Talk to Luma on the Mac, or in the Luma phone app.'},403)
                kinds={'audio/webm':'.webm','audio/ogg':'.ogg','audio/wav':'.wav','audio/mp4':'.m4a'}
                kind=self.headers.get('Content-Type','').split(';')[0].strip()
                if kind not in kinds: return self.send({'error':'Send audio.'},415)
                try: size=int(self.headers.get('Content-Length','0') or 0)
                except ValueError: return self.send({'error':'Send the recording again.'},411)
                if not 0<size<=8_000_000: return self.send({'error':'That recording is too long. Keep it under a minute.'},413)
                clip=self.rfile.read(size)
                try:
                    from luma.audio.stt import transcribe_clip
                except ImportError:
                    return self.send({'error':"Luma's ears aren't installed yet. Restart Luma to finish setting up voice."},503)
                try: return self.send({'text':transcribe_clip(clip,kinds[kind])})
                except Exception as error: return self.send({'error':"I couldn't make out that recording. "+str(error)[:160]},500)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.send({'error':'JSON required'},415)
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0<size<=12000: return self.send({'error':'Request exceeds limit'},413)
                data = json.loads(self.rfile.read(size))
                if not isinstance(data,dict): raise ValueError('Expected an object')
                if pairing:
                    result = ctx.pairing.pair(data.get('token'),data.get('name'))
                    return self.send({'paired':True,'device':result['device']},phone_token=result['token'])
                if path.startswith('/api/phone-app/'):
                    if companion or agent.mode=='kids': return self.send({'error':'Connect phones from Luma itself, in adult mode.'},403)
                    if path=='/api/phone-app/pair': result=ctx.phone_app.start_pairing(agent.profile.get('name') or 'Luma')
                    elif path=='/api/phone-app/remove': result=ctx.phone_app.remove(str(data.get('id','')))
                    else: return self.send({'error':'Not found'},404)
                elif path.startswith('/api/phone/'):
                    if companion or agent.mode=='kids': return self.send({'error':'Phone management is available only on the Mac owner controls.'},403)
                    if path=='/api/phone/start': result={'origin':ctx.start_phone(data.get('host'))}
                    elif path=='/api/phone/invite':
                        if not ctx.phone_origin: raise ValueError('Start the home Wi-Fi connection first.')
                        import qrcode
                        from qrcode.image.svg import SvgPathFillImage
                        invite = ctx.pairing.create_invite()
                        url = ctx.phone_origin+'/#pair='+invite['token']
                        svg = qrcode.make(url,image_factory=SvgPathFillImage).to_string()
                        result={'url':url,'expires_at':invite['expires_at'],'qr':'data:image/svg+xml;base64,'+base64.b64encode(svg).decode()}
                    elif path=='/api/phone/revoke': result={'revoked':ctx.pairing.revoke(data.get('id'))}
                    else: return self.send({'error':'Not found'},404)
                elif path=='/api/interrupt': result=agent.interrupt()
                elif path=='/api/speak':
                    if companion: return self.send({'error':'Voice playback is controlled on the Mac.'},403)
                    text=data.get('text')
                    if not isinstance(text,str) or not 1<=len(text.strip())<=2000: raise ValueError('Enter a short voice preview.')
                    from luma.memory.store import reject_payment_secrets
                    reject_payment_secrets(text)
                    ctx.say(text)
                    result={'ok':True,'summary':'Speaking on this Mac. Stop interrupts playback.'}
                elif path=='/api/activity/control':
                    action=data.get('action')
                    if action=='pause': result={'activity':agent.activity.pause()}
                    elif action=='resume': result={'activity':agent.activity.resume()}
                    elif action=='stop': result={'activity':agent.activity.stop()}
                    elif action=='show':
                        if companion: return self.send({'error':'Take over on the Mac.'},403)
                        view=agent.activity.view() or {}
                        agent.activity.pause()
                        agent._check('browser.open')
                        shown=agent.browser.show_for_sign_in(view.get('url') or 'https://www.google.com/')
                        result={'activity':agent.activity.view(),'url':shown.get('url'),'summary':"It's your browser now. I paused; press Resume when you're done."}
                    else: raise ValueError('Choose pause, resume, stop or show.')
                elif path=='/api/chat':
                    from luma.orchestrator import SpeechStream, spoken_reply
                    event=agent.new_turn()
                    # Start talking at the first sentence while the model is still writing.
                    stream=SpeechStream(agent,event,allow_muted=True) if data.get('voice') is True and not companion else None
                    thread=data.get('thread') or 'main'
                    if not isinstance(thread,str): raise ValueError('Choose a chat.')
                    result=agent.chat(data.get('text'),cancel_event=event,on_text=stream.feed if stream else None,thread=thread)
                    if thread!='main': result['thread']=thread
                    ctx.publish(result)
                    if stream and not event.is_set() and not stream.finish(wait=False):
                        ctx.say(spoken_reply(result), event)
                elif path=='/api/workflows/start' or path=='/api/workflows/resume':
                    result=agent.chat(data.get('goal'),agent_mode=True,resume_id=data.get('id') if path.endswith('resume') else None)
                    ctx.publish(result)
                elif path=='/api/workflows/stop': result=agent.workflows.stop(data.get('id'))
                elif path=='/api/confirm': result=agent.confirm(data.get('id'),data.get('token',''))
                elif path=='/api/cancel': result=agent.cancel(data.get('id'))
                elif path=='/api/setting':
                    key,value=data.get('key'),data.get('value')
                    if companion and key!='hush': return self.send({'error':'Change device and integration settings on the Mac.'},403)
                    if key=='mode': agent.set_mode(value); ctx.events.clear()
                    elif key=='muted' and type(value) is bool: agent.set_muted(value)
                    elif key=='hush': agent.hush()
                    elif key=='barge_in' and type(value) is bool: agent.store.set_setting('barge_in',value)
                    elif key=='daily_briefing_enabled' and type(value) is bool: agent.store.set_setting(key,value)
                    elif key in {'learn_from_chat','check_ins','diary_days'}: agent.set_presence(key,value)
                    elif key=='daily_briefing_hour' and type(value) is int and 0<=value<=23: agent.store.set_setting(key,value)
                    elif key in {'web_search','sms','home_assistant','shopping','booking','browser'} and type(value) is bool: agent.enable(key,value)
                    else: raise ValueError('Unsupported setting')
                    result={'ok':True}
                elif path=='/api/timers/start': result=agent.propose('timers.start',data)
                elif path=='/api/timers/control': result=agent.propose('timers.control',data)
                elif path=='/api/recipes/action': result=agent.propose('cooking.step',data)
                elif path=='/api/briefing': result=agent.household.briefing(mode=agent.mode)
                elif path=='/api/task/complete': result=agent.propose('tasks.complete',{'id':str(data.get('id',''))})
                else:
                    if agent.mode=='kids': raise ValueError('Personal and external action controls are unavailable in kids mode.')
                    if path=='/api/profile':
                        if companion: return self.send({'error':'Set the household personality on the Mac.'},403)
                        if set(data)=={'name'}: data={**(agent.store.setting('personality') or {}),'name':data['name']}
                        result={'profile':agent.set_profile(data)}
                    elif path=='/api/photo':
                        # Your picture, shrunk on this computer first. Only a small JPEG is kept.
                        photo=data.get('photo')
                        if photo in (None,''):
                            agent.store.set_setting('owner_photo',''); agent.store.set_setting('owner_photo_at','')
                            result={'photo':''}
                        else:
                            if not isinstance(photo,str) or not photo.startswith('data:image/jpeg;base64,'): raise ValueError('Choose a photo.')
                            raw=base64.b64decode(photo.split(',',1)[1],validate=True)
                            if not raw.startswith(b'\xff\xd8') or len(raw)>9000: raise ValueError('That photo is too big. Try another one.')
                            stamp=str(int(time.time()))
                            agent.store.set_setting('owner_photo',base64.b64encode(raw).decode()); agent.store.set_setting('owner_photo_at',stamp)
                            result={'photo':stamp}
                    elif path=='/api/voice/preferences':
                        if companion: return self.send({'error':'Set the household voice on the Mac.'},403)
                        result={'voice_preferences':agent.set_voice_preferences(data)}
                    elif path=='/api/personality/preset':
                        if companion: return self.send({'error':'Select personality on the Mac.'},403)
                        result={'profile':agent.set_preset(data.get('preset'),data.get('adult_confirmed',False))}
                    elif path=='/api/quiet-hours':
                        if companion: return self.send({'error':'Set quiet hours on the Mac.'},403)
                        result=agent.set_quiet_hours(data.get('start'),data.get('end'))
                    elif path=='/api/household/save': result={'record':agent.household.save_record(**data,mode=agent.mode)}
                    elif path=='/api/household/delete': result={'deleted':agent.household.delete_record(data.get('id'),mode=agent.mode)}
                    elif path=='/api/recipes/save': result={'recipe':agent.household.save_recipe(**data,mode=agent.mode)}
                    elif path=='/api/recipes/delete': result={'deleted':agent.household.delete_recipe(data.get('id'),mode=agent.mode)}
                    elif path=='/api/groceries/save':
                        from luma.integrations.commerce import validate_list
                        ident=data.get('id')
                        existing=agent.store.get('grocery_list',ident) if isinstance(ident,str) else None
                        if ident is not None and not existing: raise ValueError('Choose an existing grocery list to edit.')
                        result={'list':agent.store.put('grocery_list',{**validate_list({k:v for k,v in data.items() if k!='id'}),'created':existing['created'] if existing else agent.clock()},ident),'summary':'Saved locally. You can prepare a family text or create a merchant list later.'}
                    elif path=='/api/groceries/delete': result={'deleted':agent.store.delete('grocery_list',str(data.get('id','')))}
                    elif path=='/api/groceries/family':
                        row=agent.store.get('grocery_list',str(data.get('id','')))
                        if not row: raise ValueError('Save the exact grocery list first.')
                        body='Could you pick up these groceries? ' + ', '.join(f"{i['quantity']} {i['unit']} {i['name']}" for i in row['items']) + '.'
                        if len(body)>1000: raise ValueError('This list is too long for a text; prepare a shorter message.')
                        result=agent.prepare_message(data.get('recipient'),body)
                    elif path=='/api/memory/save':
                        row=agent.store.get('memory',str(data.get('id','')))
                        if not row: raise ValueError('Choose a saved memory.')
                        text=data.get('text')
                        if not isinstance(text,str) or not 1<=len(text.strip())<=2000: raise ValueError('Memory must contain 1–2000 characters.')
                        result={'memory':agent.store.put('memory',{**row,'text':text.strip()},row['id'])}
                    elif path=='/api/memory/delete': result={'deleted':agent.store.delete('memory',str(data.get('id','')))}
                    elif path=='/api/threads/new': result=agent.new_thread(data.get('title'))
                    elif path=='/api/threads/delete': result=agent.delete_thread(str(data.get('id','')))
                    elif path=='/api/shop/compare':
                        query=data.get('query')
                        if not isinstance(query,str) or not 2<=len(query.strip())<=120: raise ValueError('Tell me what to look for.')
                        limit=data.get('max_price')
                        result=agent.chat(f"find me the cheapest {query.strip()}"+(f" under ${int(limit)}" if isinstance(limit,int) and limit>0 else ''))
                        ctx.publish(result)
                    elif path=='/api/shop/add':
                        from luma.skills.shopping import money
                        offer=data.get('offer') or {}
                        if not isinstance(offer,dict): raise ValueError('Pick a product.')
                        price=offer.get('price')
                        price=money(float(price)) if isinstance(price,(int,float)) else str(price or '')
                        result=agent.propose('shop.add_to_cart',{'store':str(offer.get('store','')),'title':str(offer.get('title',''))[:200],'price':price,'url':str(offer.get('url',''))})
                    elif path=='/api/helpers/create':
                        if companion: return self.send({'error':'Set up helpers on the Mac.'},403)
                        params={k:data.get(k) for k in ('query','target','site','goal') if data.get(k) not in (None,'')}
                        result={'helper':agent.helpers.create(str(data.get('kind','')),data.get('title'),params,data.get('every') or 'daily',data.get('at') or None)}
                    elif path=='/api/helpers/update':
                        changes={k:data[k] for k in ('enabled','run_now','every') if k in data}
                        result={'helper':agent.helpers.update(str(data.get('id','')),**changes)}
                    elif path=='/api/helpers/delete': result={'deleted':agent.helpers.delete(str(data.get('id','')))}
                    elif path=='/api/cards/read': result={'card':agent.feed.mark_read(data.get('id'))}
                    elif path=='/api/cards/delete': result={'deleted':agent.feed.delete(data.get('id'))}
                    elif path=='/api/feedback': result=agent.feedback(str(data.get('id','')),data.get('value'),data.get('note'))
                    elif path=='/api/rules':
                        if companion: return self.send({'error':'Change rules on the Mac.'},403)
                        result={'rules':agent.rules.set(str(data.get('id','')),str(data.get('value','')))}
                    elif path.startswith('/api/connect/'):
                        if companion: return self.send({'error':'Connect apps on the Mac.'},403)
                        what=path[len('/api/connect/'):]
                        if what=='mail':
                            servers={k:data.get(k) for k in ('imap_host','smtp_host','smtp_port') if data.get(k)}
                            result={'mail':agent.mail.connect(data.get('address'),data.get('app_password'),**servers)}
                            agent.enable('mail',True)
                        elif what=='calendar':
                            result={'calendar':agent.calendar.connect(data.get('url'))}
                            agent.enable('calendar',True)
                        elif what=='app':
                            result={'app':agent.connectors.add(data.get('name'),url=data.get('url') or '',command=data.get('command') or '',
                                                               token=data.get('token') or '',preset=data.get('preset'),folder=data.get('folder') or '')}
                            agent.enable('connectors',True)
                        elif what=='app_remove':
                            result=agent.connectors.remove(str(data.get('id','')))
                        elif what=='disconnect':
                            service=data.get('service')
                            if service=='mail': result={'mail':agent.mail.disconnect()}; agent.enable('mail',False)
                            elif service=='calendar': result={'calendar':agent.calendar.disconnect()}; agent.enable('calendar',False)
                            else: raise ValueError('Choose mail or calendar.')
                        else: return self.send({'error':'Not found'},404)
                    elif path=='/api/contacts/save': result=agent.contacts.save(data)
                    elif path=='/api/contacts/delete': result={'deleted':agent.contacts.delete(data.get('id'))}
                    elif path in {'/api/browser/drive', '/api/browser/go'}:
                        # The owner driving Luma's browser from Luma's window: Luma steps back while they do.
                        if companion: return self.send({'error':'Drive the browser on the Mac.'},403)
                        agent._check('browser.open')
                        view=agent.activity.view() or {}
                        if view.get('state')=='running': agent.activity.pause()
                        if path.endswith('go'):
                            target=str(data.get('url') or '').strip()
                            if not target: raise ValueError('Type a web address or something to search for.')
                            if ' ' in target or '.' not in target: target='https://duckduckgo.com/?q='+quote_plus(target)
                            page=agent.browser.open(target)
                            result={'url':page.get('url'),'title':page.get('title')}
                        else: result=agent.browser.drive(data.get('kind'),{k:data.get(k) for k in ('x','y','dy','text','key') if k in data})
                        teaching=ctx.recording
                        if teaching is not None:
                            # Teach is on: keep what they did as a step (passwords are never kept).
                            result['steps']=teaching.add('go' if path.endswith('go') else data.get('kind'),data,result)
                    elif path=='/api/browser/teach':
                        if companion or agent.mode=='kids': return self.send({'error':'Teach Luma on the Mac.'},403)
                        from luma.agent.taught import Recorder
                        action=data.get('action')
                        if action=='start':
                            agent._check('browser.open')
                            here=agent.browser.read().get('url') if agent.browser else None
                            if not here or here=='about:blank': raise ValueError('Open the page where the task starts, then press Teach.')
                            ctx.recording=Recorder(here)
                            result={'recording':True,'steps':0,'summary':"I'm watching. Do the task once, then name it and press Save."}
                        elif action=='save':
                            row=agent.taught.save(data.get('name'),ctx.recording); ctx.recording=None
                            result={'taught':{'id':row['id'],'name':row['name'],'steps':len(row['steps'])},'summary':f"Saved. Say “run {row['name']}” any time."}
                        elif action=='cancel': ctx.recording=None; result={'recording':False}
                        else: raise ValueError('Start, save or cancel.')
                    elif path=='/api/taught/delete': result={'deleted':agent.taught.delete(str(data.get('id','')))}
                    elif path=='/api/taught/run':
                        # By id, so two tasks with similar names can't be mixed up.
                        if agent.mode=='kids': return self.send({'error':'Ask a grown-up.'},403)
                        row=agent.store.get('taught',str(data.get('id','')))
                        if not row: raise ValueError('That task is gone.')
                        agent._check('browser.open')
                        with agent.lock: result=agent.taught.run(row)
                    elif path in {'/api/browser/show', '/api/browser/hide'}:
                        if companion: return self.send({'error':"Sign in to sites on the Mac."},403)
                        agent._check('browser.open')
                        result = agent.browser.show_for_sign_in(data.get('url') or 'https://www.instagram.com/') if path.endswith('show') else agent.browser.hide()
                        if path.endswith('show'): result = {'summary': 'Sign in in the Luma browser window, then tap Done signing in.', 'url': result.get('url')}
                    elif path.startswith('/api/texting/'):
                        if companion and path not in {'/api/texting/account','/api/texting/upgrade','/api/texting/numbers'}:
                            return self.send({'error':"Set up Luma's number on the Mac."},403)
                        if path=='/api/texting/start': result=agent.cloud.start_signup(data.get('name'),data.get('phone'))
                        elif path=='/api/texting/finish':
                            result=agent.cloud.finish_signup(data.get('code'),device_name='Luma')
                            agent.set_message_route('luma_number')
                        elif path=='/api/texting/account': result={'account':agent.cloud.account(refresh=True)}
                        elif path=='/api/texting/numbers': result=agent.cloud.number_options(data.get('area_code'))
                        elif path=='/api/texting/upgrade': result={'url':agent.cloud.upgrade_link(data.get('number'))}
                        elif path=='/api/texting/claim': result={'account':agent.cloud.claim_number(data.get('number'))}
                        elif path=='/api/texting/manage': result={'url':agent.cloud.manage_link()}
                        elif path=='/api/texting/signout':
                            result=agent.cloud.sign_out()
                            if agent.message_route=='luma_number': agent.set_message_route('phone_draft')
                        else: return self.send({'error':'Not found'},404)
                    elif path=='/api/messages/route':
                        if companion: return self.send({'error':'Choose the sending account on the Mac.'},403)
                        result=agent.set_message_route(data.get('route'))
                    elif path=='/api/groceries/nearby':
                        agent._check('food.checkout'); result=agent.groceries.nearby(data)
                    elif path=='/api/groceries/create':
                        agent._check('food.checkout'); result=agent.groceries.create_list(data)
                        agent.store.put('grocery_receipt',result,result['local_receipt_id'])
                    elif path=='/api/messages/prepare': result=agent.prepare_message(data.get('recipient'),data.get('body'))
                    elif path=='/api/mail/compose':
                        result=agent.propose('mail.send',{'to':str(data.get('to','')),'subject':str(data.get('subject','')),'body':str(data.get('body','')),'reply_to_id':str(data.get('reply_to_id') or '')})
                        result['text']='Here it is with your changes. Send it?'
                    elif path=='/api/messages/status': result=agent.message_status(data.get('action_id'))
                    elif path=='/api/messages/delete-draft': result={'deleted':agent.store.delete('phone_draft',str(data.get('id','')))}
                    elif path=='/api/booking/availability': result=agent.propose('booking.availability',data)
                    elif path=='/api/booking/prepare': result=agent.propose('booking.create',data)
                    elif path=='/api/booking/status':
                        agent._check('booking.create'); result=agent.bookings.status(data)
                    else: return self.send({'error':'Not found'},404)
                if result.get('state')=='pending' and not result.get('event_id'): ctx.publish(result)
                return self.send(result)
            except (ValueError,TypeError,KeyError) as e: return self.send({'error':str(e)},400)
            except RuntimeError as e: return self.send({'error':str(e)},502)
            except Exception: return self.send({'error':'The operation could not be confirmed. Check the device terminal; no success was assumed.'},500)

    server=ThreadingHTTPServer((phone_host or '127.0.0.1',port),Handler)
    server.daemon_threads=True
    server.agent_stop=ctx.stop
    server.control_context=ctx
    if root_context:
        ctx.phone_app.start()
        try: agent.helpers.ensure_system()
        except Exception: pass
        def clock_loop():
            while not ctx.stop.wait(1):
                try:
                    event=agent.tick()
                    if event:
                        ctx.events.append(event)
                        threading.Thread(target=ctx.phone_app.notify,args=(event,),daemon=True).start()
                        if not agent.muted and not event.get('silent'):
                            from luma.orchestrator import speak
                            speak(event['text'],agent)
                except Exception: pass
        threading.Thread(target=clock_loop,daemon=True).start()
    return server


def serve(agent,port,phone_host=None,phone_port=8096):
    server=make_server(agent,port)
    ctx=server.control_context
    if phone_host: ctx.start_phone(phone_host,phone_port)
    print(f'LUMA local control: http://127.0.0.1:{server.server_port}/',flush=True)
    if ctx.phone_origin: print('LUMA phone connection: '+ctx.phone_origin,flush=True)
    def hands_free():
        try:
            from luma.orchestrator import start_hands_free
            start_hands_free(agent,server.agent_stop)
        except ImportError as error:
            # The desktop app installs Luma without voice; typing still works.
            print(f'LUMA voice is off ({error.name or error} is not installed). Install the voice extras to talk out loud.',flush=True)
    threading.Thread(target=hands_free,daemon=True).start()
    def ears():
        # The desktop app gets Luma's speech model ready in the background, so the mic is quick the first time.
        try:
            from luma.audio.stt import warm_up
            warm_up()
        except ImportError:
            pass
    if os.environ.get('LUMA_WHISPER_DOWNLOAD')=='1': threading.Thread(target=ears,daemon=True,name='luma-ears').start()
    import signal
    previous_signals = {}
    def stop_on_signal(signum, frame):
        ctx.stop.set(); agent.interrupt()
        threading.Thread(target=server.shutdown, daemon=True).start()
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_signals[signum] = signal.signal(signum, stop_on_signal)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        ctx.stop.set(); agent.set_muted(True); ctx.phone_app.stop()
        if ctx.phone_server: ctx.phone_server.shutdown(); ctx.phone_server.server_close()
        for signum, previous in previous_signals.items(): signal.signal(signum, previous)
        agent.interrupt(); agent.device.close()
        server.server_close(); agent.store.close()
