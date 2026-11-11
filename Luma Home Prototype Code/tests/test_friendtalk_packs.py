"""The packs of best-friend talk (luma.agent.friendtalk.packs): what the sub-agents wrote, the things people say, as
frames with blanks. Half of the frames and half of every blank's values are held out (friendtalk.half): the small model
never learns from them and nobody reads them. They say how much is heard on wording nothing was fitted to.

A failing test here prints numbers, never a held-out line."""
import random
import re
import sys
import unittest
from pathlib import Path

from luma.agent import friendtalk

ROOT = Path(__file__).resolve().parents[1]


class ThePacks(unittest.TestCase):
    """What the sub-agents wrote: the things people say, as frames with blanks."""

    def test_they_are_well_formed(self):
        packs = friendtalk.every_pack()
        self.assertGreaterEqual(len(packs), 8)
        for pack in packs:
            self.assertTrue(pack["family"])
            frames = pack["frames"]
            self.assertEqual(len(frames), len(set(frames)), pack["family"])
            for move, frame in frames:
                self.assertIn(move, friendtalk.MOVES, frame)
                for slot in re.findall(r"\{(\w+)\}", frame):
                    self.assertIn(slot, pack["slots"], frame)
            for name, values in pack["slots"].items():
                self.assertEqual(len(values), len(set(values)), f"{pack['family']}.{name}")

    def test_there_are_over_a_hundred_thousand_scenarios(self):
        self.assertGreaterEqual(friendtalk.count(), 100_000)

    def test_a_scenario_says_what_they_said_and_what_a_friend_does(self):
        seen = list(friendtalk.scenarios(500, seed=4))
        self.assertEqual(len(seen), 500)
        self.assertEqual(len({row["said"] for row in seen}), 500)
        for row in seen:
            self.assertNotIn("{", row["said"])
            self.assertIn(row["move"], friendtalk.MOVES)
            self.assertTrue(row["family"])
        again = [row["said"] for row in friendtalk.scenarios(500, seed=4)]
        self.assertEqual(again, [row["said"] for row in seen])   # the same seed, the same scenarios
        self.assertNotEqual(again, [row["said"] for row in friendtalk.scenarios(500, seed=5)])

    def test_nothing_in_them_is_for_the_safety_net(self):
        from luma.agent import friendcheck
        wrong = [row["said"] for row in friendtalk.scenarios(4000, seed=9) if friendcheck.at_risk(row["said"])]
        self.assertEqual(wrong, [])

    def test_none_of_it_is_the_human_tests_wording(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        held = {json.loads(line).get("said", "").strip().lower() for line in (root / "data" / "human_eval_v2.jsonl").read_text().splitlines() if line.strip()}
        for line in (root / "data" / "human_eval_v2.jsonl").read_text().splitlines():
            for turn in json.loads(line).get("turns") or []:
                held.add(turn.get("said", "").strip().lower())
        held.discard("")
        said = {row["said"].strip().lower() for row in friendtalk.scenarios(20000, seed=2)}
        self.assertEqual(sorted(said & held), [])

    def heard(self, said):
        got = friendtalk.read(said)
        return "look_up" if not got and friendtalk.fresh(said) else (got or {}).get("move")

    def test_how_much_is_heard_on_the_half_nobody_looked_at(self):
        """Not all of it, and this says how much. A scenario that isn't heard costs nothing: the brain does what it did."""
        by = {}
        for row in friendtalk.scenarios(12000, seed=7, only="heldout"):
            got = by.setdefault(row["move"], [0, 0])
            got[0] += self.heard(row["said"]) == row["move"]
            got[1] += 1
        share = {move: round(got[0] / got[1], 2) for move, got in by.items()}
        self.assertEqual(sorted(share), sorted(friendtalk.MOVES))
        for move, least in friendtalk.HEARD_AT_LEAST.items():
            self.assertGreaterEqual(share[move], least, f"{move}: {share}")
        self.assertEqual(sorted(friendtalk.HEARD_AT_LEAST), sorted(friendtalk.MOVES))

    def test_ordinary_talk_in_shapes_the_model_never_saw_is_left_alone(self):
        rows = list(friendtalk.ordinary(6000, seed=7, only="heldout"))
        self.assertGreater(len(rows), 3000)
        heard = sum(1 for row in rows if self.heard(row["said"]))
        self.assertLess(heard / len(rows), 0.01, f"{heard} of {len(rows)}")   # measured: 21 of 6,000

    def test_the_two_halves_share_no_frame_and_no_value(self):
        dev = list(friendtalk.scenarios(3000, seed=3, only="dev"))
        held = list(friendtalk.scenarios(3000, seed=3, only="heldout"))
        self.assertFalse({row["frame"] for row in dev} & {row["frame"] for row in held})
        for pack in friendtalk.every_pack():
            for name, values in pack["slots"].items():
                self.assertGreater(len({friendtalk.half(value) for value in values} if len(values) >= 8 else {1, 2}), 1, f"{pack['family']}.{name}")


class WhatTheModelLearnsFrom(unittest.TestCase):
    """Practice sentences and ordinary talk are lesson only. They borrow the packs' names, and only the dev half's."""

    def test_practice_and_ordinary_talk_are_well_formed(self):
        from luma.agent.friendtalk import everyday, practice
        families = {pack["family"]: pack for pack in friendtalk.every_pack()}
        for home in (practice, everyday):
            for name, (family, slot) in home.BORROWED.items():
                self.assertIn(slot, families[family]["slots"], name)
        self.assertEqual(len(practice.FRAMES), len(set(practice.FRAMES)))
        for move, frame in practice.FRAMES:
            self.assertIn(move, friendtalk.MOVES, frame)
            for slot in re.findall(r"\{(\w+)\}", frame):
                self.assertIn(slot, practice.BORROWED, frame)
        self.assertEqual({move for move, _ in practice.FRAMES}, set(friendtalk.MOVES))
        self.assertEqual(len(everyday.FRAMES), len(set(everyday.FRAMES)))
        for frame in everyday.FRAMES:
            for slot in re.findall(r"\{(\w+)\}", frame):
                self.assertTrue(slot in everyday.SLOTS or slot in everyday.BORROWED, frame)

    def test_the_trainer_only_ever_fills_in_the_dev_half(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy isn't here")
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import train_moves
        finally:
            sys.path.pop(0)
        for pack in friendtalk.every_pack():
            for part in (None, "fit", "check"):
                for name, pool in train_moves._pools(pack["slots"], "dev", part).items():
                    self.assertTrue(all(friendtalk.half(value) == "dev" for value in pool), f"{pack['family']}.{name}")
        frames = {frame for _, _, frame in train_moves.pack_lines("dev", None, 2, 0)}
        self.assertTrue(frames)
        self.assertTrue(all(friendtalk.half(frame) == "dev" for frame in frames))
        lesson = train_moves.training_rows("fit", 2, 0)
        self.assertEqual({label for _, label in lesson}, set(train_moves.LABELS))
        # A practice sentence that is also a pack's sentence is never learned from: it might be a held-out one.
        packs = {train_moves.shape(frame) for pack in friendtalk.every_pack() for _, frame in pack["frames"]}
        practised = {train_moves.shape(frame) for _, _, frame in train_moves.practice_lines(None, 2, 0)}
        self.assertGreater(len(practised), 300)
        self.assertFalse(practised & packs)

    def test_ordinary_talk_borrows_names_with_nothing_asked(self):
        rows = list(friendtalk.ordinary(400, seed=1))
        self.assertEqual(len(rows), 400)
        self.assertTrue(all(row["move"] is None and "{" not in row["said"] for row in rows))

if __name__ == "__main__":
    unittest.main()
