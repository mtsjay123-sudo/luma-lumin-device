"""The case you can print (hardware/luma_case.scad) and its build guide. The sizes are numbers anyone can change, so the sums
that say "it fits" are done again here, and the printed parts are measured from the files themselves."""
import math
import re
import struct
import unittest
from pathlib import Path

HW = Path(__file__).resolve().parents[1] / "hardware"


def numbers():
    """Every plain `name = number;` in the drawing."""
    text = (HW / "luma_case.scad").read_text(encoding="utf-8")
    return {name: float(value) for name, value in re.findall(r"^(\w+) = (-?\d+(?:\.\d+)?);", text, re.M)}


def box(name):
    """A binary STL's size: (x, y, z) and the lowest z."""
    data = (HW / "stl" / f"{name}.stl").read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count, name
    low, high = [math.inf] * 3, [-math.inf] * 3
    for i in range(count):
        values = struct.unpack_from("<12f", data, 84 + 50 * i)
        for k in range(3, 12):
            low[k % 3], high[k % 3] = min(low[k % 3], values[k]), max(high[k % 3], values[k])
    return [round(high[k] - low[k], 1) for k in range(3)], round(low[2], 1)


def inner_radius(n, z):
    """How far the inside of the base's wall is from the middle, z above the table. The base's edge is rounded underneath."""
    turn = math.radians(90 - n["start_a"])
    centre_z, r_in = n["edge_r"] * math.sin(turn), n["edge_r"] - n["wall"]
    if z >= centre_z:
        return n["body_d"] / 2 - n["wall"]
    return n["body_d"] / 2 - n["edge_r"] + math.sqrt(r_in ** 2 - (z - centre_z) ** 2)


class TheSums(unittest.TestCase):
    def setUp(self):
        self.n = numbers()
        self.text = (HW / "luma_case.scad").read_text(encoding="utf-8")

    def test_it_has_the_shape_in_the_picture(self):
        """A frosted dome on a short white base: about 1.55 times as tall as wide, the white band a little under a quarter."""
        n = self.n
        self.assertAlmostEqual(n["body_h"] / n["body_d"], 1.55, delta=0.03)
        self.assertTrue(0.20 <= (n["base_h"] + n["deck_h"]) / n["body_h"] <= 0.26)
        self.assertGreater(n["shoulder_r"], 1.5 * n["edge_r"], "soft shoulders on the dome, a tighter edge under the base")

    def test_the_computer_fits_in_the_round_base(self):
        n = self.n
        floor = n["wall"]
        back_corner = math.hypot(n["board_w"] / 2, n["board_y"] + n["board_d"] / 2)
        front_corner = math.hypot(n["board_w"] / 2, n["board_y"] - n["board_d"] / 2)
        room = inner_radius(n, floor + n["board_lift"])
        self.assertLess(back_corner + 1, room)
        self.assertLess(front_corner + 1, room)
        self.assertGreaterEqual(n["base_h"] - n["lip"] - floor - n["board_lift"] - n["board_h"], 8, "air over the fan, under the deck")

    def test_the_plugs_at_the_back_stay_inside_the_outline(self):
        n = self.n
        pocket = n["body_d"] / 2 - (n["board_y"] + n["board_d"] / 2)
        self.assertGreaterEqual(pocket, 22, "room for a short USB plug between the board's edge and the lamp's outline")
        self.assertLess(n["port_w"] / 2, n["body_d"] / 2 * math.sin(math.radians(40)), "the window is at the back, out of sight from the front")

    def test_the_speaker_lies_in_front_of_the_computer(self):
        n = self.n
        floor = n["wall"]
        self.assertGreaterEqual((n["board_y"] - n["board_d"] / 2) - (n["spk_y"] + n["spk_d"] / 2), 2, "a gap between the two")
        corner = math.hypot(n["spk_w"] / 2, abs(n["spk_y"]) + n["spk_d"] / 2)
        self.assertLess(corner + 0.8, inner_radius(n, floor + n["spk_lift"]), "its front corners clear the rounded edge")
        self.assertLess(floor + n["spk_lift"] + n["spk_h"], n["base_h"] - n["lip"])

    def test_the_posts_stand_clear_of_everything(self):
        n = self.n
        post_r = n["body_d"] / 2 - n["wall"] - n["boss"] / 2 + 0.6
        posts = [(post_r * math.sin(math.radians(a)), post_r * math.cos(math.radians(a))) for a in (90, 135, 225, 270)]
        self.assertIn("post_at = [90, 135, 225, 270];", self.text)
        for x, y in posts:
            off_board = max(abs(x) - n["board_w"] / 2, abs(y - n["board_y"]) - n["board_d"] / 2)
            off_speaker = max(abs(x) - n["spk_w"] / 2 - 2, abs(y - n["spk_y"]) - n["spk_d"] / 2)
            self.assertGreater(off_board, n["boss"] / 2 + 1, (x, y))
            self.assertGreater(off_speaker, n["boss"] / 2 + 1, (x, y))

    def test_the_switch_has_room_behind_it_and_the_light_faces_the_room(self):
        n = self.n
        inside = n["body_d"] / 2 - n["wall"]
        x = inside * math.sin(math.radians(n["sw_at"]))
        room = (x - n["board_w"] / 2) / math.sin(math.radians(n["sw_at"]))
        self.assertGreaterEqual(room, 24, "a mini toggle switch is about 22 deep with its lugs")
        self.assertLess(n["sw_at"], 90, "the switch is round the back")
        self.assertTrue(90 < n["led_at"] < 150, "the light that says the microphones can hear is where a person in the room sees it")
        self.assertGreater(n["sw_z"], n["edge_r"] * math.sin(math.radians(90 - n["start_a"])), "on the straight part of the wall")

    def test_the_dome_twists_on_and_stands_off_the_deck(self):
        n = self.n
        tower_out = n["body_d"] / 2 - n["dome_wall"] - 0.35
        self.assertLess(tower_out, n["body_d"] / 2 - n["dome_wall"], "the towers fit inside the dome")
        self.assertIn("tower_in = tower_out - 5.2;", self.text)
        slot_floor, lug_tip = tower_out - n["lug_in"] - 0.9, n["body_d"] / 2 - n["dome_wall"] - n["lug_in"]
        self.assertGreater(lug_tip - slot_floor, 0.5, "a bump clears the bottom of its slot")
        self.assertGreater(slot_floor - (tower_out - 5.2), 1.5, "and there's wall left behind the slot")
        lug_top = n["seam"] + 4.5 + 3 + n["lug_in"]
        self.assertGreater(n["tower_h"] - lug_top, 1.5, "a roof over the bump: the dome can't lift off")
        self.assertGreaterEqual(n["seam"], 2, "a ring of air under the dome: how sound gets to the microphones")
        self.assertGreaterEqual(n["start_a"], 35, "the roundings print without supports")

    def test_the_microphones_are_in_a_different_room_from_the_speaker_and_the_fan(self):
        deck = self.text[self.text.index("module deck()"):self.text.index("// ---- dome")]
        self.assertNotIn("slots(", deck, "the deck is solid: no air or sound comes straight up from the base")
        self.assertEqual(deck.count("cube([17, 10, 40], center = true)"), 1, "one way up, for the cables")
        self.assertGreaterEqual(self.n["mic_up"], 5, "room under the microphone board for its plug")

    def test_the_whole_thing_is_the_size_the_guide_says(self):
        n = self.n
        guide = (HW / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"{n['body_d']:.0f} mm across and {n['body_h']:.0f} mm tall", guide)


