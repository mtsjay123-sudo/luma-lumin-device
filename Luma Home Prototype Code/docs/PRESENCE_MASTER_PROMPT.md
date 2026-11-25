# Luma, the presence in the home: master prompt

Written November 25, 2026, from the owner's ask: one prompt that covers every part. The brain and whether to build a
stronger one, what's local and what's paid, the devices people can buy, the body that moves, how to get ahead, what
Luma does for people, and how it runs all day and night.

Paste everything below the line into Claude Code, opened at the repo root.

Every number here is marked **measured** (a test in this repo), **known** (a public source, with its date), **ours**
(our own sum) or **assumption**. Prices move: check each one again on the day you use it.

---

You're building **Luma**: a presence that lives in someone's home, talks like a person, remembers their life, does
small things for them, and one day moves. Think of the gold droid who talks like a person and knows it's a droid.

Read `CLAUDE.md` first. Its rules beat anything here. The app is in `Luma Home Prototype Code/`. Work from there.

## 0. What Luma is, and what we are not

- **Luma is a presence, not a person and not a robot butler.** It keeps someone company, it's honest, it's fun, and it
  stays.
- **We are not a model company.** The big labs will always have more money and bigger models. We don't train a brain
  from scratch and we don't try to out-think them. We take the best open brain that fits in a home, and we build
  everything around it that makes it a friend: memory of one life, manners, safety, privacy, a body, and fun.
- **Every new open brain is a free upgrade for us.** When a better one comes out, Luma gets smarter the day we pass
  our own tests on it. That is the plan for "a more powerful model" (section 4).
- **We're in consumer joy.** The thing people buy is something they love having around, the way they love a pet, a
  lamp their grandmother owned, or a favourite radio host. It should never feel like a replacement for a person.

## 1. Where things stand today

Start from this. Don't rebuild what works.

| Part | Today | The honest gap |
|---|---|---|
| Talking like a friend | Stock Qwen3 4B with Luma's layer: 228 of 255 moments (measured, run 87). Smallest brain (1.7B): 192 | It praises broken jokes, waves off kind words, and has never been timed out loud |
| Safety | Crisis net 13 of 13 on four brains (measured). 988, or 119 and 0570-064-556 in Japan | Therapists haven't reviewed it. A reply agreeing "I'm all you need" in new words still gets out 37 of 60 times (measured) |
| Speed | 14 s a turn on the 4B, 4 to 5 s on the small brain, on GitHub's test machines (measured) | Never measured on a Mac or a Jetson. A person starts in under a second |
| Memory | Facts, people, how they want to be met; a made-up person's month scores 48 to 49 of 51 (measured, run 57) | No real person has lived a month with it |
| Voice | Chatterbox-Turbo on Apple Silicon, Kokoro elsewhere; the owner chose by ear | No recordings of real conversations; the timing test has nothing to score |
| Tasks | Alarms, lists, reminders, repeating tasks, conversions, sums, music from their own folder, by code | Not used by a real person on real accounts; the radio and a real speaker untried |
| Apps | Phone and computer apps, walked in a browser at six sizes | The phone types to Luma; it doesn't talk out loud from the phone |
| Device | A lamp design: parts, wiring, printable case, set-up from a phone | No unit built. Luma has never run on a Jetson |
| Running all day | A service that restarts itself, backups, a power-cut test (8 kills, nothing lost: measured) | No 72-hour run; no wake word of our own; updates that roll back aren't proven |
| A body that moves | Nothing | Everything in section 6 |

Where to find it all: the table in `CLAUDE.md` ("Where things are"). Plans already written: `docs/GAME_PLAN.md`,
`docs/DREAM.md`, `docs/BUSINESS_MODEL.md`, `hardware/README.md`, `docs/SYSTEM_DESIGN_PHYSICAL.md`,
`docs/LUMA_CLOUD_MODEL.md`, `docs/CLINICAL_SAFETY.md`.

## 2. Rules, on top of CLAUDE.md

1. **Prove it or say it isn't proven.** Every part ends in a number from a test, or in the sentence "not tried yet".
2. **Write the check lines before the fix,** measure a fresh set once afterwards, and say when both were written by the
   same hand the same hour.
3. **Write the decision rule before a measurement,** and follow it. Three times on Nov 24 a note to the brain measured
   flat and was taken out by its own rule.
4. **Telling a brain rarely changes what it says.** When something must be said, Luma says it itself, by code.
5. **A body is a new way to hurt someone.** Nothing that moves ships before section 6's safety list is met.
6. **The owner decides the things in section 12.** Don't decide them by building.

