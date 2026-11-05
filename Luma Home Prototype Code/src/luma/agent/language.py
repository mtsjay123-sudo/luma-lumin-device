"""Talking in the owner's language: hear which one they're speaking, answer in it, and say it in a voice made for it.

The choice (Settings > Voice > Language) is English, "follow me" (whatever they speak, turn by turn), or one language.
Speech-to-text tells which language it heard (Whisper's multilingual model does, the English-only one can't); typed
messages are read for it here. The brain is told the language for the turn, and the classic voice speaks it with one of
Kokoro's voices for that language. The things Luma says on its own (a quick "let me check" while the brain works, sorry
for cutting someone off) come from this module too, in every language it speaks.
"""
from __future__ import annotations

import re
import threading
import time
import zlib

# code: (name, name in the language itself, Kokoro voice, Kokoro language). Kokoro v1.0 ships voices for all of these.
LANGUAGES = {
    "en": ("English", "English", "af_heart", "en-us"),
    "es": ("Spanish", "Español", "ef_dora", "es"),
    "fr": ("French", "Français", "ff_siwis", "fr-fr"),
    "it": ("Italian", "Italiano", "if_sara", "it"),
    "pt": ("Portuguese", "Português", "pf_dora", "pt-br"),
    "hi": ("Hindi", "हिन्दी", "hf_alpha", "hi"),
    "ja": ("Japanese", "日本語", "jf_alpha", "ja"),
    "zh": ("Chinese", "中文", "zf_xiaobei", "cmn"),
}
CHOICES = ("en", "auto") + tuple(c for c in LANGUAGES if c != "en")
HEARD_FOR = 20.0       # seconds: what speech-to-text heard counts for the turn it starts
SURE = 0.6             # how sure speech-to-text has to be before Luma switches language

_lock = threading.Lock()
_state = {"choice": "en", "code": "en", "heard": None, "heard_at": 0.0}


def configure(choice):
    """The owner's choice: "en", "auto" (follow whatever they speak) or one language's code."""
    choice = str(choice or "en").strip().lower()
    if choice not in CHOICES:
        raise ValueError("Choose English, follow me, or one of: " + ", ".join(LANGUAGES[c][1] for c in LANGUAGES if c != "en") + ".")
    with _lock:
        _state["choice"] = choice
        _state["code"] = choice if choice in LANGUAGES else "en"
    return choice


def choice():
    return _state["choice"]


def stt_language():
    """What speech-to-text is told: "en", one language, or None to work it out (only "follow me" does)."""
    c = _state["choice"]
    return None if c == "auto" else c


def needs_multilingual_model():
    return _state["choice"] != "en"


def heard(code, probability=1.0):
    """Speech-to-text heard this language (Whisper's own guess and how sure it was)."""
    code = (str(code or "").split("-")[0] or "en").lower()
    with _lock:
        _state["heard"] = (code, float(probability or 0.0))
        _state["heard_at"] = time.monotonic()


# The words that give a language away in a typed message. Short and common on purpose: a few of them together are a
# language; one borrowed word ("vamos a la beach") isn't.
WORDS = {
    "en": "the and you is are to of it that what i my this was for with have not but so just do your me we".split(),
    "es": "el la los las que de y es en un una por para con no lo pero qué cómo estoy está tengo quiero mi tu muy hoy también eso".split(),
    "fr": "le la les des que de et est un une pour avec pas je tu il elle nous vous mais très aujourd'hui c'est ça suis".split(),
    "it": "il lo gli che di e è un una per con non sono sei mi ti ma molto oggi anche come cosa questo".split(),
    "pt": "o os as que de e é um uma para com não eu você ele ela mas muito hoje também como isso estou tenho".split(),
}
_WORD = re.compile(r"[\w'’]+", re.UNICODE)


def detect_text(text):
    """The language of a typed message, or None when it's not clear (short, or mostly English with a borrowed word)."""
    text = str(text or "")
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if len(re.findall(r"[一-鿿]", text)) >= 2:
        return "zh"
    words = [w.lower().replace("’", "'") for w in _WORD.findall(text)]
    if len(words) < 3:
        return None
    score = {code: sum(w in set(vocab) for w in words) for code, vocab in WORDS.items()}
    best = max(score, key=score.get)
    if best == "en" or score[best] < 2:
        return None
    if score[best] < max(2, 1.5 * score["en"]) or score[best] / len(words) < 0.25:
        return None  # Spanglish, Taglish and friends stay English, with their words
    return best


def of_reply(text):
    """The language a sentence Luma is about to say is in: the turn's language, unless the sentence is plainly English
    (Luma's own built-in lines are) or plainly another language."""
    turn = speaking()
    if turn == "en":
        return "en"
    found = detect_text(text)
    if found:
        return found
    words = [w.lower() for w in _WORD.findall(str(text or ""))]
    english = sum(w in set(WORDS["en"]) for w in words)
    return "en" if len(words) >= 3 and english / len(words) >= 0.3 else turn


def for_turn(text):
    """The language this turn is in, and Luma answers in. Remembered for the voice that says the reply."""
    with _lock:
        c, recent = _state["choice"], _state["heard"] if time.monotonic() - _state["heard_at"] < HEARD_FOR else None
    if c in LANGUAGES:
        code = c
    elif c == "auto":
        code = (recent[0] if recent and recent[1] >= SURE and recent[0] in LANGUAGES else None) or detect_text(text) or "en"
    else:
        code = "en"
    with _lock:
        _state["code"] = code
    return code


