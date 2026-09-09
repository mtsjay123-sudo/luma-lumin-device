"""Local owner controls and an opt-in, paired HTTPS phone companion."""
from __future__ import annotations
import base64
import json
import secrets
import ssl
import subprocess
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit
from luma.control.pairing import PairingManager, ensure_local_certificate, private_ipv4

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
            for k, v in {'Content-Type':kind, 'Content-Length':str(len(encoded)), 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer', 'X-Frame-Options':'DENY', 'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items(): self.send_header(k,v)
            if owner_cookie: self.send_header('Set-Cookie',f'luma_owner={ctx.owner_session}; HttpOnly; SameSite=Strict; Path=/')
            if phone_token: self.send_header('Set-Cookie',f'luma_phone={phone_token}; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000; Path=/')
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            if not self.valid_host(): return self.send({'error':'Invalid device host'},403)
            path = urlsplit(self.path).path
            static = {'/':('index.html','text/html'), '/app.js':('app.js','text/javascript'), '/companion.js':('companion.js','text/javascript'), '/style.css':('style.css','text/css')}
            if path in static:
                file, kind = static[path]
                return self.send((ROOT/file).read_bytes(),kind=kind+'; charset=utf-8',owner_cookie=path=='/' and not companion)
            if path=='/api/session': return self.send({'viewer':'phone' if companion else 'owner', 'paired':self.authenticated()})
            if not self.authenticated(): return self.send({'error':'Pair this phone from the Mac, or reopen the local owner controls.'},401)
            if path=='/api/state':
                adult = agent.mode!='kids'
                actions = [{k:v for k,v in r.items() if k!='approval_hash'} for r in agent.store.all('action',30)] if adult else []
                return self.send({'viewer':'phone' if companion else 'owner', 'status':agent.status(), 'household':{'timers':agent.household.timers(mode=agent.mode),'records':agent.household.records(mode=agent.mode),'recipes':agent.household.recipes(mode=agent.mode),'briefing':agent.household.briefing(mode=agent.mode)}, 'workflows':agent.workflows.list() if adult else [], 'local_grocery_lists':agent.store.all('grocery_list',20) if adult else [], 'memories':agent.store.all('memory',40) if adult else [], 'contacts':agent.contacts.list() if adult else [], 'message_drafts':agent.store.all('phone_draft',20) if adult else [], 'sms_receipts':agent.store.all('sms_receipt',30) if adult else [], 'grocery_receipts':agent.store.all('grocery_receipt',15) if adult else [], 'tasks':agent._run('tasks.list',{})['tasks'], 'routines':[r for r in agent.store.all('routine') if r.get('mode','friend')==agent.mode], 'actions':actions, 'events':list(ctx.events)[-20:] if adult else [], 'booking_services':agent.bookings.services() if adult else [], 'phone':{'origin':ctx.phone_origin, 'addresses':lan_addresses() if not companion and not ctx.phone_origin else [], 'devices':ctx.pairing.list_devices() if not companion and adult else []}})
            return self.send({'error':'Not found'},404)

        def do_POST(self):
            if not self.valid_host() or not self.valid_origin(): return self.send({'error':'Device origin required'},403)
            path = urlsplit(self.path).path
            pairing = companion and path=='/api/phone/pair'
            if not pairing and not self.authenticated(): return self.send({'error':'Unauthorized device request'},403)
            if not ctx.allowed(('pair' if pairing else 'request', self.client_address[0]), 10 if pairing else 90): return self.send({'error':'Too many requests. Wait one minute.'},429)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.send({'error':'JSON required'},415)
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0<size<=12000: return self.send({'error':'Request exceeds limit'},413)
                data = json.loads(self.rfile.read(size))
                if not isinstance(data,dict): raise ValueError('Expected an object')
                if pairing:
                    result = ctx.pairing.pair(data.get('token'),data.get('name'))
                    return self.send({'paired':True,'device':result['device']},phone_token=result['token'])
                if path.startswith('/api/phone/'):
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
                elif path=='/api/chat':
                    event=agent.new_turn()
                    result=agent.chat(data.get('text'),cancel_event=event)
                    ctx.publish(result)
                    if data.get('voice') is True and not companion and not event.is_set():
                        spoken='Please review the exact details in the action card.' if result.get('state')=='pending' else result.get('text') or result.get('summary') or 'Your result is ready in Luma.'
                        ctx.say(spoken, event)
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
                    elif key=='daily_briefing_hour' and type(value) is int and 0<=value<=23: agent.store.set_setting(key,value)
                    elif key in {'web_search','sms','home_assistant','shopping','booking'} and type(value) is bool: agent.enable(key,value)
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
                        result={'profile':agent.set_profile(data)}
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
                    elif path=='/api/contacts/save': result=agent.contacts.save(data)
                    elif path=='/api/contacts/delete': result={'deleted':agent.contacts.delete(data.get('id'))}
                    elif path=='/api/messages/route':
                        if companion: return self.send({'error':'Choose the sending account on the Mac.'},403)
                        result=agent.set_message_route(data.get('route'))
                    elif path=='/api/groceries/nearby':
                        agent._check('food.checkout'); result=agent.groceries.nearby(data)
                    elif path=='/api/groceries/create':
                        agent._check('food.checkout'); result=agent.groceries.create_list(data)
                        agent.store.put('grocery_receipt',result,result['local_receipt_id'])
                    elif path=='/api/messages/prepare': result=agent.prepare_message(data.get('recipient'),data.get('body'))
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
        def clock_loop():
            while not ctx.stop.wait(1):
                try:
                    event=agent.tick()
                    if event:
                        ctx.events.append(event)
                        if not agent.muted:
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
    from luma.orchestrator import start_hands_free
    threading.Thread(target=start_hands_free,args=(agent,server.agent_stop),daemon=True).start()
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
        ctx.stop.set(); agent.set_muted(True)
        if ctx.phone_server: ctx.phone_server.shutdown(); ctx.phone_server.server_close()
        for signum, previous in previous_signals.items(): signal.signal(signum, previous)
        agent.interrupt(); agent.device.close()
        server.server_close(); agent.store.close()
