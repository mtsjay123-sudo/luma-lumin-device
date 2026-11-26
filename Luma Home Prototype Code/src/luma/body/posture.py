"""Six postures and one glow: the orb's moods, as a body.

    rest     idle        level, facing where it last looked, a low steady glow
    listen   listening   turned to the voice, leaning in a little, a nod as they talk
    wait     waiting     turned to them, level, patient
    think    thinking    a small tilt to one side, looking a little away
    speak    speaking    turned to them, a small movement with its own voice
    nap      napping     settled down and dim, turned to nobody

Movement means something or it doesn't happen. What never changes, whatever the mood:

- The microphone switch is off: nothing moves. A body that follows a voice it says it can't hear is a lie.
- A safety reply is being said: it turns to face them and stays. No nod, no lean, no sway. It doesn't perform.
- They're hurting: the same stillness, facing them.
- Left alone, it always comes back to rest.
- The speed limit is the head's own (luma.body.head), so nothing here can break it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from luma.body.head import MAX_SPEED, Head, within

POSTURES = {"idle": "rest", "listening": "listen", "waiting": "wait", "thinking": "think", "speaking": "speak", "napping": "nap"}
GLOW = {"rest": 0.35, "listen": 0.75, "wait": 0.55, "think": 0.6, "speak": 0.9, "nap": 0.12}
HOME_AFTER = 90.0      # seconds at rest before it turns back to where it sits facing
GENTLE = 14.0          # degrees a second when someone's hurting or it's settling into a nap


@dataclass
class Scene:
    """What the body is told each moment. Nothing here is a camera: bearing comes from the microphone ring."""
    mood: str = "idle"                 # the orb's mood: idle, listening, waiting, thinking, speaking, napping
    level: float = 0.0                 # how loud the voice is right now, 0 to 1 (the orb takes the same number)
    bearing: float | None = None       # where the voice came from, in degrees from straight ahead; None if unknown
    mic_on: bool = True                # the microphone switch
    safety: bool = False               # a safety reply is being said
    hurting: bool = False              # they're having a hard time


class Body:
    def __init__(self, head=None):
        self.head = head or Head()
        self.t = 0.0
        self.facing = 0.0              # where it last turned to someone
        self.rested = 0.0              # how long it has been at rest
        self.posture = "rest"

    def target(self, scene):
        """Where the head should be for this scene: the posture, then the rules that override it."""
        posture = POSTURES.get(scene.mood, "rest")
        if scene.bearing is not None and posture != "nap":
            self.facing = within("turn", scene.bearing)
        turn, tilt, lean = self.facing, 0.0, 0.0
        level = max(0.0, min(1.0, float(scene.level or 0.0)))
        if posture == "listen":
            lean = 6.0
            tilt = 2.0 + 3.0 * level * math.sin(self.t * 2.2)                 # a nod that follows their voice
        elif posture == "think":
            tilt, turn = 7.0, within("turn", self.facing + 12.0)              # a tilt, looking a little away
        elif posture == "speak":
            lean = 2.0
            tilt = 2.5 * level * math.sin(self.t * 3.1)                       # moves a little with its own voice
        elif posture == "nap":
            tilt, lean, turn = -14.0, -4.0, 0.0                               # settled, turned to nobody
        elif posture == "rest" and self.rested >= HOME_AFTER:
            turn = 0.0                                                        # back to where it sits facing
        still = scene.safety or scene.hurting
        if still:
            turn, tilt, lean = self.facing, 0.0, 0.0                          # it stays, and faces them
        glow = 0.6 if scene.safety else GLOW[posture]
        speed = GENTLE if (still or posture == "nap") else MAX_SPEED
        return posture, {"turn": turn, "tilt": tilt, "lean": lean, "glow": glow}, speed

    def update(self, scene, dt):
        """One tick. Returns where the head is now."""
        self.t += dt
        self.posture, target, speed = self.target(scene)
        self.rested = self.rested + dt if self.posture == "rest" else 0.0
        if not scene.mic_on:
            # The mic switch is off: the glow says so (dim), and nothing moves until it's back on.
            return self.head.step({**self.head.where(), "glow": 0.08}, dt, speed=0.0)
        return self.head.step(target, dt, speed=speed)


def may_approach(asleep=False, child_alone=False, pet_near=False, stairs_near=False):
    """For a body that can come to the room you're in: it doesn't move toward a sleeping person, a child alone or a
    pet, and it keeps away from stairs. No such body exists yet; the rule is written first."""
    return not (asleep or child_alone or pet_near or stairs_near)
