"""The index: everything needed to find a memory, kept in RAM, so a look-up takes milliseconds at any size.

The memories themselves stay encrypted on disk; the index holds no sentence, only which memories have which words
(numbers), when each was said, what kind it is, who it's about, and its meaning as a small row of numbers. It's built
once when Luma starts, by reading every memory a single time, and kept in step with every memory added, changed or
forgotten after that. Nothing here is written to disk.

Three things it knows that a plain word search doesn't:

- **Who's who.** "My sister's name is Dana" and "Dana (their sister) lives in Denver" are about one person, so "where
  does my sister live" finds the second through the first.
- **What's still true.** "You moved to Denver" takes the place of "You live in Austin": the older one is kept, as what
  used to be true, and comes after the newer one (or first, for "where did I live before").
- **What it was never told.** It knows the person but not the thing asked, or nobody by that name, or no memory mentions
  the thing at all: then it says so, and the answer isn't a guess from a lookalike.
"""
from __future__ import annotations

import hashlib
import math
import re
from array import array
from datetime import timezone

import numpy as np

from luma.memory import facts, segments, when

CATEGORIES = list(segments.CATEGORIES)
SAID = {"said", "log"}                 # lines of talk kept as they were said; everything else is a fact Luma keeps
TRIP, MILESTONE, PRIVATE = 1, 2, 4     # bits in `kind`
RRF = 60                               # reciprocal rank fusion: the usual constant
BIG = 20000                            # past this many meanings, a first pass on one bit a number, then the real ones
# words in a question that don't name the thing asked about
GENERIC = segments.words("name kind type thing stuff day date time place one part way lot anything something everything nothing someone anyone "
                         "people person number much many old new first last next year month week today favorite best ever usually actually still "
                         "called named mean means meant")
CUES = {what: segments.words(text) for what, text in {
    "home": "live lives living city town based moved move home hometown address",
    "work": "work works working job jobs living profession career employer company boss",
    "birthday": "birthday born bday",
    "name": "name named called",
    "into": "into hobby hobbies interested obsessed loves",
    "spouse": "married marry spouse husband wife partner",
    "allergy": "allergic allergy allergies",
    "pet": "name named call called dog cat puppy kitten pet",
    "favorite": "favorite favourite",
    "where": "keep kept left put parked stored",
    "diet": "vegetarian vegan eat eats diet",
}.items()}
# little words the word-finder lets through in another shape ("does" as "doe", "this" as "thi"): never what was asked about
NOISE = set().union(*(segments.words(w) for w in segments.STOP))
TIME_WORDS = segments.words("last this past ago during spring summer fall autumn winter year month week weekend yesterday today tonight night morning "
                            + " ".join(when.MONTHS) + " " + " ".join(when.DAYS))
OWNER = re.compile(r"\b(?:i|i'm|i've|i'd|my|me|mine|we|our)\b", re.I)
# "where did I travel", "what trip did I take": the words that ask about a trip aren't the thing asked about
TRAVEL_WORDS = segments.words("travel traveled travelled traveling travelling trip trips vacation vacations visit visited went go going gone flew fly flown take took taken")


def fingerprint(text):
    return hashlib.sha256(str(text or "").encode()).digest()[:8]