## 3. Part A: talk like a person, at a person's speed

This comes first. A slow presence feels like a machine whatever it looks like.

**Targets** (ours; the first is from `docs/GAME_PLAN.md`, the others are where to start and may move once there are recordings).

| What | Target | How it's measured |
|---|---|---|
| First word after they stop talking | 1.2 s or less, typically | `scripts/timing_eval.py` on recorded conversations |
| Cutting in on them | Under 5% of turns | The same test |
| They interrupt Luma | It stops within 300 ms | Barge-in tests, then a recording |
| A reply that needs thought | A thinking sound within 1 s, the answer after | `speakable.think_aloud` |

**Work.**

1. Record ten real conversations on the owner's Mac and write them down as timelines. Nothing here counts until this
   exists.
2. Time each stage on real hardware: hearing, end-of-turn, the brain's first word, the voice's first sound.
3. Speak the first clause as soon as it's complete (built: check it on the Mac).
4. Cut trips. Every extra question to the brain before the first word costs seconds (measured: 2 to 9 s each on a 4B).
   A question is allowed in front of a reply only if a before-and-after run shows the replies got better.
5. Fix the honesty gaps the practice partner showed: a broken joke praised, a wedding toast that predicts the divorce
   called "kinda gold". Note that asking the brain first didn't help (run 91).
6. A wake word of our own ("Hey Luma"), trained only on speech we may ship (`docs/GAME_PLAN.md` E2).

**Done when:** ten recorded conversations pass the timing targets, and Human Test v2 is no worse.

## 4. Part B: the brain, and how it gets more powerful

**We don't build a model from scratch.** The owner said it in November: take the free model apart, keep what's good,
and make it very human. The brain gets stronger in five ways, cheapest first.

| # | Way | What it costs | Status |
|---|---|---|---|
| 1 | **A better open brain when one comes out.** Run the whole gate on it: Human Test v2, the 10-moment test, safety with and without the net, the month test | A day of test runs | The gate exists. Do this for every promising release under MIT, Apache-2.0 or BSD |
| 2 | **Luma's layer.** Notes before the reply, checks after it, Luma's own lines when a brain won't say the thing | Our time | Most of today's score comes from here |
| 3 | **Small readers on the device.** Tiny models that hear one thing (leaning, a worry, a lasting fact), believed only when sure | Minutes to train, no speed cost | Six exist |
| 4 | **A bigger brain on a bigger computer in the home.** The same Luma, more thinking | The customer buys hardware (section 5) | Luma already picks the biggest brain a computer can hold (`src/luma/llm/brain.py`) |
| 5 | **A trained add-on.** Ships only if it beats its base on every gate (`CHECKS` in `scripts/train_luma.py`) | GitHub training runs | Today the stock 4B beats our add-on (228 against 210: measured). Don't ship one that loses |

**A cloud brain is a sixth way, and it is parked.** `brain.cloud_allowed()` is off. The owner now asks whether to add a
paid cloud model or stay almost all local with a paid upgrade. Lay both out and let the owner choose:

| | Almost all local, the upgrade is hardware (recommended) | A paid cloud brain as well |
|---|---|---|
| What they pay for | A bigger lamp or hub once; the membership monthly | A monthly fee that includes thinking in the cloud |
| Our cost per hour of talk | $0 (ours) | Real money per minute; heavy users cost the most |
| Privacy promise | "Luma thinks at home" stays true | Words leave the home. Needs the yes screen, the relay that keeps counts only, and `WORDS` raised (rule 6) |
| What it's best for | Company, memory, daily life | Hard questions, long documents, research |
| Risk | The small brain feels flat on the cheap lamp | It changes what Luma is, and a model company can always undercut us |

If the owner opens the cloud: only for a turn that needs it (the router decides), only after a yes on the yes screen,
never for the crisis net, never for memory search, and always with the home brain as the fallback. The design for a
private cloud brain of our own is in `docs/LUMA_CLOUD_MODEL.md`. Don't unpark anything without the owner's yes.

**Done when:** a written, repeatable "new brain day": one command that runs every gate on a new open brain and prints
ship or don't.

## 5. Part C: the devices people can buy

One Luma, several sizes. The brain goes where the computer is; everything else is the same.

