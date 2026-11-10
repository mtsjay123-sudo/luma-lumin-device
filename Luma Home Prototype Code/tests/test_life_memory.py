"""A life memory: found in milliseconds without reading every memory, each one sealed with its own key, knowing who's who,
what's still true, when things were said, and what it was never told."""
import random
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from luma.agent.runtime import Agent
from luma.llm import prompts
from luma.memory import life, meaning, segments, when
from luma.memory.index import BIG, Meanings
from luma.memory.store import Store

DAY = 86400
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc).timestamp()


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "s.db", self.root / "k")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def keep(self, text, days_ago=0, source="noticed_in_conversation", id=None):
        return self.store.put("memory", {"text": text, "source": source, "created": NOW - days_ago * DAY}, id)

    def found(self, question, **kw):
        return [m["text"] for m in self.store.search(question, now=NOW, **kw)["memories"]]


class TheIndex(Base):
    def test_it_ranks_exactly_like_reading_every_memory(self):
        rng = random.Random(4)
        vocab = "keys sister dana mom dog biscuit garage coffee tacos birthday june passport drawer car lavender candles gym audit wedding rent".split()
        for i in range(400):
            self.keep(" ".join(rng.choice(vocab) for _ in range(rng.randint(3, 7))), days_ago=400 - i)
        everything = self.store.memories()
        for _ in range(80):
            question = " ".join(rng.choice(vocab + ["where", "when", "who", "what", "my"]) for _ in range(rng.randint(1, 4)))
            self.assertEqual([m["id"] for m in self.store.recall(question)], [m["id"] for m in segments.recall(question, everything)], question)

    def test_finding_one_doesnt_open_them_all(self):
        self.store.put_many("memory", [{"id": f"n{i}", "text": f"note {i} about the garden", "created": NOW - i} for i in range(3000)])
        self.keep("Your passport is in the top desk drawer", id="passport")
        self.assertEqual(self.store.recall("where's my passport")[0]["id"], "passport")
        self.assertIsNone(self.store._all, "nothing asked for every memory")
        self.assertLess(len(self.store._hot), 50, "only the few it found were opened")

    def test_a_new_one_is_found_at_once_and_a_changed_one_by_its_new_words(self):
        self.store.recall("anything")
        row = self.keep("Your bike lock code is in your notes app")
        self.assertEqual(self.store.recall("bike lock")[0]["id"], row["id"])
        self.store.put("memory", {**row, "text": "Your spare tire is in the shed"}, row["id"])
        self.assertEqual(self.store.recall("bike lock"), [])
        self.assertEqual(self.store.recall("spare tire")[0]["id"], row["id"])
        self.store.delete("memory", row["id"])
        self.assertEqual(self.store.recall("spare tire"), [])

    def test_what_another_process_wrote_is_seen(self):
        self.store.recall("anything")
        other = Store(self.root / "s.db", self.root / "k")
        try:
            row = other.put("memory", {"text": "Your umbrella is in the trunk", "created": NOW})
            self.assertEqual(self.store.recall("umbrella")[0]["id"], row["id"])
            other.delete("memory", row["id"])
            self.assertEqual(self.store.recall("umbrella"), [])
        finally:
            other.close()

    def test_asked_while_its_still_being_read(self):
        self.store.put_many("memory", [{"id": f"n{i}", "text": f"note {i} about the garden", "created": NOW - i} for i in range(6000)])
        got = []
        threads = [threading.Thread(target=lambda: got.append(len(self.store.recall("garden")))) for _ in range(4)]
        for t in threads:
            t.start()
        late = self.keep("Your ladder is behind the shed")
        for t in threads:
            t.join()
        self.assertEqual(got, [5] * 4)
        self.assertEqual(self.store.recall("ladder")[0]["id"], late["id"], "kept while the index was being built, and still found")


