"""A simulated head: two small motors under the dome (turn and tilt) and a lean. Slow and weak by design.

Every move goes through step(), and step() is where the limits live: never faster than MAX_SPEED, never harder than
MAX_PUSH, never past the stops. Whatever asks for a target can't ask its way round them.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_SPEED = 40.0     # degrees a second, for any motor. A person turning to look at you is faster than this.
MAX_PUSH = 80.0      # degrees a second, each second: how quickly a motor may speed up or slow down
LIMITS = {"turn": (-150.0, 150.0), "tilt": (-20.0, 20.0), "lean": (-6.0, 12.0)}   # the stops
AXES = tuple(LIMITS)


def within(axis, value):
    low, high = LIMITS[axis]
    return max(low, min(high, float(value)))


@dataclass
class Head:
    turn: float = 0.0
    tilt: float = 0.0
    lean: float = 0.0
    glow: float = 0.0
    powered: bool = True          # the motors' own switch. Off, nothing here can move it

    def __post_init__(self):
        self.speed = {axis: 0.0 for axis in AXES}
        self.fastest = 0.0        # the fastest any motor has gone, for the tests
        self.travel = 0.0         # degrees moved in all, for the tests

    def where(self):
        return {axis: getattr(self, axis) for axis in AXES}

    def step(self, target, dt, speed=MAX_SPEED):
        """Move toward the target for dt seconds, inside every limit. target: {"turn", "tilt", "lean", "glow"}."""
        dt = max(0.0, min(float(dt), 0.25))      # a late tick never becomes a lunge
        self.glow = max(0.0, min(1.0, float(target.get("glow", self.glow))))
        if not self.powered:
            self.speed = {axis: 0.0 for axis in AXES}
            return self.where()
        top = max(0.0, min(float(speed), MAX_SPEED))
        for axis in AXES:
            here, want = getattr(self, axis), within(axis, target.get(axis, getattr(self, axis)))
            gap = want - here
            # the speed that still lets it stop on the mark
            wish = max(-top, min(top, (1 if gap > 0 else -1) * (2 * MAX_PUSH * abs(gap)) ** 0.5))
            change = max(-MAX_PUSH * dt, min(MAX_PUSH * dt, wish - self.speed[axis]))
            now = max(-top, min(top, self.speed[axis] + change))
            move = now * dt
            if abs(move) >= abs(gap):            # arrive, don't pass
                move, now = gap, 0.0
            setattr(self, axis, within(axis, here + move))
            self.speed[axis] = now
            self.fastest = max(self.fastest, abs(now))
            self.travel += abs(move)
        return self.where()

    def still(self):
        return all(abs(v) < 1e-6 for v in self.speed.values())