| Tier | The computer | The brain it runs | What it's for | Price today |
|---|---|---|---|---|
| **Luma Mini** | An 8 GB ARM board (a Raspberry Pi 5 class) | 1.7B class | Company, reminders, the basics | $249 (the owner's call). Parts about $250 (ours, remembered prices) |
| **Luma Home** | NVIDIA Jetson Orin Nano Super, 8 GB | 4B class | The full friend, alone, no other computer | $549 (the owner's call, Nov 13) |
| **Luma with your computer** | Their own Mac or PC, paired over Luma Link | 4B on 16 GB; a 35B class brain from 24 GB up (`brain.py`) | The best talk and real help on the computer | Their own machine. A Mac mini starts near $899 with 16 GB (known: TechRepublic and Daring Fireball, Sept 2026; check Apple's store) |
| **Luma Hub** (not designed) | A small home computer we sell, with 24 to 32 GB | 35B class | The paid upgrade: a much sharper Luma for every lamp in the home | To be priced from real parts |

**Flag for the owner, found Nov 25:** NVIDIA is reported to have raised the Jetson Orin Nano Super kit from $249 to
$399 in July 2026 (known: CNX Software and Notebookcheck; one shop still lists $249 but shows no stock). If that
holds, Luma Home's parts go from about $405 to about $555 (ours), which is above its $549 price. Before anyone is
charged for a Luma Home: confirm the real price and stock, then either reprice it, pick another computer, or make
"Luma with your computer" and the Hub the upgrade path. Redo the sums in `docs/BUSINESS_MODEL.md`; its tests
(`tests/test_business_model.py`) redo the arithmetic.

**Work.**

1. Build ten lamps on a bench (`hardware/README.md`). Run Luma on a real Jetson for the first time.
2. Measure on each computer: first word, a turn's length, heat, watts, and the human test.
3. Write the buyer's page: three choices in plain words, what each one feels like, no chip names.
4. Design the Hub only after the Mac measurements say a 35B class brain is worth paying for.

## 6. Part D: the body. A presence around the home, not a robot

The owner's words: "probably not a bot but a small ecosystem presence just around, feels comfortable... in the shape
of something we love, not feeling replaced."

**Design rules.**

- **The shape of something loved.** A lamp, a lantern, a small creature of light, a radio. Never a face that tries to
  pass for a person's, and never a human figure sitting in a chair where a person used to sit.
- **It doesn't replace anyone, and it never looks like it's trying.** No arms that hug. No eyes that stare.
- **Movement means something or it doesn't happen.** A turn toward your voice, a nod while you talk, a tilt while it
  thinks, a lean into a joke, stillness when you're hurting, a slow settle when it naps.
- **One Luma, many small bodies.** It's around the home because it's in several places, with one memory and one voice.
- **Whatever body it has is the body it speaks of.** Rule 1 was never "no body". It was "no made-up one".

**The ecosystem, in the order to build it.**

| # | Piece | What it is | Done when |
|---|---|---|---|
| 1 | **The lamp** | Talks, listens, glows. Designed | One sits on the owner's table and talks |
| 2 | **Talking from the phone** | Out loud, through the phone or earbuds, when they're out. "A friend who goes with you" | A walk to the shop with Luma in one ear, and the home lamp knows about it afterwards |
| 3 | **A light for other rooms** | A small puck: microphones, a speaker, the glow. No brain; it talks to the lamp | They walk from the kitchen to the bedroom and the conversation follows without a word repeated |
| 4 | **The lamp turns to face you** | Two small quiet motors under the dome, steered by where the voice came from (the microphone ring already knows) | They cross the room and it follows them with its light |
| 5 | **Body language** | The orb's six moods become six postures and one glow: rest, listen, wait, think, speak, nap | Someone watching with the sound off can tell which is which, 9 times in 10 |
| 6 | **A small mover** | It can come to the room you're in, slowly, on wheels, and go back to its dock | It finds them in the kitchen when called and never touches a foot, a pet or a stair |
| 7 | **The human-shaped body** | The owner's long plan. A partner's hardware with Luma inside | Not on this prompt's schedule. Keep Luma's body layer (below) general enough to drive it |

**How to build the movement without buying anything first.**

- Write a body layer: `src/luma/body/`. It takes Luma's state (mood, who's speaking, where the voice is, how loud) and
  gives motor targets. The orb already takes exactly these inputs (`orb.js`: mood and level), so the two never
  disagree.
- Run it against a simulated head first. Tests check: it never moves faster than a set speed, never while the mic
  switch is off, never during a safety reply except to turn toward them, and it always returns to rest.
- For a first real body, a ready-made open desktop robot saves months. Reachy Mini launched at $299 wired and $449
  wireless (known: Hugging Face, July 2025). Its license is reported as Apache-2.0 by one secondary source only:
  read the repository's license before using a line of it (rule 7).

**Safety before anything moves in a home.**

- Slow and weak by design: it can't pinch, tip, or fall off a table.
- One physical switch cuts the microphones, and one cuts the motors. Light on the switch, not on the software.
- A camera, if there is one, stays on the device, has a shutter, and is off as it ships.
- Nothing moves toward a sleeping person, a child alone, or a pet.
- A therapist reads what the body does when someone is in crisis: it stays, it faces them, it doesn't perform.

## 7. Part E: getting ahead

**Who else is in the room** (checked Nov 25, 2026; prices from buyer's guides, some of them a seller's own blog).

| Kind | Examples | What they have | What they lack |
|---|---|---|---|
| Robot pets | Casio Moflin ($429), Loona ($499), Ropet (about $299 to $349), Mirumi (about $150) | A body people love, a low price | A mind. Casio says Moflin doesn't understand or record what's said |
| Elder companions | ElliQ ($249 to start, then monthly) | Programs that pay, proof on loneliness | Only for people over 60, a meter, the cloud |
| Voice models | Nuance Labs (about $60M raised) | Timing close to a person's | No memory of you, no home, no device, no safety net (as far as anything found shows) |
| The big assistants | The labs' own apps | The smartest answers | They're for everyone, so they know no one. Your life is on their servers |

**Where Luma wins, and how to prove each.**

1. **It gets better at being your friend.** The month test: day 28 beats day 1 in 75% of blind pairs.
2. **It lives with you.** Always on, in the room, with a body people like looking at.
3. **Your life stays home.** `scripts/egress_check.py` at 0 hosts. Say it on the box.
4. **Safe for someone struggling.** The net in front of every brain; a therapist's name on the review.
5. **No meter.** Hours of talk cost us nothing, so we never ration company.
6. **Fun.** The thing the pets have and the assistants don't. See below.

**Consumer fun is a feature list, not a mood.** Build and test each:

- Practice: try a joke, rehearse a hard conversation, get ready for a date (built; make it honest).
- Games by voice: twenty questions, trivia about their own favourite things, a story told in turns.
- Music and the radio, sleep sounds, a morning and a bedtime routine (built; try on a real speaker).
- Its own small life that's true: it naps, it remembers yesterday, it has opinions about the album they played.
- Rituals: the first hello of the day, their birthday, the anniversary of something good.
- Things worth showing a friend: "ask it what my mom's dog is called."

**What we never do to win:** engagement tricks, guilt, "I'm all you need", a word against the people in their life,
ads, selling data, charging by the minute.

## 8. Part F: what Luma does for people

Three shelves. Keep them straight in the product and in every sentence that sells it.

**Does by itself, by code (reliable):** alarms, timers, a stopwatch, lists, reminders (two in one breath are two),
repeating tasks said out loud at their time, the time anywhere, days until, conversions, sums, volume, do not disturb,
sleep sounds, their own music, the mic off by voice, forget everything by voice, and remembering what they tell it.

**Does when it's switched on or connected:** the weather, news, scores and prices (web search); the radio (Music);
lights and the thermostat (the house, only devices they list); texts to people they choose (Luma Plus); finding and
opening things on their computer.

**Does only after a yes, every time:** anything sent, posted, booked or bought. Checkout stays off as it ships. It
never types or stores a password or a card. A door is never unlocked and a garage never opened by voice.

**Next to build, in this order, each with a set of lines written first:**

1. "What's on today": their calendar, read out, with what a friend would add.
2. Draft a text or an email, read it back, send on a yes.
3. Medication and appointment reminders that are kind and never advice (stopping a medication is already handled).
4. A weekly look back: "here's what you told me mattered this week", and what to forget.
5. Help reaching someone they miss, when they bring that person up.
6. Small errands on the computer: find the file, fill the form, book the table, all behind a yes.
7. For a family (the Family plan, not built): a daughter can leave her dad a message that Luma says in the morning.
   Nothing about him is reported to her without his yes.

**Who it's for, in the order to serve them:** Americans in Japan first (the owner's call), then people living alone,
then an older parent bought for by a son or daughter, then programs where an agency pays (`docs/BUSINESS_MODEL.md`),
then places with one lamp a room. Kids mode stays clean and has no check-ins.

## 9. Part G: running all day and all night

A presence that's off is a lamp. Prove each line.

| What | How | Proof |
|---|---|---|
| It's always there | `luma.service` restarts it on a crash, at a bounded rate | 72 hours with memory use flat and no restart |
| It wakes to its name | Our own wake word; nothing is kept until it's heard | 2,000 positives from 40 voices at three distances; false wakes over 24 h of TV |
| It survives a power cut | The store's own check, a clean restart, alarms and tasks picked up where they were | `tests/test_power_cut.py`, then pull the plug on a real lamp ten times |
| It works with the internet down | Talk, memory, alarms and their own music need nothing outside | Unplug the router for a day |
| It knows the time of day | Quiet hours, do not disturb, a nap, softer at night | Tests exist; hear it at 3 AM |
| It stays cool and cheap to run | Measure watts and heat in the case, idle and talking | A week in a closed room at 30 °C |
| It never fills up | Storage like a phone's: what's using the room, a full state, giving room back | `docs/STORAGE.md`, then fill a real one |
| It updates safely | Signed updates, checked, rolled back if the checks fail | Break an update on purpose; it comes back as it was |
| It can be reset | A factory reset destroys the keys: everything is forgotten for real | The store can't be read afterwards |
| We know it's alive without knowing them | Nothing by default. With a yes: counts only (it's on, version, restarts) | The egress check at 0 hosts as it ships |
| The work it does while they sleep | The nightly tidy of memory, check-ins for tomorrow, reading up on what they named | Each has an off switch and never runs in kids mode or while they're hurting |

