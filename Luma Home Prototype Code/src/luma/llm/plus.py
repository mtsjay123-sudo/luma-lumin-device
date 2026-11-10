"""Luma Plus's Super Intelligence: the cloud brain asked through Luma Cloud, with no key of the owner's.

Off until they say yes. Paying isn't the yes: after they subscribe, Luma asks once, on a plain screen (screen()), which
says what leaves the home, where it goes, what's kept and how to turn it off. The yes is to those words; when the words
change (WORDS), everyone is asked again. It can be taken back any time, and Luma thinks at home again right away.

Nothing here talks to the brain. This is the yes, the state the app shows, and what Luma does when Luma Cloud says no
(the month's time is used up, the yes was taken back somewhere else, the subscription ended)."""
from __future__ import annotations

from datetime import datetime, timezone

WORDS = 1                       # the yes screen's wording. Raise it whenever what leaves the home, where it goes or what's kept changes.
SETTING = "plus_brain"          # the owner said yes on this Luma, and hasn't taken it back
KIDS = "plus_brain_kids"        # a parent turned it on for kids mode too (off unless they do)
MODEL = "plus_model"            # which brain: Auto unless they pick one
NOTE = "plus_budget_note"       # this month's time ran out: Luma says so once, plainly
TAKE_BACK = "plus_take_back"    # the yes was taken back while Luma Cloud couldn't be reached: it's told as soon as it answers
ASKED = "plus_asked"            # the wording they've already answered (yes, or not now): Luma asks once, not every day
ACCOUNT = "luma_cloud_account"  # what Luma Cloud last said about the account (luma.integrations.luma_cloud)


def screen():
    """The yes screen, word for word. Every sentence is something that's built and checked (tests/test_plus_brain.py,
    tests/luma-brain.test.mjs at the top of the repo), and what's said about Anthropic is what its own page on API data
    retention says about zero data retention."""
    return {
        "words": WORDS,
        "title": "Think with the Super Intelligence?",
        "intro": "It's part of your Luma Plus, and it's off until you say yes here.",
        "parts": [
            {"head": "What leaves your home",
             "text": "While it's on: what you say to Luma, the recent conversation, the short file of what Luma knows about you with the "
                     "memories that fit, and anything Luma read to answer you, like a web page or an email you asked about. "
                     "A photo or the camera's view, when you ask Luma to look. "
                     "Your passwords, your app sign-ins and the keys to your memories never leave."},
            {"head": "Where it goes",
             "text": "Through Luma Cloud to Claude, an AI model made by Anthropic. Claude thinks and sends back an answer. "
                     "Everything Luma does, and every yes it needs from you, still happens here at home."},
            {"head": "What's kept",
             "text": "Not a word by Luma. Luma Cloud passes it along and keeps only counts: how much thinking, how long it took, what it cost. "
                     "Anthropic doesn't store what was said once it has answered, apart from a copy held in memory for a few minutes so "
                     "the next turn is quick, and it doesn't train on it. "
                     "One exception is theirs: they may keep something their safety systems flag, or that the law requires."},
            {"head": "How to turn it off",
             "text": "Settings, Luma's brain, Super Intelligence, Turn off. Luma thinks at home again right away."},
        ],
        "more": "It comes with a monthly amount of thinking. If that runs out, Luma tells you once and thinks at home until the next month. "
                "Luma is the same Luma either way, and its safety net always answers first, at home.",
        "yes": "Yes, turn it on",
        "no": "Not now",
    }


def _when(stamp):
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _brain(store):
    account = store.setting(ACCOUNT) or {}
    return account, (account.get("brain") or {})


def ready(store, luma_cloud, now=None):
    """Luma Cloud will answer a turn, as far as this Luma knows: signed in, Plus, set up there, the yes on record for the
    words this Luma shows, and this month's time not used up. No network: it's what Luma Cloud last said."""
    account, there = _brain(store)
    if not luma_cloud.connected() or account.get("plan") != "plus" or not there.get("available") or not there.get("consent"):
        return False
    if (there.get("words") or WORDS) > WORDS:
        return False  # the words changed and this Luma only has the old ones to show
    if (there.get("left_share") if there.get("left_share") is not None else 1) <= 0:
        now = luma_cloud.clock() if now is None else now
        return bool(there.get("resets")) and now >= _when(there["resets"])  # used up: back when the month turns
    return True


