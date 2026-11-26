"""With the owner's yes, Luma does it (the owner, Nov 25): the standing yes, and the two-step yes for a sign-in.

"If the owner says yes to do it they can do it." "It can write passwords when given verbal permission and a message
from the phone or email."

A standing yes: "you can always text my sister". From then on a text to her that they ask for goes without the
"want me to send it?" in between. It's kept with the words they said, shown in both apps, and taken back with a word
("ask me before you text my sister") or a tap.

A sign-in: they put it into the app once (the site, their name there, the password). It's sealed in the home's store
with everything else, and no app, brain, chat, log or relay is ever handed it back. Luma types it into that site's
password box, and only that site's, when two things have happened: they said so out loud, and they confirmed it from
their phone. Both together can be a standing yes too ("you can always log me in to my bank").

What never changes:

- What Luma read is never a yes. A standing yes covers what they asked for in their own words this turn; something
  Luma came up with after reading a page or an email still waits for them.
- A password is typed only into a password box on the site it was saved for. A page that looks like their bank isn't
  their bank.
- Not in kids mode. Checkout isn't here at all: it stays off until the owner turns it on.
"""
from __future__ import annotations

import re
import secrets

KEY = "yeses"
WAIT = 300   # seconds a two-step yes waits for its second step

LEAD = r"^\W*(?:(?:hey|ok|okay|yo)\W+)?(?:luma\W+)?(?:from now on\W+)?"
WHO = r"(?P<who>(?:my|our)\s+[\w'-]+(?:\s+[\w'-]+)?|[A-Za-z][\w'-]*(?:\s+[A-Z][\w'-]*)?)"
SEND = r"(?P<verb>text|message|email|e-mail)"
NO_ASK = r"without asking(?: me)?(?: first)?|no need to (?:check|ask)(?: with me)?(?: first)?|don'?t (?:check|ask)(?: with me)?(?: first)?"
TAIL = rf"(?P<tail>(?:\W+(?:for me|when(?:ever)? i (?:ask|say(?: so)?)|anytime|any time|{NO_ASK}))*)\W*$"
MAY = r"(?:you can|you may|you'?re allowed to|feel free to|go ahead and)"
GIVE = [
    re.compile(LEAD + rf"(?:{MAY}\s+)?(?:(?P<always>always|just)\s+)?{SEND}\s+{WHO}{TAIL}", re.I),
    re.compile(LEAD + rf"(?:you don'?t (?:have|need) to ask(?: me)?|no need to ask(?: me)?|you needn'?t ask(?: me)?)(?P<always>) (?:first )?before (?:you )?{SEND}(?:ing)?\s+{WHO}(?P<tail>)\W*$", re.I),
]
GIVE_SIGNIN = re.compile(LEAD + rf"(?:{MAY}\s+)?(?:(?P<always>always|just)\s+)?(?P<verb>log|sign) me (?:in ?to|into|in on|in at|on to|onto)\s+{WHO}{TAIL}", re.I)
NOT_A_PERSON = re.compile(r"^(?:me|us|him|her|them|you|it|back|people|anyone|everyone|someone|somebody|whoever)$", re.I)
ING = r"(?P<verb>text|messag|email|e-mail)(?:ing|e)?"
TAKE = [
    re.compile(LEAD + rf"(?:stop|quit)\s+{ING}\s+{WHO}\s+(?:on your own|by yourself|without asking(?: me)?(?: first)?)\W*$", re.I),
    re.compile(LEAD + rf"(?:always )?ask(?: me)?(?: first)? before (?:you )?{ING}\s+{WHO}\W*$", re.I),
    re.compile(LEAD + rf"(?:don'?t|do not|you can'?t|you cannot|you can no longer)\s+{ING}\s+{WHO}\s+without asking(?: me)?(?: first)?(?: anymore| any more)?\W*$", re.I),
    re.compile(LEAD + rf"(?:stop|quit)\s+(?P<verb>logg|sign)ing me (?:in ?to|into)\s+{WHO}\s+(?:on your own|by yourself|without asking(?: me)?(?: first)?)\W*$", re.I),
    re.compile(LEAD + rf"take back (?:the|that|my) yes(?P<verb>) (?:for|about|on)\s+{WHO}\W*$", re.I),
]
SENDS = {"sms.send": "texts", "luma.send": "texts", "mac_messages.send": "texts", "mail.send": "email"}
LOGIN_ASK = re.compile(r"\b(?:log|sign) (?:me |us )?(?:in|into|on|onto)\b|\blog ?in to\b|\bsign ?in to\b", re.I)

