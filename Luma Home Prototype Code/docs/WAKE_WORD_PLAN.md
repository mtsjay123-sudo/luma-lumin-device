# A real "Hey Luma": the data, the licenses and the trainer

Game plan E2. Written Nov 26, 2026. Nothing here has been trained or measured: this is the plan, what was read, and
the one decision that is the owner's.

## Where it stands

Luma has no wake model. Today it hears its name by putting whatever the voice detector lets through into
speech-to-text's quick pass and matching the words (`presence.WAKE`, `audio/stt.py`). That's fine for an app with the
microphone open. On a lamp that is on all day it means a speech model runs on every sound in the room, and the wake
numbers in the game plan (heard 95 times in 100 at 3 m; one false wake a day at most) have never been measured.

## What was read, and where

Rule 7 says to read the license itself. Each row says what the thing's own file or page says, where it was read on
Nov 26, and what that means for Luma. "Not reached" means the page couldn't be opened from the machine this was written
on (only GitHub could); nothing in this table is from memory.

| Thing | What its own file or page says | Read where | For Luma |
|---|---|---|---|
| openWakeWord, the code | Apache-2.0 | its `LICENSE` | Allowed |
| openWakeWord, the ready-made wake models | "All of the included pre-trained models are licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license due to the inclusion of datasets with unknown or restrictive licensing as part of the training data." | its `README.md` | Out |
| The speech-embedding model openWakeWord builds on (Google's) | openWakeWord's README says Apache-2.0 and links to the model's own page | The README only; the model's page not reached | Read its page before it's used |
| microWakeWord, the code | Apache-2.0 | its `LICENSE` | Allowed |
| microWakeWord's audio front end (TensorFlow Lite Micro) | Apache-2.0 | tflite-micro's `LICENSE` | Allowed |
| What both projects' training notebooks download: MIT impulse responses, a part of AudioSet, Free Music Archive, 2,000 hours of ACAV100M features, microWakeWord's ready-made negative features | microWakeWord's notebook: "The data downloaded here has a mixture of difference licenses and usage restrictions. As such, any custom models trained with this data should be considered as appropriate for **non-commercial** personal use only." | both notebooks, read whole | Out: every one of them |
| Piper (rhasspy/piper, archived) | MIT | its `LICENSE.md` | Not needed: Luma has its own voices |
| Piper's successor (OHF-Voice/piper1-gpl) | GPL-3.0 | the repository's page | Out |
| Piper's sample generator | MIT | its `LICENSE.md`; the voice it downloads (made from LibriTTS-R): page not reached | Not needed |
| Room impulse responses, OpenSLR 26 and 28 | Microsoft's DNS-Challenge README lists them as "License: Apache 2.0" | Microsoft's README; the OpenSLR pages not reached | Read the pages before they're used |
| Freesound noise, as chosen by Microsoft | "Only files with CC0 licenses were selected" | Microsoft's README | See the open question |
| AudioSet, DEMAND | Microsoft's README lists AudioSet as CC BY 4.0 and DEMAND as CC BY-SA 3.0 | Microsoft's README; their own pages not reached | DEMAND is share-alike by that listing: out. AudioSet: nothing until its own page is read (and see the open question) |
| Common Voice, LibriSpeech, MUSAN, FSD50K, People's Speech | | Not reached | Nothing is said about them until their pages are read |

Two rules for this table. A dataset is used only after its own page has been read and its row filled in. And a model
inherits the strictest term of anything it learned from: one non-commercial clip among the negatives makes the whole
wake model non-commercial, which is exactly what happened to the ready-made ones.

## The one open question (the owner's)

Rule 7 names MIT, Apache-2.0 and BSD. Those are licenses for code. Recorded sound mostly comes as CC0 (public domain:
no conditions) or CC BY 4.0 (any use, if you say whose it is), and neither is on the list. Plan A below needs neither.
Plan B adds real human speech and real noise under CC0 and CC BY 4.0, which would very likely make a better model.
**Does rule 7 allow CC0 and CC BY 4.0 for sound a model is trained on?** Non-commercial, share-alike and unknown stay
out either way. Until there's an answer, Plan A.

## Plan A: nothing borrowed

**The phrases.** "Hey Luma" and "yo Luma" (the owner's own, master prompt 9.2). Whether a bare "Luma" can be a wake
phrase is measured, not assumed: two syllables is little to tell from a television.

**Positives: the phrase, said.**
- Luma's own voices: the classic voice's set (Apache-2.0) and the new voice (MIT), at many speeds, pitches and
  loudnesses. The new voice can copy a speaker from a short clip: only clips from people who signed for exactly that.
- People, recorded with their written yes, on the lamp's own microphones: each says each phrase 25 times at 1, 3 and
  5 m. The people who train it and the people who test it are different people.
- Rooms: every clean phrase is also played through rooms. Ours: a sweep played from a speaker at twenty spots, recorded
  by the lamp, turned into impulse responses by code we write. Others': OpenSLR 26 and 28 once their pages are read.
- Mixed with noise we record ourselves (kitchen, fan, rain on a window, a street, a dishwasher), with Luma's own
  sleep sounds (made in code), and with Luma's own voice talking, so that it can be woken while it speaks.

**Negatives: everything else.**
- Look-alikes, said by the same voices and people: "hey Lumen", "illuminate", "aluminum", "a room", "volume up", "hey
  mama", "a llama", "hey Lou", "hello ma", "the looming". "Hey Luna" is reported, not trained against: it differs by
  one sound, and nobody should promise a model can tell them apart.
- Ordinary talk: Luma's own text (the 816,241 things people say in `friendtalk/packs/`, its practice sentences) through
  its own voices, in the same rooms and noise. As many hours as wanted, and all of it ours.
- What Plan A doesn't have is real television, real music and real strangers to learn from. That is its known weak
  spot, and it's why the wake is two stages.

## Two stages, so the small model doesn't have to be perfect

1. A tiny model listens all the time. It keeps two seconds of sound in memory, written over as it goes, and nothing
   else.
2. When it fires, those two seconds go through the speech-to-text quick pass Luma already has, and the words have to
   match `presence.WAKE`. Only then does Luma wake.

A false wake needs both to be wrong about the same two seconds. The cost is the quick pass's time on a real wake, which
is measured on the lamp (E1), not guessed here. Both stages run in the home. The microphone switch cuts the
microphones' power, and nothing here changes that.

## The trainer

**Chosen: microWakeWord's trainer (Apache-2.0), trained from nothing on Plan A's data.** Nothing is inherited: no
weights that learned from anyone else's sound, so the whole chain is ours plus Apache code. Its model is a streaming
one made for chips far smaller than the lamp's, so listening all day costs little.

**Written before any training, the rule for changing it:** if two rounds can't meet the bar on the bench set, train
openWakeWord's small head on Google's speech-embedding model instead (it learns from much less), after that model's own
license page has been read and its row above filled in. Neither project's ready-made model or notebook data is used in
either case.

What isn't known: whether Plan A's data is enough to stay asleep through 24 hours of real television. It may not be.
That's what the test, the second stage, the fallback and Plan B are for.

## The test

The bar is the game plan's: heard at least 95 times in 100 at 3 m, and at most one false wake in 24 hours.

| What | How much | How it's scored |
|---|---|---|
| The phrase, said by people | 2,000: 40 people the model never heard, 50 each, at 1, 3 and 5 m; in quiet, with the TV on, and while Luma is talking | Heard, by distance and by what else was on |
| A day of everything else | 24 hours of real television, music, talk radio and a household | False wakes |
| Look-alikes, said on purpose | 50 of each | Reported for each phrase, apart from the day's false wakes |

Playing a television in the room to test is not training on it: nothing of the test is learned from or shipped.
Recordings are written down as timelines (when the phrase was really said, when the model fired) and scored by
`python scripts/wake_eval.py score recordings/wake/*.json`, which gives no verdict on less than 24 hours and 300
phrases at 3 m. The test people's numbers are read once for each model, never tuned on.

## Order of work

| Step | Needs |
|---|---|
| 1. The owner's answer on CC0 and CC BY 4.0 | The owner |
| 2. Read OpenSLR 26 and 28's own pages (and Google's embedding page only if the fallback is used) | A machine that can reach them |
| 3. Make Plan A's synthetic data: phrases, look-alikes and talk through Luma's voices | GitHub's machines can run the voices; the script isn't written |
| 4. Record rooms, noise and people | The lamp's microphones (E1) and people's written yes |
| 5. Train; bench test; second stage wired into the voice loop | Steps 3 and 4 |
| 6. The 2,000 and the 24 hours | The lamp, 40 people |

Built today: this plan and the scorer (`scripts/wake_eval.py`, `tests/test_wake_eval.py`). Not built: the data
script, the trainer's run, the second stage in the voice loop. Not measured: anything.
