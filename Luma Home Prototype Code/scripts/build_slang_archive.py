"""Build luma/agent/slang_archive.py from the Digital Slang Archive .docx (Session 3 and later sessions in the same layout).

    python3 -I scripts/build_slang_archive.py path/to/archive.docx

Reads the document's headings (Heading 1 section, Heading 2 community, Heading 3 term) and each term's four lines (meaning,
origin, usage, "Original example"), then writes the lexicon lines, the everyday-word list, details and example sentences.
The .docx is read as data with zipfile; nothing in it runs. Retrain afterwards: scripts/train_understanding.py.
"""
import html
import json
import pprint
import re
import sys
import unicodedata
import zipfile
from pathlib import Path


def read_docx(path):
    """[{term, h1, h2, body}] from the archive's headings and paragraphs."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    h1 = h2 = ""
    entries, cur = [], None
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        style = (re.search(r'<w:pStyle w:val="([^"]+)"', p) or [None, ""])[1]
        text = html.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S))).strip()
        if style == "Heading1":
            h1, h2, cur = text, "", None
        elif style == "Heading2":
            h2, cur = text, None
        elif style == "Heading3":
            cur = {"term": text, "h1": h1, "h2": h2, "body": []}
            entries.append(cur)
        elif cur is not None and text:
            cur["body"].append(text)
    return [e for e in entries if len(e["body"]) >= 4]


entries = read_docx(sys.argv[1])
out_path = Path(__file__).resolve().parents[1] / "src" / "luma" / "agent" / "slang_archive.py"

SECTION = {
    ("21", "Grammar"): "aave", ("21", "Core"): "aave", ("22", ""): "ballroom", ("23", ""): "aave+gaming",
    ("24", "The South"): "south", ("24", "Appalachia"): "appalachia", ("24", "The Midwest"): "midwest", ("24", "The Northeast"): "northeast",
    ("24", "The West"): "west", ("24", "Subcultures"): "subculture", ("25", ""): "internet",
    ("26", "Mexican"): "mexican", ("26", "Spanglish"): "latino", ("26", "Caribbean"): "caribe", ("26", "Central"): "latam",
    ("27", "Filipino"): "filipino", ("27", "Vietnamese"): "seasia", ("27", "Korean"): "korean", ("27", "Japanese"): "anime",
    ("27", "Chinese"): "chinese", ("27", "South Asian"): "desi", ("27", "Hawai"): "hawaii", ("27", "Asian Gaming"): "gaming",
    ("28", "Jamaican"): "jam", ("28", "Trinidad"): "westindies", ("28", "Nigerian"): "africa", ("28", "Multicultural"): "uk",
    ("28", "General British"): "brit", ("28", "Irish"): "irish", ("28", "Scots"): "scotwales", ("28", "Australian"): "aus",
    ("29", "Arab"): "arab", ("29", "Samoan"): "pasifika", ("29", "Indigenous"): "native", ("29", "Jewish"): "yiddish",
    ("29", "Italian"): "italian", ("29", "Louisiana"): "cajun", ("29", "Gullah"): "gullah", ("30", ""): "gaming",
}
ORIGINS = {
    "appalachia": "Appalachia", "northeast": "the Northeast (Boston, New York, Philly, Pittsburgh, Baltimore)",
    "west": "the West Coast and the Pacific Northwest", "subculture": "skate, surf, emo and other scenes",
    "mexican": "Mexican Spanish and Chicano culture", "caribe": "Puerto Rican, Dominican and Cuban Spanish",
    "latam": "Central and South American Spanish", "filipino": "Filipino and Taglish", "seasia": "Vietnamese, Thai and Hmong",
    "korean": "Korean and K-culture", "anime": "Japanese and anime fandom", "chinese": "Chinese and the Chinese diaspora",
    "desi": "South Asian (Desi) English", "hawaii": "Hawai'i Pidgin", "westindies": "Trinidad, Barbados, Guyana and Haiti",
    "africa": "Nigerian Pidgin and West and East Africa", "brit": "British English", "irish": "Irish English",
    "scotwales": "Scotland and Wales", "aus": "Australia and New Zealand", "arab": "Arab, Muslim and Persian American speech",
    "pasifika": "Samoan, Tongan and Māori", "native": "Native American communities", "yiddish": "Yiddish and Jewish American English",
    "italian": "Italian American speech", "cajun": "Louisiana Cajun and Creole", "gullah": "Gullah Geechee",
}
# grammar and ideas, not words: their examples still teach Luma how people talk
SKIP = {"habitual be", "copula absence", "completive done", "stressed bin", "negative concord", "stay plus verb", "come as an indignation marker",
        "ask pronounced aks", "third-person singular s absence", "existential it", "zero possessive", "preterite had", "bad meaning good",
        "a-prefixing", "like as a discourse marker", "intersentential switching", "intrasentential switching", "tag switching",
        "rush strategy in starcraft", "old way and new way"}
RENAME = {"it's the blank for me": ("it's the ___ for me", []), "its giving": ("it's giving", ["its giving"]),
          "mad as an intensifier": ("mad", []), "coke as a generic": ("coke", []), "carry as drive": ("carry", []),
          "sugar as address": ("sugar", []), "haram and halal in slang": ("haram", []), "ma'am and sir": ("ma'am", ["maam"]),
          "latinx and latine": ("latinx", ["latine"]), "anh, chị, and em": ("anh chị em", ["anh chi em"]),
          "oppa, unnie, noona, and hyung": ("oppa", ["unnie", "noona", "hyung"]), "wey or güey": ("güey", ["wey", "guey", "wei"]),
          "kuya and ate": ("kuya", []), "po and opo": ("opo", ["po"]), "aunty and uncle": ("aunty", ["auntie"]),
          "mid or feed": ("mid or feed", []), "the five and the 405": ("the 5 and the 405", ["the five and the 405"]),
          "gg ez": ("gg ez", ["ggez"]), "w in chat": ("w in chat", ["w in the chat"]), "l in chat": ("l in chat", ["l in the chat"])}
# Aimed at people or carrying a label for a group: Luma understands and explains it, and doesn't say it
SENSITIVE = {"redneck", "naco", "pocho", "fob", "abcd", "abc", "culchie", "laowai", "palagi", "bogan", "clanker", "indian time", "ndn",
             "chicano", "latinx", "boricua", "nuyorican", "desi", "chilango", "ese", "roadman", "cholo", "pachuco", "yuma", "wasteman"}
VULGAR = {"pinche", "jagoff", "seggs"}
# Real words in everyday English (or common names), so seeing one doesn't mean someone talks in slang
EVERYDAY = {
    "steady", "receipts", "fly", "cool", "hip", "house", "category", "walking", "vogue", "legendary", "lobby", "cheese", "scrub", "pocket",
    "the park", "pro-am", "green", "badges", "ping", "coke", "buggy", "holler", "supper", "directly", "mash", "sugar", "ma'am", "plumb", "poke",
    "tote", "the cities", "up north", "supper club", "frappe", "jimmies", "rotary", "the t", "stoop", "on line", "regular coffee", "hon", "hoagie",
    "bogus", "bail", "emo", "goth", "tailgate", "corn", "carnal", "padre", "lana", "feria", "sale", "pana", "mano", "cabal", "che", "tara", "lodi",
    "nako", "opo", "ewan", "anh chị em", "moe", "involution", "lying flat", "let it rot", "996", "abc", "aunty", "mast", "didi", "shoots", "pau",
    "ono", "choke", "akamai", "lolo", "kapu", "ohana", "pupu", "lime", "fete", "wine", "doh", "ent", "gist", "chop", "vex", "sabi", "oya", "sasa",
    "poa", "now now", "ubuntu", "mint", "banter", "proper", "grand", "deadly", "giving out", "yoke", "wee", "ken", "lush", "butty", "thongs", "ute",
    "dairy", "selfie", "mana", "hui", "mahi", "uso", "fia", "malo", "ofa", "powwow", "glitch", "spiel", "gravy", "cher", "bayou", "goober",
    "gumbo", "cooter", "tabby", "second line", "neutral ground", "peek", "rush", "flank", "boosting", "jungle", "feeding", "macro", "micro", "tank",
    "healer", "raid", "wipe", "pug", "cooldown", "kiting", "bonfire", "neutral", "mix-up", "zoning", "frame data", "rta", "tas", "pb", "tycoon",
    "creeper", "redstone", "whale", "bells", "ollie", "haram", "squad", "hater", "swag", "dap", "def", "sugar", "simón", "vos", "chivo", "kip",
    "bloke", "rez", "alofa", "yat", "duckwalk", "carry", "mad", "you died", "glitchless", "loot box", "pay to win", "schlep", "klutz", "nosh",
    "word up", "dank", "kook", "tryhard", "clapped", "going dumb", "trill",
}
EVERYDAY -= {"trill", "dank", "kook", "tryhard", "clapped", "going dumb", "word up"}  # these really are slang
NO_PLAIN = {"da", "que", "chi", "em", "po", "ken", "nat", "sale", "mano", "pana", "padre", "ate", "uncle", "sir", "halal", "yat", "ese", "si"}


def plain(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def origin_of(e):
    num = e["h1"].split(".")[0]
    for (n, h2), code in SECTION.items():
        if n == num and e["h2"].startswith(h2):
            return code
    return None


def clean(s):
    return s.replace("|", "/").replace("\n", " ").strip()


def meaning_of(term, first):
    m = re.match(r"^.{1,60}? (?:means?|describes|is|refers to) (.+)$", first)
    text = m.group(1) if m else re.sub(r"^" + re.escape(term) + r"\s+", "", first, flags=re.I)
    return clean(text.rstrip(".")[:160])


lines, details, examples, everyday, skipped = [], {}, [], set(), []
for e in entries:
    raw = e["term"].replace("’", "'")
    low = raw.lower()
    ex = re.search(r"[“\"](.+?)[”\"]\s*$", e["body"][3]) if len(e["body"]) > 3 else None
    example = ex.group(1).strip() if ex else ""
    if example:
        examples.append(example)
    origin = origin_of(e)
    if low in SKIP or origin is None:
        skipped.append(raw)
        continue
    if low in RENAME:
        term, variants = RENAME[low]
    else:
        m = re.match(r"^(\S+) (?:and|or) (\S+)$", low)
        term, variants = (m.group(1), [m.group(2)]) if m and low not in {"nerf and buff"} else (low, [])
        if low == "nerf and buff":
            term, variants = "nerf", ["buff"]
    forms = set(variants)
    for f in [term] + list(variants):
        p = plain(f)
        for v in {p, p.replace("'", ""), f.replace("'", ""), f.replace("-", " "), p.replace("-", " ")}:
            if v != f and v not in NO_PLAIN and len(v) >= 2:
                forms.add(v)
    forms.discard(term)
    register = "s" if term in SENSITIVE else "v" if term in VULGAR else "c"
    if term in EVERYDAY:
        everyday.add(term)
    lines.append(" | ".join([clean(term), ", ".join(sorted(forms)), origin, register, meaning_of(term, e["body"][0]), ""]))
    details[term] = (clean(e["body"][1]), clean(e["body"][2]), example)

header = '''"""The Digital Slang Archive, Session 3: slang community by community, as Luma reads it.

