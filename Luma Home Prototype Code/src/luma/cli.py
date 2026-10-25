"""Local CLI for LUMA's conversation, durable tools and device control surface."""
from __future__ import annotations
import argparse, json, os, threading
from pathlib import Path
from dotenv import load_dotenv

def main():
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    parser=argparse.ArgumentParser(prog='luma')
    parser.add_argument('--no-model',action='store_true',help='Use local task/memory tools without loading the LLM')
    parser.add_argument('--voice',action='store_true',help='Opt into push-to-talk microphone input')
    parser.add_argument('--hands-free',action='store_true',help='Opt into local voice detection with name/follow-up gating')
    parser.add_argument('--ambient',action='store_true',help='Experimental command-content address detection')
    parser.add_argument('command',nargs='?',default='chat',choices=['chat','serve','status','ask','work','projects','project','resume','stop','approve','usage'])
    parser.add_argument('message',nargs='*',help='For work: what to make (quotes optional). For project/resume/stop/approve: the project name or id.')
    parser.add_argument('--device',action='store_true',help='Run the work on your paired Luma device (over Luma Link)')
    parser.add_argument('--yes','-y',action='store_true',help='Allow risky steps (like running code) without asking')
    parser.add_argument('--project',help='Add the work to this existing project (name or id)')
    parser.add_argument('--port',type=int,default=8095)
    parser.add_argument('--phone-host',help='Optional private Wi-Fi IPv4 for the HTTPS phone companion')
    parser.add_argument('--phone-port',type=int,default=8096)
    args=parser.parse_args()
    args.message=' '.join(args.message).strip() or None
    if args.command in {'work','projects','project','resume','stop','approve','usage'}: return work(args, parser)
    # Serving: the model thinks in a process of its own, so if it ever crashes, Luma doesn't.
    if args.command=='serve': os.environ.setdefault('LUMA_BRAIN_WORKER','1')
    from luma.agent.runtime import Agent
    agent=Agent(use_model=not args.no_model)
    if args.command=='serve':
        from luma.control.server import serve
        serve(agent,args.port,args.phone_host,args.phone_port);return
    if args.command=='status':print(json.dumps(agent.status(),indent=2));return
    if args.command=='ask':
        if not args.message:parser.error('ask requires a quoted message')
        print(json.dumps(agent.chat(args.message),indent=2));return
    from luma.orchestrator import ask_typed,ask_voice,start_hands_free
    stopped=threading.Event()
    def reminders():
        while not stopped.wait(1):
            result=agent.tick()
            if result:print('\nLUMA: '+result['text'],flush=True)
    threading.Thread(target=reminders,daemon=True).start()
    if args.voice or args.hands_free:agent.set_muted(False)
    if args.hands_free:threading.Thread(target=start_hands_free,args=(agent,stopped,args.ambient),daemon=True).start()
    print('LUMA local agent. /help for owner controls. /quit to exit. Microphone '+('enabled' if not agent.muted else 'muted')+'.')
    try:
        while True:
            if args.voice:ask_voice(agent);continue
            line=input('You: ').strip()
            if not line:continue
            try:
                bits=line.split()
                if line=='/quit':break
                elif line=='/help':print('/status · /mode friend|study|cofounder|kids · /enable web_search|sms|home_assistant|shopping|booking · /disable SERVICE · /confirm ACTION TOKEN · /cancel ACTION · /mute · /unmute · /hush · /quit')
                elif line=='/status':print(json.dumps(agent.status(),indent=2))
                elif bits[0]=='/mode' and len(bits)==2:agent.set_mode(bits[1])
                elif bits[0] in {'/enable','/disable'} and len(bits)==2:agent.enable(bits[1],bits[0]=='/enable')
                elif bits[0]=='/confirm' and len(bits)==3:print(json.dumps(agent.confirm(bits[1],bits[2]),indent=2))
                elif bits[0]=='/cancel' and len(bits)==2:print(json.dumps(agent.cancel(bits[1]),indent=2))
                elif line in {'/mute','/unmute'}:agent.set_muted(line=='/mute')
                elif line=='/hush':agent.hush()
                elif line.startswith('/'):print('Unknown control. Use /help.')
                else:ask_typed(line,agent,voice=args.hands_free)
            except (ValueError,RuntimeError) as e:print('LUMA: '+str(e))
    except (EOFError,KeyboardInterrupt):pass
    finally:stopped.set();agent.set_muted(True);agent.store.close()

def work(args, parser):
    """Projects from the terminal: plan, build, check and deliver, on this computer or your Luma device."""
    from luma.work import terminal
    try:
        if args.command == 'usage': return usage(args, terminal)
        target = terminal.pick(on_device=args.device, assume_yes=args.yes, use_model=not args.no_model)
        if args.command == 'work':
            if not args.message: parser.error('work needs what to make, like: luma work "research my idea and make a 10-slide deck"')
            kwargs = {'assume_yes': args.yes} if isinstance(target, terminal.Remote) else {}
            run = target.work(args.message, project=args.project, **kwargs)
            raise SystemExit(0 if run.get('state') == 'done' else 1)
        if args.command == 'projects': return terminal.show_projects(target)
        if not args.message and args.command != 'usage': parser.error(f'{args.command} needs a project name or id')
        if args.command == 'project': return terminal.show_project(target, args.message)
        if args.command == 'resume':
            kwargs = {'assume_yes': args.yes} if isinstance(target, terminal.Remote) else {}
            run = target.work(args.message, resume=True, **kwargs)
            raise SystemExit(0 if run.get('state') == 'done' else 1)
        if args.command == 'stop': return print(json.dumps(target.stop(args.message)))
        if args.command == 'approve': return print(json.dumps(target.approve(args.message)))
    except ValueError as error:
        print('LUMA: ' + str(error)); raise SystemExit(2)

def usage(args, terminal):
    """Model calls, tokens and time over the last 30 days, without loading a model to find out."""
    remote = terminal.device() if args.device else terminal.app_on_this_computer()
    if remote:
        summary = remote._get('usage', {})
    else:
        from luma.llm import usage as counted
        from luma.memory.store import Store
        from luma.config import STATE_DB_PATH, STATE_KEY_PATH
        store = Store(STATE_DB_PATH, STATE_KEY_PATH)
        try: summary = counted.summary(store)
        finally: store.close()
    if not summary['models']: return print('No model calls counted yet.')
    for model, row in summary['models'].items():
        cost = f"  ${row['cost']:.2f}" if row.get('cost') is not None else ''
        print(f"{model:<36} {row['calls']:>6} calls  {row['tokens_in'] + row['tokens_out']:>10,} tokens  {row['seconds']:>8.0f}s  {row['errors']} errors{cost}")

if __name__=='__main__':main()