def view(store, luma_cloud, now=None):
    """What the app shows. "ask": bring up the yes screen by itself, once (they have Plus and haven't answered these
    words). "can_turn_on": it's off and Settings may offer it, which opens the same screen."""
    account, there = _brain(store)
    member = bool(luma_cloud.connected() and account.get("plan") == "plus")
    words_ok = (there.get("words") or WORDS) <= WORDS
    on = bool(store.setting(SETTING, False)) and ready(store, luma_cloud, now)
    left = there.get("left_share")
    said_yes = bool(there.get("consent") and store.setting(SETTING, False))
    can_turn_on = bool(member and there.get("available") and words_ok and not said_yes)
    return {
        "member": member,
        "available": bool(member and there.get("available")),
        "consent": bool(there.get("consent")),
        "on": on,
        "can_turn_on": can_turn_on,
        "ask": can_turn_on and (store.setting(ASKED, 0) or 0) < WORDS,
        "screen": screen() if can_turn_on else None,
        "update": bool(member and not words_ok),  # this Luma is too old to show the current words
        "left_share": left,
        "used_up": bool(member and left is not None and left <= 0 and not on),
        "resets": there.get("resets"),
        "kids": bool(store.setting(KIDS, False)),
        "model": store.setting(MODEL, "auto"),
        "words": WORDS,
    }


def say_yes(store, luma_cloud):
    """They said yes on the yes screen. Luma Cloud records it (against these words) before anything is sent."""
    luma_cloud.brain_consent(True, WORDS)
    store.set_setting(TAKE_BACK, None)
    store.set_setting(ASKED, WORDS)
    store.set_setting(SETTING, True)


def say_no(store, luma_cloud):
    """They turned it off. It's off here at once; Luma Cloud is told now, or as soon as it can be reached (finish)."""
    store.set_setting(SETTING, False)
    store.set_setting(ASKED, WORDS)  # "not now" is an answer: Luma doesn't keep asking
    try:
        luma_cloud.brain_consent(False)
        store.set_setting(TAKE_BACK, None)
    except Exception:
        store.set_setting(TAKE_BACK, True)


def finish(store, luma_cloud):
    """A yes taken back while Luma Cloud couldn't be reached is taken back there too, once it answers."""
    if store.setting(TAKE_BACK) and not store.setting(SETTING, False):
        say_no(store, luma_cloud)


def _patch(store, **brain):
    account = store.setting(ACCOUNT) or {}
    store.set_setting(ACCOUNT, {**account, "brain": {**(account.get("brain") or {}), **brain}})


def trouble(store, error, now):
    """Luma Cloud said no to a turn. What that means is noted, so the next turn doesn't ask again, and the plain reason
    comes back for the app (None when it wasn't Luma Cloud's no: a bad connection, a busy brain)."""
    status = getattr(error, "status_code", None)
    body = getattr(error, "body", None)
    code = body.get("error") if isinstance(body, dict) else None
    if status == 402 and code == "budget":
        resets = body.get("resets")
        _patch(store, left_share=0, resets=resets)
        month = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m")
        if (store.setting(NOTE) or {}).get("month") != month:
            store.set_setting(NOTE, {"month": month, "resets": resets, "said": False})
        return "This month's Super Intelligence time is used up, so I'm thinking at home until it resets."
    if status == 402 and code == "plus":
        store.set_setting(ACCOUNT, {**(store.setting(ACCOUNT) or {}), "plan": "free"})
        return "The Super Intelligence is part of Luma Plus, so I'm thinking at home."
    if status == 403 and code == "consent":
        store.set_setting(SETTING, False)
        _patch(store, consent=False, **({"words": body["words"]} if isinstance(body.get("words"), int) else {}))
        return "The Super Intelligence is waiting for your yes again, so I'm thinking at home."
    if status == 401 and code == "auth":
        _patch(store, available=False)
        return "This Luma isn't signed in to Luma Cloud, so I'm thinking at home."
    if status == 503 and code == "not_configured":
        _patch(store, available=False)
        return "The Super Intelligence isn't set up yet, so I'm thinking at home."
    return None


def budget_line(note, own_key=False):
    """What Luma says, once, when the month's time runs out. News, not a pitch: nothing about buying anything."""
    month = ""
    when = _when((note or {}).get("resets"))
    if when:
        month = " until " + datetime.fromtimestamp(when + 86400, timezone.utc).strftime("%B")  # a day in, so every time zone agrees on the month
    how = "so I'm on your own cloud key" if own_key else "so I'm thinking with my own brain at home"
    return f"Heads up: this month's Super Intelligence time is used up, {how}{month}."