NEEDS_PHONE = "Okay. Tap Confirm on your phone and I'll type it."
CANCELLED = "Okay, I've left it. Nothing was typed."


class Refused(ValueError):
    """Luma isn't typing this. The message is the sentence it says."""


def _state(agent):
    state = agent.store.setting(KEY) or {}
    state.setdefault("standing", [])
    return state


def _kind(verb):
    verb = (verb or "").lower()
    return "email" if verb.startswith("e") else "signin" if verb.startswith(("log", "sign")) else "texts"


def reads(text):
    """A standing yes given in what they said: (kind, who), or None. kind is "texts", "email" or "signin"."""
    said = " ".join(str(text or "").split())
    for pattern in GIVE + [GIVE_SIGNIN]:
        m = pattern.match(said)
        if not m or NOT_A_PERSON.match(m["who"].strip()):
            continue
        tail = (m["tail"] or "").lower()
        standing = (m["always"] or "").lower() == "always" or m["always"] == "" and pattern in GIVE[1:] or re.search(NO_ASK + r"|any ?time", tail)
        if (m["always"] or "").lower() == "just" and not re.search(NO_ASK, tail):
            standing = False     # "just text Sam" is a text to send now
        if standing:
            return _kind(m["verb"]), m["who"].strip()
    return None


def takes_back(text):
    """A standing yes taken back in what they said: (kind or None, who), or None."""
    said = " ".join(str(text or "").split())
    for pattern in TAKE:
        m = pattern.match(said)
        if m and not NOT_A_PERSON.match(m["who"].strip()):
            return (_kind(m["verb"]) if m["verb"] else None), m["who"].strip()
    return None


def _name(who):
    return re.sub(r"^(?:my|our)\s+", "", " ".join(str(who).split()), flags=re.I).casefold()


def _your(who):
    return re.sub(r"^(?:my|our)\b", "your", who.strip(), flags=re.I)


def _contact(agent, who):
    try:
        return agent.contacts.resolve(who)
    except ValueError:
        simpler = re.sub(r"^(?:my|our)\s+", "", who.strip(), flags=re.I)
        if simpler == who.strip():
            raise
        return agent.contacts.resolve(simpler)


# -- sign-ins, sealed at home -----------------------------------------------------------------------------------------
def host_of(text):
    """The site's name from an address or from "Title — https://…": lower case, no www, no port, no path."""
    text = str(text or "").strip()
    url = re.search(r"https?://[^\s]+", text)
    text = url.group(0) if url else text
    host = re.sub(r"^[a-z]+://", "", text, flags=re.I).split("/")[0].split("?")[0].split("@")[-1].split(":")[0].lower().strip(". ")
    return re.sub(r"^www\.", "", host)


def same_site(page_host, saved_host):
    """The page is the saved site or a part of it (login.bank.com for bank.com). bank.com.evil.net is neither."""
    page_host, saved_host = host_of(page_host), host_of(saved_host)
    return bool(saved_host) and "." in saved_host and (page_host == saved_host or page_host.endswith("." + saved_host))


def save_signin(agent, site, user, secret, label=None):
    """From the apps only: the owner types it once. Kept sealed; never handed back."""
    if agent.mode == "kids":
        raise Refused("Sign-ins are for grown-ups. Switch to adult mode at home.")
    host = host_of(site)
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", host or ""):
        raise Refused("Give me the site's address, like chase.com.")
    if not isinstance(secret, str) or not 1 <= len(secret) <= 200 or not isinstance(user, str) or len(user) > 200:
        raise Refused("That password doesn't look right. Try typing it again.")
    old = next((r for r in agent.store.all("signin", 500) if r.get("host") == host and r.get("user") == user.strip()), None)
    row = agent.store.put_secret("signin", {"host": host, "user": user.strip(), "secret": secret, "label": " ".join(str(label or "").split())[:40],
                                            "added": agent.clock()}, old["id"] if old else None)
    agent._audit("kept a sign-in", "signin.save", {"site": host}, "own")
    return _shown(row)