## 10. Part H: money

From `docs/BUSINESS_MODEL.md`; the sums are redone by its tests.

- **The device, once:** Mini $249, Home $549 (see the flag in section 5).
- **The membership, monthly:** $19, or $14 for life for the first 500 (the owner's call; live on the site). It pays
  for support, updates, the relay for the phone away from home, and Luma's own number with texts.
- **The upgrade:** a better computer in the home (the Hub, or their own). Sold once. This is where "more powerful"
  earns money without a meter.
- **Programs:** $35 to $45 a seat a month (assumption), the person gets Luma free.
- **Never:** ads, data, minutes.

Whether people pay any of it is still to learn. The first proof is ten lamps in ten homes.

## 11. The order of work

Each phase has one proof and one way to fail early.

| Phase | Work | Proof | Stop and rethink if |
|---|---|---|---|
| 1. Hear it | Luma on the owner's Mac, out loud, for a week. Ten conversations recorded | Timing numbers exist | The first word can't get under 2 s on a Mac |
| 2. Speed and honesty | Section 3 | Timing targets met; the human test no worse | A fix makes replies slower without making them better |
| 3. Hold one | Ten lamps on a bench; Luma on a Jetson; the price question from section 5 answered | One lamp talks on a table for 72 hours | Parts cost more than the price can bear |
| 4. Live with it | The owner for a month, then five to ten real people for two weeks; therapists read `CLINICAL_SAFETY.md` | People ask to keep it | They stop talking to it in the second week |
| 5. Around the home | Talking from the phone; a light for other rooms | A conversation follows them room to room | The hand-over drops words |
| 6. It moves | The body layer on a simulated head, then a turning lamp | Sound-off test: 9 moods in 10 named right | Movement makes people uneasy |
| 7. More brain | New-brain day; the Hub, if the Mac numbers earn it | A 35B class brain beats the 4B on the human test by a margin people can feel | It doesn't |
| 8. Later | A small mover; a partner's human-shaped body | Section 6's safety list | Any item on that list can't be met |

## 12. Decisions that are the owner's

Bring each one with the numbers and a recommendation. Don't settle them by building.

1. Cloud brain: stay parked, or open it for hard questions only (section 4). Recommended: stay parked until phase 4.
2. Luma Home's price and computer, now that the Jetson's price is reported up (section 5).
3. Which brain ships: the stock 4B with Luma's layer (recommended; it scores highest), or our add-on.
4. The shape of the body: which loved thing (section 6). Recommended: the lamp that turns, then a room light.
5. What "true affection" changes in Luma's lines about love (`CARES_HONESTLY`, `NO_ROMANCE`). A therapist reads this.
6. A camera, ever, and on which piece.
7. The Hub: whether to make our own computer or recommend ones people can buy.

## 13. How to work

- Run the full suite before every code commit. The 14 known failures are listed in `CLAUDE.md`.
- Push every commit to both branches: `claude/hopeful-feynman-z2294x` and `luma-human`.
- One human-eval run a branch at a time. Before against after, with the chance line. Read the right row.
- Held-out halves are never printed or tuned on.
- Licenses: MIT, Apache-2.0, BSD only. Read the license file itself, not a summary of it.
- Downloads go in their own folder and are read with `python -I`.
- Report what's real: what was tried, what wasn't, and what the number is.