class ThePrintedParts(unittest.TestCase):
    """Measured from the files in hardware/stl, which OpenSCAD made from the drawing."""

    def test_each_part_is_the_size_the_drawing_gives(self):
        n = numbers()
        dome_h = n["body_h"] - n["base_h"] - n["deck_h"] - n["seam"]
        want = {"base": ([n["body_d"], n["body_d"], n["base_h"]], 0.0),
                "deck": ([n["body_d"], n["body_d"], n["lip"] + n["deck_h"] + n["tower_h"]], -n["lip"]),
                "dome": ([n["body_d"], n["body_d"], dome_h], 0.0)}
        for name, (size, lowest) in want.items():
            got, low = box(name)
            if name == "base":   # the port window is cut out of the very back of the wall
                self.assertTrue(n["body_d"] - 3 < got[1] <= n["body_d"], got)
                got[1] = n["body_d"]
            self.assertEqual(got, [round(v, 1) for v in size], name)
            self.assertEqual(low, lowest, name)
        (x, y, z), low = box("rim")
        self.assertEqual((x, z, low), (n["body_d"], 16.0, 0.0), "the test slice of the dome's rim")

    def test_every_part_fits_an_ordinary_printer(self):
        for name in ("base", "deck", "dome", "rim", "tag", "fit"):
            (x, y, z), _ = box(name)
            self.assertLessEqual(max(x, y), 220, name)
            self.assertLessEqual(z, 200, name)

    def test_the_old_tower_is_gone(self):
        for name in ("mid", "top", "lid", "ring", "plate"):
            self.assertFalse((HW / "stl" / f"{name}.stl").exists(), name)


class TheGuide(unittest.TestCase):
    def setUp(self):
        self.guide = (HW / "README.md").read_text(encoding="utf-8")

    def test_it_says_what_is_not_proven(self):
        for words in ("Nobody has built this exact", "has not been measured", "Check it against the pinout", "not advice",
                      "has not been proven", "not written"):
            self.assertIn(words, self.guide)

    def test_the_switch_cuts_power_and_the_light_is_on_that_wire(self):
        self.assertIn("cuts the microphones' power wire", self.guide)
        self.assertIn("LUMA_PRIVACY_GPIO=29", self.guide)
        self.assertIn("LUMA_PRIVACY_ACTIVE_LEVEL=0", self.guide)   # the pin reads ground when the switch is off, and that means blocked
        wiring = (HW / "wiring.svg").read_text(encoding="utf-8")
        self.assertIn("lit =", wiring)
        self.assertIn("can hear", wiring)
        self.assertIn("a loose wire reads off", wiring)
        self.assertIn("The glow", wiring)

    def test_the_glow_never_stands_in_for_the_microphone_light(self):
        """The dome glows whenever Luma is on. Whether it can hear is one amber light on the microphones' own power, nothing else."""
        self.assertIn("The glow is not the microphone light", self.guide)

    def test_it_says_how_a_phone_sets_it_up(self):
        for words in ("Luma Setup", "says the code", "the same code"):
            self.assertIn(words, self.guide)

    def test_a_low_pin_blocks_listening_in_lumas_own_code(self):
        from luma.hardware.device import DeviceConfig, DeviceController

        class Pins:
            BOARD, IN, OUT = "board", "in", "out"
            level = 0

            def setmode(self, mode): pass
            def setup(self, *args, **kwargs): pass
            def input(self, pin): return self.level
            def output(self, *args): pass
            def cleanup(self, *args): pass
        pins = Pins()
        device = DeviceController(DeviceConfig.from_env({"LUMA_PRIVACY_GPIO": "29", "LUMA_PRIVACY_ACTIVE_LEVEL": "0"}), gpio=pins)
        self.assertFalse(device.capture_allowed(), "switch off (the pin at ground): Luma may not listen")
        pins.level = 1
        self.assertTrue(device.capture_allowed(), "switch on (the pin at 3.3 V)")


if __name__ == "__main__":
    unittest.main()