Built from the owner's research archive (scripts/build_slang_archive.py turns the .docx into this file). Same line format
as slang_data.LEXICON; where a word is already in slang_data, Luma keeps that meaning and learns the new spellings and
communities. DETAILS holds where each word comes from, how it's used and an example, for "what does X mean?". EXAMPLES
are the archive's own sentences: they teach the understanding model that talk like this is conversation, not a command.

Slurs aren't in here (the archive leaves them out on purpose). Words aimed at people, or labels for a group, are marked
s: Luma understands and explains them and doesn't say them. EVERYDAY words are ordinary English too ("cool", "house",
"tank"), so seeing one doesn't count as a sign that someone talks in slang.
"""
'''
with open(out_path, "w", encoding="utf-8") as f:
    f.write(header)
    f.write("ORIGINS = " + pprint.pformat(ORIGINS, width=150, sort_dicts=False) + "\n\n")
    f.write('LEXICON = r"""\n' + "\n".join(lines) + '\n""".strip()\n\n')
    f.write("EVERYDAY = " + pprint.pformat(sorted(everyday), width=150, compact=True).replace("[", "frozenset({", 1).rstrip("]") + "})\n\n")
    f.write("DETAILS = " + pprint.pformat(details, width=150, sort_dicts=False) + "\n\n")
    f.write("EXAMPLES = " + pprint.pformat(examples, width=150) + "\n")
print(len(lines), "words,", len(examples), "examples,", len(everyday), "everyday, skipped:", skipped)
