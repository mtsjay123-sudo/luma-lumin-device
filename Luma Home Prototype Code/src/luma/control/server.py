from __future__ import annotations
import json,secrets,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).parent/'web'

def make_server(agent,port=8095):
    events=[]
    def on_result(result):
        events.append({"created":time.time(),"result":result})
        if len(events)>30:events.pop(0)
    agent.on_result=on_result
    session=secrets.token_urlsafe(32);stop=threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass # Do not log memory, messages, tokens or contact information.
        def valid_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        def authenticated(self):
            c=SimpleCookie()
            try:c.load(self.headers.get('Cookie',''))
            except Exception:return False
            token=c.get('luma_owner')
            return bool(token and secrets.compare_digest(token.value,session))
        def send(self,data,status=200,kind='application/json',cookie=False):
            encoded=(json.dumps(data,ensure_ascii=False).encode() if kind=='application/json' else data)
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(encoded)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            if cookie:self.send_header('Set-Cookie',f'luma_owner={session}; HttpOnly; SameSite=Strict; Path=/')
            self.end_headers();self.wfile.write(encoded)
        def do_GET(self):
            if not self.valid_host():return self.send({'error':'Invalid local host'},403)
            path=urlsplit(self.path).path
            if path in {'/','/app.js','/style.css'}:
                f=ROOT/('index.html' if path=='/' else path[1:]);kind={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[path]
                return self.send(f.read_bytes(),kind=kind,cookie=path=='/')
            if not self.authenticated():return self.send({'error':'Open the local control page first.'},401)
            if path=='/api/state':
                # Approval hashes and one-time confirmation tokens never appear in history.
                actions=[{k:v for k,v in r.items() if k!='approval_hash'} for r in agent.store.all('action',30)]
                return self.send({'status':agent.status(),'memories':[] if agent.mode=='kids' else agent.store.all('memory',40),'tasks':agent._run('tasks.list',{})['tasks'],'routines':[r for r in agent.store.all('routine') if r.get('mode','friend')==agent.mode],'actions':[] if agent.mode=='kids' else actions,'events':events[-20:]})
            return self.send({'error':'Not found'},404)
        def do_POST(self):
            if not self.valid_host() or not self.authenticated():return self.send({'error':'Unauthorized local request'},403)
            origin=self.headers.get('Origin')
            if origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:return self.send({'error':'Local origin required'},403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send({'error':'JSON required'},415)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=12000:return self.send({'error':'Request exceeds limit'},413)
                data=json.loads(self.rfile.read(size));path=urlsplit(self.path).path
                if not isinstance(data,dict):raise ValueError('Expected an object')
                if path=='/api/chat':result=agent.chat(data.get('text'))
                elif path=='/api/confirm':result=agent.confirm(data.get('id'),data.get('token',''))
                elif path=='/api/cancel':result=agent.cancel(data.get('id'))
                elif path=='/api/setting':
                    key=data.get('key');value=data.get('value')
                    if key=='mode':
                        agent.set_mode(value);events.clear()
                    elif key=='muted' and type(value) is bool:agent.set_muted(value)
                    elif key=='hush':agent.hush()
                    elif key in {'web_search','sms','home_assistant','shopping'} and type(value) is bool:agent.enable(key,value)
                    else:raise ValueError('Unsupported setting')
                    result={'ok':True}
                elif path=='/api/memory/delete':
                    if agent.mode=='kids':raise ValueError('Memory controls are not available in kids mode')
                    result={'deleted':agent.store.delete('memory',str(data.get('id','')))}
                elif path=='/api/task/complete':result=agent.propose('tasks.complete',{'id':str(data.get('id',''))})
                else:return self.send({'error':'Not found'},404)
                return self.send(result)
            except (ValueError,TypeError,KeyError) as e:return self.send({'error':str(e)},400)
            except Exception:return self.send({'error':'The local operation failed. Check the runtime terminal; no success was confirmed.'},500)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True;server.agent_stop=stop
    def clock_loop():
        while not stop.wait(1):
            try:
                event=agent.tick()
                if event:
                    events.append(event)
                    if len(events)>30:events.pop(0)
                    if not agent.muted:
                        from luma.orchestrator import speak
                        speak(event['text'],agent)
            except Exception:pass
    threading.Thread(target=clock_loop,daemon=True).start()
    return server

def serve(agent,port):
    server=make_server(agent,port)
    print(f'LUMA local control: http://127.0.0.1:{server.server_port}/',flush=True)
    # Listening remains muted until the owner explicitly enables it in the UI.
    from luma.orchestrator import start_hands_free
    threading.Thread(target=start_hands_free,args=(agent,server.agent_stop),daemon=True).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.agent_stop.set();agent.set_muted(True);server.server_close();agent.store.close()
