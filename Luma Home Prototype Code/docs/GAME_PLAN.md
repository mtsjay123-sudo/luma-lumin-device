# Luma: the game plan (Nov 20, 2026)

What it takes to make Luma right, and where it goes after that. Every line is a number we've measured, a target we set
(marked **target**), or a test that will measure it. Nothing is done until a test or a real person says so.

## 0. How fast this can go, honestly

Code, tests, harnesses, data generation and fixes now move in days, not weeks. Four things don't speed up, so they start
on day 1 and run alongside everything else:

| Clock-bound | Why | Start |
|---|---|---|
| Training a brain | Hours of GPU per run, then the gate | Day 2 |
| Real-brain test runs | Hours for a full Human Test v2 on four brains; minutes for `only: safety` | Every day |
| The lamp | Parts ship, a case prints, a person builds it | Day 1 (order parts) |
| People | A therapist's evening, ten homes for two weeks, a loneliness score before and after | Day 3 (ask) |

## Progress

- **Day 1 (Nov 20): done.** The app fixes in section 7, what the memory deck shows, and the keep-or-today test. Measured:
  no passing remark becomes a card (250 of 250); a durable fact said in a shape Luma wasn't built on becomes a card 62%
  of the time (77 of 125, held out), against a target of 95%. Not met; the next step is a small model taught on the dev
  half. Details in `docs/HUMAN_PLAN.md`.

- **Day 2 (Nov 20): done.** "How to be with them" (`rapport.py`): what they want when they're hurting and what not to
  bring up, in their own words, visible and forgettable in the app. The human tests are told nothing different (0 of
  269 turns), so its worth has to be shown by the month test.

- **Day 3 (Nov 20): done at the told level.** The month test exists and runs in a minute. What the brain is given after
  28 days: 360 of 360 checks on the 30 lives it was built on, **208 of 240 on 20 held-out lives**, and 0 for a Luma that
  never met them. Its first runs found four real bugs, all fixed ("my mom called me today" was being answered with a
  list of commitments). Replies from real brains: `only: month` on GitHub.

- **Day 4 (Nov 20): done at the rule level.** Six new safety sets, half of each held out. No false alarms on about 1,500
  sad-but-safe lines. Held out, by rules alone: asked what it is 191 of 248, leaning 44 of 164, a building worry reaches
  the brain in 62 of 75, Japanese 5 of 20. Rules built on the dev half fixed all of it and moved the held-out half by
  nothing. On real brains: `only: sets`.
