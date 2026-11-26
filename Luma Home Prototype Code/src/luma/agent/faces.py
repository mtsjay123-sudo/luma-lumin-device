"""Knowing its people by sight (docs/PRESENCE_MASTER_PROMPT.md, 9.2): the frame, with no model in it.

"In order for the person to confirm who they are, they must access their camera and Luma scans to see them" (the
owner, Nov 25). This is everything around the model that reads a face: introducing someone, keeping what's kept,
deciding whether a face seen is one of the home's people, and unlocking the room (luma.agent.who) when it is.

What isn't here is the model itself. One has to be chosen with its license read (MIT, Apache-2.0 or BSD), and its
numbers have to be set on real people who've agreed: the right person let in 98 times in 100 at three distances and
in evening light; a stranger, a photo of the owner and a video on a phone let in 0 times in 100. Until then nothing
is installed (`use()` was never called), so Luma can't know anyone by sight and the passcode is the way in.

What the frame guarantees whatever model is put in:

- Off until the owner switches it on (`know_faces`), and nobody is introduced except from the app.
- What's kept is a set of numbers for each person, sealed with everything else. Never a picture.
- A face is theirs only when it's close to theirs, clearly closer than to anyone else's, and the model says it's a
  live person in the room. Anything less is "someone I haven't met": Luma never puts a name to a stranger.
- "Forget me" deletes it, and so does forgetting everything.
"""
from __future__ import annotations

import math

SETTING = "know_faces"
KIND = "face"
ENOUGH = 5            # looks from a few angles before someone is known
CLOSE = 0.80          # how alike a face seen and a face kept must be (cosine). A placeholder until measured on real people
CLEAR = 0.08          # and how much closer than to anyone else in the home
LOOKS = 3             # looks in a row that must agree before the room is unlocked

_reader = {"model": None}


def use(model):
    """Install the model that reads a face. It needs two methods: embed(frame) gives a list of numbers for the one
    face clearly in view (or None), and live(frames) says whether these looks are of a live person in the room,
    not a photo or a screen. Its license is the installer's to have read first."""
    if model is not None and not (callable(getattr(model, "embed", None)) and callable(getattr(model, "live", None))):
        raise ValueError("A face model needs embed(frame) and live(frames).")
    _reader["model"] = model


def ready(agent):
    """Luma can know someone by sight right now: a model is installed and the owner switched it on."""
    return _reader["model"] is not None and agent.store.setting(SETTING, False) is True and agent.mode != "kids"


def _unit(vector):
    values = [float(v) for v in vector]
    size = math.sqrt(sum(v * v for v in values))
    if not values or size == 0 or any(math.isnan(v) or math.isinf(v) for v in values):
        return None
    return [v / size for v in values]


def _alike(a, b):
    return sum(x * y for x, y in zip(a, b)) if len(a) == len(b) else -1.0


def introduce(agent, pid, frames):
    """From the app, with the phone in their hand: a few looks from a few angles. Keeps numbers, never a picture."""
    if not ready(agent):
        raise ValueError("Knowing faces is off. Switch it on in the app first.")
    model = _reader["model"]
    if not model.live(list(frames)):
        raise ValueError("I need to see you, in the room. A picture won't do.")
    looks = [u for u in (_unit(v) for v in (model.embed(f) for f in frames) if v is not None) if u]
    if len(looks) < ENOUGH:
        raise ValueError(f"I need a few more looks: {ENOUGH} from a few angles.")
    forget(agent, pid)
    agent.store.put(KIND, {"person": str(pid), "looks": [[round(v, 5) for v in look] for look in looks[:12]], "added": agent.clock()})
    return known(agent)


def known(agent):
    """Who Luma knows by sight: ids only, for the app. Never the numbers."""
    return sorted({row.get("person") for row in agent.store.all(KIND, 200) if row.get("person")})


def forget(agent, pid=None):
    """Delete what's kept for one person, or for everyone."""
    gone = 0
    for row in agent.store.all(KIND, 1000):
        if pid is None or row.get("person") == str(pid):
            gone += bool(agent.store.delete(KIND, row["id"]))
    return gone


def whose(agent, frame):
    """Whose face this is, or None. Close to theirs, and clearly closer than to anyone else's."""
    model = _reader["model"]
    if model is None:
        return None
    seen = model.embed(frame)
    seen = _unit(seen) if seen is not None else None
    if not seen:
        return None
    best = {}
    for row in agent.store.all(KIND, 200):
        score = max((_alike(seen, look) for look in row.get("looks") or []), default=-1.0)
        best[row.get("person")] = max(best.get(row.get("person"), -1.0), score)
    ranked = sorted(best.items(), key=lambda kv: -kv[1])
    if not ranked or ranked[0][1] < CLOSE:
        return None
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < CLEAR:
        return None       # it could be either of two people: that isn't knowing
    return ranked[0][0]


def look(agent, frames):
    """What the camera loop calls with its last few looks. When they're all of the same one of its people, live in
    the room, the room is unlocked for them and their id is returned. Otherwise None: someone Luma hasn't met, a
    picture, nobody, or not sure. Nothing about a look is kept."""
    frames = list(frames)
    if not ready(agent) or len(frames) < LOOKS:
        return None
    model = _reader["model"]
    people = [whose(agent, frame) for frame in frames[-LOOKS:]]
    if people[0] is None or any(p != people[0] for p in people):
        return None
    if not model.live(frames[-LOOKS:]):
        return None
    from luma.agent import who
    who.seen(agent, people[0])
    return people[0]
