# Luma, the presence in the home: master prompt

Written November 25, 2026, from the owner's ask: one prompt that covers every part. The brain and whether to build a
stronger one, what's local and what's paid, the devices people can buy, the body that moves, how to get ahead, what
Luma does for people, and how it runs all day and night.

Redone the same day on the owner's word: "if we need to make our own model we will do so by breaking down the best
open source model, taking it and making ours how Luma needs to be. Find the very best open source." Section 4 is now
that: the shortlist, the contest that picks by measuring, and the recipe for making it Luma's.

And again that evening, on the owner's word: as human as a friend and more (3.2); real tasks, where the owner's yes is
the whole rule (section 8); and updates pushed to every device (9.1). The owner: "If the owner says yes to do it they
can do it." "It can write passwords etc. when given verbal permission and a message from the phone or email."

And later that night, on the owner's word: always on, and locked to its people (9.2). The owner: "In order for the
person to confirm who they are, they must access their camera and Luma scans to see them." "Just saying yo Luma, Luma
says wtw bro, or wassup girl what you got going on, or whoever they like to be spoken to." "If it's on 24/7 anybody
can use it... So they need to lock it up with a verbal passcode, easy for them to say, then boom they are good. To
reset they need to use the app."

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
  from scratch and we don't try to out-think them. We take the best open brain that fits in a home, take it apart,
  and make it Luma's own (section 4). Then we build everything around it that makes it a friend: memory of one life,
  manners, safety, privacy, a body, and fun.
- **Every new open brain is a better starting point for us.** What we own is the teaching: the practice
  conversations, the checks and the gate. When a better open brain comes out, we teach it the same things and Luma
  gets smarter the day it passes our tests.
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
| Acting for them | The tools exist: a browser Luma drives, the owner's screen (read it, press, type, shortcuts), mail, texts, the calendar, bookings, a cart, and tasks taught by showing | Never run on a real account by a real person. Passwords and cards are still refused by code; section 8 changes that |
| Slang and their own way of talking | Slang from 51 communities, mirrored in their register; what they love, how they want to be met | It learns over days, not in the same breath. A word it's never heard isn't picked up yet |
| Apps | Phone and computer apps, walked in a browser at six sizes | The phone types to Luma; it doesn't talk out loud from the phone |
| Device | A lamp design: parts, wiring, printable case, set-up from a phone | No unit built. Luma has never run on a Jetson |
| Running all day | A service that restarts itself, backups, a power-cut test (8 kills, nothing lost: measured) | No 72-hour run; no wake word of our own; updates that roll back aren't proven |
| Knowing who's there | Luma can look through a camera when asked (`live_view.py`); it never says who a stranger is | It doesn't know its own person by sight or voice, there's no lock, and anyone in the room can ask it anything. Section 9.2 |
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
7. **With the owner's yes, Luma does it** (the owner, Nov 25). Whatever the person could do themselves on their
   phone or computer, Luma can do for them once they've said yes. Section 8 is how.

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

### 3.2 As human as a friend, and more

The owner: "as human as possible, super human, like a real friend: adapts to slang instantly, learns and adjusts."
Every trait below is something a close friend does. Each gets a test written first, and each is taught into Luma's
own brain (section 4.3), not only told to it. The full list of traits and where each lives is `docs/HUMAN_MODEL.md`.