class ItsOwnKey(Base):
    def raw(self):
        return (self.root / "s.db").read_bytes()

    def test_each_memory_is_sealed_with_a_key_of_its_own(self):
        a, b = self.keep("Mom loves lavender candles"), self.keep("Your car is on level 3")
        db = sqlite3.connect(self.root / "s.db")
        keys = dict(db.execute("SELECT id, wrapped FROM keys").fetchall())
        self.assertEqual(set(keys), {a["id"], b["id"]})
        self.assertNotEqual(keys[a["id"]], keys[b["id"]])
        self.assertNotIn(b"lavender", self.raw())
        self.assertNotIn(self.store._unwrap(keys[a["id"]], a["id"]), self.raw(), "the key itself is only ever stored wrapped")
        db.close()

    def test_forgetting_deletes_the_key_so_no_copy_opens_again(self):
        row = self.keep("My sister's name is Dana")
        db = sqlite3.connect(self.root / "s.db")
        copy = db.execute("SELECT payload FROM records WHERE id=?", (row["id"],)).fetchone()  # as an archive or another device holds it
        db.close()
        self.assertEqual(self.store._decode(copy)["text"], "My sister's name is Dana")
        self.store.delete("memory", row["id"])
        self.assertIsNone(self.store._decode(copy), "the sealed copy is still there, and can't be opened")
        self.assertEqual(self.store.recall("sister"), [])

    def test_memories_sealed_the_older_way_still_open_and_get_their_own_key_when_changed(self):
        import json
        old = {"id": "old1", "text": "Your keys are in the blue bowl", "created": NOW - DAY}
        with self.store.lock, self.store.db:
            self.store.db.execute("INSERT INTO records VALUES(?,?,?,?,?)", ("memory", "old1", NOW, NOW, self.store.cipher.encrypt(json.dumps(old).encode())))
            self.store._changed()
        self.assertEqual(self.store.recall("where are my keys")[0]["text"], "Your keys are in the blue bowl")
        self.assertEqual(self.store.get("memory", "old1")["text"], "Your keys are in the blue bowl")
        self.store.put("memory", {**old, "text": "Your keys are on the hook"}, "old1")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM keys WHERE id='old1'").fetchone()[0], 1)
        self.assertEqual(self.store.recall("where are my keys")[0]["text"], "Your keys are on the hook")

    def test_what_was_written_from_a_memory_goes_with_it(self):
        a, b = self.keep("You went to Lisbon with Dana"), self.keep("You love thai food")
        self.store.put("episode", {"day": "2026-05-03", "text": "A trip to Lisbon with Dana.", "from": [a["id"]]}, "episode:2026-05-03")
        self.store.put("episode", {"day": "2026-05-04", "text": "Thai food for dinner.", "from": [b["id"]]}, "episode:2026-05-04")
        self.store.delete("memory", a["id"])
        self.assertIsNone(self.store.get("episode", "episode:2026-05-03"))
        self.assertIsNotNone(self.store.get("episode", "episode:2026-05-04"))

    def test_erase_takes_the_keys_too(self):
        self.keep("My sister's name is Dana")
        self.store.erase()
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM keys").fetchone()[0], 0)
        self.assertEqual(self.store.recall("sister"), [])


class WhatsStillTrue(Base):
    def test_a_newer_fact_takes_the_older_ones_place_and_the_older_one_is_kept(self):
        self.keep("You live in Austin", days_ago=900)
        denver = self.keep("You moved to Denver", days_ago=200)
        found = self.store.search("where do i live", now=NOW)["memories"]
        self.assertEqual(found[0]["text"], "You moved to Denver")
        self.assertTrue(next(m for m in found if "Austin" in m["text"]).get("ended"), "kept, as what used to be true")
        self.assertEqual(self.found("where did i live before")[0], "You live in Austin")
        self.store.delete("memory", denver["id"])
        found = self.store.search("where do i live", now=NOW)["memories"]
        self.assertEqual(found[0]["text"], "You live in Austin")
        self.assertFalse(found[0].get("ended"), "forget the newer one and the older one is true again")

    def test_things_there_can_be_many_of_dont_replace_each_other(self):
        self.keep("I'm allergic to peanuts", days_ago=500)
        self.keep("I'm allergic to shellfish", days_ago=20)
        found = self.store.search("what am i allergic to", now=NOW)["memories"]
        self.assertEqual({m["text"] for m in found}, {"I'm allergic to peanuts", "I'm allergic to shellfish"})
        self.assertFalse(any(m.get("ended") for m in found))

    def test_a_newer_one_it_cant_read_still_comes_first(self):
        self.keep("You work at Brightside Dental as a hygienist", days_ago=700)
        self.keep("Big news, the job at the river clinic came through and I said yes", days_ago=30)
        self.assertIn("river clinic", self.found("where do i work")[0], "newer, about the same thing: it may be what's true now")


class WhosWho(Base):
    def setUp(self):
        super().setUp()
        self.keep("My sister's name is Dana", days_ago=900)
        self.keep("My sister's birthday is June 3", days_ago=800)
        self.keep("Dana (their sister) lives in Denver", days_ago=700)
        self.keep("Dana (their sister) is married to Theo", days_ago=600)
        self.keep("Theo works as a pilot", days_ago=500)
        self.keep("My brother's name is Marcus", days_ago=900)
        self.keep("Marcus (their brother) lives in Tulsa", days_ago=650)
        for i in range(40):
            self.keep(f"had lunch with Dana and talked about the {['audit', 'garden', 'lease'][i % 3]}", days_ago=i, source="said")

    def test_a_name_and_a_relation_are_one_person(self):
        self.assertEqual(self.found("what day was Dana born")[0], "My sister's birthday is June 3")
        self.assertEqual(self.found("where does my sister live")[0], "Dana (their sister) lives in Denver")
        self.assertEqual(self.found("where does my brother live")[0], "Marcus (their brother) lives in Tulsa")

    def test_two_memories_away(self):
        self.assertEqual(self.found("what does my sister's husband do for work")[0], "Theo works as a pilot")

    def test_one_stray_line_doesnt_change_who_someone_is(self):
        for i in range(6):
            self.keep(f"my sister Dana called about the wedding plans, day {i}", days_ago=i, source="said")
        self.keep("my sister Kim (a friend calls her that) stopped by", days_ago=1, source="said")
        self.assertEqual(self.found("where does my sister live")[0], "Dana (their sister) lives in Denver")

    def test_forgetting_who_someone_is_unlinks_them(self):
        name = next(m for m in self.store.memories() if m["text"] == "My sister's name is Dana")
        self.store.delete("memory", name["id"])
        for m in self.store.kept():
            if "(their sister)" in m["text"]:
                self.store.delete("memory", m["id"])
        self.assertNotIn("Dana (their sister) lives in Denver", self.found("where does my sister live"))


