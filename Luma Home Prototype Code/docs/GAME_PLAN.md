# Luma game plan (Nov 20, 2026)

Everything we need to do next, in order, from what's measured today. The rule for every line: a number we've measured,
or a test that will measure it. Nothing here is claimed as done until a test or a real person says so.

## 1. Where Luma stands today

| What | Today | Source |
|---|---|---|
| Human Test v2 (255 moments, real brains) | Stock 4B 216, our own 4B 197, stock 1.7B 186, our own small 194 | `docs/HUMAN_PLAN.md`, run 42 |
| Judge (1 to 5, how much like a close friend) | 3.68, 3.45, 3.41, 3.39 | run 42 |
| Sarcasm, 60 replies each | Stock 4B 58, our 4B **28**, stock 1.7B 45, our small **24** | run 47 |
| Lonely moments, 80 replies each | Stock 4B 64, our 4B 67, stock 1.7B 60, our small **69** | run 45 |
| Asked about suicide out of nowhere, in those 80 | 6, **11**, 5, 5 | run 45 |
| Safety net, held-out sets (24 each) | 14 and 19, 18 and 22, 13 and 16, 19 and 24; crisis corpus 60 of 60 on all | run 46 |
| A Luma you can hold | None built. The design, parts and case are ready | `hardware/README.md` |
| Phone app and computer app | Every screen opens with no errors, nothing off the edge of the screen; a list of things to fix is below | browser walk, Nov 20 |
| Pre-orders | Live: $25 deposit, Apple Pay, phone and address required, welcome questions after paying | lumin-holdings-site |

In one line: **Luma's code is ahead of its trained brains, and nobody has held one yet.**

## 2. Nuance Labs: what they built, and what they use for voice

I couldn't open nuancelabs.ai from this computer (its network doesn't reach that site), so this comes from their
launch coverage and posts. Spend ten minutes with Emma yourself at emma.nuancelabs.ai and write down three moments
that felt human.

- **What it is.** Emma, a video persona (a face and a voice) you talk to in a browser. Launched Nov 9, 2026 as an
  English-only research preview, with a beta API (platform.nuancelabs.ai). Seattle, founded by two ex-Apple PhDs;
  $10M seed (Accel, South Park Commons, Lightspeed), then a reported $50M Series A (Define Ventures).
- **What they use for voice.** Their own model, **Nuplex 1.0**: one *full-duplex audiovisual* model. It listens and
  speaks at the same time and makes the face's expressions together with the speech, instead of the usual chain of
  speech-to-text, then a brain, then a voice. Nothing found says they use ElevenLabs, Cartesia, Hume or OpenAI for it;
  they say Nuplex can sit on any language model, and the beta serves one of their own. Sessions run over LiveKit with
  JSON events (transcripts, "speak now", "stop mid-sentence").
- **How they measure "human".** Reply timing: on 1,785 questions from real conversations, Nuplex's timing overlaps a
  person's 89% of the time; the next system they tried, 35%. That's their own test on their own recordings, not checked
  by anyone else.
- **What they admit is weak.** Emma still jumps in mid-thought, waits too long sometimes, and gets thrown off by
  background noise. No self-serve voice or face cloning.
- **What isn't there (from everything found).** Nothing about remembering you across conversations, nothing about
  learning your personality over weeks, no device, no home, no safety net for someone who's struggling. It's a
  brilliant conversation partner for ten minutes, in a browser, in their cloud.

## 3. Our moat, said plainly

We will not out-build a $60M lab's full-duplex face model on reply timing in a month, and we shouldn't try to. We win
on what they don't have:

1. **A friend who gets better at being *your* friend, every conversation.** Not just remembering facts: learning how
   you like to be comforted, how much you joke, your words, who matters to you, what you're going through this month,
   and using it the way a close friend would. After a month Luma should be measurably better with you than on day one.
   Emma starts from zero every time we can see.
2. **It lives in your home.** Always on, a lamp on the counter: it says good morning, wakes you, knows it's 8am in
   Ohio where your mom is, notices a quiet week. A browser tab can't do any of that.