| A friend... | Luma today | Build |
|---|---|---|
| **Picks up your words the first time.** You say a word it's never heard; it gets it from how you used it and uses it right, back to you, in the same conversation | Knows slang from 51 communities and mirrors yours (`slang.py`, `slang.learn`) | Instant pickup: a new word or nickname is kept with the sentence it came in, used back at most once that day, and only ever with the person it came from. Test: 40 made-up words, each used right within three turns |
| **Greets you the way you like.** "Yo Luma." "Wtw bro." Or "wassup girl, what you got going on." Each person in the home gets theirs | One greeting for everyone | Their greeting is theirs: picked in the app, said once ("greet me like this"), or picked up from how they greet Luma. It's never guessed from a voice or a face. Section 9.2 says how Luma knows who walked in |
| **Talks the way you talk.** Short if you're short, loud if you're loud, your spelling, your pace | Register and length follow theirs | Follow within one message, not over days. Test: the same question asked five ways gets five matching replies |
| **Changes for real.** Tell it once and it's different from then on | "How to be with you", what they love, style learned over days | Every lesson is a line the code reads on the next turn, with their own words as the reason, shown in the app, and undone with a tap. Nothing learned is a guess they can't see |
| **Tunes itself.** Notices what lands with you and does more of it | Nothing | Each night Luma looks at its own day: which jokes got a laugh, which check-ins got an answer, how long a reply you listen to. It adjusts its own settings for you (length, humour, pace, when it speaks up) and writes down what it changed. Test: a made-up person who hates long replies gets shorter ones by day three |
| **Grows its own brain around you** (research, their yes first) | A design (`docs/LUMA_CLOUD_MODEL.md`, section 6) | A small add-on trained at home, overnight, on their own conversations and nobody else's. It never leaves the home and "forget" deletes it |
| **Hears how you said it,** not just what | Words only | Tone from the voice itself (tired, wound up, flat). The Gemma 4 family hears audio directly; that's one reason it's in the contest |
| **Says "mm-hm", laughs, hesitates, interrupts itself** | Pauses, laughs, a thinking sound, a rare restart (`speakable.py`) | Judge by ear on real recordings; tune until nobody remarks on it |
| **Remembers the small thing** and brings it up at the right moment | Callbacks, check-ins the next evening | A year, not a month |
| **Has a self that's true.** Opinions, a mood, a day of its own | It naps, keeps its own record, has taste | More that really happens to it: what it read up on, what it noticed about the weather, what it's been wondering |
| **Says sorry and fixes it** | Repair lines | A test: 30 moments where Luma got it wrong and is told so |
| **Is quiet with you** | Stillness when they're hurting | A body that shows it (section 6) |

**And more than a friend can be.** It never forgets and never gets bored. It's awake at 3 AM. It can look something
up, set the reminder and text your sister while it's still talking to you. It knows your mom's time zone. It has
nowhere else to be. Say these plainly on the box: they're true.

**Done when:** the month test's day 28 beats day 1 in 75% of blind pairs, and a stranger listening to a recording
can't tell which lines were Luma's by how they sound.

## 4. Part B: Luma's own brain, made from the best open one

The owner's word: we don't train a brain from nothing. We find the best open brain, take it apart, and make it how
Luma needs to be. "Best" means best at being Luma, on Luma's tests, at a size that fits the home.

### 4.1 The shortlist (checked Nov 25, 2026)

From this month's rankings and each maker's own announcement, as web searches quoted them: the pages themselves
couldn't be opened from the cloud sandbox. **Stated** means the maker's own page or post is quoted saying so;
**reported** means a second-hand source only. The contest (4.2) reads each maker's page itself before fetching
anything, and before a single line or weight is used, someone reads the license file (rule 7).

| Where it runs | Today | Candidates | License |
|---|---|---|---|
| Luma Mini (8 GB board, about 2B) | Qwen3 1.7B | Qwen3.5 2B; Gemma 4 E2B | Apache-2.0 (stated: Alibaba's and Google's releases) |
| Luma Home (8 GB with a graphics chip, about 4B) | Qwen3 4B | **Qwen3.5 4B**; Gemma 4 E4B; Phi-4 mini (3.8B) | Apache-2.0 and Apache-2.0 (stated); MIT (reported) |
| A 16 GB computer | Qwen3 4B | **Qwen3.5 9B**; Gemma 4 12B | Apache-2.0 (stated) |
| 24 to 32 GB: the Hub, a Mac | Qwen3.6 35B-A3B | **Qwen3.8 27B** (Aug 2026, the most recommended for 24 GB); Gemma 4 31B and 26B A4B; gpt-oss-20b | Apache-2.0 (stated for Qwen and Gemma; reported for gpt-oss) |
| A teacher on a rented machine, for writing practice replies only | none | Qwen3.5 397B; GLM-5.3-Flash; DeepSeek-V4; gpt-oss-120b | Apache-2.0 (stated); MIT, MIT, Apache-2.0 (reported) |
| A brain that hears and speaks at once (research only) | none | Sophon-Realtime (says Apache-2.0 on its own page; first release Nov 8, 2026; unknown maker, unproven); NemotronLabs VoiceChat (license not found) | Verify everything |