class WhenItWasSaid(Base):
    def setUp(self):
        super().setUp()
        self.keep("You went to Lisbon with Dana", days_ago=(NOW - datetime(2024, 5, 12, tzinfo=timezone.utc).timestamp()) / DAY, source="said")
        self.keep("You went to Kyoto with Sam", days_ago=(NOW - datetime(2025, 9, 3, tzinfo=timezone.utc).timestamp()) / DAY, source="said")
        self.keep("You went to Banff with Theo", days_ago=(NOW - datetime(2026, 4, 20, tzinfo=timezone.utc).timestamp()) / DAY, source="said")
        for i in range(300):
            self.keep(f"had tacos and talked about the trip, day {i}", days_ago=i * 3, source="said")

    def test_a_month_a_year_and_a_season(self):
        self.assertEqual(self.found("where did i travel in may 2024")[0], "You went to Lisbon with Dana")
        self.assertEqual(self.found("what trip did i take in 2025")[0], "You went to Kyoto with Sam")
        self.assertEqual(self.found("where did i go last spring")[0], "You went to Banff with Theo")

    def test_nothing_from_then(self):
        found = self.store.search("where did i travel in march 2019", now=NOW)
        self.assertFalse(found["known"])
        self.assertEqual(found["memories"], [])

    def test_the_words_for_time(self):
        day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")  # noqa: E731
        for said, start, end in [("in may 2024", "2024-05-01", "2024-06-01"), ("last spring", "2026-03-01", "2026-06-01"), ("in 2024", "2024-01-01", "2025-01-01"),
                                 ("last month", "2026-10-01", "2026-11-01"), ("yesterday", "2026-10-31", "2026-11-01"), ("last winter", "2025-12-01", "2026-03-01")]:
            got = when.window(f"what happened {said}", NOW)
            self.assertEqual((day(got[0]), day(got[1])), (start, end), said)
        self.assertIsNone(when.window("where do i live", NOW))
        self.assertIsNone(when.window("what may happen", NOW))


class NeverTold(Base):
    def setUp(self):
        super().setUp()
        self.keep("My sister's name is Dana", days_ago=900)
        self.keep("Dana (their sister) lives in Denver", days_ago=700)
        self.keep("had lunch with Dana at the taco place", days_ago=3, source="said")

    def test_nobody_by_that_name(self):
        found = self.store.search("what's my uncle's name", now=NOW)
        self.assertFalse(found["known"])
        self.assertEqual(found["memories"], [])
        self.assertIn("uncle", found["why"])

    def test_nothing_mentions_the_thing(self):
        found = self.store.search("what's the combination for my storage locker", now=NOW)
        self.assertFalse(found["known"])
        self.assertEqual(found["memories"], [])

    def test_it_knows_the_person_but_not_the_thing_so_it_says_which_word_it_never_saw(self):
        found = self.store.search("what's Dana's middle name", now=NOW)
        self.assertTrue(found["known"])
        self.assertIn("middle", found["unseen"])
        self.assertIn("My sister's name is Dana", [m["text"] for m in found["memories"]], "what it does know goes to the brain, which says the rest")

    def test_something_it_does_know_is_never_called_unknown(self):
        for question in ("what's my sister's name", "where does Dana live", "where does my sister live"):
            self.assertTrue(self.store.search(question, now=NOW)["known"], question)