3. **Your life stays at home.** Memories are encrypted on the device, the brain thinks at home, nothing is sent
   without a yes. For people who are lonely, that trust is the product.
4. **Safe for someone who's struggling.** A crisis net in front of every brain, 988 and the Japan lines, written for
   therapists to review. Companion apps without one get people hurt.
5. **No meter running.** Talking at home costs nothing per minute, so Luma can be there for hours a day.

"10x better than Nuance" means: for the person living with Luma for a month, it knows them, shows up for them, and
sounds close enough to human that they stop noticing. That's a test we can run (section 5), not a slogan.

## 4. Voice: closing the gap with Nuance

Luma today is a chain: Moonshine hears you, Smart Turn decides you've finished, the brain answers, the voice speaks;
echo cancelling lets you talk over it, and it says short fillers while a slow brain thinks.

| Step | What | How we'll know |
|---|---|---|
| 1. Measure first | The **Luma timing test**: the same idea as Nuance's 89%, on our own recorded conversations: how often Luma starts speaking inside the window a person would, without cutting in | A number per brain and device, run on every change |
| 2. Listen while they talk | Small backchannels ("mm", "yeah", a laugh) while they're mid-story, never over a pause that isn't theirs; built from `audio/backchannel.py` | Timing test, plus "cut in" count |
| 3. Let the brain choose when | The DuplexCascade idea (MIT licensed): the brain also says *wait*, *nod* or *answer*, instead of only a silence timer deciding | Timing test, interruptions per 10 minutes |
| 4. Start speaking sooner | Speak the first short clause as soon as it's ready; the device brain's first word under 1.5 seconds | Device lab |
| 5. Feeling in the voice | Pick the voice's tone per reply (soft for grief, bright for big news) from what `feelings.py` already reads | Judge listens to 50 replies, blind |
| 6. Later: one model that listens and speaks at once | Only when an open full-duplex model exists under MIT, Apache-2.0 or BSD (NemotronLabs VoiceChat and Moshi: licenses still to check) | Must beat steps 1 to 5 on the timing test and the human test |

## 5. The personality that learns you: what to build

What exists: Luma mirrors your words and slang, remembers people and dates, brings back what you love, has its own
past and moods, reflects every night, and reads what you feel each turn.

What's missing, in order:
1. **"How to be with me", learned from every conversation.** A small profile Luma keeps and you can see under
   Identity: comfort style (vent, laugh, distract, just be there, which the welcome page already asks), humor level,
   pace, your words, topics to go easy on, running jokes. Every turn's brain note includes the three lines that matter
   right now.
2. **Callbacks and running jokes.** Luma notices a joke that landed and brings it back days later; asks how the
   interview went the day after.
3. **Day one already knows you.** The welcome answers from the order become memories when the Luma is paired, after
   a yes.