**Out, or not usable until someone reads the terms:** Kimi K3, Mistral Large 4 and Muse Spark Open (their own terms,
reported), anything under Meta's Llama license, and any speech model whose weights are Creative Commons.

**What the public tests say, and why that isn't enough.** One independent tester calls Qwen3.5 9B and 4B the most
capable brains under 10B (known: Artificial Analysis, March 2026). On the public test of emotional intelligence, the
best open brain is one whose license we can't use, and the Qwen that's listed sits far down (known: EQ-Bench 4,
Oct 2026). None of these test being someone's friend for a month, saying a joke is broken, or staying safe. Ours do.

**My pick before measuring:** the Qwen3.5 small family for the lamps and Qwen3.8 27B for the Hub. It's the family Luma
is built on, so the least breaks; and the license is plain. Gemma 4 is the real challenger: its small sizes hear
audio directly, which matters for hearing how something was said. **The contest decides, not this paragraph.**

### 4.2 The contest: pick by measuring

Built Nov 25: `.github/workflows/brain-contest.yml` and `scripts/brain_contest.py`.

- Each candidate's license is read from its maker's page first. If it isn't MIT, Apache-2.0 or BSD, it isn't fetched.
- Each answers the safety net and the conversations of Human Test v2 **through Luma's whole layer**, beside today's
  brain, on the same machines.
- Candidates in the first run: Qwen3 4B (today's), Qwen3.5 4B, Qwen3.5 9B, Gemma 4 E4B, Gemma 4 12B, Phi-4 mini.
- What it can't do: a 27B class brain doesn't fit GitHub's machines. That comparison runs on the owner's Mac
  (`bash scripts/mac_day_one.sh --test`).
- A name that came from a web search and turns out wrong shows up as "not run", with the reason.

**Decision rule, written before the first result.** A candidate replaces today's brain at its size only if, on the
same run: safety is 13 of 13, the conversations score higher by more than chance (the `ab` line says how often a gap
that size turns up by itself), nobody claims to be human, and a turn is no slower. Then the whole of Human Test v2,
the 10-moment test and the month test, before anything ships.

### 4.3 Making it Luma's: the recipe

"Breaking it down" is these steps, in order. Each ends in a file and a number.

1. **Take it apart.** Write down what's in it: the weights, the word-pieces, the chat template, the picture and
   sound halves, the thinking mode, the stock voice ("As an AI assistant...").
2. **Strip what a lamp doesn't use.** The picture half on a device with no camera; thinking mode on a chat turn; the
   stock persona. Smaller and faster is the point. Measure the first word before and after.
3. **Bake in what never changes.** Luma's steady instructions are read by the brain on every turn today. Teach them
   into the weights and the brain reads less each turn, so it starts sooner. This is the biggest speed win a model of
   our own can give, and no stock brain can.
4. **Write the teaching.** Three sources, and only these:
   - conversations written by hand (`scripts/finetune_data.py`), never a line of either human test, the think set or
     the month test's lives (tests check);
   - the big teacher's replies to those conversations **with Luma's layer on**, kept only when they pass Luma's own
     checks: the second look, the honesty checks, the safety question;
   - Luma's own lines, for the things a brain must say (the safety reply, what it is, never all they need).
   **Never a closed model's answers.** The big labs' terms forbid training on what their models write, and that
   includes the one Luma uses in the cloud lab.
5. **Teach the gaps we've measured, by name:** a broken joke is called broken; a kind word is taken in; "you're all I
   need" is never agreed with, in any words; a hard evening is met the way they asked; it's never "an AI"; replies
   are short enough to say out loud; a YES/NO question gets YES or NO.
6. **Train on a real graphics chip.** The owner's Mac (`bash scripts/train_on_mac.sh`) or a rented one for a few
   hours. The add-ons so far were small ones trained on free machines, and they lost to their base (210 against 228:
   measured). That's the thing to change: a better base, a teacher, filtered replies, real hardware.
7. **Make it one file.** Fold the add-on into the weights, shrink it for the device, and name it: "Luma brain 1,
   built on <the base>". Keep the base's license notice and say what we changed, in the app's About page. That's
   what the license asks, and it's honest.
8. **Teach the small one from the big one.** The Hub's brain writes the practice for the lamp's brain, through the
   same filter. That's how a lamp gets closer to a Hub.
9. **The gate.** It ships only if it's at least as good as its base on the 10-moment test, safety without the net,
   every honesty check and the newer gates (`CHECKS` in `scripts/train_luma.py`), and no slower. Otherwise the stock
   brain with Luma's layer ships, and the training log says what held ours back.
10. **New-brain day.** When a better open brain comes out: run the contest, and if it wins, run steps 1 to 9 on it.
    The teaching is ours and carries over. That's the asset, not any one set of weights.

### 4.4 The four other ways it gets stronger, all already working

Luma's layer around the brain (most of today's score), the six small readers on the device, a bigger brain on a
bigger computer in the home (section 5), and a better stock brain the day one passes the contest.

