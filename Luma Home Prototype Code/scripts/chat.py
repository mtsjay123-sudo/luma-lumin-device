#!/usr/bin/env python3
"""
Type-to-hear chat with LUMA.
Type a message, press Enter — LUMA thinks and speaks back.
Type 'quit' or press Ctrl+C to exit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from luma.orchestrator import ask_typed, reset


def main():
    print("LUMA chat — type a message and press Enter. Type 'quit' to exit.\n")
    reset()
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "bye"}:
            print("LUMA: take care!")
            break
        reply = ask_typed(user_input)
        print(f"LUMA: {reply}\n")


if __name__ == "__main__":
    main()