class People:
    """Who's who: which names go with which relations ("sister" is Dana), counted, so one stray line can't change it."""

    def __init__(self):
        self.by_rel, self.by_name, self.display = {}, {}, {}

    def link(self, name, rel, shown=None):
        self.by_rel.setdefault(rel, {})[name] = self.by_rel.get(rel, {}).get(name, 0) + 1
        self.by_name.setdefault(name, {})[rel] = self.by_name.get(name, {}).get(rel, 0) + 1
        self.know(name, shown)

    def unlink(self, name, rel):
        for table, a, b in ((self.by_rel, rel, name), (self.by_name, name, rel)):
            left = table.get(a, {}).get(b, 0) - 1
            if left > 0:
                table[a][b] = left
            else:
                table.get(a, {}).pop(b, None)
                if a in table and not table[a]:
                    table.pop(a)
        self.unknow(name)

    def know(self, name, shown=None):
        seen = self.display.get(name)
        self.display[name] = (shown or (seen[0] if seen else name.capitalize()), (seen[1] if seen else 0) + 1)

    def unknow(self, name):
        seen = self.display.get(name)
        if seen and seen[1] > 1:
            self.display[name] = (seen[0], seen[1] - 1)
        else:
            self.display.pop(name, None)

    def named(self, rel):
        """The names that go with a relation, most said first; one name when it's clearly the one ("my dad" is Jude)."""
        ranked = sorted(self.by_rel.get(rel, {}).items(), key=lambda kv: -kv[1])
        if len(ranked) > 1 and ranked[0][1] >= 3 * ranked[1][1]:
            ranked = ranked[:1]
        return [name for name, _ in ranked]

    def only(self, name):
        """The relations that mean this one person."""
        return [rel for rel in self.by_name.get(name, {}) if self.named(rel) == [name]]