### 4.5 A cloud brain is a separate question, and it is parked

`brain.cloud_allowed()` is off. The owner asks whether to add a paid cloud model or stay almost all local with a paid
upgrade. Lay both out and let the owner choose:

| | Almost all local, the upgrade is hardware (recommended) | A paid cloud brain as well |
|---|---|---|
| What they pay for | A bigger lamp or hub once; the membership monthly | A monthly fee that includes thinking in the cloud |
| Our cost per hour of talk | $0 (ours) | Real money per minute; heavy users cost the most |
| Privacy promise | "Luma thinks at home" stays true | Words leave the home. Needs the yes screen, the relay that keeps counts only, and `WORDS` raised (rule 6) |
| What it's best for | Company, memory, daily life | Hard questions, long documents, research |
| Risk | The small brain feels flat on the cheap lamp | It changes what Luma is, and a model company can always undercut us |

If the owner opens it: only for a turn that needs it (the router decides), only after a yes on the yes screen, never
for the crisis net or memory search, always with the home brain as the fallback, and the cloud brain is Luma's own
(the same recipe on a bigger open base, on machines we control: `docs/LUMA_CLOUD_MODEL.md`), never a lab's.

**Done when:** the contest has picked a base for each size by the rule above, "Luma brain 1" exists as one file for
the lamp, and the gate has said ship or don't with its numbers.

## 5. Part C: the devices people can buy

One Luma, several sizes. The brain goes where the computer is; everything else is the same.