def _shown(row):
    return {"id": row["id"], "site": row.get("host"), "user": row.get("user") or "", "label": row.get("label") or ""}


def signins(agent):
    return [_shown(r) for r in sorted(agent.store.all("signin", 500), key=lambda r: r.get("host") or "")]


def forget_signin(agent, id):
    row = agent.store.get("signin", str(id))
    if not row:
        raise Refused("That sign-in is already gone.")
    agent.store.delete("signin", row["id"])
    state = _state(agent)
    state["standing"] = [y for y in state["standing"] if not (y["kind"] == "signin" and y.get("site") == row.get("host"))]
    agent.store.set_setting(KEY, state)
    agent._audit("forgot a sign-in", "signin.forget", {"site": row.get("host")}, "own")
    return view(agent)


def forget_all(agent):
    """"Forget everything about me": every sign-in and every standing yes goes too."""
    for row in agent.store.all("signin", 10 ** 6):
        agent.store.delete("signin", row["id"])
    if agent.store.setting(KEY) is not None:
        agent.store.set_setting(KEY, None)
    agent._yes_waiting = []


def _signin_for(agent, where):
    """The sign-in for a page, or for what they called it ("my bank", "netflix")."""
    rows = agent.store.all("signin", 500)
    host = host_of(where)
    hit = [r for r in rows if same_site(host, r.get("host"))] if "." in host else []
    if not hit:
        name = _name(where)
        hit = [r for r in rows if name and (name == _name(r.get("label") or "") or name == (r.get("host") or "").split(".")[0]
                                            or name in (r.get("host") or "").split("."))]
    return hit[0] if len(hit) == 1 else None


# -- the standing yes -------------------------------------------------------------------------------------------------
def _give(agent, kind, who, how="said", words=""):
    state = _state(agent)
    if kind == "signin":
        entry = _signin_for(agent, who)
        if not entry:
            return {"text": f"I don't have a sign-in for {_your(who)} yet. Add it under Sign-ins in the app, and say that again.", "section": "yes", "handy": True}
        waiting = _wait(agent, {"kind": "standing_signin", "site": entry["host"], "user": entry.get("user") or "", "who": who, "step": "phone", "words": words})
        return {"text": f"Okay: I'll sign you in to {entry['host']} whenever you ask. Tap Confirm on your phone and it's set.", "section": "yes",
                "waiting": waiting["id"], "handy": True}
    try:
        contact = _contact(agent, who)
    except ValueError:
        return {"text": f"I don't have {_your(who)} saved yet. Tell me their number and say that again.", "section": "yes", "handy": True}
    to = contact.get("phone") if kind == "texts" else contact.get("email")
    if not to:
        return {"text": f"I don't have {'a number' if kind == 'texts' else 'an email address'} for {contact['name']} yet.", "section": "yes", "handy": True}
    state["standing"] = [y for y in state["standing"] if not (y["kind"] == kind and y.get("to") == to)]
    state["standing"].append({"id": secrets.token_hex(4), "kind": kind, "who": contact["name"], "to": to, "words": words[:200], "how": how, "at": agent.clock()})
    agent.store.set_setting(KEY, state)
    agent._audit("standing yes given", "yes." + kind, {"who": contact["name"]}, "own")
    doing, back = ("text", "texting") if kind == "texts" else ("email", "emailing")
    return {"text": f"Okay. From now on, when you ask me to {doing} {contact['name']} I'll send it without checking first. "
                    f"Say “ask me before {back} {contact['name']}” to take that back.", "section": "yes", "handy": True}