class Meanings:
    """Each memory's meaning as a small row of whole numbers (a quarter the size of the real ones), plus one bit a number
    for a quick first pass when there are very many. The real numbers stay encrypted in the store."""

    def __init__(self, dims):
        self.dims, self.rows = dims, 0
        self.m = np.zeros((0, dims), dtype=np.int8)
        self.bits = np.zeros((0, (dims + 63) // 64), dtype=np.uint64)
        self.norm = np.zeros(0, dtype=np.float32)
        self.has = np.zeros(0, dtype=bool)
        self.count = 0

    def _room(self, row):
        if row < len(self.has):
            return
        size = max(row + 1, int(len(self.has) * 1.5) + 1024)
        for name in ("m", "bits", "norm", "has"):
            old = getattr(self, name)
            new = np.zeros((size,) + old.shape[1:], dtype=old.dtype)
            new[:len(old)] = old
            setattr(self, name, new)

    def put(self, row, vector):
        v = np.zeros(self.dims, dtype=np.float32)
        raw = np.asarray(vector, dtype=np.float32).reshape(-1)[:self.dims]
        v[:len(raw)] = raw
        size = float(np.linalg.norm(v))
        if size <= 0:
            return
        self._room(row)
        q = np.rint(v / size * 127).astype(np.int8)
        self.count += not self.has[row]
        self.m[row], self.norm[row], self.has[row] = q, float(np.linalg.norm(q.astype(np.float32))) or 1.0, True
        self.bits[row] = self._bits(v)

    def _bits(self, v):
        packed = np.packbits(v > 0)
        out = np.zeros(self.bits.shape[1] * 8, dtype=np.uint8)
        out[:len(packed)] = packed
        return out.view(np.uint64)

    def drop(self, row):
        if row < len(self.has) and self.has[row]:
            self.has[row] = False
            self.count -= 1

    def near(self, vector, alive, limit=16):
        """[(how close, row)] best first: close to the truth, to be checked against the real numbers by whoever asks."""
        n = min(len(self.has), len(alive))
        if not self.count or not n:
            return []
        q = np.zeros(self.dims, dtype=np.float32)
        raw = np.asarray(vector, dtype=np.float32).reshape(-1)[:self.dims]
        q[:len(raw)] = raw
        size = float(np.linalg.norm(q))
        if size <= 0:
            return []
        q /= size
        ok = self.has[:n] & (alive[:n] > 0)
        rows = np.flatnonzero(ok)
        if not len(rows):
            return []
        if len(rows) > BIG:  # one bit a number first: the nearest few thousand, then their real(ish) numbers
            far = np.bitwise_count(self.bits[rows] ^ self._bits(q)).sum(axis=1)
            keep = min(len(rows), max(2000, limit * 50))
            rows = rows[np.argpartition(far, keep - 1)[:keep]]
        score = (self.m[rows].astype(np.float32) @ q) / self.norm[rows]
        best = np.argsort(-score)[:limit]
        return [(float(score[i]), int(rows[i])) for i in best]


class LifeIndex:
    def __init__(self, dims=256):
        self.ids, self.row = [], {}
        self.created = array("d")
        self.cat, self.weight, self.kind = bytearray(), bytearray(), bytearray()
        self.alive, self.ended, self.said = bytearray(), bytearray(), bytearray()
        self.marks = bytearray()                 # 8 bytes a row: which words the meaning was worked out for
        self.count = array("H")                  # how many words that matter each row has
        self.postings, self.df, self.live = {}, {}, 0
        self.people = People()
        self.slots = {}                          # (who, what) -> [rows]
        self.read = {}                           # row -> (links, slots, mentions) for the rows that say a fact
        self.by_who = {}                         # who -> {what}
        self.meanings = Meanings(dims)

    # ------------------------------------------------------------------------------------------------ keeping in step ---
    def add(self, memory):
        mid, text, source = memory.get("id"), str(memory.get("text") or ""), str(memory.get("source") or "")
        if not mid:
            return None
        if mid in self.row:
            self.remove(mid)
        row = len(self.ids)
        self.ids.append(mid)
        self.row[mid] = row
        self.created.append(float(memory.get("created") or 0))
        category = memory.get("category") or segments.category(text, source)
        self.cat.append(CATEGORIES.index(category) if category in CATEGORIES else len(CATEGORIES) - 1)
        said = source in SAID
        self.said.append(1 if said else 0)
        self.weight.append(facts.weight(text, source))
        self.kind.append((TRIP if facts.is_trip(text) else 0) | (PRIVATE if facts.private(text, category) else 0))
        self.alive.append(1)
        self.ended.append(0)
        self.marks.extend(fingerprint(text))
        self.live += 1
        terms = segments.words(text)
        self.count.append(min(len(terms), 65535))
        for term in terms:
            self.postings.setdefault(term, array("I")).append(row)
            self.df[term] = self.df.get(term, 0) + 1
        self._learn(row, text, said)
        return row

    def _learn(self, row, text, said):
        reading = facts.read(text)
        links = list(reading.links) if reading else []
        slots = list(reading.slots) if reading else []
        mentions = []
        if "my " in text or "My " in text:
            from luma.agent import people as who
            for name, rel, _ in who.mentions(text):
                if name in text and (name.lower(), rel) not in links:  # said with a capital: a name, not a verb
                    mentions.append((name.lower(), rel))
        if not (links or slots or mentions):
            return
        self.read[row] = (links, slots, mentions)
        for name, rel in links + mentions:
            self.people.link(name, rel)
        touched = set()
        for who_, what, _ in slots:
            self.slots.setdefault((who_, what), []).append(row)
            self.by_who.setdefault(who_, set()).add(what)
            if who_.startswith("name:"):
                self.people.know(who_[5:])
            touched.add((who_, what))
        for name, rel in links + mentions:  # who's who changed: what's true about them may have too
            for who_ in ("name:" + name, "rel:" + rel):
                touched.update((who_, what) for what in self.by_who.get(who_, ()))
        for who_, what in touched:
            self._settle(who_, what)

    def remove(self, mid, text=None):
        """Forget one memory. `text` (what it said) keeps the word counts exact; without it they're a little high until
        the index is rebuilt, which only makes rare words look slightly less rare."""
        row = self.row.pop(mid, None)
        if row is None:
            return
        self.alive[row] = 0
        self.ids[row] = None
        self.live -= 1
        for term in segments.words(text) if text is not None else ():
            left = self.df.get(term, 0) - 1
            if left > 0:
                self.df[term] = left
            else:
                self.df.pop(term, None)
                self.postings.pop(term, None)
        self.meanings.drop(row)
        links, slots, mentions = self.read.pop(row, ((), (), ()))
        touched = set()
        for who_, what, _ in slots:
            rows = self.slots.get((who_, what), [])
            if row in rows:
                rows.remove(row)
            if not rows:
                self.slots.pop((who_, what), None)
                self.by_who.get(who_, set()).discard(what)
            if who_.startswith("name:"):
                self.people.unknow(who_[5:])
            touched.add((who_, what))
        for name, rel in list(links) + list(mentions):
            self.people.unlink(name, rel)
            for who_ in ("name:" + name, "rel:" + rel):
                touched.update((who_, what) for what in self.by_who.get(who_, ()))
        for who_, what in touched:
            self._settle(who_, what)

    def set_meaning(self, mid, vector, mark=None):
        row = self.row.get(mid)
        if row is None or (mark is not None and bytes(self.marks[row * 8:row * 8 + 8]) != mark):
            return False  # worked out for other words: the memory changed since
        self.meanings.put(row, vector)
        return True

    def drop_meaning(self, mid):
        row = self.row.get(mid)
        if row is not None:
            self.meanings.drop(row)

    def lacking_meaning(self, limit=2000):
        """Ids of memories whose meaning hasn't been worked out yet (the newest first)."""
        n = len(self.ids)
        if not n:
            return []
        lacks = np.frombuffer(self.alive, dtype=np.uint8, count=n) > 0
        has = self.meanings.has[:n]
        lacks[:len(has)] &= ~has
        return [self.ids[int(row)] for row in np.flatnonzero(lacks)[::-1][:limit]]

    # ------------------------------------------------------------------------------------------------- who and what ---
    def same(self, who):
        """Every way the index knows this person: {"name:dana", "rel:sister"}."""
        if who.startswith("rel:"):
            names = self.people.named(who[4:])
            if len(names) != 1:
                return {who}
            who = "name:" + names[0]
        if who.startswith("name:"):
            return {who} | {"rel:" + rel for rel in self.people.only(who[5:])}
        return {who}

    def _group(self, who, what):
        rows = []
        for key in self.same(who):
            rows += [r for r in self.slots.get((key, what), ()) if self.alive[r]]
        return sorted(set(rows), key=lambda r: (self.created[r], r))

    def _settle(self, who, what):
        """Of the facts that say the same kind of thing about the same person, the newest is what's true now."""
        base = what.split(":")[0]
        rows = self._group(who, what)
        many = base in facts.MANY or base == "pet" or (base == "name" and who.startswith("rel:") and len(self.people.named(who[4:])) != 1)
        for i, row in enumerate(rows):
            self.ended[row] = 0 if many or i == len(rows) - 1 else 1

    def _values(self, row, what):
        return [value for _, w, value in self.read.get(row, ((), (), ()))[1] if w == what]

    def _fact_rows(self, whos, what, past=False):
        """The rows that state this fact about these people: what's true now first (or what used to be, for the past)."""
        rows, base = [], what.split(":")[0]
        for who in whos:
            if ":" in what and base in ("where", "favorite"):  # "where are my keys" finds "Your car keys are..."
                wanted = segments.words(what.split(":", 1)[1])
                for (key, kept), found in self.slots.items():
                    if key == who and kept.startswith(base + ":"):
                        have = segments.words(kept.split(":", 1)[1])
                        if wanted and have and (wanted <= have or have <= wanted):
                            rows += found
            elif what == "pet":
                for (key, kept), found in self.slots.items():
                    if key == who and kept.startswith("pet:"):
                        rows += found
            else:
                rows += self.slots.get((who, what), ())
                if what == "work":  # "Sam (their wife) is a teacher" answers what Sam does
                    rows += self.slots.get((who, "is"), ())
        rows = sorted({r for r in rows if self.alive[r]}, key=lambda r: (-self.created[r], -r))
        now, before = [r for r in rows if not self.ended[r]], [r for r in rows if self.ended[r]]
        return before + now if past else now + before

    # ------------------------------------------------------------------------------------------------------ by words ---
    def _arrays(self):
        n = len(self.ids)
        return (np.frombuffer(self.alive, dtype=np.uint8, count=n), np.frombuffer(self.created, dtype=np.float64, count=n),
                np.frombuffer(self.cat, dtype=np.uint8, count=n), np.frombuffer(self.said, dtype=np.uint8, count=n),
                np.frombuffer(self.weight, dtype=np.uint8, count=n), np.frombuffer(self.kind, dtype=np.uint8, count=n))

    def words(self, question, limit=5, mask=None, terms=None):
        """[(score, row)] best first: the same ranking as luma.memory.segments.recall (rare words count more, the right
        bucket gets a lift, newest wins a tie), without reading a single memory."""
        terms = segments.words(question) if terms is None else terms
        n = len(self.ids)
        if not terms or not self.live or not n:
            return []
        alive, created, cat = self._arrays()[:3]
        score = np.zeros(n, dtype=np.float64)
        hit = False
        for term in sorted(terms):  # in one order, so the same words always add up the same
            rows = self.postings.get(term)
            count = self.df.get(term, 0)
            if rows is None or not count:
                continue
            score[np.frombuffer(rows, dtype=np.uint32)] += math.log(1 + self.live / count)
            hit = True
        if not hit:
            return []
        score[alive == 0] = 0
        if mask is not None:
            score[~mask] = 0
        wanted = [CATEGORIES.index(c) for c in segments.intents(question)]
        if wanted:
            score[(score > 0) & np.isin(cat, wanted)] += 1.5
        found = np.flatnonzero(score > 0)
        if not len(found):
            return []
        if len(found) > limit:
            worst = np.partition(score[found], len(found) - limit)[len(found) - limit]
            found = found[score[found] >= worst]
        order = np.lexsort((found, created[found], score[found]))[::-1][:limit]
        return [(float(score[found[i]]), int(found[i])) for i in order]

    def _rows_with(self, terms):
        """Rows that have any of these words, as a sorted array."""
        parts = [np.frombuffer(self.postings[t], dtype=np.uint32) for t in terms if t in self.postings]
        return np.unique(np.concatenate(parts)) if parts else np.zeros(0, dtype=np.uint32)

    # ------------------------------------------------------------------------------------------------------ the search ---
    def search(self, question, limit=5, now=None, zone=None, near=None):
        """What answers this question. Returns {"rows": best first, "known": False when Luma was never told,
        "why": in plain words, "window": (start, end) when the question is about a time, "ended": rows that used to be true}.

        near(question) -> [(how close, row)] is the meaning search, when this computer has it."""
        q = " ".join(str(question or "").replace("’", "'").split())
        terms = segments.words(q)
        ask = facts.asked(q)
        span = when.window(q, now, zone or timezone.utc)
        past = when.about_the_past(q)
        alive, created, _, said, weight, kind = self._arrays()
        picked, why, known = [], "", True
        used = set()          # the question's words that named who, what or when
        lowered = [w.strip("'") for w in re.findall(r"[a-z][a-z'-]*", q.lower())]
        lowered = [w[:-2] if w.endswith("'s") else w for w in lowered]

        # who it's about: everyone the question names, then the one the thing asked belongs to (the nearest one before it)
        named, unknown = set(), None
        mentioned = []        # (where in the question, the ways the index knows them or None, how they were named)
        for rel, at in zip(ask["rels"], ask["rel_at"]):
            used |= segments.words(rel)
            named |= segments.words(rel)
            names = self.people.named(rel)
            if names:
                group = set()
                for name in names:
                    group |= self.same("name:" + name)
                mentioned.append((at, group, rel))
            elif "rel:" + rel in self.by_who:
                mentioned.append((at, {"rel:" + rel}, rel))
            else:
                mentioned.append((at, None, rel))
        for found in re.finditer(r"[a-z][a-z'-]*", q.lower()):
            word = found.group(0).strip("'")
            word = word[:-2] if word.endswith("'s") else word
            if word in self.people.display and not any(group and "name:" + word in group for _, group, _ in mentioned):
                mentioned.append((found.start(), self.same("name:" + word), word))
                used |= segments.words(word)
                named |= segments.words(word)
        for found in re.finditer(r"\b(?:i|we|i'm|i've|i'd|i'll)\b", q, re.I):
            mentioned.append((found.start(), {"you"}, "i"))
        before = [m for m in mentioned if ask["at"] is not None and m[0] <= ask["at"]]
        people_named = [m for m in mentioned if m[1] != {"you"}]
        subject = max(before, key=lambda m: m[0]) if before else (people_named[-1] if people_named else (mentioned[-1] if mentioned else None))
        whos = []
        if subject is not None and subject[1] is None:
            unknown = subject[2]
        elif subject is not None:
            whos = [subject[1]]
        if ask["hop"] and whos and whos[0] != {"you"}:  # "my sister's husband": whoever she's married to
            used |= CUES["spouse"]
            partners = []
            for row in self._fact_rows(whos[0], "spouse"):
                partners += self._values(row, "spouse")
            whos = [self.same("name:" + partners[0])] if partners else []
            if not partners:
                known, why = False, f"nothing saved about who my {subject[2]} is married to"
        if not whos and not unknown and known and OWNER.search(q):
            whos = [{"you"}]

        # 1. the fact itself, then whatever else is kept about them
        fact_rows, cue = [], set()
        person = bool(whos) and whos[-1] != {"you"}
        if unknown:
            known, why = False, f"nobody saved as my {unknown}"
        elif whos and known:
            if ask["what"]:
                base = ask["what"].split(":")[0]
                cue = CUES.get(base, set()) | (segments.words(ask["what"].split(":", 1)[1]) if ":" in ask["what"] else set())
                used |= cue
                fact_rows = self._fact_rows(whos[-1], ask["what"], past)
            facts_only = (said == 0) & (alive > 0)
            theirs = self._about(whos[-1]) if person else self._rows_with(cue)
            theirs = theirs[facts_only[theirs]] if len(theirs) else theirs
            on_topic = np.intersect1d(theirs, self._rows_with(cue)) if person and cue and len(theirs) else theirs if not person else theirs[:0]
            newest = max((created[r] for r in fact_rows), default=-1.0)
            # a newer fact about the same thing, worded some way this couldn't read, may be the one that's true now
            maybe_newer = [int(r) for r in on_topic[np.argsort(-created[on_topic])]
                           if created[r] > newest and not self.read.get(int(r), ((), ()))[1]][:2] if not past else []
            picked += maybe_newer + [r for r in fact_rows if r not in maybe_newer]
            if person and len(theirs):  # what else is kept about this person: closest to the question, then the newest
                mask = np.zeros(len(self.ids), dtype=bool)
                mask[theirs] = True
                closest = [r for _, r in self.words(q, limit, mask=mask, terms=terms - named - NOISE)]
                topic = set(int(r) for r in on_topic)
                others = sorted((int(r) for r in theirs), key=lambda r: (r not in topic, -created[r]))
                picked += [r for r in closest + others if r not in picked][:limit * 2]

        # 2. what was said at that time
        window_rows = []
        if span:
            used |= TIME_WORDS | {t for t in terms if t.isdigit()}
            inside = (created >= span[0]) & (created < span[1]) & (alive > 0)
            if inside.any():
                rest = terms - used
                if facts.asks_about_travel(q):
                    used |= TRAVEL_WORDS
                    trips = np.flatnonzero(inside & ((kind & TRIP) > 0))
                    window_rows += [int(r) for r in trips[np.argsort(-created[trips])][:limit]]
                window_rows += [r for _, r in self.words(q, limit, mask=inside, terms=rest) if r not in window_rows] if rest else []
                if not window_rows:  # nothing by its words: the moments that mattered then
                    notable = np.flatnonzero(inside & (weight > 0))
                    order = np.lexsort((created[notable], weight[notable]))[::-1][:limit]
                    window_rows += [int(notable[i]) for i in order]
                picked += [r for r in window_rows if r not in picked]
            if not window_rows and not fact_rows:
                known, why = False, "nothing saved from then"

        # 3. words and meaning: facts first, then the talk around them
        lists = [(1.5, [r for _, r in self.words(q, limit * 2, mask=(said == 0))]), (1.0, [r for _, r in self.words(q, limit * 2)])]
        close = []
        if near is not None:
            close = [r for _, r in near(q)]
            lists.append((1.5, close))
        fused = {}
        for weight_, rows in lists:
            for rank, row in enumerate(rows):
                fused[row] = fused.get(row, 0.0) + weight_ / (RRF + rank)
        if span and window_rows:  # asked about a time: what's outside it isn't the answer
            fused = {row: s for row, s in fused.items() if span[0] <= created[row] < span[1]}
        picked += [row for row, _ in sorted(fused.items(), key=lambda kv: -kv[1]) if row not in picked]

        # 4. never told. Only when it's sure: nobody by that name (above), nothing from that time (above), or no person in
        # the question and not one memory that mentions the thing. About someone it knows, it hands over what it has and
        # says which words it has never seen ("middle"): whether that answers the question is for the brain to say.
        rest = terms - used - GENERIC - NOISE
        unseen = sorted(t for t in rest if not self.df.get(t))
        if known and not person and rest and len(unseen) == len(rest) and not close and not window_rows and not fact_rows:
            known, why = False, "nothing saved mentions " + ", ".join(unseen)
        if not picked and known:
            known, why = False, "nothing saved about that"

        ended = {r for r in picked if self.ended[r]}
        if not past:  # what used to be true comes after what's true now
            picked = [r for r in picked if r not in ended] + [r for r in picked if r in ended]
        return {"rows": picked[:limit], "known": known, "why": why, "window": span[:2] if span else None, "ended": ended & set(picked[:limit]),
                "unseen": unseen if known and len(unseen) <= 2 and len(rest) <= 3 else [], "facts": set(fact_rows) & set(picked[:limit])}

    def _about(self, who):
        """Rows that mention this person by name or by relation."""
        terms = set()
        for key in who:
            terms |= segments.words(key.split(":", 1)[1]) if ":" in key else set()
        return self._rows_with(terms)

    # ------------------------------------------------------------------------------------------------------- the same ---
    def twins(self, text, limit=300, lines=False):
        """Rows that might say the same thing as this sentence: every word of one is in the other. The caller reads those
        few to be sure. Facts only, unless `lines` (then the lines of talk too). Newest first."""
        terms = segments.words(text)
        n = len(self.ids)
        if not terms or not n:
            return []
        alive, _, _, said = self._arrays()[:4]
        seen = np.zeros(n, dtype=np.int32)
        for term in terms:
            rows = self.postings.get(term)
            if rows is not None:
                seen[np.frombuffer(rows, dtype=np.uint32)] += 1
        count = np.frombuffer(self.count, dtype=np.uint16, count=n)
        maybe = (alive > 0) & (seen > 0) & ((seen == len(terms)) | (seen == count))
        if not lines:
            maybe &= said == 0
        return [int(r) for r in np.flatnonzero(maybe)[::-1][:limit]]

    def counts(self):
        """(facts kept, lines of talk kept)."""
        n = len(self.ids)
        if not n:
            return 0, 0
        alive, _, _, said = self._arrays()[:4]
        lines = int(np.count_nonzero((alive > 0) & (said > 0)))
        return self.live - lines, lines

    def fact_ids(self, limit=100000):
        """Ids of the facts (not the talk around them), newest first."""
        n = len(self.ids)
        if not n:
            return []
        alive, created, _, said = self._arrays()[:4]
        rows = np.flatnonzero((alive > 0) & (said == 0))
        rows = rows[np.lexsort((rows, created[rows]))[::-1][:limit]]
        return [self.ids[int(r)] for r in rows]

    def ids_before(self, cutoff):
        """Ids of everything said before a moment: facts and talk."""
        n = len(self.ids)
        if not n:
            return []
        alive, created = self._arrays()[:2]
        return [self.ids[int(r)] for r in np.flatnonzero((alive > 0) & (created < cutoff))]

    def ids_between(self, start, end):
        """Ids of everything said in a span of time, oldest first."""
        n = len(self.ids)
        if not n:
            return []
        alive, created = self._arrays()[:2]
        rows = np.flatnonzero((alive > 0) & (created >= start) & (created < end))
        return [self.ids[int(r)] for r in rows[np.argsort(created[rows], kind="stable")]]

    ABOUT_THEM = ("name", "home", "work", "birthday", "diet", "allergy", "spouse", "pet", "favorite", "goal", "into", "likes", "is", "where")

    def whats_true(self, limit=2000):
        """Ids of what's true now, in the order a friend would tell it: about them, then their people (the ones they talk
        about most first), then everything else Luma keeps as a fact, newest first."""
        n = len(self.ids)
        if not n:
            return []
        order = {what: i for i, what in enumerate(self.ABOUT_THEM)}
        rank = lambda what: order.get(what.split(":")[0], len(order))  # noqa: E731
        rows, seen = [], set()

        def take(found):
            for row in found:
                if self.alive[row] and not self.ended[row] and row not in seen:
                    seen.add(row)
                    rows.append(row)

        for who, what in sorted((k for k in self.slots if k[0] == "you"), key=lambda k: rank(k[1])):
            take(sorted(self.slots[(who, what)], key=lambda r: -self.created[r]))
        for name, _ in sorted(self.people.display.items(), key=lambda kv: -kv[1][1]):
            for key in sorted(self.same("name:" + name)):
                for what in sorted(self.by_who.get(key, ()), key=rank):
                    take(sorted(self.slots.get((key, what), ()), key=lambda r: -self.created[r]))
        alive, created, _, said = self._arrays()[:4]
        rest = np.flatnonzero((alive > 0) & (said == 0))
        take(int(r) for r in rest[np.argsort(-created[rest], kind="stable")][:limit])
        return [self.ids[row] for row in rows[:limit]]

    def repeats(self):
        """(the one to keep, the one that only repeats it): facts that are word for word the same sentence, where nothing
        else was true in between. "You live in Austin", then Denver, then "You live in Austin" again is their history, not
        a repeat."""
        n = len(self.ids)
        if not n:
            return []
        alive, created, _, said = self._arrays()[:4]
        marks = np.frombuffer(self.marks, dtype=np.uint64, count=n)
        rows = np.flatnonzero((alive > 0) & (said == 0))
        if len(rows) < 2:
            return []
        order = rows[np.lexsort((-created[rows], marks[rows]))]  # the same sentence together, newest first
        same = marks[order][1:] == marks[order][:-1]
        pairs = []
        for i in np.flatnonzero(same):
            newer, older = int(order[i]), int(order[i + 1])
            if self._nothing_between(older, newer):
                pairs.append((self.ids[newer], self.ids[older]))
        return pairs

    def _nothing_between(self, older, newer):
        for who, what, value in self.read.get(older, ((), (), ()))[1]:
            group = self._group(who, what)
            if older in group and newer in group:
                a, b = sorted((group.index(older), group.index(newer)))
                if any(value not in self._values(row, what) for row in group[a + 1:b]):
                    return False
        return True

    def is_ended(self, mid):
        row = self.row.get(mid)
        return row is not None and bool(self.ended[row])

    def mentioning(self, keys):
        """Rows that may have a word starting with each of these (a few too many, never too few): for "forget about the
        interview". None when a key is one of the little words the index doesn't keep, so the caller has to read them all."""
        found = None
        for key in keys:
            key = str(key).lower()
            if len(key) < 2 or key in segments.STOP or not segments.words(key):
                return None
            same = segments.words(key)
            stem = key[:-2] if len(key) > 3 else key
            terms = [t for t in self.postings
                     if t in same or any(part.startswith(key) or (part.startswith(stem) and len(part) <= len(key)) for part in t.split("'"))]
            rows = self._rows_with(terms)
            found = rows if found is None else np.intersect1d(found, rows)
            if not len(found):
                return []
        if found is None:
            return []
        alive = np.frombuffer(self.alive, dtype=np.uint8, count=len(self.ids))
        return [int(r) for r in found[alive[found] > 0]]