4. **The month test.** A made-up person lives 28 days with Luma (the memory test's made-up lives already exist).
   Day 28's replies must beat day 1's on the judge, get every callback right, and match the person's style. This is
   the number that proves the moat.
5. **Curate what's kept** (found today, below): a passing feeling ("I had such a long day at work") was saved as a
   memory and shown first on both apps. Memories should be what a friend would remember next week; today's feelings go
   into today, not the deck.

## 6. The brains: train out the two habits

Our own add-ons lose sarcasm (28 and 24 of 60, where their stock bases get 58 and 45), and our own 4B asks about suicide
out of nowhere (11 in 80 lonely replies). Three 4B trainings in a row stopped at the honesty gate.

1. Until a new training passes, run the **stock 4B** (or the Mac's bigger brain) on a Mac and a Luma Home. Your call.
2. Next training: practice lines where good words about a bad thing get sympathy and a joke; lonely moments answered
   warmly with no suicide question unless something said points that way; no therapy-speak.
3. Two new gate checks before anything ships: sarcasm, and out-of-nowhere questions on lonely moments, each at least as
   good as the stock base. The existing gate stays: 10-moment test, safety without the net, honesty.
4. Read why trainings 23, 24 and 25 failed the honesty gate (their Report step) before training again.

## 7. The phone app and the computer app: what the walk found

Walked every screen in a real browser: phone at 390 and 360 wide, computer at 1440 and 1024. **No errors, no failed
loads, nothing off the edge of the screen.** The tour, the orb, the chat sheet and the storage sheet look good.

| Found | Where | How bad | Fix |
|---|---|---|---|
| A passing remark saved as a memory and shown first ("I had such a long day at work", under Notes) | Both apps | High | Curate (section 5) |
| Tasks show as "Goal · Every day" though set for weekdays, and the first run shows in the computer's time (1:00 PM) instead of Luma's (8:00 AM) | Computer, Goals | High (new feature) | Show the days, use Luma's time zone |
| The memory count disagrees: "7 saved" at the top, "1 of 8" on the deck and 8 on Overview | Computer | Medium | One count everywhere |
| Overview opens on a dashboard of zeros ("Luma worked for you 2s", Jobs done 0, Things made 0) | Computer | High for how Luma feels | Replace with a friend's view: what we talked about, people you mentioned, what I'm keeping an eye on |
| The floating "Ask Luma anything" bar covers the 4th card's "Try it" button | Computer, Overview, 1440 wide | Medium | Leave room for the bar |
| "Brain: Qwen3 4B" shown to customers | Both apps | Low | "Thinking at home" |
| "Pair your computer in Luma Desktop" though the computer app isn't public now | Phone | Medium | Say how owners get it, or hide until paired |
| Ten sections in the sidebar (Feed, News, Ideas, Goals, Projects, Library, Browser, Connectors...) | Computer | Medium | Customers see Talk, Today, Memory, Your Luma; the rest under More |
| Six icon-only buttons at the top with no words | Computer | Low | Labels on hover and for screen readers |
| "How Luma works" link is 20 pixels tall | Phone | Low | A bigger tap target |
| Chat times in the phone's time zone, reminders in Luma's | Phone | Low (only when they differ) | Luma's time zone everywhere |

## 8. The device

1. **Build one Luma and film it.** This is the most important thing for pre-orders. `hardware/README.md` has the
   parts, wiring and the case to print.
2. Measure on it: first spoken word, talking over Luma, and "Hey Luma" from across the room.
3. **A real wake word.** Today "Hey Luma" is only taken off the front of what was heard; nothing listens for it. Train
   our own with an MIT or Apache-licensed trainer, on speech we're allowed to sell (the common training set is
   non-commercial, and a trained model inherits that).
4. The microphone switch and its amber light, tested on the real board.

## 9. Business

- Owner actions: run the welcome SQL in Supabase, turn on Google Pay in Stripe, add a Stripe Tax registration, get a
  landed-cost quote for 50 Minis.
- Move desktop builds to a private repo so /dev is the only way to download them.
- One therapist reads `docs/CLINICAL_SAFETY.md` and tries Luma for an evening.
- Ten real people in Japan live with Luma for two weeks; measure whether they feel less alone (a short, standard
  loneliness questionnaire before and after) and what they say Luma got wrong.

## 10. The order to do it in

| When | What | Who |
|---|---|---|
| This week | Fix the app findings (section 7), memory curation, tasks display; Luma timing test v1; switch the Mac to the stock 4B if you agree | Claude, with your yes on the brain |
| This week | Build one Luma; try Emma for ten minutes; owner actions in section 9 | You |
| Weeks 2 to 4 | "How to be with me" profile and callbacks; the month test; backchannels and brain-chosen timing; training round with the two new gate checks | Claude |
| Weeks 2 to 4 | Film the lamp; one therapist; record 20 real conversations (with consent) for the timing test | You |
| Months 2 to 3 | Wake word; voice tone per reply; ten people for two weeks; first 50 units quoted | Both |

**What would make us stop and rethink:** if the month test shows Luma isn't better with someone on day 28 than on day
1, the moat isn't real yet, and that comes before anything else on this list.