def take_back(agent, id=None, kind=None, who=None):
    state = _state(agent)
    name = _name(who or "")
    gone = [y for y in state["standing"] if (id and y["id"] == id) or (not id and (kind is None or y["kind"] == kind)
            and name in {_name(y.get("who") or ""), _name(y.get("label") or ""), (y.get("site") or "").split(".")[0]})]
    if not gone and who and not id:
        try:   # "my sister" is Priya's card
            contact = _contact(agent, who)
            gone = [y for y in state["standing"] if (kind is None or y["kind"] == kind) and y.get("to") in {contact.get("phone"), contact.get("email")}]
        except Exception:
            gone = []
    if not gone:
        return None
    state["standing"] = [y for y in state["standing"] if y not in gone]
    agent.store.set_setting(KEY, state)
    for y in gone:
        agent._audit("standing yes taken back", "yes." + y["kind"], {"who": y.get("who") or y.get("site")}, "own")
    return gone


def covers(agent, tool, args):
    """The standing yes that covers this send, or None. Only for something they asked for in their own words this
    turn: what Luma came up with after reading something still waits for them."""
    kind = SENDS.get(tool)
    if not kind or agent.mode == "kids" or getattr(agent, "_just_read", None):
        return None
    to = str((args or {}).get("to") or "")
    return next((y for y in _state(agent)["standing"] if y["kind"] == kind and y.get("to") and y["to"].casefold() == to.casefold()), None)


# -- the two-step yes -------------------------------------------------------------------------------------------------
def _waiting(agent):
    now = agent.clock()
    agent._yes_waiting = [w for w in (getattr(agent, "_yes_waiting", None) or []) if w["expires"] > now]
    return agent._yes_waiting


def _wait(agent, what):
    waiting = _waiting(agent)
    waiting[:] = [w for w in waiting if not (w["kind"] == what["kind"] and w["site"] == what["site"])]
    row = {**what, "id": secrets.token_hex(6), "asked": agent.clock(), "expires": agent.clock() + WAIT}
    waiting.append(row)
    return row


def _page(agent):
    return host_of(agent.store.setting("browser_page", "") or "")


def signin_asked(agent, ref, item):
    """A password box is about to be typed into (Agent.propose). With a standing yes for this site it's typed now.
    Otherwise this starts the two steps and returns what Luma says. Raises Refused with the sentence when it can't."""
    if agent.mode == "kids":
        raise Refused("I don't type passwords in kids mode.")
    page = _page(agent)
    entry = _signin_for(agent, page) if page else None
    if not entry:
        raise Refused(f"I don't have a sign-in for {page or 'this page'}. Add it under Sign-ins in the app, or sign in yourself in Luma's browser.")
    standing = next((y for y in _state(agent)["standing"] if y["kind"] == "signin" and y.get("site") == entry["host"]), None)
    theirs = bool(LOGIN_ASK.search(getattr(agent, "_yes_said", "") or "")) and not getattr(agent, "_just_read_before_ask", None)
    if standing and theirs:
        return _type(agent, {"site": entry["host"], "ref": int(ref), "label": item.get("label", "")}, entry, "a standing yes")
    waiting = _wait(agent, {"kind": "signin", "site": entry["host"], "user": entry.get("user") or "", "ref": int(ref), "label": item.get("label", "")[:200],
                            "step": "phone" if theirs else "voice"})
    said = (f"I can type your password for {entry['host']}. Tap Confirm on your phone and I'll do it." if theirs
            else f"Want me to type your password for {entry['host']}? Say yes, then confirm on your phone.")
    return {"state": "pending", "waiting": waiting["id"], "text": said, "asked": True, "section": "yes"}


