"""The phrase bank: over a million ways people in different communities talk, each labeled with the truth.

Every slang word in every phrase comes from Luma's lexicon, so the labels can be checked: the words are recognized in
the finished sentence, the meanings are the lexicon's own, the community is recognized from how someone talks, and the
words Luma may use back are all real ones. Nothing guessed, nothing made up."""
import unittest

from luma.agent import phrasebank, slang


class PhraseBankTests(unittest.TestCase):
    def test_over_a_million_phrases_across_many_communities(self):
        self.assertGreaterEqual(phrasebank.count(), 1_000_000)
        sizes = phrasebank.by_community()
        self.assertGreaterEqual(len(sizes), 25)
        self.assertEqual(sum(sizes.values()), phrasebank.count())
        self.assertTrue(all(n >= 100 for n in sizes.values()), {c: n for c, n in sizes.items() if n < 100})
        self.assertGreaterEqual(sum(1 for n in sizes.values() if n >= 10_000), 12, "a dozen big circles, not one giant one")

    def test_every_community_is_one_luma_knows(self):
        self.assertEqual([c for c in phrasebank.PACKS if c not in slang.ORIGINS], [])

    def test_every_slang_word_in_every_pack_is_in_the_lexicon(self):
        missing = [(c, role, w) for c, pack in phrasebank.PACKS.items() for role, words in pack["roles"].items()
                   for w in words if not slang.find(w)]
        self.assertEqual(missing, [], "a pack word with no lexicon entry would be a made-up label")

    def test_labels_are_the_lexicon_and_are_found_in_the_sentence(self):
        for ph in phrasebank.sample(1500, seed=3):
            self.assertTrue(ph["terms"], ph)
            in_text = {e.term for _, e in slang.find(ph["text"])}
            for said, meaning, origins in ph["terms"]:
                entry = slang.find(said)[0][1]
                self.assertEqual(meaning, entry.meaning, ph)
                self.assertEqual(origins, entry.origins, ph)
                self.assertIn(entry.term, in_text, f"{said!r} isn't recognized in {ph['text']!r}")

    def test_same_number_same_phrase_and_no_repeats(self):
        self.assertEqual(phrasebank.phrase(123_456), phrasebank.phrase(123_456))
        self.assertEqual(phrasebank.phrase(phrasebank.count() - 1)["community"], list(phrasebank.PACKS)[-1])
        with self.assertRaises(IndexError):
            phrasebank.phrase(phrasebank.count())
        texts = [phrasebank.phrase(i)["text"] for i in range(0, phrasebank.count(), 997)]
        self.assertEqual(len(texts), len(set(texts)), "different numbers give different phrases")

    def test_no_leftover_slots_and_grammar_holds(self):
        for ph in phrasebank.sample(800, seed=11):
            self.assertNotIn("{", ph["text"])
            self.assertNotRegex(ph["text"], r"\b(?!fr\b|sharp\b)(\w+) \1\b", "no doubled words ('fr fr' and 'sharp sharp' are said that way)")
        picked = [ph["text"] for ph in phrasebank.sample(4000, seed=5) if "the fries " in ph["text"]]
        self.assertTrue(all(" fries was " not in t and " fries is " not in t for t in picked), picked[:3])

    def test_the_community_is_recognized_from_how_someone_talks(self):
        right = 0
        communities = [c for c in phrasebank.PACKS if c not in ("internet",)]
        for c in communities:
            stats = {"n": 0}
            for ph in phrasebank.sample(12, seed=21, community=c):
                stats = slang.learn(stats, ph["text"])
                stats["n"] += 1
            right += c in slang.leaning(stats)
        self.assertGreaterEqual(right / len(communities), 0.8, "most circles are recognized from a dozen messages")

    def test_one_borrowed_word_makes_nobody_a_member(self):
        stats = {"n": 0}
        for text in ["heard", "ok heard", "heard, thanks"]:
            stats = slang.learn(stats, text)
            stats["n"] += 1
        self.assertEqual(slang.leaning(stats), [])

    def test_words_luma_may_use_back_are_real_and_casual(self):
        for c in phrasebank.PACKS:
            for term, meaning in phrasebank.voice(c):
                entry = slang.find(term)[0][1]
                self.assertEqual((entry.meaning, entry.register), (meaning, "c"), (c, term))

    def test_every_circle_has_its_own_jokes(self):
        for c, pack in phrasebank.PACKS.items():
            self.assertGreaterEqual(len(pack["bits"]), 2, c)
            self.assertEqual(phrasebank.joke(c, 0), pack["bits"][0])
            self.assertEqual(phrasebank.joke(c, len(pack["bits"])), pack["bits"][0])
            self.assertTrue(all(not slang.clean(b) or slang.clean(b) == b for b in pack["bits"]), c)
        self.assertIsNone(phrasebank.joke("nobody"))


class TalkingBackTests(unittest.TestCase):
    def talk(self, messages):
        stats = {"n": 0}
        for m in messages:
            stats = slang.learn(stats, m)
            stats["n"] += 1
        return stats

    def test_luma_mirrors_a_kitchen_crew_with_real_words_and_their_kind_of_joke(self):
        stats = self.talk(["86 the salmon, heard?", "yes chef, behind!", "we got slammed, all day four burgers",
                           "in the weeds tonight", "the pass is dying, fire it"])
        self.assertEqual(slang.leaning(stats), ["kitchen"])
        note = slang.register_note(stats)
        self.assertIn("restaurant and kitchen crews", note)
        self.assertIn("never make slang up", note)
        self.assertIn(phrasebank.joke("kitchen", stats["n"]), note)
        listed = note.split("never make slang up): ")[1].split(". The kind of joke")[0]
        for term in [t.split("”")[0] for t in listed.split("“")[1:]]:
            self.assertTrue(slang.find(term), term)
            self.assertNotIn(term, stats["terms"], "words they already use aren't offered back as new")

    def test_no_jokes_in_kids_mode(self):
        stats = self.talk(["that set was bussin fr", "no cap the fit is fire", "deadass that party was lit", "that drop was hard bruh"])
        self.assertIn("The kind of joke", slang.register_note(stats))
        self.assertNotIn("The kind of joke", slang.register_note(stats, kids=True))

    def test_plain_talkers_get_no_slang_pushed_on_them(self):
        stats = self.talk(["Could you remind me about the dentist at 3?", "What's the weather tomorrow?", "Please add milk to the list.",
                           "Thanks, that's helpful.", "Send the report to Dana.", "How long is the drive to Tahoe?"])
        note = slang.register_note(stats)
        self.assertNotIn("from their circle", note)
        self.assertIn("without slang", note)


if __name__ == "__main__":
    unittest.main()
