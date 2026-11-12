#!/usr/bin/env python3
"""Make the printed case's parts again from the drawing (hardware/luma_case.scad). Needs OpenSCAD.

    python scripts/case_parts.py              # every part, into hardware/stl
    python scripts/case_parts.py base lid     # just these
    python scripts/case_parts.py --pictures   # the four pictures in hardware/pictures too (needs xvfb-run where there's no screen)

OpenSCAD writes text STL files; this keeps the small binary kind (a fifth of the size). Then measure them:
    PYTHONPATH=src:tests python3 -m pytest -q -p no:cacheprovider tests/test_hardware_case.py
"""
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HW = Path(__file__).resolve().parents[1] / "hardware"
PARTS = ("base", "mid", "top", "lid", "ring", "plate", "fit")
VIEWS = {"exploded": ("exploded", "0,0,130,64,0,200,990", "1200,1560"), "cut": ("cut", "0,0,84,72,0,72,570", "1200,1200"),
         "back": ("assembly", "0,0,84,70,0,205,590", "1200,1200"), "front": ("assembly", "0,0,84,70,0,28,590", "1200,1200")}
NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
FACET = re.compile(r"facet normal\s+" + r"\s+".join([f"({NUMBER})"] * 3) + r"\s+outer loop" + (r"\s+vertex\s+" + r"\s+".join([f"({NUMBER})"] * 3)) * 3)


def binary(text, name):
    """A text STL as a binary one."""
    triangles = FACET.findall(text)
    out = bytearray(f"Luma Home case, part: {name} (millimetres)".encode().ljust(80, b" ")[:80]) + struct.pack("<I", len(triangles))
    for triangle in triangles:
        out += struct.pack("<12fH", *(float(value) for value in triangle), 0)
    return bytes(out), len(triangles)


def main(argv):
    openscad = shutil.which("openscad") or shutil.which("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    if not openscad:
        print("This needs OpenSCAD (openscad.org). Install it, then run this again.")
        return 1
    pictures = "--pictures" in argv
    parts = [a for a in argv if a in PARTS] or list(PARTS)
    drawing = str(HW / "luma_case.scad")
    with tempfile.TemporaryDirectory() as folder:
        for name in parts:
            made = Path(folder) / f"{name}.stl"
            subprocess.run([openscad, "-o", str(made), "-D", f'part="{name}"', drawing], check=True, capture_output=True)
            data, count = binary(made.read_text(), name)
            (HW / "stl" / f"{name}.stl").write_bytes(data)
            print(f"{name}: {count} triangles, {len(data) // 1024} KB")
    if pictures:
        screen = [shutil.which("xvfb-run"), "-a"] if shutil.which("xvfb-run") else []
        for name, (part, camera, size) in VIEWS.items():
            subprocess.run(screen + [openscad, "-o", str(HW / "pictures" / f"{name}.png"), f"--imgsize={size}", f"--camera={camera}",
                                     "--colorscheme=Tomorrow", "-D", f'part="{part}"', drawing], check=True, capture_output=True)
            print(f"pictures/{name}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
