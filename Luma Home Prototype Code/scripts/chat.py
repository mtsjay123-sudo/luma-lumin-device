#!/usr/bin/env python3
"""
Chat with LUMA.
  Default:     type a message, press Enter.
  --voice:     hold SPACEBAR to speak, release to send.
Type 'quit' or press Ctrl+C to exit.
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from luma.orchestrator import ask_typed, ask_voice, reset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", action="store_true", help="Push-to-talk mic input")
    args = parser.parse_args()

    mode = "voice (hold SPACEBAR to speak)" if args.voice else "text"
    print(f"LUMA chat [{mode}] — type 'quit' to exit.\n")
    reset()

    while True:
        try:
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
            break


if __name__ == "__main__":
    main()
