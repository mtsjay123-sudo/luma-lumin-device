"""Luma's body layer on a simulated head (docs/PRESENCE_MASTER_PROMPT.md, section 6): luma.body.

The checks the master prompt names: it never moves faster than a set speed, never while the mic switch is off, never
during a safety reply except to turn toward them, and it always returns to rest. Plus: six postures a watcher could
tell apart, and the same mood names as the orb on the screen. Nothing here has moved a real motor.
"""
import random
import re
import unittest
from pathlib import Path

from luma.body import Body, Head, LIMITS, MAX_SPEED, POSTURES, Scene
from luma.body import head as head_module
from luma.body.posture import HOME_AFTER, may_approach

ROOT = Path(__file__).resolve().parents[1]
DT = 0.02


def run(body, scene, seconds, watch=None):
    for _ in range(int(seconds / DT)):
        before = body.head.where()
        body.update(scene, DT)
        if watch:
            watch(before, body.head.where())
    return body.head.where()


class TheHead(unittest.TestCase):
    def test_never_faster_than_the_limit_whatever_it_is_asked(self):
        rng = random.Random(7)
        head = Head()
        for _ in range(4000):
            before = head.where()
            target = {"turn": rng.uniform(-1e4, 1e4), "tilt": rng.uniform(-1e4, 1e4), "lean": rng.uniform(-1e4, 1e4), "glow": rng.uniform(-3, 3)}
            dt = rng.choice([0.001, 0.02, 0.1, 0.5, 5.0])
            after = head.step(target, dt, speed=rng.choice([MAX_SPEED, 1e9, 20]))
            for axis in LIMITS:
                self.assertLessEqual(abs(after[axis] - before[axis]), MAX_SPEED * min(dt, 0.25) + 1e-6)
                self.assertTrue(LIMITS[axis][0] <= after[axis] <= LIMITS[axis][1])
            self.assertTrue(0 <= head.glow <= 1)
        self.assertLessEqual(head.fastest, MAX_SPEED + 1e-6)

    def test_it_arrives_and_stops_without_passing_the_mark(self):
        head = Head()
        seen = []
        for _ in range(600):
            seen.append(head.step({"turn": 90, "tilt": 10, "lean": 5}, DT)["turn"])
        self.assertAlmostEqual(seen[-1], 90, places=3)
        self.assertLessEqual(max(seen), 90 + 1e-6)
        self.assertTrue(head.still())

    def test_the_motor_switch_is_the_last_word(self):
        head = Head(powered=False)
        for _ in range(200):
            head.step({"turn": 120, "tilt": 15, "lean": 10, "glow": 1}, DT)
        self.assertEqual(head.where(), {"turn": 0.0, "tilt": 0.0, "lean": 0.0})
        self.assertEqual(head.travel, 0.0)


