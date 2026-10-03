"""Speak while the model is still writing.

The local model answers in constrained JSON ({"type": "reply", "text": "..."}), so
the words of a reply arrive inside a JSON string. This pulls them out as they
stream so the first sentence can be spoken before the rest exists. Tool
proposals never stream: only a reply's text is emitted.
"""
from __future__ import annotations

import re

_ESCAPES = {"n": "\n", "t": " ", "r": "", "b": "", "f": "", '"': '"', "\\": "\\", "/": "/"}


class ReplyTextStream:
    def __init__(self, emit):
        self.emit = emit
        self.head = ""
        self.pending = ""
        self.state = "seek"  # seek -> text -> done

    def feed(self, chunk):
        if self.state == "done" or not chunk:
            return
        if self.state == "seek":
            self.head += chunk
            if re.search(r'"type"\s*:\s*"tool"', self.head):
                self.state = "done"
                return
            match = re.search(r'"text"\s*:\s*"', self.head)
            if not match:
                return
            if not re.search(r'"type"\s*:\s*"reply"', self.head[:match.start()]):
                self.state = "done"  # unexpected order: don't guess, let the caller speak the final text
                return
            self.state = "text"
            chunk = self.head[match.end():]
            self.head = ""
        self._decode(chunk)

    def _decode(self, data):
        data, self.pending = self.pending + data, ""
        out, i = [], 0
        while i < len(data):
            char = data[i]
            if char == "\\":
                if i + 1 >= len(data):
                    self.pending = data[i:]
                    break
                code = data[i + 1]
                if code == "u":
                    if i + 6 > len(data):
                        self.pending = data[i:]
                        break
                    try:
                        value = int(data[i + 2:i + 6], 16)
                    except ValueError:
                        value = 0x20
                    if not 0xD800 <= value <= 0xDFFF:  # emoji halves aren't spoken anyway
                        out.append(chr(value))
                    i += 6
                    continue
                out.append(_ESCAPES.get(code, code))
                i += 2
                continue
            if char == '"':
                self.state = "done"
                break
            out.append(char)
            i += 1
        if out:
            self.emit("".join(out))


SENTENCE_END = re.compile(r'[.!?…]+["”’)\]]*(?:\s+|$)')


class SentenceBuffer:
    """Collects streamed text and hands back whole sentences, the first one as early as possible."""

    def __init__(self, first_min=8, min_chars=40):
        self.text = ""
        self.first = True
        self.first_min, self.min_chars = first_min, min_chars

    def feed(self, delta):
        self.text += delta
        ready = []
        while True:
            need = self.first_min if self.first else self.min_chars
            cut = None
            for match in SENTENCE_END.finditer(self.text):
                if match.end() >= need and match.end() < len(self.text):
                    cut = match.end()
                    break
            if cut is None:
                break
            phrase, self.text = self.text[:cut].strip(), self.text[cut:]
            if phrase:
                ready.append(phrase)
                self.first = False
        return ready

    def flush(self):
        phrase, self.text = self.text.strip(), ""
        return [phrase] if phrase else []