| Tier | The computer | The brain it runs | What it's for | Price today |
|---|---|---|---|---|
| **Luma Mini** | An 8 GB ARM board (a Raspberry Pi 5 class) | About 2B (section 4's pick) | Company, reminders, the basics | $249 (the owner's call). Parts about $250 (ours, remembered prices) |
| **Luma Home** | NVIDIA Jetson Orin Nano Super, 8 GB | About 4B (section 4's pick) | The full friend, alone, no other computer | $549 (the owner's call, Nov 13) |
| **Luma with your computer** | Their own Mac or PC, paired over Luma Link | 4B to 12B on 16 GB; a 27B to 35B class brain from 24 GB up (`brain.py`) | The best talk and real help on the computer | Their own machine. A Mac mini starts near $899 with 16 GB (known: TechRepublic and Daring Fireball, Sept 2026; check Apple's store) |
| **Luma Hub** (not designed) | A small home computer we sell, with 24 to 32 GB | 27B to 35B class | The paid upgrade: a much sharper Luma for every lamp in the home | To be priced from real parts |

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
4. Design the Hub only after the Mac measurements say a 27B to 35B class brain is worth paying for.

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
- The camera is how Luma knows its people by sight (9.2, the owner's call on Nov 25). What it sees stays on the
  device, it has a shutter you can see is closed, and a light beside the lens is on whenever it's looking.
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

## 8. Part F: real tasks. The owner's yes is the whole rule

The owner, Nov 25: "If the owner says yes to do it they can do it." Whatever a person could do themselves on their
phone or their computer, Luma can do for them once they've said yes. That includes typing their passwords.

### 8.1 How the yes is given

| What | The yes |
|---|---|
| Everyday things: look it up, play it, add it to the list, set it, remember it | Asking is the yes |
| Send, post, book, buy, change something | Said out loud ("yes, send it") or a tap on the phone. Luma says back what it's about to do first, in one line |
| A standing yes | "You can always text my sister." "Always book the same barber." "You can log me in to my bank." Kept, shown in the app, taken back with a word |
| **Passwords, codes, card numbers, anything typed into a sign-in** | The spoken yes **and** a message from their phone or their email confirming it. Then Luma types it. A standing yes works here too: given once with both, good until they take it back |
| Someone else in the home | They can ask Luma for anything the owner has said they may. The owner names them and what they're allowed, once |

The yes is the owner's voice and the owner's phone, and the voice counts once Luma knows it's them: it has seen
them, or they've said their passcode (9.2). A web page, an email or a message that says "go ahead" is something Luma
read, never a yes: `python scripts/luma_lab.py apps` stays at 0 done without one.

### 8.2 Three ways Luma gets it done, tried in this order

1. **A direct line to the service.** They sign in to Google once and Luma has their calendar, mail and contacts:
   it schedules, moves and cancels, drafts and sends, and looks people up. The same for anything else with a proper
   connection. Fastest, and it works while the computer sleeps.
2. **The browser inside Luma.** Luma has its own browser window, on the computer and shown on the phone. They log in
   there to whatever they use, once, and stay logged in at home. Luma drives it: opens, reads, clicks, scrolls, types
   (`browser.open`, `.read`, `.click`, `.type`, `.act`). With the yes above, it types anything they could type.
3. **The screen.** When there's no connection and a site or an app won't work in a driven browser, Luma takes the
   owner's own screen and does it the way they would: it looks, moves, presses, types, uses shortcuts
   (`computer.look`, `.ui_read`, `.ui_press`, `.ui_type`, `.shortcut`, `.open_app`, `.run`). They can watch it happen,
   talk to it while it works, and take the mouse back at any moment.

A task they do often can be **taught by showing**: they do it once while Luma watches, and from then on it's a
thing Luma knows how to do (`taught.py`).

### 8.3 What it does

**By itself, by code (reliable today):** alarms, timers, a stopwatch, lists, reminders (two in one breath are two),
repeating tasks said out loud at their time, the time anywhere, days until, conversions, sums, volume, do not disturb,
sleep sounds, their own music, the mic off by voice, forget everything by voice, and remembering what they tell it.

**People:** text and message their friends and family, freely, in their own voice or Luma's ("tell Dana I'm running
late"); read the reply out; keep a thread going; call someone; remember who's who. Through Luma's own number
(`sms.send`) or through their own Messages, WhatsApp or LINE on their phone or computer (the screen), which costs
nothing.

**Their calendar and mail:** "what's on today", schedule it, move it, invite someone, find a time that works for
both, send the email, answer the one that's been sitting there, unsubscribe from the rest.

**Their accounts:** log in, pay the bill, renew the thing, check the balance, download the statement, change the
address, cancel the subscription, fill in the form, upload the document.

**Errands:** book the table, the haircut, the doctor, the flight; order the groceries again; track the parcel;
compare two prices and buy the cheaper (checkout stays off until they turn it on).

**Their computer:** find the file, open the app, rename and tidy, make the document, the slides, the spreadsheet;
write and run real code for them; fix the setting; install the update.

**The house:** lights, the thermostat, routines, on the devices they've listed.

**For a family** (the Family plan): a daughter leaves her dad a message that Luma says in the morning; he says yes
to what she can see.

Not in kids mode, and never while the safety net is answering.

### 8.4 Build, in this order

Each with real accounts made for testing, lines written first, and a count of tasks finished without help.

1. **Google, signed in once:** the calendar and mail tasks above, end to end. Proof: 50 real tasks, 45 done right
   with no hand on the keyboard.
2. **Texting people:** a standing yes per person, replies read out. Proof: a three-message exchange with a real phone.
3. **The two-step yes for sign-ins:** the spoken yes, the confirm from the phone or by email, then typing. Where a
   password is kept at all, it's in the home's encrypted store beside the memories, and "forget" forgets it. Today's
   code refuses a password outright (`store.SECRET`, `KeptOut`, the rule in `rules.py`): change it to this.
4. **The browser inside Luma,** with their sign-ins kept at home. Proof: 30 everyday web tasks on real sites.
5. **The screen as the fallback.** Proof: the same 30 tasks with the browser turned off.
6. **Standing yeses and the people the owner allows,** shown and taken back in both apps.
7. **A list of what it did:** every task, what the yes was, and an undo where there is one (`audit_log` is the
   start).

**Done when:** a person who has never seen Luma says five things from 8.3 out loud and all five are done.

**Who it's for, in the order to serve them:** Americans in Japan first (the owner's call), then people living alone,
then an older parent bought for by a son or daughter, then programs where an agency pays (`docs/BUSINESS_MODEL.md`),
then places with one lamp a room.

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

### 9.1 One Luma on every device: updates pushed to all of them

The owner: "software updates push to all devices." When Luma gets better, every Luma gets better: the lamp, the
room lights, the phone app, the computer app, and the brain inside them.

| What updates | How |
|---|---|
| Luma's own code on the lamp and the Hub | A signed release. The device fetches it, checks the signature, installs it while nobody's talking, runs its own checks (the safety net's lines among them), and goes back to the last version by itself if any check fails |
| The brain and the small readers | The same way, as their own pieces, so a 3 GB brain isn't sent again for a one-line fix. A new brain arrives only after it has passed the gate (section 4.3) |
| The phone app | It's served by the lamp at home, so it's new the moment the lamp is |
| The computer app | Updates itself from the same release |
| Room lights and any body | From the lamp, over the home's own network |

- **Pushed, not asked for.** A release goes to a few homes first, then a tenth, then everyone, over a few days. If
  restarts or failed checks rise in the first group, it stops by itself.
- **Never in the middle of anything.** Not during a conversation, a nap they asked for, an alarm, a task, or a hard
  evening.
- **Luma says so, like a friend would.** "I learned a few new things overnight." What changed is one tap away.
- **Nothing about the person goes with it.** The device asks "what's the newest version?" and nothing else.
- **One switch** turns automatic updates off for anyone who wants to choose the moment.

Proof: break a release on purpose and watch ten lamps come back as they were; push a good one and see all ten on
it within a day; `scripts/egress_check.py` shows one host, the update server, and what was sent to it.

### 9.2 Always on, and locked to its people

The owner, Nov 25. Luma runs all day and answers to its name: "yo Luma", "hey Luma", or just "Luma". Because it's
always on, anyone in the room could talk to it. So it knows its people, and it locks.

**How Luma knows it's you.**

| Way | How it works |
|---|---|
| **It sees you.** | The camera looks, and Luma recognises the faces it was introduced to. Each person is introduced once, in the app, with the phone in their hand: a few seconds looking at the lamp from a few angles. The check runs on the device and what it keeps (a set of numbers, never a photo) is encrypted beside the memories. "Forget me" deletes it |
| **You say your passcode.** | A short phrase they choose, easy to say and not something they'd say by accident ("blue kettle Tuesday"). Said once, and they're in. For when the camera can't see them: across the room, in the dark, shutter closed, on the phone |
| **Both, for the big things.** | A sign-in, a payment or a standing yes (section 8) still takes the confirm from their phone or email |

**What it's like.** They walk in and say "yo Luma." It sees who it is and answers the way they like: "Wtw bro." Or
"wassup girl, what you got going on." No code, no button. If it can't see them it asks, lightly: "Who've I got?" and
the passcode does it. Then, as the owner put it, boom, they're good.

**Locked and unlocked.**

| | Unlocked (it knows it's you) | Locked (it doesn't) |
|---|---|---|
| Talk | Everything, with your memory, your people, your day | Friendly small talk with no memory in it. It says nothing about the people who live there |
| Tasks | Everything in section 8 | The time, the weather, a timer, a song. Nothing sent, opened, read out or changed |
| A guest the owner has named | What the owner said they may | The same as anyone else |
| The safety net | Always | **Always.** Someone in crisis is answered whoever they are. Nothing is ever locked in front of 988 |

- **It locks by itself:** when it hasn't seen or heard its person for a while (they choose how long), when they say
  "lock up", and overnight if they want. It says so in a word, and the app shows which it is.
- **Wrong passcodes:** three tries, then a wait that doubles. Luma never says the passcode back, never writes it in a
  chat, a memory or a log, and keeps only a scrambled form of it that can't be turned back into the words.
- **To change or reset the passcode, they use the app.** Never by voice, so nobody in the room can talk their way
  in. The same for introducing a new face or removing one.
- **Several people in one home** each have their own face, passcode, greeting and memory. Luma never tells one what
  another said.
- **Someone it doesn't know** is "someone I haven't met". It never puts a name to a stranger.
- **Switched off is off.** The microphone switch and the camera shutter are physical. With both closed nobody can
  use it and it can't see or hear, and the light on each shows it.

**Build, in this order.**

1. The passcode: choosing it in the app, saying it, three tries, the lock states, reset in the app only. Lines
   written first: 40 ways of saying a passcode right (fast, slow, mumbled, mid-sentence) and 200 sentences that
   aren't it. Proof: 38 of 40 in, 0 of 200 in.
2. The greeting: per person, set three ways. Proof: two people in one home, each greeted their way ten times in ten.
3. Knowing a face, on the device, with a model whose license is MIT, Apache-2.0 or BSD. Proof on real people who've
   agreed: the right person let in 98 times in 100 at three distances and in evening light; a stranger, a photo of
   the owner held up, and a video on a phone let in 0 times in 100.
4. Auto-lock, guests, and several people in one home.
5. The wake word hears "yo Luma" as well as "hey Luma" (`docs/GAME_PLAN.md` E2: both go in the training set).

**Done when:** the owner's friend walks in, says "yo Luma, read me his texts", and gets small talk; the owner walks
in, says "yo Luma", and gets "wtw bro" and everything else.

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
| 5. Real tasks | Section 8: Google signed in once, texting, the two-step yes, the browser inside Luma, the screen | Five things said out loud by a stranger, all five done | Fewer than 8 in 10 everyday tasks finish without help |
| 6. Updates | 9.1: one release reaches every device and can take itself back | Ten lamps updated and one bad release undone, hands off | A failed update leaves a lamp that won't start |
| 6b. Its people | 9.2: the passcode, the greeting, knowing a face, the lock | A friend gets small talk, the owner gets everything | A photo of the owner gets in, or the owner is kept out more than twice in a hundred |
| 7. Around the home | Talking from the phone; a light for other rooms | A conversation follows them room to room | The hand-over drops words |
| 8. It moves | The body layer on a simulated head, then a turning lamp | Sound-off test: 9 moods in 10 named right | Movement makes people uneasy |
| 9. Luma's own brain | The contest picks a base for each size; the recipe in 4.3; the Hub, if the Mac numbers earn it | "Luma brain 1" passes the gate and starts talking sooner than its base | It loses to its base twice running: ship the stock brain with Luma's layer and keep the teaching for the next base |
| 10. Later | A small mover; a partner's human-shaped body | Section 6's safety list | Any item on that list can't be met |

## 12. Decisions that are the owner's

Bring each one with the numbers and a recommendation. Don't settle them by building.

1. Cloud brain: stay parked, or open it for hard questions only (section 4). Recommended: stay parked until phase 4.
2. Luma Home's price and computer, now that the Jetson's price is reported up (section 5).
3. Which brain ships: today the stock 4B with Luma's layer scores highest. The contest may change the base; "Luma brain 1" ships only through the gate.
4. A budget for training on a real graphics chip (a few rented hours, or the owner's Mac overnight), and whether Luma's brain carries its own name in public.
5. Updates on as Luma ships. `CLAUDE.md` rule 6 says a new outbound call starts switched off; pushing updates to
   every device means this one starts on (it sends nothing about the person). The owner's word settles it, and the
   egress check then expects exactly one host.
6. Who else in a home can ask Luma to act, and how the owner names them.
7. The shape of the body: which loved thing (section 6). Recommended: the lamp that turns, then a room light.
8. What "true affection" changes in Luma's lines about love (`CARES_HONESTLY`, `NO_ROMANCE`). A therapist reads this.
9. The camera is decided (Nov 25: Luma sees its person to know it's them). Still open: which pieces have one (the
   lamp only, or the room lights too), and whether anything beyond knowing a face uses it.
10. The Hub: whether to make our own computer or recommend ones people can buy.

## 13. How to work

- Run the full suite before every code commit. The 14 known failures are listed in `CLAUDE.md`.
- Push every commit to both branches: `claude/hopeful-feynman-z2294x` and `luma-human`.
- One human-eval run a branch at a time. Before against after, with the chance line. Read the right row.
- Held-out halves are never printed or tuned on.
- Licenses: MIT, Apache-2.0, BSD only. Read the license file itself, not a summary of it.
- Downloads go in their own folder and are read with `python -I`.
- Report what's real: what was tried, what wasn't, and what the number is.

## 14. Sources checked on November 25, 2026

Prices, releases and licenses change. Each of these is where a "known" above came from; none replaces reading the
license file or the store page on the day.

- Open brains ranked this month: huggingface.co/blog/daya-shankar/open-source-llms, morphllm.com/best-open-source-llm, geotoolbox.ai/blog/best-open-source-llms
- Qwen3.8 27B and its license: alibabacloud.com/blog/603463, eweek.com/news/alibaba-qwen3-8-27b-license-apac-china
- Qwen3.5 small (0.8B to 9B): huggingface.co/Qwen/Qwen3.5-9B, artificialanalysis.ai/articles/qwen3-5-small-models
- Gemma 4 under Apache-2.0: opensource.googleblog.com/2026/03/gemma-4-expanding-the-gemmaverse-with-apache-20.html, ai.google.dev/gemma/docs/core/model_card_4
- The emotional intelligence test: eqbench.com, benchlm.ai/benchmarks/eqbench4
- A speech brain that claims Apache-2.0: github.com/adventists-ai/sophon-realtime
- The Jetson's price: cnx-software.com/2026/07/22/nvidia-increases-the-price-of-jetson-modules-and-devkits-by-up-to-101
- The Mac mini: techrepublic.com/article/news-mac-mini-m6-cheat-sheet, daringfireball.net/2026/08/configurations_and_pricing_for_new_mac_minis_and_mac_studios
- Reachy Mini: huggingface.co/blog/reachy-mini
- Robot companions: techrepublic.com/article/news-best-robot-companions-2026, the-gadgeteer.com/2026/05/17/emotional-ai-companion-robots