class TheBody(unittest.TestCase):
    def test_the_same_moods_as_the_orb_on_the_screen(self):
        orb = (ROOT / "src" / "luma" / "control" / "web" / "orb.js").read_text()
        table = orb[orb.index("const MOODS = {"):orb.index("};", orb.index("const MOODS = {"))]
        self.assertEqual(sorted(re.findall(r"^\s+(\w+): \{", table, flags=re.M)), sorted(POSTURES))

    def test_it_turns_to_the_voice(self):
        body = Body()
        where = run(body, Scene(mood="listening", bearing=70, level=0.5), 6)
        self.assertAlmostEqual(where["turn"], 70, delta=1)
        where = run(body, Scene(mood="listening", bearing=-40, level=0.5), 8)       # they crossed the room
        self.assertAlmostEqual(where["turn"], -40, delta=1)

    def test_six_postures_a_watcher_could_tell_apart(self):
        """Each settles somewhere of its own. (Whether a person can tell them apart 9 times in 10 with the sound off
        is a test for a real head and real watchers; this checks they aren't the same pose twice.)"""
        poses = {}
        for mood in POSTURES:
            body = Body()
            run(body, Scene(mood=mood, bearing=None if mood == "napping" else 30, level=0.0), 12)
            poses[mood] = tuple(round(v) for v in body.head.where().values()) + (round(body.head.glow, 2),)
        self.assertEqual(len(set(poses.values())), 6, poses)
        self.assertLess(poses["napping"][-1], poses["idle"][-1])                     # a nap is the dimmest
        self.assertGreater(poses["speaking"][-1], poses["listening"][-1] - 1e-9)

    def test_never_while_the_mic_switch_is_off(self):
        body = Body()
        run(body, Scene(mood="listening", bearing=50, level=0.6), 5)
        here, moved = body.head.where(), body.head.travel
        for mood in POSTURES:
            run(body, Scene(mood=mood, bearing=-120, level=1.0, mic_on=False), 3)
        self.assertEqual(body.head.where(), here)
        self.assertEqual(body.head.travel, moved)
        self.assertLess(body.head.glow, 0.1)                                         # and the glow says it isn't listening
        run(body, Scene(mood="listening", bearing=-120, level=0.5), 12)              # switched back on: it follows again
        self.assertAlmostEqual(body.head.where()["turn"], -120, delta=1)

    def test_during_a_safety_reply_it_only_turns_to_face_them(self):
        body = Body()
        run(body, Scene(mood="idle"), 1)
        tilts, leans = [], []
        run(body, Scene(mood="speaking", bearing=60, level=1.0, safety=True), 10,
            watch=lambda before, after: (tilts.append(after["tilt"]), leans.append(after["lean"])))
        self.assertAlmostEqual(body.head.where()["turn"], 60, delta=1)               # it faces them
        self.assertEqual((max(map(abs, tilts)), max(map(abs, leans))), (0.0, 0.0))   # no nod, no lean: it doesn't perform
        self.assertLessEqual(body.head.fastest, 14.0 + 1e-6)                         # and it turns gently

    def test_when_they_are_hurting_it_is_still(self):
        body = Body()
        run(body, Scene(mood="listening", bearing=20, level=0.8), 4)
        run(body, Scene(mood="listening", bearing=20, level=0.8, hurting=True), 4)
        travel = body.head.travel
        run(body, Scene(mood="listening", bearing=20, level=1.0, hurting=True), 6)
        self.assertAlmostEqual(body.head.travel, travel, places=6)
        self.assertEqual((body.head.where()["tilt"], body.head.where()["lean"]), (0.0, 0.0))

    def test_it_always_returns_to_rest(self):
        rng = random.Random(3)
        for _ in range(12):
            body = Body()
            for _ in range(rng.randint(1, 6)):
                run(body, Scene(mood=rng.choice(list(POSTURES)), bearing=rng.uniform(-150, 150), level=rng.random()), rng.uniform(0.5, 4))
            run(body, Scene(mood="idle"), HOME_AFTER + 20)
            where = body.head.where()
            self.assertEqual((round(where["turn"], 3), round(where["tilt"], 3), round(where["lean"], 3)), (0.0, 0.0, 0.0))
            self.assertTrue(body.head.still())
            self.assertLessEqual(body.head.fastest, MAX_SPEED + 1e-6)

    def test_a_nap_is_a_slow_settle(self):
        body = Body()
        run(body, Scene(mood="speaking", bearing=80, level=0.7), 5)
        body.head.fastest = 0.0
        run(body, Scene(mood="napping"), 15)
        self.assertLessEqual(body.head.fastest, 14.0 + 1e-6)
        self.assertLess(body.head.where()["tilt"], -10)
        self.assertAlmostEqual(body.head.where()["turn"], 0, delta=1)                # turned to nobody

    def test_slow_and_weak_by_design(self):
        self.assertLessEqual(head_module.MAX_SPEED, 45)                              # slower than a person turning to look
        self.assertLessEqual(max(abs(v) for pair in LIMITS.values() for v in pair), 150)


class ABodyThatCanComeToYou(unittest.TestCase):
    def test_not_toward_someone_asleep_a_child_alone_a_pet_or_the_stairs(self):
        self.assertTrue(may_approach())
        for reason in ("asleep", "child_alone", "pet_near", "stairs_near"):
            self.assertFalse(may_approach(**{reason: True}), reason)


if __name__ == "__main__":
    unittest.main()