class Meaning(Base):
    def test_many_meanings_fast_and_right(self):
        rng = np.random.default_rng(3)
        count = BIG + 5000
        meanings = Meanings(64)
        data = rng.standard_normal((count, 64)).astype(np.float32)
        for row in range(count):
            meanings.put(row, data[row])
        alive = np.ones(count, dtype=np.uint8)
        for target in (7, 12345, count - 1):
            asked = data[target] + 0.25 * rng.standard_normal(64).astype(np.float32)
            self.assertEqual(meanings.near(asked, alive, 5)[0][1], target)
        alive[12345] = 0
        self.assertNotEqual(meanings.near(data[12345], alive, 5)[0][1], 12345, "a forgotten memory's meaning is never found")

    def test_meanings_are_kept_small(self):
        meaning.embedder = lambda text: [float("mom" in text.lower()), float("candle" in text.lower() or "scent" in text.lower()), 0.2]
        meaning._cache.clear()
        try:
            row = self.keep("Mom loves lavender candles")
            meaning.catch_up(self.store, self.store.memories(), wait=True)
            record = self.store.get("vector", "vector:" + row["id"])
            self.assertIn("h", record)
            self.assertNotIn("v", record)
            self.assertIn("Mom loves lavender candles", [m["text"] for m in self.store.recall("what scent does my mom like")])
        finally:
            meaning.embedder = None
            meaning._cache.clear()


class TheLifeFile(Base):
    def setUp(self):
        super().setUp()
        self.keep("Your name is Jay", 900)
        self.keep("You live in Austin", 900)
        self.keep("You moved to Denver", 100)
        self.keep("Your sister's name is Dana", 800)
        self.keep("Dana (their sister) lives in Portland", 700)
        self.keep("You're allergic to penicillin", 600)
        self.keep("You started therapy for anxiety in March", 200)
        self.keep("we went to Lisbon in May and it rained the whole time", 170, source="said")

    def test_its_whats_true_now_about_them_first_then_their_people(self):
        lines = life.file(self.store).splitlines()
        self.assertIn("- You moved to Denver", lines)
        self.assertNotIn("- You live in Austin", lines, "a newer fact took its place")
        self.assertLess(lines.index("- Your name is Jay"), lines.index("- Dana (their sister) lives in Portland"))
        self.assertFalse(any("Lisbon" in line for line in lines), "a line of talk isn't a fact Luma keeps")

    def test_its_kept_until_something_changes(self):
        first = life.file(self.store)
        self.assertEqual(self.store.get("life", life.FILE)["text"], first)
        reads, real = [], self.store.whats_true
        self.store.whats_true = lambda *a, **k: reads.append(1) or real(*a, **k)
        self.assertEqual(life.file(self.store), first)
        self.assertEqual(reads, [], "nothing changed, so nothing was read again")
        self.keep("Your favorite band is Khruangbin")
        self.assertIn("Khruangbin", life.file(self.store))
        self.assertEqual(reads, [1])
        self.assertEqual(life.file(self.store), life.file(self.store))
        self.assertEqual(reads, [1])

    def test_with_company_the_private_things_are_left_out_and_that_version_isnt_kept(self):
        text = life.file(self.store, private=False)
        self.assertNotIn("therapy", text)
        self.assertIn("Denver", text)
        self.assertIsNone(self.store.get("life", life.FILE))
        self.assertIn("therapy", life.file(self.store))

    def test_forgetting_something_takes_it_out_of_the_file_and_the_files_key_goes(self):
        life.file(self.store)
        db = sqlite3.connect(str(self.root / "s.db"))
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM keys WHERE id=?", (life.FILE,)).fetchone()[0], 1)
            row = next(m for m in self.store.memories() if "penicillin" in m["text"])
            self.store.delete("memory", row["id"])
            self.assertIsNone(self.store.get("life", life.FILE), "the kept file went with the memory it was written from")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM keys WHERE id=?", (life.FILE,)).fetchone()[0], 0)
        finally:
            db.close()
        self.assertNotIn("penicillin", life.file(self.store))

    def test_it_stays_inside_its_room_and_whats_about_them_is_what_stays(self):
        self.store.put_many("memory", [{"id": f"n{i}", "text": f"Your note {i} is in folder {i}", "created": NOW - i} for i in range(400)])
        text = life.file(self.store, room=1500)
        self.assertLessEqual(len(text), 1800)
        self.assertIn("Your name is Jay", text)
        self.assertIn("Denver", text)