def _type(agent, waiting, entry, by):
    item = agent.browser.describe(waiting["ref"])
    if (item or {}).get("type") != "password":
        raise Refused("That box isn't a password box anymore, so I haven't typed anything.")
    try:   # where the browser is right now, not where it was when they were asked
        snap = agent.browser.read()
        agent.store.set_setting("browser_page", (snap.get("title") or "") + " — " + snap.get("url", ""))
    except Exception:
        pass
    if not same_site(_page(agent), entry["host"]):
        raise Refused(f"The page isn't {entry['host']} anymore, so I haven't typed anything.")
    agent.browser.type(waiting["ref"], entry["secret"], False, item.get("label"))
    agent._audit("typed a sign-in", "browser.type", {"site": entry["host"], "yes": by}, "act")
    return {"state": "succeeded", "typed": True, "site": entry["host"], "section": "yes",
            "text": f"I've typed your password on {entry['host']}." + (f" Your name there is {entry['user']}." if entry.get("user") else "")}


def confirm(agent, id, by="phone"):
    """The second step, from their phone. The first must already have happened."""
    waiting = next((w for w in _waiting(agent) if w["id"] == id), None)
    if not waiting:
        raise Refused("That one ran out of time. Ask me again.")
    if waiting["step"] != "phone":
        raise Refused("Say yes out loud first, then confirm here.")
    _waiting(agent).remove(waiting)
    entry = next((r for r in agent.store.all("signin", 500) if r.get("host") == waiting["site"]), None)
    if not entry:
        raise Refused("That sign-in is gone, so there's nothing to type.")
    if waiting["kind"] == "standing_signin":
        state = _state(agent)
        state["standing"] = [y for y in state["standing"] if not (y["kind"] == "signin" and y.get("site") == entry["host"])]
        state["standing"].append({"id": secrets.token_hex(4), "kind": "signin", "site": entry["host"], "who": entry.get("label") or entry["host"],
                                  "words": (waiting.get("words") or "")[:200], "how": "said, and confirmed on the " + by, "at": agent.clock()})
        agent.store.set_setting(KEY, state)
        agent._audit("standing yes given", "yes.signin", {"site": entry["host"], "confirmed": by}, "own")
        return {"state": "kept", "section": "yes", "text": f"Set. I'll sign you in to {entry['host']} whenever you ask."}
    return _type(agent, waiting, entry, "said out loud, and confirmed on the " + by)


def cancel(agent, id):
    waiting = _waiting(agent)
    waiting[:] = [w for w in waiting if w["id"] != id]
    return view(agent)


def heard(agent, text):
    """In the chat path, after the safety net: a standing yes given or taken back, or the spoken step of a sign-in.
    A reply, or None. It also notes what they said this turn, which is what a standing yes covers."""
    agent._yes_said = str(text or "")
    if agent.mode == "kids":
        return None
    from luma.agent import texting
    voice = next((w for w in _waiting(agent) if w["step"] == "voice"), None)
    if voice:
        intent = texting.confirm_intent(text)
        if intent == "confirm":
            voice["step"], voice["expires"] = "phone", agent.clock() + WAIT
            return {"text": NEEDS_PHONE, "section": "yes", "waiting": voice["id"], "handy": True}
        if intent == "cancel":
            _waiting(agent).remove(voice)
            return {"text": CANCELLED, "section": "yes", "handy": True}
    back = takes_back(text)
    if back:
        gone = take_back(agent, kind=back[0], who=back[1])
        if gone:
            return {"text": f"Done. I'll ask you first from now on{'' if len(gone) == 1 else ', for all of those'}.", "section": "yes", "handy": True}
        return {"text": f"I ask first for {_your(back[1])} already. Nothing to change.", "section": "yes", "handy": True}
    given = reads(text)
    if given:
        return _give(agent, given[0], given[1], words=" ".join(str(text).split()))
    return None


def view(agent):
    """For the apps: what Luma may do without asking, the sign-ins it holds (never a password), and what's waiting."""
    state = _state(agent)
    return {"standing": [{"id": y["id"], "kind": y["kind"], "who": y.get("who") or y.get("site") or "", "site": y.get("site"), "words": y.get("words") or "",
                          "how": y.get("how") or "said", "at": y.get("at")} for y in state["standing"]],
            "signins": signins(agent),
            "waiting": [{"id": w["id"], "kind": w["kind"], "site": w["site"], "user": w.get("user") or "", "step": w["step"], "expires": w["expires"]} for w in _waiting(agent)]}
