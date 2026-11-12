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


class TheSums(unittest.TestCase):
    def setUp(self):
        self.n = numbers()
        n = self.n
        self.iw, self.id, self.ir = n["body_w"] - 2 * n["wall"], n["body_d"] - 2 * n["wall"], n["corner_r"] - n["wall"]

    def test_the_computer_fits_against_the_back_wall_inside_the_round_corners(self):
        n = self.n
        self.assertLess(n["board_w"] + 2, self.iw)
        self.assertLess(n["board_d"] + 2, self.id)
        # its back corners, against the back wall, have to be inside the corner's curve
        cx, cy = self.iw / 2 - self.ir, self.id / 2 - self.ir
        x, y = n["board_w"] / 2, self.id / 2 - 0.5
        self.assertLess(math.hypot(max(x - cx, 0), max(y - cy, 0)), self.ir)

    def test_the_corner_posts_stand_clear_of_the_computer(self):
        n = self.n
        off = (self.ir - n["boss"] / 2 + 0.6) * 0.7071
        post_inner_edge = self.iw / 2 - self.ir + off - n["boss"] / 2
        self.assertGreater(post_inner_edge, n["board_w"] / 2 + 1)

    def test_the_speaker_sits_on_the_flat_of_the_front_and_inside_its_box(self):
        n = self.n
        self.assertLessEqual(n["spk_frame"] + 6, n["body_w"] - 2 * n["corner_r"])   # the pad is on the flat, not on a corner's curve
        self.assertLess(n["spk_frame"], n["chamber_h"] - n["lip"] - 1)              # under the top section's step
        self.assertLess(n["spk_cone"], n["spk_frame"])
        self.assertLess(n["spk_screw"] * math.sqrt(2) / 2 + 2, (n["spk_frame"] + 6) / 2 * math.sqrt(2))

    def test_the_microphones_sit_under_the_lid_and_outside_the_speakers_box(self):
        n = self.n
        ledge = n["top_h"] - n["lid_t"] - n["mic_drop"] - 1.6
        self.assertGreater(ledge, n["floor_t"] + 4, "room under the board for its parts and plugs")
        self.assertLess(n["mic_d"] + 19, min(n["body_w"], n["body_d"]) - 2 * n["wall"], "the lattice is inside the walls")
        text = (HW / "luma_case.scad").read_text(encoding="utf-8")
        top = text[text.index("module top()"):text.index("module lid()")]
        self.assertIn("slab(body_w, body_d, corner_r, floor_t);", top, "a solid floor: the speaker's box is closed under the microphones")

    def test_the_whole_thing_is_the_size_the_guide_says(self):
        n = self.n
        bay = n["floor_t"] + n["board_lift"] + n["board_h"] + n["cable_room"]
        height = bay + n["floor_t"] + n["chamber_h"] + n["top_h"]
        guide = (HW / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"{n['body_w']:.0f} mm wide, {n['body_d']:.0f} mm deep and {round(height):.0f} mm tall", guide)


class ThePrintedParts(unittest.TestCase):
    """Measured from the files in hardware/stl, which OpenSCAD made from the drawing."""

    def test_each_part_is_the_size_the_drawing_gives(self):
        n = numbers()
        bay = n["floor_t"] + n["board_lift"] + n["board_h"] + n["cable_room"]
        want = {"base": ([n["body_w"], n["body_d"], round(bay, 1)], 0.0),
                "mid": ([n["body_w"], n["body_d"], round(n["floor_t"] + n["chamber_h"] + n["lip"], 1)], -n["lip"]),
                "top": ([n["body_w"], n["body_d"], round(n["top_h"] - n["lid_t"] + n["lip"], 1)], -n["lip"]),
                "lid": ([n["body_w"], n["body_d"], round(n["lid_t"] + n["lip"], 1)], None)}
        for name, (size, lowest) in want.items():
            got, low = box(name)
            self.assertEqual(got, size, name)
            if lowest is not None:
                self.assertEqual(low, lowest, name)

    def test_every_part_fits_an_ordinary_printer(self):
        for name in ("base", "mid", "top", "lid", "ring", "plate", "fit"):
            (x, y, z), _ = box(name)
            self.assertLessEqual(max(x, y), 220, name)
            self.assertLessEqual(z, 200, name)


class TheGuide(unittest.TestCase):
    def setUp(self):
        self.guide = (HW / "README.md").read_text(encoding="utf-8")

    def test_it_says_what_is_not_proven(self):
        for words in ("Nobody has built this exact", "has not been measured", "Check it against the pinout", "not advice"):
            self.assertIn(words, self.guide)

    def test_the_switch_cuts_power_and_the_light_is_on_that_wire(self):
        self.assertIn("cuts the microphones' power wire", self.guide)
        self.assertIn("LUMA_PRIVACY_GPIO=29", self.guide)
        self.assertIn("LUMA_PRIVACY_ACTIVE_LEVEL=0", self.guide)   # the pin reads ground when the switch is off, and that means blocked
        wiring = (HW / "wiring.svg").read_text(encoding="utf-8")
        self.assertIn("lit =", wiring)
        self.assertIn("can hear", wiring)
        self.assertIn("a loose wire reads off", wiring)

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