class TheDaysStory(Base):
    def said(self, text, days_ago, minute=0):
        return self.store.put("memory", {"text": text, "source": "said", "created": NOW - days_ago * DAY + minute * 60})

    def days(self):
        return sorted(e["id"] for e in self.store.all("episode", 1000) if e.get("span") == "day")

    def test_yesterday_gets_a_story_made_of_what_mattered_most_in_their_own_words(self):
        self.said("had cereal for breakfast and watched tv most of the morning", 1, 1)
        promoted = self.said("i got promoted to shift lead today, still can't believe it", 1, 2)
        self.said("drove up to Tahoe with Dana for the afternoon", 1, 3)
        self.said("the bus was late again this morning which was annoying", 1, 4)
        self.assertEqual(life.write_episodes(self.store, NOW), 2, "yesterday, and October (it ended yesterday)")
        self.assertEqual(self.days(), ["episode:2026-10-31"])
        story = self.store.get("episode", "episode:2026-10-31")
        self.assertEqual(story["span"], "day")
        self.assertIn("promoted to shift lead", story["text"])
        self.assertIn("Tahoe", story["text"])
        self.assertNotIn("bus was late", story["text"], "three lines a day: the ones that mattered")
        self.assertIn(promoted["id"], story["from"])
        self.assertEqual(life.write_episodes(self.store, NOW), 0, "once is enough")
        self.assertIn("(2026-10-31)", life.file(self.store), "the last few days are in the life file")

    def test_forgetting_a_line_takes_the_story_and_the_night_writes_it_again_without_it(self):
        promoted = self.said("i got promoted to shift lead today, still can't believe it", 1, 2)
        self.said("drove up to Tahoe with Dana for the afternoon", 1, 3)
        life.write_episodes(self.store, NOW)
        self.store.delete("memory", promoted["id"])
        self.assertIsNone(self.store.get("episode", "episode:2026-10-31"))
        self.assertIsNone(self.store.get("episode", "episode:2026-10"), "the month's story had it too")
        self.assertEqual(life.write_episodes(self.store, NOW), 2)
        self.assertNotIn("promoted", self.store.get("episode", "episode:2026-10")["text"])
        again = self.store.get("episode", "episode:2026-10-31")
        self.assertNotIn("promoted", again["text"])
        self.assertIn("Tahoe", again["text"])

    def test_an_old_days_story_is_written_again_too(self):
        gone = self.said("i got engaged at the lake house this weekend", 300, 1)
        self.said("we flew to Chicago for the weekend to see my cousin", 300, 2)
        life.write_episodes(self.store, NOW, days=400)
        day = datetime.fromtimestamp(NOW - 300 * DAY, timezone.utc).date().isoformat()
        self.assertIn("engaged", self.store.get("episode", "episode:" + day)["text"])
        self.store.delete("memory", gone["id"])
        self.assertIsNone(self.store.get("episode", "episode:" + day))
        life.write_episodes(self.store, NOW)  # tonight only catches up 45 days, and the days whose story was taken
        again = self.store.get("episode", "episode:" + day)
        self.assertIn("Chicago", again["text"])
        self.assertNotIn("engaged", again["text"])

    def test_a_month_thats_over_gets_one_from_its_big_moments(self):
        self.said("i got promoted to shift lead today", 20)
        self.said("we flew to Chicago for the weekend to see my cousin", 12)
        self.said("made pasta again tonight, nothing special", 15)
        life.write_episodes(self.store, NOW)
        month = self.store.get("episode", "episode:2026-10")
        self.assertEqual(month["span"], "month")
        self.assertIn("promoted", month["text"])
        self.assertIn("Chicago", month["text"])
        self.assertNotIn("pasta", month["text"])
        start = datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()
        self.assertEqual([e["id"] for e in life.episodes(self.store, start, NOW)], ["episode:2026-10"])

    def test_a_story_is_never_shown_as_a_memory_of_its_own(self):
        self.said("drove up to Tahoe with Dana for the afternoon", 1)
        life.write_episodes(self.store, NOW)
        self.assertEqual(len(self.store.memories()), 1)
        self.assertEqual(self.store.kept_counts(), (0, 1))


