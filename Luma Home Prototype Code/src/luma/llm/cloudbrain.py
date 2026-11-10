"""One interface for every cloud brain.

Claude on the owner's own key, Claude through Luma Cloud (Luma Plus), Kimi, and later Luma's own cloud model all look the
same from the rest of Luma: stream(messages, tools) gives events as the answer comes, plan() gives the finished answer,
and `abilities` says what that brain can do. Nothing else has to know which one is answering, and a new brain is one
more class here.

Whichever brain it is, it only thinks. What it asks for comes back to this computer as a proposal in Luma's own answer
shape, and the home checks it and runs it with the home's approvals."""
from __future__ import annotations

import queue
import threading
from dataclasses import asdict, dataclass


class CantDoThat(ValueError):
    """This brain doesn't have that ability (see its abilities)."""


@dataclass(frozen=True)
class Abilities:
    context: int | None      # tokens it can read at once; None when that isn't published where Luma could check it
    window: int              # messages of the conversation Luma sends it
    caching: bool            # what it has already read is read again for a fraction of the price (measured: the cloud lab)
    streams: bool            # its words come as it writes them; False: all at once, when it's done
    tools: str               # how it asks for a tool. "shape": in Luma's own answer shape, read and checked at home
    thinking: tuple          # the efforts Luma asks it for, lightest first; empty: it thinks one way
    sees: bool               # it can look at a photo
    retry_on_decline: bool   # when a safety check declines, the service tries another model by itself


class CloudBrain:
    """One cloud brain: where it's reached (`via`: "own", the owner's key; "plus", through Luma Cloud), its model, and
    what it can do."""
    via = "own"
    abilities: Abilities

    def __init__(self, key, model, via="own"):
        self.key, self.model, self.via = key, model, via

    @property
    def label(self):
        return self.model

    def plan(self, messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, effort=None):
        """One turn: a reply, or one tool it asks the home to run. The words go to on_text as they come."""
        raise NotImplementedError

    def rewrite(self, prompt, max_tokens=300):
        raise NotImplementedError

    def look(self, image_bytes, question=None):
        raise CantDoThat("This brain can't look at pictures.")

    def warm(self, memories, mode, profile=None, effort=None):
        """Have it read Luma's instructions and the life file before the first word. None where that buys nothing."""
        return None

    def numbers(self):
        """What the last call on this thread really used (tokens, how many came from its cache, time to the first words)."""
        return None

    def stream(self, messages, tools, memories=(), mode="friend", profile=None, effort=None, cancel_event=None):
        """The turn as events, in order: {"type": "words", "text"} as the reply is written, then {"type": "numbers", ...}
        if the brain reports them, then {"type": "proposal", "proposal"}. What goes wrong in the brain is raised here."""
        events = queue.Queue()

        def run():
            try:
                proposal = self.plan(list(messages), list(memories), tools, mode, profile=profile, cancel_event=cancel_event,
                                     on_text=lambda chunk: events.put({"type": "words", "text": chunk}), effort=effort)
                used = self.numbers()  # noted on this thread, by the call that just finished
                if used:
                    events.put({"type": "numbers", **used})
                events.put({"type": "proposal", "proposal": proposal})
            except BaseException as error:  # handed to whoever is reading the stream
                events.put(error)
            finally:
                events.put(None)
        threading.Thread(target=run, daemon=True, name="luma-cloud-stream").start()
        while True:
            event = events.get()
            if event is None:
                return
            if isinstance(event, BaseException):
                raise event
            yield event


class Claude(CloudBrain):
    """Claude, on the owner's own Anthropic key or through Luma Cloud (luma.llm.cloud does the asking either way)."""

    def __init__(self, key, model, via="own"):
        super().__init__(key, model, via)
        from luma.llm import cloud
        self.abilities = Abilities(
            context=1_000_000, window=cloud.WINDOW, caching=True, streams=True, tools="shape", thinking=("low", "medium", "high"), sees=True,
            # Through Luma Cloud a decline comes home and the home's brain answers: that retry isn't on Anthropic's list of
            # what zero data retention covers, so the relay leaves it off until whoever runs it has confirmed it.
            retry_on_decline=via == "own" and model not in cloud.NO_SERVER_FALLBACK)

    @property
    def label(self):
        from luma.llm import cloud
        return cloud.MODELS.get(self.model, self.model)

    def plan(self, messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, effort=None):
        from luma.llm import cloud
        more = {"effort": effort} if effort else {}
        return cloud.plan(self.key, messages, memories, tools, mode, profile=profile, cancel_event=cancel_event, on_text=on_text, model=self.model, **more)

    def rewrite(self, prompt, max_tokens=300):
        from luma.llm import cloud
        return cloud.rewrite(self.key, prompt, max_tokens=max_tokens, model=self.model)

    def look(self, image_bytes, question=None):
        from luma.llm import cloud
        return cloud.look(self.key, image_bytes, question, model=self.model)

    def warm(self, memories, mode, profile=None, effort=None):
        from luma.llm import cloud
        return cloud.warm(self.key, memories, mode, profile, model=self.model, effort=effort)

    def numbers(self):
        from luma.llm import cloud
        return cloud.last_turn()


class Kimi(CloudBrain):
    """Kimi K3.1 Pro on the owner's own Moonshot key (luma.llm.kimi)."""

    def __init__(self, key, model, via="own"):
        super().__init__(key, model, "own")
        self.abilities = Abilities(context=None, window=40, caching=False, streams=False, tools="shape", thinking=(), sees=False, retry_on_decline=False)

    @property
    def label(self):
        from luma.llm import kimi
        return kimi.MODELS.get(self.model, self.model)

    def plan(self, messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, effort=None):
        from luma.llm import kimi
        return kimi.plan(self.key, messages, memories, tools, mode, profile=profile, cancel_event=cancel_event, on_text=on_text, model=self.model)

    def rewrite(self, prompt, max_tokens=300):
        from luma.llm import kimi
        return kimi.rewrite(self.key, prompt, max_tokens=max_tokens, model=self.model)


def pick(via, model, key):
    """The brain for a turn: `via` "plus" (through Luma Cloud) or "own" (the owner's key), and the model it runs on."""
    from luma.llm import kimi
    if model in kimi.MODELS and via == "own":
        return Kimi(key, model)
    return Claude(key, model, via)


def catalog():
    """Every cloud brain Luma can be pointed at, and what each can do. Plus offers only the brains that keep nothing."""
    from luma.llm import cloud, kimi
    rows = []
    for via, models in (("own", [*cloud.MODELS, *kimi.MODELS]), ("plus", list(cloud.MODELS))):
        for model in models:
            chosen = pick(via, model, "")
            rows.append({"name": model, "label": chosen.label, "via": via, "abilities": asdict(chosen.abilities)})
    return rows
