# Luma Home: the lamp you can build

A frosted dome on a short white base, with a warm glow low in the middle. Luma lives in it: it hears the room, talks
back, and thinks inside the lamp.

| | |
|---|---|
| ![Front](pictures/front.png) | ![The case, taken apart](pictures/exploded.png) |

**What this is, plainly.** A design you can build from parts you can buy, with a case you can print. The parts are real,
the wiring is ordinary, and the case's files were built and measured by the CAD program. **Nobody has built this exact
unit yet.** The section near the end lists what has to be proven on a bench before anyone calls it a product.

It's 168 mm across and 260 mm tall: about the size of a table lamp. The shape is the one on the website: the dome is
three quarters of the height, the white base the rest.

## Five ideas the hardware is built around

1. **The microphone switch is real.** It doesn't ask software to stop listening. It cuts the microphones' power wire. With
   no power they are not a device the computer can see at all.
2. **The light can't lie.** A small amber light on the front is wired to the microphones' own power, after the switch. If
   it's lit, they have power and can hear. If it's dark, they can't. No software sits between the two.
3. **The glow is not the microphone light.** The dome glows whenever Luma is plugged in, like any lamp. It says nothing
   about listening. Only the amber light does.
4. **Luma can still speak with the microphones off.** Sound out goes a different way, so a reminder ("time for your
   evening pills") still comes.
5. **It thinks at home.** The brain is in the base. No camera in this one: a friend to talk to doesn't need eyes, and
   one less sensor is one less thing to trust.

## Parts

Prices are for one of each, from the makers' own shops or the usual sellers. The computer's price was checked on
November 12, 2026 (list price $249; some sellers charge a good deal more, so shop around). The rest are the prices I know
of and may have moved: check before you order.

| Part | Which one | About | Why this one |
|---|---|---|---|
| The computer | NVIDIA Jetson Orin Nano Super developer kit, 8 GB (comes with its 19 V supply and a Wi-Fi card) | $249 | Meant to run Luma's 4B brain on its graphics chip, alone, with no other computer in the home |
| Storage | NVMe M.2 drive, 256 GB | $35 | The brain, the voices and years of memories |
| Microphones | Seeed ReSpeaker Mic Array v2.0 (4 microphones, a ring of 12 lights, USB) | $67 | Hears across a room |
| Sound out | Any plain USB audio adapter with a headphone jack | $8 | Its own path, so the switch never silences Luma |
| Amplifier | Adafruit PAM8302, 2.5 W, one channel | $4 | Small, runs on 5 V |
| Speaker | A small speaker sealed in its own box, 4 Ω, 3 W, about 70 × 30 × 17 mm (Adafruit 3351 is one) | $4 | Already sealed, so nothing printed has to be airtight. A voice, not a hi-fi |
| The switch | Mini toggle switch, two poles, two positions (DPDT, on-on), 6 mm threaded neck | $3 | One pole cuts the power, the other tells the computer. One round hole |
| The light | 3 mm amber LED and a 1 kΩ resistor | $1 | Lit means they can hear |
| The glow | 5 V warm white LED strip, about 23 cm of it | $6 | The lamp |
| Small parts | 1 kΩ and 100 kΩ resistors, a short USB-A to micro-B cable to cut, a USB-A plug with bare wires, a 3.5 mm plug with bare wires, hook-up wire, heat-shrink. Short or right-angle USB plugs | $10 | |
| Fixings | 4 brass M3 heat-set inserts, 4 M3 × 12 screws, 4 stick-on rubber feet at least 4 mm tall, double-sided foam tape | $4 | The feet lift the base: air goes in and sound comes out underneath |
| Plastic | PETG: about 250 g white, about 260 g natural (clear) | $14 | Natural PETG prints frosted. PETG stands up to the computer's warmth better than PLA |
| | **Total** | **about $405** | |

## Wiring

![Wiring](wiring.svg)

Everything plugs into the computer's own USB ports, except three thin wires to its 40-pin header.

**The microphone switch (do this one carefully).**

1. Cut the short USB cable in the middle. Inside are four wires: red (5 V), white (data −), green (data +), black (ground).
2. Join white to white, green to green and black to black again, soldered, each in heat-shrink. Keep the white and green
   pair twisted right up to the joints.
3. The red wire from the computer's side goes to the middle lug of the switch's first pole. The red wire from the
   microphones' side goes to the outer lug that the middle one touches when the switch says ON.
4. The light: from that same outer lug (the microphones' side), through the 1 kΩ resistor, to the LED's long leg. The
   LED's short leg goes to black. Now the light is on exactly when the microphones have power.
5. The second pole tells the computer. Its middle lug goes, through a 1 kΩ resistor, to header pin 29. Its ON lug goes to
   pin 1 (3.3 V). Its OFF lug goes to pin 6 (ground). Add the 100 kΩ resistor from pin 29 to ground, so a wire that comes
   loose reads as OFF.

Pin 29 is the pin I propose: on NVIDIA's pinout it's a plain input. **Check it against the pinout for your board before
you wire it.** Then tell Luma:

```
LUMA_PRIVACY_GPIO=29
LUMA_PRIVACY_ACTIVE_LEVEL=0
```

**Sound out.** USB audio adapter into a USB port. Its headphone jack goes to the amplifier's input (tip to A+, sleeve to
A−). The amplifier's 5 V and ground come from the bare-wire USB plug in a third USB port. The amplifier's two output
screws go to the speaker's two wires. Neither speaker wire is ground: don't join them to anything else.

**The glow.** The light strip's two wires join the amplifier's 5 V and ground. It's on whenever Luma is plugged in.

## The case

| | |
|---|---|
| ![Cut in half](pictures/cut.png) | ![Back](pictures/back.png) |

Three sections, bottom to top:

- **Base.** The computer stands on its own feet between four guides, pushed towards the back. Its ports sit in a pocket
  inside the lamp's outline, behind one window, so the plugs don't stick out. The speaker lies face down in front of the
  computer, over slots in the floor. The switch is round the back on the right; the amber light is on the front right.
  Air comes in through slots underneath and leaves through the window.
- **Deck.** The lid of the base, and solid: the speaker and the fan are in a different room from the microphones. The
  microphone board lies on a raised ring in the middle. The glow's strip goes round that ring.
- **Dome.** The frosted shade. It twists onto three towers on the deck and stands 2 mm above it. That ring of air is how
  sound reaches the microphones.

Files: [`luma_case.scad`](luma_case.scad) is the drawing, with every size as a number you can change. The printable parts
are in [`stl/`](stl/).

**Print it.** PETG, 0.2 mm layers, no supports. Base and deck in white, 3 walls, 20% infill, standing as drawn. The dome in
natural PETG, 4 walls, standing on its flat top; it's 197 mm tall, so check your printer's height. Slow the outer wall
for the dome's first 30 mm, where the shoulder leans out.

1. Print `fit.stl` and `rim.stl` first (under an hour together). `fit` is three thin frames: lay your computer, your
   speaker and your microphone board in them. `rim` is the last 16 mm of the dome: print the deck, then try the twist.
   If something is tight or loose, change that number in `luma_case.scad` and make the parts again:
   `python scripts/case_parts.py` (it needs OpenSCAD, which is free).
2. Print `base`, `deck`, `dome` and `tag`.
3. Press the four heat-set inserts into the base's posts with a soldering iron.

For a Raspberry Pi 5 instead of the Jetson (the smaller device below), set `pi5 = true`, `board_w = 85`, `board_d = 56`,
`board_h = 30` and `board_y = 20`, and make the base again (`python scripts/case_parts.py base`).

## Putting it together

1. Fit the storage drive to the computer. Stick the feet under the base.
2. Lay the speaker face down in its cradle at the front and hold it with a strip of foam tape. Fix the amplifier and the
   USB audio adapter beside the computer's left side with tape.
3. Push the switch's neck through its hole from inside, slip the tag over it outside (MIC up, OFF down), and tighten
   its nut. Press the amber LED into its hole from inside.
4. Set the computer between its guides, ports to the window. Plug the audio adapter and the amplifier's power into two
   USB ports. Run the three header wires to pins 1, 6 and 29.
5. Feed the cut USB cable's microphone end and the glow's two wires up through the slot in the deck. Screw the deck down
   (four screws; their heads end up under the dome).
6. Lay the microphone board on its ring and plug it in. Stick the light strip round the ring, facing out.
7. Lower the dome so its three bumps drop into the towers, and twist it to the right until it stops.

## Turning it on, from a phone

The lamp has no screen, so the phone is the screen (`src/luma/hardware/firstrun.py`).

1. Plug Luma in. If it isn't on Wi-Fi it opens its own network, **Luma Setup** and four numbers, and says the code out
   loud.
2. On the phone, join that network with the code. A page opens. Pick your Wi-Fi and type its password. The password goes
   to the lamp's Wi-Fi software and nowhere else: Luma keeps no copy and writes it in no log.
3. Luma joins your Wi-Fi and says where to find it ("open 192.168.1.40 in your phone's browser"). If the password was
   wrong it says so and opens its setup network again.
4. At that address, type the same code. The phone opens Luma's app, paired. Add it to the home screen.

Five wrong codes, or half an hour, and that door closes. Unplugging Luma and plugging it back in opens it again while no
phone is paired. More phones are added from Luma on a computer.

Before any of that, a builder follows [`docs/DEVICE_SETUP.md`](../docs/DEVICE_SETUP.md) once: install on the Jetson, copy
the brain and the voices, pick the microphone array as the input and the USB audio adapter as the output. Luma starts
with the microphones muted in software too, until you say otherwise.

## Check it before you trust it

| Check | How | It passes when |
|---|---|---|
| The switch cuts power | Switch OFF. Put a meter on the microphones' red wire | 0 V |
| The computer can't see them | Switch OFF. Run `arecord -l` | The microphone array isn't in the list |
| The light tells the truth | Flip the switch back and forth | Lit only when the array is in the list |
| The glow says nothing | Switch OFF | The dome still glows; the amber light is dark |
| Luma knows | Switch OFF, open Luma's app | It shows the microphone as off, and it won't listen |
| A loose wire is safe | Pull the wire off pin 29 | Luma treats it as OFF |
| Luma can still speak | Switch OFF, set a one-minute timer from the phone | You hear it |
| It keeps cool | Talk with it for thirty minutes with the dome on, watching `tegrastats` | The computer stays under its own limit and doesn't slow down |
| It hears through the dome | Speak from across the room, dome on and dome off | It hears you both ways |
| It hears over itself | Play music through it at a normal volume and speak from across the room | It hears you |
| A phone sets it up | Forget the Wi-Fi on the lamp and plug it in | It says a code, the page opens, and the phone ends up paired |

## Two sizes, and the big picture

| | Luma Home (this build) | Luma Mini |
|---|---|---|
| The computer | Jetson Orin Nano Super, 8 GB | An 8 GB ARM board such as a Raspberry Pi 5 |
| The brain inside | The 4B brain | The 1.7B brain |
| Stands alone | Yes | Yes, with a simpler brain |
| Parts, for one | about $405 | about $250 |
| Same case, same switch, same wiring | yes | yes (`pi5 = true`) |

**Thinking big.** A home can hold one mind and many voices. When a bigger computer is at home and its owner says yes (a
Mac Studio, for one), either device thinks with that computer's brain over Luma Link, and falls back to its own when it's
away. The safety net, the microphone switch and the memories stay in the device either way.

## What isn't proven yet

- Nobody has assembled this unit. The fit of the bought parts is from the makers' published sizes; that's what `fit.stl`
  is for.
- Hearing through the dome has not been proven. Sound gets in through a 2 mm ring of air under the dome's rim. How well
  four microphones hear a voice across a room that way has not been measured. If it's poor, the fix is a wider ring or a
  row of fine holes round the dome's foot.
- Heat with the dome on has not been measured.
- Sound out has not been measured: a small speaker firing down under the base is a voice, not music.
- The dome has not been printed. A printed dome has a soft edge where its flat top meets the shoulder; a moulded one
  wouldn't.
- Pin 29 has not been tried on a board.
- Luma has run on a Mac and on GitHub's computers. It has not yet run on a Jetson (see `docs/DEVICE_SETUP.md`).
- The setup from a phone is tested with a made-up Wi-Fi, in a real browser. It has not been tried on a lamp.
- The glow is plain on and off. Luma dimming it, or moving it with the voice, is not written.
- The parts list tops out near $405, so the $199 price on the website isn't reachable with this computer.
  `docs/BUSINESS_MODEL.md` has the prices that are.

## From this to a product

This build is the first of the three usual steps.

1. **This one (engineering test).** Bought boards in a printed case. Proves the idea, the switch and the sound.
2. **Design test.** One board of Luma's own instead of a developer kit: the computer module, four microphones under a
   ring of fine holes at the dome's foot, the speaker amplifier, the glow, and the switch cutting the microphones' power
   on the board itself. A moulded base and a blown or moulded frosted dome, in the website's three colours.
3. **Production test.** The same thing made in the hundreds, tested on a line.

Before it's sold or handed out, these need a compliance lab and a lawyer. This list is a starting point, not advice:

- **Radio and interference:** FCC Part 15 for the finished device. A radio module that's already certified makes this
  much simpler. A developer kit can't be resold as a product.
- **Electrical safety:** a listed power supply, and a case material with a flame rating (a printed case is for
  prototypes).
- **Connected-device rules:** no shared default passwords. Every Luma makes its own setup code, and each phone is paired
  one at a time.
- **Children:** if kids mode is offered to children under 13, the rules for children's privacy apply.
- **Health claims:** Luma is company, not treatment. Claims should stay there. `docs/CLINICAL_SAFETY.md` is the
  document for clinicians.
- **Public programs:** accessibility (a report against Section 508), and a plain account of what data exists and where
  it lives. For Luma that account is short: it's in the home.

Files here are MIT-licensed.