class Sleep(Base):
    def test_the_same_sentence_kept_twice_becomes_one(self):
        self.store.put_many("memory", [{"id": "old", "text": "Your gym bag is in the hall closet", "created": NOW - 9 * DAY},
                                       {"id": "new", "text": "Your gym bag is in the hall closet", "created": NOW - 2 * DAY},
                                       {"id": "other", "text": "Your gym shoes are in the car", "created": NOW - 3 * DAY}])
        did = life.sleep(self.store, NOW)
        self.assertEqual(did["merged"], 1)
        self.assertEqual(sorted(m["id"] for m in self.store.memories()), ["new", "other"])
        self.assertEqual(life.sleep(self.store, NOW)["merged"], 0)

    def test_but_not_when_something_else_was_true_in_between(self):
        self.store.put_many("memory", [{"id": "a", "text": "You live in Austin", "created": NOW - 900 * DAY},
                                       {"id": "b", "text": "You moved to Denver", "created": NOW - 400 * DAY},
                                       {"id": "c", "text": "You live in Austin", "created": NOW - 10 * DAY}])
        self.assertEqual(life.sleep(self.store, NOW)["merged"], 0, "they lived in Austin twice: both are their history")
        self.assertEqual(len(self.store.memories()), 3)
        self.assertEqual(self.found("where do i live")[0], "You live in Austin")
        self.assertEqual(self.found("where did i live before")[0], "You moved to Denver")

    def test_older_memories_get_a_key_of_their_own(self):
        import json
        blob = self.store.cipher.encrypt(json.dumps({"id": "legacy", "text": "Your bike is in the shed", "created": NOW - DAY}).encode())
        with self.store.db:
            self.store.db.execute("INSERT INTO records VALUES(?,?,?,?,?)", ("memory", "legacy", NOW - DAY, NOW - DAY, blob))
            self.store._changed()
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM keys WHERE id='legacy'").fetchone()[0], 0)
        self.assertEqual(life.sleep(self.store, NOW)["resealed"], 1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM keys WHERE id='legacy'").fetchone()[0], 1)
        self.assertEqual(self.store.recall("where's my bike")[0]["id"], "legacy")
        self.store.delete("memory", "legacy")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM keys WHERE id='legacy'").fetchone()[0], 0)

    def test_it_writes_yesterday_and_refreshes_the_life_file(self):
        self.keep("Your name is Jay", 30)
        self.store.put("memory", {"text": "drove up to Tahoe with Dana for the afternoon", "source": "said", "created": NOW - DAY})
        did = life.sleep(self.store, NOW)
        self.assertEqual(did["episodes"], 2, "yesterday, and the month that ended with it")
        kept = self.store.get("life", life.FILE)
        self.assertIn("Your name is Jay", kept["text"])
        self.assertIn("Tahoe", kept["text"])


class InLuma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.now = [NOW]
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.clock = lambda: self.now[0]
        self.agent.use_model = True
        for extra in ("think_first", "deliberate", "deep_mind"):
            self.store.set_setting(extra, False)  # one trip to the brain per reply, so what it was given is plain to see
        self.seen = []

        def planner(messages, context, allowed, mode):
            self.seen.append(context)
            return {"type": "reply", "text": "Okay."}
        self.agent.planner = planner

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def texts(self):
        return [m["text"] for m in self.store.all("memory", 1000)]

    def test_no_cap_and_no_word_about_a_plan(self):
        self.assertFalse(hasattr(self.agent, "FREE_MEMORIES"))
        for i in range(250):
            self.assertIsNotNone(self.agent.remember_fact(f"Your note {i} is in folder {i}"))
        quota = self.agent.memory_quota()
        self.assertEqual((quota["used"], quota["limit"], quota["full"]), (250, None, False))
        import inspect
        from luma.agent import runtime
        self.assertNotIn("memory's full", inspect.getsource(runtime))

    def test_a_fact_it_already_has_isnt_kept_twice_and_keys_still_move(self):
        self.agent.remember_fact("Your favorite color is green")
        self.assertIsNone(self.agent.remember_fact("your favorite color is green"))
        self.agent.remember_fact("Your keys are in the kitchen drawer")
        self.agent.remember_fact("Your keys are on the hook by the door")
        self.assertEqual([t for t in self.texts() if "keys" in t], ["Your keys are on the hook by the door"])

    def test_what_they_tell_luma_about_their_life_is_kept_as_they_said_it(self):
        self.agent.chat("we went to Lisbon in May with Dana and it rained the whole time")
        self.assertIn("we went to Lisbon in May with Dana and it rained the whole time", self.texts())
        quota = self.agent.memory_quota()
        self.assertEqual(quota["lines"], 1)
        self.assertEqual(quota["used"], 0, "a line of talk isn't counted as a fact, or listed on the Memory page")
        from luma.agent import memory_folder
        self.assertEqual(sum(len(k["items"]) for k in memory_folder.folder(self.agent)["kinds"]), 0)

    def test_what_they_just_said_isnt_handed_back_as_a_memory(self):
        """A line of talk Luma kept is a memory once the conversation has moved past it. While the brain can still see
        them say it a few messages up, it's only the conversation: handed back as a "saved fact" it muddles a small
        brain. (Two home brains lost the lonely moment of the 10-moment test to exactly this: they were handed the two
        lines below while answering it.)"""
        def handed_back(message):
            """The kept lines of talk the brain was given while answering this message (on any of its trips to the brain)."""
            before = len(self.seen)
            self.agent.chat(message)
            return [m["text"] for context in self.seen[before:] for m in context if m.get("source") == "said"]

        self.agent.chat("my dad passed away last night and i can't stop thinking about it")
        self.agent.chat("omg i got into my dream school, the letter came today")
        self.assertEqual(handed_back("it's been so hard since my dad passed away"), [], "lines still in the conversation came back as memories")
        self.assertEqual(len([t for t in self.texts() if "last night" in t or "dream school" in t]), 2, "they're still kept")
        # A new conversation: the brain can't see them say it any more, so now it's a memory, with its day.
        self.agent.history.clear()
        self.now[0] += 2 * 86400
        back = handed_back("i still can't believe my dad passed away")
        self.assertTrue(any("my dad passed away last night" in line and line.startswith("(They said, ") for line in back), back)
        # And in a long conversation, once it has scrolled out of what the brain is given.
        self.agent.history.clear()
        self.agent.chat("my sister moved to a tiny town in the mountains last month")
        from luma.llm import brain
        for i in range(brain.LOCAL_WINDOW):
            self.agent.history.append({"role": "user" if i % 2 == 0 else "assistant", "content": f"filler line number {i}"})
        back = handed_back("i keep meaning to go see my sister in the mountains")
        self.assertTrue(any("tiny town in the mountains" in line for line in back), back)

    def test_a_side_prompt_isnt_handed_a_line_it_already_shows(self):
        """A question Luma thinks over from several sides gets a prompt of its own: the last few lines of the conversation,
        then what Luma remembers. A line that's right there in the conversation isn't also handed over as a memory. (In
        the human test "Should I cook for her or take her out?" came with "I haven't seen her since last Christmas" twice.)"""
        self.agent.chat("i haven't seen my cousin dana since last winter")
        prompt = self.agent._recent_talk("should i bake for dana or take her to that noodle place?")
        self.assertIn("Them: i haven't seen my cousin dana since last winter", prompt)
        self.assertNotIn("What you remember that may matter here", prompt)
        # A new conversation: the line isn't in front of the brain any more, so now it's something Luma remembers.
        self.agent.history.clear()
        prompt = self.agent._recent_talk("should i bake for my cousin dana or take her out?")
        self.assertIn("What you remember that may matter here (use it if it does): i haven't seen my cousin dana since last winter", prompt)

    def test_asking_what_to_do_about_someone_isnt_asking_its_memory(self):
        """ "Should I tell my best friend her boyfriend is cheating on her?" names a friend Luma was never told about. It
        isn't asking who she is, so the brain isn't told to say it "hasn't been told". (Human Test v2 has this very line,
        and the note was going with it.)"""
        advice = ["Should I tell my best friend her boyfriend is cheating on her?", "should i call my mom tonight", "do you think my boss hates me?",
                  "what should i get my sister for her birthday", "how do i tell my dad i'm dropping out", "is it weird that my roommate never talks to me?",
                  "be real with me, should i go to my ex's wedding?", "would you text my ex back if you were me?", "can i bring my dog to the party?",
                  "am i wrong for being mad at my sister?", "why does my brother always do this", "what do you think about my friend moving in with me?",
                  "my mom keeps calling, should i pick up?", "how can i make my wife feel better", "is my boyfriend being unfair here?",
                  "what do i do about my sister", "my coworker asked where i live and how long it's been, what should i tell her?"]
        memory = ["where does my sister live", "what's my brother's name", "does my mom like tulips?", "is my sister still in Denver?",
                  "do you remember my landlord's name", "when is my dad's birthday", "how old is my daughter", "what did i tell you about my boss",
                  "who is my dentist", "what's my wifi password", "any idea what my uncle does for work these days?", "did i tell you what my mom said?",
                  "should i know my landlord's name? do you remember it"]
        for line in advice:
            self.assertFalse(self.agent._asks_memory(line), line)
        for line in memory:
            self.assertTrue(self.agent._asks_memory(line), line)
        # and through a whole turn: no "never told" note goes to the brain with the advice question, and it still goes with the memory one
        self.agent.chat("Should I tell my best friend her boyfriend is cheating on her?")
        self.assertFalse(any(m.get("note") for context in self.seen for m in context), [m for c in self.seen for m in c if m.get("note")])
        self.seen.clear()
        self.agent.chat("any idea what my best friend does for work these days?")
        self.assertTrue(any("checked for this message" in m["text"] for context in self.seen for m in context if m.get("note")))

    def test_questions_requests_and_unsafe_moments_arent_kept(self):
        for said in ("what should i cook tonight for the four of us", "remind me to call the dentist tomorrow morning please",
                     "i keep thinking everyone would be better off without me", "ok cool"):
            self.agent.chat(said)
        self.assertEqual(self.texts(), [])

    def test_it_stops_with_learning_from_chat_and_forget_that_takes_the_line(self):
        self.agent.chat("i started a new job at the river clinic on monday")
        self.assertEqual(len(self.texts()), 1)
        self.agent.chat("forget that")
        self.assertEqual(self.texts(), [])
        self.store.set_setting("learn_from_chat", False)
        self.agent.chat("i started a new job at the river clinic on monday")
        self.assertEqual(self.texts(), [])

    def test_forget_about_takes_the_talk_too_without_reading_everything(self):
        self.store.put_many("memory", [{"id": f"n{i}", "text": f"note {i} about the garden", "source": "said", "created": NOW - i} for i in range(2000)])
        self.agent.chat("my interview at the hospital is on thursday and i'm nervous about it")
        self.agent.remember_fact("Your interview is at the hospital")
        self.store._hot.clear()
        self.agent.forget_about("the interview")
        self.assertFalse(any("interview" in t for t in self.texts()))
        self.assertLess(len(self.store._hot), 50)
        self.assertEqual(len(self.texts()), 1000, "nothing else was touched")

    def test_the_brain_gets_whats_true_now_and_is_told_what_was_never_said(self):
        self.store.put("memory", {"text": "You live in Austin", "created": NOW - 900 * DAY})
        self.store.put("memory", {"text": "You moved to Denver", "created": NOW - 100 * DAY})
        self.assertIn("Denver", self.agent.chat("where do i live?")["text"], "answered straight from memory: what's true now")
        self.agent.chat("my coworker asked where i live and how long it's been, what should i tell her?")
        facts = next([m["text"] for m in context if not m.get("note")] for context in self.seen if context)
        self.assertEqual(facts[0], "You moved to Denver")
        self.assertTrue(any(t.startswith("(Used to be true, not anymore) You live in Austin") for t in facts))
        self.assertFalse(any(m.get("note") for context in self.seen for m in context), "a long question with words it hasn't seen isn't a 'never told'")
        self.seen.clear()
        self.agent.chat("any idea what my uncle does for work these days?")
        told = next(context for context in self.seen if context)
        note = next(m["text"] for m in told if m.get("note"))
        self.assertIn("nobody saved as my uncle", note)
        self.assertIn("Never guess", note)
        steady, turn = prompts.build_plan_parts(told, {}, "friend", {}, "now")
        self.assertIn("nobody saved as my uncle", turn)
        self.assertNotIn("nobody saved as my uncle", steady)

    def test_a_statement_never_gets_a_you_never_told_me(self):
        self.agent.chat("my uncle passed away on sunday and the funeral is friday")
        self.assertFalse(any(m.get("note") for context in self.seen for m in context), "they're telling, not asking")

    def test_with_company_in_the_room_private_things_wait_until_asked(self):
        self.store.put("memory", {"text": "You started therapy for anxiety in March", "created": NOW - 100 * DAY})
        self.store.put("memory", {"text": "You love thai food", "created": NOW - 100 * DAY})
        self.agent.chat("heads up, my friends are here")
        self.assertTrue(self.agent._company())
        self.seen.clear()
        self.agent.chat("thinking about therapy stuff and thai food tonight")
        shown = [m["text"] for context in self.seen for m in context]
        self.assertFalse(any("anxiety" in t for t in shown))
        self.assertTrue(any("thai food" in t for t in shown))
        self.assertTrue(any("company in the room" in t for t in shown))
        self.seen.clear()
        self.agent.chat("when did i start therapy?")
        self.assertTrue(any("anxiety" in m["text"] for context in self.seen for m in context), "they asked, so it's theirs to hear")
        self.agent.chat("ok they left")
        self.assertFalse(self.agent._company())
        self.now[0] += 60
        self.agent.chat("it's just me")
        self.assertFalse(self.agent._company(), "a lonely line is never taken for company leaving")


    def test_something_true_again_is_true_again(self):
        self.agent.remember_fact("You live in Austin")
        self.now[0] += 400 * DAY
        self.agent.remember_fact("You moved to Denver")
        self.assertIn("Denver", self.agent.chat("where do i live?")["text"])
        self.now[0] += 400 * DAY
        self.assertIsNotNone(self.agent.remember_fact("You live in Austin"), "it was replaced, and now it's true again")
        self.assertIn("Austin", self.agent.chat("where do i live?")["text"])
        self.assertEqual(len(self.texts()), 3, "all three are their history")

    def night(self, hour=3, days=1):
        local = datetime.fromtimestamp(self.now[0], self.agent.zone).replace(hour=hour, minute=10, second=0, microsecond=0)
        self.now[0] = local.timestamp() + days * DAY
        return datetime.fromtimestamp(self.now[0], self.agent.zone).date().isoformat()

    def test_it_tidies_once_a_night(self):
        self.store.put_many("memory", [{"id": "old", "text": "Your gym bag is in the hall closet", "created": NOW - 9 * DAY},
                                       {"id": "new", "text": "Your gym bag is in the hall closet", "created": NOW - 2 * DAY}])
        day = self.night()
        self.store.put("memory", {"text": "drove up to Tahoe with Dana for the afternoon", "source": "said", "created": self.now[0] - DAY})
        self.agent.tick()
        self.agent._sleeper.join(20)
        self.assertEqual(self.store.setting("last_sleep"), day)
        self.assertEqual([m["id"] for m in self.store.memories() if "gym bag" in m["text"]], ["new"])
        self.assertEqual(len([e for e in self.store.all("episode", 50) if e.get("span") == "day"]), 1)
        first = self.agent._sleeper
        self.now[0] += 1800
        self.agent.tick()
        self.assertIs(self.agent._sleeper, first, "once a night")

    def test_it_doesnt_tidy_before_three_or_mid_conversation(self):
        self.night(hour=1)
        self.agent.tick()
        self.assertIsNone(self.agent._sleeper)
        self.night(hour=3, days=0)
        self.agent.last_reply_at = self.now[0] - 60  # they were talking a minute ago
        self.agent.tick()
        self.assertIsNone(self.agent._sleeper)
        self.now[0] += 3600
        self.agent.tick()
        self.assertIsNotNone(self.agent._sleeper)
        self.agent._sleeper.join(20)


if __name__ == "__main__":
    unittest.main()