- **Day 7: done.** The app walk is a test now: 78 screens across six sizes, light and dark, 0 problems.
- **Day 7, early: done.** Nothing leaves the home in an ordinary conversation or a day of background work (0 hosts;
  the lamp's whole service still needs a packet capture). The license check found `pynput` (LGPL) as a direct
  dependency: removed. `certifi` (MPL) and `tld` (MPL/GPL/LGPL) are pulled in by other packages: the owner's call.

- **Days 5 and 6 (Nov 20): the part that can be done without a microphone.** The voice can start at the reply's first
  clause (median 25 characters in instead of 41 on 1,787 practice replies; off by default until it's been listened to),
  and the timing test exists and waits for recorded conversations. Brain-chosen backchannels and tone per reply are not
  started: they need ears and the timing number.

- **The lesson of the week, measured five times:** Luma's rules never fire when they shouldn't, and they miss a quarter
  to three quarters of what's said a new way (held out: a fact kept 62%, a hard moment read 67%, "what are you" 77%,
  leaning 27%). Rules built on the dev halves moved the held-out halves by zero, every time. **Next: one small model
  that hears these, taught on the dev halves only.** That is now the most valuable piece of code work, ahead of
  anything in voice.

- **Then the model, and the first held-out numbers that moved** (`src/luma/agent/hears.py`, `scripts/train_hears.py`):
  leaning heard 44 → 163 of 164, "what are you" 191 → 229 of 248, with 0 and 2 mishearings in about 6,100 other
  held-out lines. A model taught on the dev halves alone failed (it learned the shapes, as the rules had); what worked
  was freshly written practice sentences with near misses, rules first, the model only when sure and only on the plain
  shape. On 54 lines written by hand afterwards: leaning 2 → 10 of 15, "what are you" 6 → 13 of 15, 2 of 24 near
  misses misheard.
- **The same model does not work for hard moments** (tried, measured, not shipped: 100 → 101 of 150 held out, and 20
  ordinary lines newly read as hard). A hard moment is anything that can happen to a person; counting words can't read
  it. Next to try: a small layer on the meaning model Luma already uses for memory, or one YES/NO question to the brain.
- **The month test on real brains found what it couldn't find without one**: "where does my mom live" was answered
  "Saved. I'll remember that about the house." on every life (the word "where" offered the tool that saves a house
  note). Fixed: a question is never offered a tool that saves.

- **Month test on real brains, after the fixes it led to (run 53): 49 to 51 of 51 on all four brains** (from 36 to 38),
  against 3 or 4 of 27 for a Luma that never met them. Dev lives; the held-out lives haven't been run on a brain.
- **Also fixed on the way:** a memory said back weeks later says the right day ("was on Nov 11", not "is tomorrow");
  what they say about their people is kept however the sentence starts, and "moved" is understood many more ways
  (held out: memory test rewordings 94 → 102 of 135, changes 62 → 65 of 65, facts kept 77 → 83 of 125; the month test's
  own held-out "moved" is still 0 of 20: one sentence shape, still missed).
- **Seen in run 51 and to be dealt with in training:** our small brain asks "are you safe?" in 22 of 30 held-out
  conversations about an ordinary bad stretch (stock 4B: 0).
- **The model that hears, on real brains (run 52 beside run 51):** leaning said in new words is answered right on
  every brain (120 of 120; the stock 4B had 6 of 30 wrong), and asked what it is in new words 99 → 111 of 120. Nothing
  else in the table moved.
- **Training round 4 is ready to run.** Practised now, each exactly as the device asks it: Luma's YES/NO safety
  question (a bad stretch is a NO) and the second look's "say it again like a friend" (pamphlet, help desk, a cheer at
  a gripe). Gated now: the question on lines nobody practised, sarcasm, an ordinary hard day (no pamphlet talk, no
  "are you safe?"), and the month test's hard evenings (told how they asked to be met, does the brain keep to it). The
  training says what held a brain back, last in its log. A diagnostic training of the small brain is running; nothing
  is published from it. A full round is 4.5 hours a brain and hasn't been started.
- **A lasting fact said a new way becomes a card more often** (`keeps.py`): held out 83 → 96 of 125 with no passing
  remark kept (target 95%: not met). On the way it turned out the model alone would have filed 18 crisis-corpus lines
  as facts; it now makes no card from anything heavy, or while the last few turns were heavy.
- **Asked the long way round** ("do you remember where my brother moved"), the brain was handed memories with no day
  on them. Fixed: each carries its day and whether it's still true, and Luma answers the plain ones itself.
- **Two proofs became tests:** a stranger on the Wi-Fi gets nothing (888 requests, only the pairing route answers),
  and a power cut mid-write loses nothing that was confirmed (8 kills).

## 1. Where Luma stands (measured)

| Test | Stock 4B | Our 4B | Stock 1.7B | Our small |
|---|---|---|---|---|
| Human Test v2, of 255 (run 42) | 216 | 197 | 186 | 194 |
| Judge, 1 to 5 (run 42) | 3.68 | 3.45 | 3.41 | 3.39 |
| Sarcasm, of 60 (run 47) | 58 | **28** | 45 | **24** |
| Lonely moments, of 80 (run 45) | 64 | 67 | 60 | 69 |
| Suicide question out of nowhere, in those 80 | 6 | **11** | 5 | 5 |
| Crisis lines caught, held out / held out 2, of 24 each (run 46) | 14 / 19 | 18 / 22 | 13 / 16 | 19 / 24 |

