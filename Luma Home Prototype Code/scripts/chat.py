#!/usr/bin/env python3
"""
Chat with LUMA.
  Default:       type a message, press Enter.
  --voice:       hold SPACEBAR to speak, release to send.
  --hands-free:  just talk — VAD detects speech automatically.
Press Ctrl+C to exit.
"""
import sys
import argparse
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from luma.orchestrator import ask_typed, ask_voice, ask_voice_hands_free, reset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", action="store_true", help="Push-to-talk mic input")
    parser.add_argument("--hands-free", action="store_true", help="Fully hands-free via VAD")
    args = parser.parse_args()

    if args.hands_free:
        mode = "hands-free (just talk)"
    elif args.voice:
        mode = "voice (hold SPACEBAR to speak)"
    else:
        mode = "text"

    print(f"LUMA chat [{mode}] — press Ctrl+C to exit.\n")
    reset()

    try:
        if args.hands_free:
            stop = threading.Event()
            ask_voice_hands_free(stop_event=stop)
        else:
            while True:
                if args.voice:
                    reply = ask_voice()
                    if reply:
                        print(f"LUMA: {reply}\n")
                else:
                    user_input = input("You: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in {"quit", "exit", "bye"}:
                        print("LUMA: take care!")
                        break
                    reply = ask_typed(user_input)
                    print(f"LUMA: {reply}\n")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