def speaking():
    """The language of the turn Luma is answering."""
    return _state["code"]


def note(code=None):
    """For the brain, when the turn isn't in English."""
    code = code or speaking()
    if code == "en" or code not in LANGUAGES:
        return ""
    name = LANGUAGES[code][0]
    return (f"They're speaking {name}. Answer in {name}: natural, everyday {name}, the way a friend who speaks it would, "
            "matching how they talk. Names, numbers and brand names stay as they are.")


def voice(code=None):
    """(Kokoro voice, Kokoro language) for the classic voice in this language."""
    entry = LANGUAGES.get(code or speaking(), LANGUAGES["en"])
    return entry[2], entry[3]


# What Luma says on its own, in each language. "thinking": a real question; "checking": something it looks up;
# "okay": anything else that takes a moment; "sorry": it jumped in before they'd finished.
PHRASES = {
    "thinking": {"en": ["Hmm, let me think.", "Ooh, good question.", "Okay, let me think about that.", "Hmm, give me a sec."],
                 "es": ["Mmm, déjame pensar.", "Buena pregunta.", "A ver, déjame pensarlo."],
                 "fr": ["Hmm, laisse-moi réfléchir.", "Bonne question.", "Attends, je réfléchis."],
                 "it": ["Mmm, fammi pensare.", "Bella domanda.", "Aspetta, ci penso."],
                 "pt": ["Hmm, deixa eu pensar.", "Boa pergunta.", "Peraí, deixa eu pensar."],
                 "hi": ["हम्म, एक सेकंड।", "अच्छा सवाल है।"],
                 "ja": ["うーん、ちょっと考えるね。", "いい質問だね。"],
                 "zh": ["嗯，我想一想。", "好问题。"]},
    "checking": {"en": ["Let me check.", "One sec, looking.", "Checking now.", "Hang on, let me look."],
                 "es": ["Déjame ver.", "Un momento, lo busco.", "Ya lo reviso."],
                 "fr": ["Je regarde.", "Une seconde, je vérifie."],
                 "it": ["Controllo subito.", "Un attimo, guardo."],
                 "pt": ["Deixa eu ver.", "Um segundo, vou olhar."],
                 "hi": ["एक सेकंड, देखते हैं।"],
                 "ja": ["ちょっと調べるね。", "見てみるね。"],
                 "zh": ["我查一下。", "稍等，我看看。"]},
    "okay": {"en": ["Mm, okay.", "One sec.", "Okay, so."],
             "es": ["Mm, vale.", "Un segundo."],
             "fr": ["D'accord, une seconde."],
             "it": ["Ok, un attimo."],
             "pt": ["Beleza, um segundo."],
             "hi": ["ठीक है, एक सेकंड।"],
             "ja": ["うん、ちょっと待ってね。"],
             "zh": ["好，稍等一下。"]},
    "sorry": {"es": ["Perdón, no quise interrumpirte.", "Ay, perdón, te corté."],
              "fr": ["Pardon, je ne voulais pas te couper.", "Oups, je t'ai coupé."],
              "it": ["Scusa, non volevo interromperti."],
              "pt": ["Desculpa, não quis te interromper."],
              "hi": ["माफ़ करना, मैंने आपको टोक दिया।"],
              "ja": ["ごめん、話をさえぎっちゃったね。"],
              "zh": ["抱歉，我打断你了。"]},
}


def phrase(kind, seed="", code=None, avoid=()):
    """One of Luma's own lines in the turn's language (English if that language has none), the same for the same seed,
    and not one it just said."""
    code = code or speaking()
    options = PHRASES.get(kind, {}).get(code) or PHRASES.get(kind, {}).get("en") or []
    fresh = [p for p in options if p not in avoid] or options
    if not fresh:
        return ""
    return fresh[zlib.crc32(str(seed).encode("utf-8", "ignore")) % len(fresh)]


# Thinking out loud: which kind of line fits what they asked. A look-up gets "let me check", a real question gets "let me
# think", anything else that takes a moment gets "one sec".
LOOKUP = re.compile(r"\b(?:look (?:it |that )?up|search|google|check|find|how much|price|cost|weather|forecast|rain|news|headlines|score|"
                    r"who won|did .{2,30} win|what time does|open (?:now|today|tonight)|near me|traffic|"
                    r"precio|cuánto|clima|noticias|prix|météo|prezzo|meteo|preço|notícias)\b", re.I)
THINK = re.compile(r"\b(?:should i|do you think|what would you|how (?:do|can|should) i|why|help me|advice|figure out|decide|plan|"
                   r"which (?:one|is better)|qué (?:hago|piensas)|debería|que faire|cosa (?:faccio|pensi)|o que (?:eu )?faço)\b|\?\s*$", re.I)


def filler(said, seed="", avoid=()):
    """A short line for while the brain works on what they said."""
    said = str(said or "")
    kind = "checking" if LOOKUP.search(said) else "thinking" if THINK.search(said) else "okay"
    return phrase(kind, seed or said, avoid=avoid)