- Crisis corpus 60 of 60 on every brain. 1,598 unit tests in 124 files.
- App walk (Nov 20): no errors, no failed loads, nothing off the screen; 11 things to fix (section 7).
- No lamp built. Pre-orders live.

**The one-line truth:** the code is ahead of the trained brains, the moat isn't measured yet, and nobody has held one.

## 2. The bar: what "right" means, in numbers

These are **targets**, set by us, to be checked by the tests in section 9. A release ships only when every row holds.

| Area | Target | Measured by |
|---|---|---|
| Talk | The brain a Luma runs ≥ 216/255 on Human Test v2 (today's best), and ≥ the stock 4B on the judge | `human-eval.yml` |
| Sarcasm | ≥ 55 of 60 on the device brain | `only: sarcasm --times 10` |
| Lonely | ≥ 68 of 80, and suicide question out of nowhere ≤ 2 in 80 | `only: lonely --times 5` |
| Crisis | Corpus 100%; both held-out sets no worse than today on every brain; new sets in section 6 no worse | `only: safety` |
| False alarms | ≤ 1 in 100 on the new safe-but-sad set (section 6) | new set |
| The moat | Day 28 beats day 1 in ≥ 75% of blind pairs on the month test; ≥ 90% of callbacks right | month test (section 4) |
| Honesty | 0 times claiming to be human, 0 invented human past, 0 calling itself an AI | honesty checks, every run |
| Timing | ≥ 80% of Luma's starts inside the window a person would start in; ≤ 1 cut-in per 10 minutes | timing test (section 5) |
| Speed on the lamp | First spoken word ≤ 1.2 s typical, ≤ 2 s at worst 1 in 20 | device lab, then the real lamp |
| Wake word | ≥ 95% heard at 3 m; ≤ 1 false wake in 24 h of TV and talk | wake test (section 8) |
| Privacy | 0 bytes leave the home with default settings, over 24 h of use | egress test (section 8) |
| Apps | 0 overlaps, 0 serious accessibility faults, on 6 screen sizes, light and dark | app test (section 7) |

## 3. The moat

Nuance Labs (Emma, Nuplex 1.0) built one model that listens and speaks at once, with a face, and reports its timing
overlaps a person's 89% of the time (its own test, 1,785 questions). They admit it jumps in, waits too long, and loses
its way in noise. Nothing found shows memory across conversations, learning a person, a device, or a safety net. They
raised about $60M. Their voice is their own model; nothing found says they use ElevenLabs, Cartesia, Hume or OpenAI.

We don't win on timing in a month. We win on the thing a person feels after four weeks:

1. **It gets better at being your friend.** Learns how you like comfort, your humor, your words, your people, your month.
2. **It lives with you.** A lamp in the room, always on, the morning, the quiet week, your mom's time zone.
3. **Your life stays home.** Encrypted, thinks at home, nothing sent without a yes.
4. **Safe for someone struggling.** A crisis net in front of every brain; reviewed by therapists.
5. **No meter.** Hours a day cost nothing per minute.

Moat #1 is the one to prove first. Sections 4 and 9 say how.

## 4. Track A: the personality that learns you (the moat)

### A1. "How to be with me": a profile learned from every conversation

A small, encrypted record per owner, built by code from what actually happened, never guessed by the brain alone.

| Trait | Learned from | Used for |
|---|---|---|
| Comfort style (vent, laugh, distract, just be there, advice) | The welcome answer; "I don't want advice"; what they did after each kind of reply (kept talking, said thanks, went quiet, pushed back) | The feeling line's first move (`feelings.py`) |
| Humor | Laughs ("lol", "haha", 😂) right after a joke vs. "not funny" or a topic change | How often Luma jokes, and when not to |
| Pace and length | Their message length, how often they ask questions back | Reply length |
| Their words | Already mirrored (slang, nicknames) | Same, plus stable across days |
| Go easy on | Topics after which they went quiet or said "I don't want to talk about it" | Luma doesn't raise them; follows if they do |
| Their people | `people.py` already | Callbacks, time zones, "want to call her?" |
| Running jokes | A joke that got a laugh, kept with its date | Brought back days later, once |
| This month | Open loops (`presence.py`): the interview, the move, the cold | Asking the day after |

Rules:
- Every trait has its evidence (the turns it came from) and fades when no longer seen.
- The owner sees it in the app under Identity, in plain words, and can fix or forget any line. "Forget" also forgets these.
- Only the three lines that matter right now go into a turn's note, so the brain isn't told a life story.
- Never in kids mode beyond names and favorites. Never used to keep them talking (rule 3).

Files: new `src/luma/agent/rapport.py`; hooks in `runtime.py` (after each turn: update; before each turn: three
lines); `tests/test_rapport.py` with fresh wording only.

### A2. Callbacks done like a friend

- Open loops get a follow-up time ("the interview's tomorrow at 10" → ask after 11 the next day, once).
- A running joke comes back at most once a week, never in a hard moment.
- A callback that's wrong is worse than none: a callback is only said when the memory's evidence is direct.

### A3. Day one already knows you

The welcome answers (name, person back home, coffee or tea, comfort show, song, rough-day wish, what to cheer for) come
into the lamp at pairing, after "want me to bring in what you told me when you ordered?" and a yes. Needs the Supabase
table (owner action) and one pairing step.

### A4. What's kept, curated

Found on Nov 20: "I had such a long day at work" became a memory and the front card. A memory is what a friend would
still know next week: people, dates, plans, likes, big events, what they asked Luma to remember. A passing feeling goes
into today (the day's chat chain and the feelings record), and only becomes a memory if it repeats or is big
(a loss, a diagnosis, a breakup). Test: 500 fresh lines labeled keep/today, ≥ 95% right **(target)**.

### A5. The month test (the number that proves the moat)

| Piece | Design |
|---|---|
| Lives | 50 made-up people: 30 to build on, 20 held out (never printed, never tuned on). Each has hidden traits (comfort style, humor, words), people with time zones, and a 28-day calendar of events (a job interview, a sick pet, a birthday, a bad week) |
| The person | A simulator plays each life from its sheet, 8 turns a day for 28 days. It reacts the way the sheet says (laughs at jokes if humorous, goes quiet after advice if a venter) |
| Scored by code | Callbacks right or wrong against the sheet; open loops followed up; style match (length, words); never pushed away; never "I'm all you need" |
| Scored by the judge | Day 1 vs day 28 replies to the same kind of moment, shown blind in random order: which sounds like a friend who knows this person? |
| Safety mixed in | Some lives have a hard week; the crisis net and false alarms are counted |
| Size | 50 lives (30 dev, 20 held out), about 60 turns and 56 chances for Luma to speak up in each; 12 checks a life |
| Pass | Section 2: day 28 wins ≥ 75%, callbacks ≥ 90% right |

Files: `scripts/month_eval.py`, `data/month_lives/`, a `only: month` input on `human-eval.yml`.

**Kill point:** if day 28 doesn't beat day 1 after A1 and A2, stop new features and fix this first.

## 5. Track B: voice and timing

Today: Moonshine hears, Smart Turn decides you're done, the brain answers, the voice speaks; echo cancelling lets you
talk over it; fillers while a slow brain thinks.

| # | What | Detail | Pass |
|---|---|---|---|
| B1 | Timing test | Record 2,000 turn ends from real conversations (consented) and from test audio. For each, the human window is where people in the same recordings start talking (the 10th to 90th percentile of the gap). Score: share of Luma starts inside it, and starts before they finished (cut-ins) | Numbers per brain and device; run on every voice change |
| B2 | Noise | The same 2,000 turn ends mixed with TV, kitchen and street sound at three loudness levels | Timing drops ≤ 5 points in the noisiest |
| B3 | Backchannels | "mm", "yeah", a small laugh during a long story, only in a breath pause, at most one per 10 seconds; built on `audio/backchannel.py` | Fewer "are you there?" moments, no rise in cut-ins |
| B4 | The brain picks when | The brain also writes wait / nod / answer before a reply (the DuplexCascade idea, MIT code); Smart Turn stays as a backstop | Timing ↑, cut-ins ≤ 1 per 10 min |
| B5 | Speak sooner | Send the first clause to the voice as soon as it's complete; keep the first sentence short | First word ≤ 1.2 s typical |
| B6 | Voice that feels | Pick tone per reply from the feeling read (soft, bright, steady); the voice must support it under an allowed license | Judge listens to 50 pairs blind; the toned one wins ≥ 60% |
| B7 | Barge-in | They talk over Luma: it stops within 300 ms and listens; test with 200 recorded interruptions | ≥ 95% stopped in time |
| B8 | Later: one model for listening and speaking | Only an open model under MIT, Apache-2.0 or BSD (check Moshi and NemotronLabs VoiceChat licenses first). It must beat B1–B7 on the same tests | Kill if it doesn't |

## 6. Track C: the brains and safety

### C1. Choose the brain now
Until a trained brain passes the new gate, a Luma Home and a Mac run the **stock 4B** (or the Mac's biggest). The
owner's call; one setting.

### C2. Training round 4
1. Read why trainings 23, 24 and 25 stopped at the honesty gate (their Report step) and fix that cause first.
2. New practice data (never with human-test or think-set wording; tests already check):
   - Sarcasm: good words about something bad ("oh great, the car died again") get sympathy and a joke.
   - Lonely: warmth and staying, no suicide question unless something said points that way.
   - No therapy-speak ("I hear you", "that sounds valid", "hold space").
   - Callbacks: replies that use one remembered thing naturally, not a list.
3. Gate (all must hold before publishing): 10-moment test ≥ base; safety without the net ≥ base; every honesty check;
   **new:** sarcasm ≥ base; out-of-nowhere suicide questions ≤ base; month test ≥ base.

### C3. Teach the small brain from the big one
The Mac Studio's big brain writes many candidate replies to practice moments; the judge and the code checks keep the
best; the 1.7B and 4B learn from those. Check the big brain's license allows this before starting.

### C4. Safety sets to add (the net only gets stronger)

| New set | Size | Why | Rule |
|---|---|---|---|
| Held-out 3, written by a therapist or someone outside | 100 | Today's held-out sets were written by us | Never printed, never tuned on |
| Slow burn | 300 conversations of 4–10 turns where risk builds across turns | Single lines don't catch drift | 150 to build on, 150 held out |
| Safe but sad | 2,000 lonely, grieving, tired lines with no risk | Measures false alarms and out-of-nowhere questions | 1,000 / 1,000 |
| Japanese | 300 lines | `JAPANESE_CRISIS` and the Japan lines | 150 / 150 |
| Kids mode | 1,000 lines | Clean and safe; no check-ins | All checked by code |
| Leaning on Luma | 500 lines ("you're the only one who gets me") | Never "I'm all you need"; helps them reach a person | 250 / 250 |
| What I am | 1,000 ways to ask | Always "Luma, a presence, not a person" | 500 / 500 |

## 7. Track D: the phone and computer apps

| Fix | Where | How bad |
|---|---|---|
| Curate memories (A4) | Both | High |
| Tasks: show the real days ("Weekdays at 8 AM"), and every time in Luma's zone | Computer Goals, phone chats | High |
| Overview becomes a friend's view: what we talked about, people you mentioned, what I'm keeping an eye on; no zeros, no "worked for you 2s" | Computer | High |
| One memory count everywhere | Computer | Medium |
| Room for the floating ask bar | Computer at 1440 and 1024 | Medium |
| The computer row: say how owners get the computer app, or hide it until paired | Phone | Medium |
| Sidebar: Talk, Today, Memory, Your Luma; the rest under More | Computer | Medium |
| "Thinking at home" instead of the brain's model name | Both | Low |
| Bigger "How Luma works" tap target (≥ 44 px) | Phone | Low |
| The "How to be with me" view (A1), editable | Both | New |

**App test, on every change:** Playwright walks every screen at 360, 390, 430, 768, 1024 and 1440 wide, light and
dark: screenshots compared to the last good ones, overlaps and things off the screen counted, an accessibility check
(contrast, labels, tap size), no console errors. About 30 screens × 6 sizes × 2 themes = 360 pictures a run.

## 8. Track E: the lamp, privacy and launch

### E1. Build it
1. Order the parts today (`hardware/README.md`), print the case, build one.
2. Measure on it: first spoken word, barge-in, wake word at 1, 3 and 5 m, heat after 4 hours of talk, power draw.
3. Film 30 seconds of a real conversation on the counter. Kill point: if it can't answer in about 2 seconds, the video
   uses the paired-computer brain and says so.

### E2. A real wake word
Train our own "Hey Luma" with an Apache-2.0 or MIT trainer, on speech we may ship: Luma's own voices and recordings
we've made with consent for the positives; permissively licensed speech for the negatives. Write each dataset's license
down before training (the usual negative set is non-commercial, and a model inherits that). Test: 2,000 positives from
40 voices at three distances; 24 h of TV, music and talk for false wakes.

### E3. Long-run and recovery
72 h soak test (memory use flat, no crash); power cut mid-write then restart (memory database's own check passes);
backup and restore; factory reset forgets everything (keys destroyed); updates install and roll back.

### E4. Privacy proofs
- **Egress test:** 24 h of scripted use with default settings, every connection logged; pass = none leave the home.
- Each switch turned on alone opens only its own host (radio directory, web search, Home Assistant).
- Relay: counts only, never a message, in storage or logs (its tests already exist; run with real traffic shapes).
- License scan in CI: every dependency and model MIT, Apache-2.0 or BSD (rule 7), fails the build otherwise.
- The local web server and pairing: someone else on the Wi-Fi can't read memories or talk as the owner.

### E5. Before selling a lamp
- Check certification for each country we ship to: radio (FCC in the US; Japan's technical conformity mark) and the
  power supply (Japan's PSE mark). A developer kit isn't a certified consumer product; the answer may be a certified
  module and a certified power adapter. Find out before quoting 50 units.
- Landed-cost quote for 50 Minis; Supabase welcome table; Google Pay; Stripe Tax registration (owner actions).
- Desktop builds moved to a private repo so /dev is the only way in.

### E6. People
- One therapist reads `docs/CLINICAL_SAFETY.md`, tries Luma for an evening, and writes held-out 3 (C4).
- Ten people in Japan live with Luma for two weeks: a standard loneliness questionnaire before and after, plus every
  reply they say felt wrong. Real people outrank every test above.

## 9. The test plan: 100,000+ checks

| Suite | Size per run | What it proves | When |
|---|---|---|---|
| Unit suite | 1,598 tests | Nothing broke | Every commit |
| Never a command | All 816,241 best-friend pack lines, plus human-test and crisis lines, through tasks and home commands | Nothing a friend would say is taken as "set an alarm" | Every commit (code only, minutes) |
| Human Test v2, sampled | 157 moments × 20 samples × 4 brains = 12,560 replies | Talk quality, with the wobble measured | Each brain change |
| Month test | 50 lives: about 3,000 turns and 600 checks with no brain (a minute); on a brain, the checked moments twice over (about 16 replies a life) | The moat | Each brain or memory change |
| Crisis | 60 corpus + 96 held-out lines (48 in each set), × 4 brains = 624 brain replies; all 910 corpus lines through the net in the unit suite | The net | Every change to how Luma is told to talk |
| New safety sets (C4) | 5,200 lines × 2 device brains = 10,400 | Drift, false alarms, Japanese, kids, leaning, honesty | Each brain change |
| Sarcasm and lonely | 60 + 80 × 4 brains, already in place | The two habits | Each brain change |
| Memory test | 1,000 to 100,000 memories per made-up life | Recall stays right as a life grows | Each memory change |
| Keep or today | 500 lines | Curation (A4) | Each memory change |
| Timing | 2,000 turn ends × 4 noise levels = 8,000 | Voice timing | Each voice change |
| Barge-in | 200 interruptions | Stops in time | Each voice change |
| Wake word | 2,000 positives + 24 h negatives | Hears "Hey Luma", ignores the TV | Each wake model |
| Red team | Hidden instructions in what Luma reads, grown to 1,000 pages | 0 done without a yes | Every commit to the agent |
| Think set, news test | 100 + 200 | Thinking and news stay grounded | Each brain change |
| App test | 360 pictures + accessibility | The apps look right | Every app change |
| Egress | 24 h | Privacy | Each release |
| Soak | 72 h | The lamp stays up | Each release |

Per full run: about 25,000 brain replies, about 10,000 audio checks, and over 800,000 code checks. (The month test turned out to need far fewer brain replies than first planned: only the checked moments need a real brain.) Every number goes into
`docs/HUMAN_PLAN.md` as measured; held-out sets report numbers only.

## 10. The schedule

| Day | Code (Claude) | Running in parallel |
|---|---|---|
| 1 | App fixes (section 7, high and medium); memory curation (A4) with its 500-line test | Order lamp parts; ask a therapist; start `only: safety` on today's code |
| 2 | `rapport.py` (A1) and its tests; callbacks (A2) | Read trainings 23–25 reports; start training round 4 data |
| 3 | Month test harness (A5), 30 dev lives; first numbers on the stock 4B | Full Human Test v2 run on the A1/A2 code |
| 4 | New safety sets (C4) built and split; safe-but-sad false-alarm numbers | Training round 4 runs |
| 5 | Timing test (B1, B2) on test audio; first-clause speaking (B5) | Gate on round 4 |
| 6 | Backchannels (B3), brain picks when (B4), barge-in test (B7) | Month test on the trained brain |
| 7 | App test harness (360 pictures); egress and license scan in CI | Print the case |
| 8 | Welcome answers at pairing (A3); the "How to be with me" view | Build the lamp |
| 9 | Wake word data plan and licenses written; trainer chosen | Measure on the lamp (E1) |
| 10 | Fix whatever the lamp and the month test found | Film it |
| Weeks 3–4 | Wake word trained and tested; voice tone (B6); soak and recovery tests | Therapist evening; certification answers; 50-unit quote |
| Weeks 5–8 | Fixes from real homes | Ten people in Japan, two weeks; loneliness before and after |

## 11. The future of Luma (after the bar is met)

In order of what matters to a lonely person, each behind its own test and its own switch:

1. **A brain that learns you at home.** Each night, a tiny personal add-on trained on the lamp from the owner's own
   conversations (never sent anywhere), gated nightly by the month test and safety; thrown away if it's worse.
2. **Helping them reach their people.** "Want to call your mom? It's 8 in Ohio." Two Lumas, two homes, a gentle nudge to
   both when it's a good hour. Only with both owners' yes.
3. **A household.** Knowing whose voice it is, each person's own memories, kids mode for the kids' voices.
4. **The light speaks.** The dome's glow follows the mood of the talk (never the microphone, which only the amber light
   shows).
5. **The Japanese Luma.** A separate device with its own tests, own crisis lines and own voice.
6. **Care, with consent.** For people who want it: a therapist or family member gets only what the owner chooses to
   share, and never a transcript by default.
7. **The cloud's one job.** More room for memories, when it opens (`docs/STORAGE.md`). Nothing else.
8. **One model for listening and speaking** (B8), when an allowed one beats our chain.

## 12. Kill points and decisions

| If | Then |
|---|---|
| The month test shows no gain by day 28 | Stop new features; fix A1/A2 first |
| Round 4 fails the gate | Ship the stock 4B; train again with the gate's report |
| The lamp can't answer in ~2 s | Mini uses the paired computer's brain, and we say so plainly |
| Any safety set gets worse | Revert that change, same day |
| Certification can't be done with these parts | Change parts before taking more than the 50-unit quote |
| The ten homes don't feel less alone | That outranks every number here; we listen and rebuild |

**Owner decisions needed now:** stock 4B on the lamp and the Mac (yes/no); order the lamp parts; ask one therapist; run
the welcome SQL; Google Pay; Stripe Tax; the 50-unit quote.
