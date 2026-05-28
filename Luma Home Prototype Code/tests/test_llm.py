"""Day 2 smoke test — verify LLM loads and returns a LUMA-flavored reply."""
import time
from luma.llm.inference import generate


def test_basic_reply():
    messages = [{"role": "user", "content": "Hello, who are you?"}]

    start = time.time()
    reply = generate(messages)
    elapsed = time.time() - start

    print(f"\nLUMA replied ({elapsed:.1f}s):\n{reply}\n")
    assert isinstance(reply, str)
    assert len(reply) > 10, "Reply too short — check model load"
    assert elapsed < 30, f"Response took {elapsed:.1f}s — too slow"


if __name__ == "__main__":
    test_basic_reply()
