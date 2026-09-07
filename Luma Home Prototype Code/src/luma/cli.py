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
    parser.add_argument('command',nargs='?',default='chat',choices=['chat','serve','status','ask'])
    parser.add_argument('message',nargs='?')
    parser.add_argument('--port',type=int,default=8095)
    args=parser.parse_args()
    from luma.agent.runtime import Agent
    agent=Agent(use_model=not args.no_model)
    if args.command=='serve':
        from luma.control.server import serve
        serve(agent,args.port);return
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
                elif line=='/help':print('/status · /mode friend|study|cofounder|kids · /enable web_search|sms|home_assistant|shopping · /disable SERVICE · /confirm ACTION TOKEN · /cancel ACTION · /mute · /unmute · /hush · /quit')
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

if __name__=='__main__':main()
