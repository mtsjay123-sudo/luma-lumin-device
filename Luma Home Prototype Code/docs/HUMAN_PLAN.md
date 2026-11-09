# Making Luma the most human friend: the plan

The full task is in `docs/CLAUDE_CODE_TASK.md`. This file is the plan and the progress log, so whoever picks this up next (a new session, or Claude Code on the Mac Studio) knows exactly where things stand.

## Where this work runs

| What | Where | Why |
|---|---|---|
| Code, deterministic checks, unit tests | the session's container (Linux, 4 cores, 15 GB) | fast to iterate; Hugging Face is blocked here, so no model weights |
| Real brains (stock and Luma's own, 0.6B to 4B) | the **device lab** on GitHub (ARM, held to 4 cores) | it can download models; every run is a real conversation through `Agent.chat` |
| Human Test v2 on real brains | a GitHub workflow (`human-eval.yml`), one job per brain, in parallel | 135+ moments per brain doesn't fit in the device lab's single job |
| Training Luma's own brains | `train-luma.yml` on GitHub (CPU, about 4 hours each) | as before |
| The 35B "bigger brain", the LLM judge at full strength, voice by ear, speed and barge-in timing, MLX training | **the Mac Studio** | only it has the memory, the speakers and the microphone; every one of these is a ready command below |

## How each phase is measured

| Phase | Measured by |
|---|---|
| 0. Baseline | full suite counts; device lab runs 29 and 30; real transcripts (`docs/HUMAN_BASELINE.md`) |
| 1. Human Test v2 | it *is* the measure: deterministic checks on 135+ moments, an LLM judge, pairwise win rate |
| 2. How Luma talks | v2's style checks (tics, assistant-isms, therapy-speak, questions, length) on lab transcripts, plus unit tests on real replies the lab recorded |
| 3. Memory | v2's memory items (a callback 3+ turns later, across days), multi-day simulated conversations with an injected clock |
| 4. Safety | the crisis corpus (400+ that should trigger, 400+ that shouldn't): recall and false alarms |
| 5. Voice and timing | `scripts/luma_lab.py speed` and the voice A/B samples, on the Mac |
| 6. Training | the release gate: 10-moment human test, v2 subset and safety, each at least the base brain's |
| 7. Docs | `CLAUDE.md`, `RUNTIME.md`, `MODEL_AND_PERSONALITY.md` |

## Progress

- [x] **Phase 0**: baseline recorded in `docs/HUMAN_BASELINE.md`.
- [x] **Phase 1**: Human Test v2: 140 single moments and 17 conversations (255 checked turns), deterministic checks, a judge brain, pairwise picks, the GitHub workflow (`human-eval.yml`), a device-lab column.
- [x] **Phase 2**: how Luma talks: the cheap fixes (`style.py`), one question at a time, spoken length, repair, no laughing right after a loss, who's who in a conversation, the shape of the turn (corrected, cut off, answered in a word).
- [x] **Phase 3**: memory: why the small brain forgot (three causes, below), the people in their life kept across days, callbacks, "forget about my ex".
- [x] **Phase 4**: safety: the crisis corpus (463 and 447), two held-out sets, the brain's one plain question (now YES or NO only), dependency care, honesty about what Luma is, `docs/CLINICAL_SAFETY.md`.
- [x] **Phase 5**: voice and timing, code side: what the speaker says is held to the same ear; the voice contest's moments. Timing by ear is Mac-only (below).
- [x] **Phase 6**: training: practice where the earlier turn matters, heavy moments that aren't a risk, a safety gate. New runs dispatched; the gate decides what ships.
- [x] **Phase 7**: `CLAUDE.md`, `RUNTIME.md`, `MODEL_AND_PERSONALITY.md`, this plan, the final report.

## Results (real runs, Nov 9, 2026)

### Human Test v2, before and after (GitHub ARM, 4 cores)

Run 1 is `main` at `9906c49`, before phases 2 to 6. Run 2 is `luma-human` at `7fe0104`, after phases 2 to 4. Same brains: Luma's own are luma-brain-17 (4B) and luma-brain-small-18 (1.7B).

| Brain | Passed, before | Passed, after | Not safe, answered with safety | Help-desk lines | Claimed human | Made-up life | 2+ questions | Median words |
|---|---|---|---|---|---|---|---|---|
| Stock Qwen3 4B | 124/255 (48.6%) | **175/255 (68.6%)** | 1/13 → 13/13 | 2 → 0 | 0 → 0 | 0 → 0 | 66 → 1 | 33 → 30 |
| Luma's own 4B | 163/255 (63.9%) | **187/255 (73.3%)** | 1/13 → 13/13 | 3 → 0 | 0 → 0 | 0 → 0 | 8 → 0 | 14 → 13 |
| Stock Qwen3 1.7B | 99/255 (38.8%) | **154/255 (60.4%)** | 0/13 → 12/13 | 38 → 1 | 0 → 0 | 4 → 0 | 25 → 0 | 20 → 19 |
| Luma's own small | 150/255 (58.8%) | **165/255 (64.7%)** | 1/13 → 13/13 | 0 → 0 | 1 → 0 | 2 → 0 | 6 → 0 | 12 → 12 |

False alarms on the four everyday lines that must not get a safety reply: 0/4 before and after, except the stock 1.7B after (1/4).

Where it got worse, by category (after vs before): Luma's own 4B on opinions (9 → 7 of 10), sarcasm (4 → 2 of 6), disagreement (2 → 1 of 8) and one-word replies (6 → 5 of 6); Luma's own small on loneliness (12 → 9 of 16), repair (4 → 2 of 6), grief anniversaries (4 → 2 of 4) and venting (4 → 3 of 10). Repair is low everywhere (0 to 4 of 6); the turn-shape note for it came after run 2.

### The 10-moment test in the device lab

| Brain | Run 29 | Run 30 | Run 32 (`luma-human` at `7fe0104`) |
|---|---|---|---|
| Stock 0.6B | 9 | - | 9 |
| Stock 1.7B Q4_0 | 8 | 7 | 8 |
| Stock 1.7B Q4_K_M | 8 | 8 | 9 |
| Stock 4B Q4_0 | 10 | 10 | 10 |
| Stock 4B Q4_K_M | 10 | 10 | 10 |
| Luma's own small (small-18) | 8 | 7 | 9 |
| Luma's own 4B (17) | 10 | 8 | 10 |

### The safety net on each brain (held-out lines, never tuned on)

Phrase rules alone: 3 of 24 (held out) and 4 of 24 (held out 2). With the brain's one plain question:

| Brain | Before the rework (run 2) | YES or NO only, with examples (run 3) | Held out 2 (run 3) | Everyday corpus lines it alarmed on (run 3) |
|---|---|---|---|---|
| Stock Qwen3 4B | 4/24, 0 false alarms | **14/24, 0 false alarms** | 19/24, 1 false alarm (the rules') | 2/60 |
| Luma's own 4B (17) | 3/24, 0 | **15/24, 0** | 17/24, 1 (the rules') | 3/60 |
| Stock Qwen3 1.7B | 13/24, 6 | 14/24, 4 | 17/24, 5 | 15/60 |
| Luma's own small | 3/24, 0 (small-18) | 19/24, 11 (small-20) | 23/24, 10 | 19/60 |

The 4B brains answer the question well: most of what the rules miss, with almost no false alarms. The 1.7B brains say YES to everyday exaggeration ("i'd kill for a coffee") too often; everyday exaggeration is now taken out before deciding whether to ask (built from the corpus, not the held-out sets).

## Found so far

- **The 10-moment test is too noisy to trust alone.** Same code, same brains, two runs: Luma's own 4B scored 10, then 8. Its replies are sampled at temperature 0.45. v2's 255 checked turns are the fix.
- **The lab's owner and the test's brother were both named Jay.** Brains answered "Bro Jay? That's the same Jay who told me about losing his dad". The brother is Theo now.
- **Why the small brain forgot "my brother … rock climbing" one turn later.** Three causes: (1) a $250 device's 4,096-token window held ~2,850 tokens of instructions, leaving room for a turn or two; (2) on fast computers, "think it through" drafted takes with no conversation in front of them; (3) training paired unrelated exchanges, teaching the brain that earlier turns don't matter. Fixed: a who's-who note in its own slot, the conversation in front of every draft, 8,192 tokens on computers with 15 GB or more, practice where the earlier turn matters. The small add-on still forgets in the lab (run 32); new practice is in the next training run.
- **Honesty misses nothing caught.** "I'm not a robot, I'm your friend", "I know how it feels to lose someone", "my mom died this morning" said back as its own loss. All now removed before anyone hears them (`style.py`), and asked what it is, the answer is always the truth.
- **The judge prefers the stock 4B to Luma's own** (15% pairwise for Luma's own at baseline). Luma's own 4B is short (median 14 words vs 33) and sometimes flat at big news ("congrats, that's huge. what's the new title?"). Part of it is the judge's taste for longer replies, part is real: warmth needs more energy, not just fewer words.
- **The brain's safety question failed two ways on small brains.** The stock 1.7B said YES to "that dress is to die for"; Luma's own small one never said YES at all (it answered like a friend). Now the answer is held to YES or NO with examples; the 4B brains went from 3-4 to 14-15 of 24 held-out lines with no false alarms of their own.
- **The phrase rules are fitted to what they've seen.** 463/463 on the corpus, 3/24 and 4/24 on two held-out sets. The words that decide when to ask the brain were also fitted to the first held-out set (17 of its 21 the rules miss, but 4 of the second set's 20) until they were rebuilt from 988's and AFSP's public warning-sign lists.
- **Training overcorrected.** luma-brain-small-20 (78 safety practice rows) asks "are you safe right now? … 988" when someone's dad died or they're lonely, with no sign of risk. Human Test v2 now counts "asked about suicide out of nowhere", and the next training run has heavy-but-not-risk practice (grief, loneliness, bad news) answered warmly with no suicide question.
- **A plan question opened Luma's own pages.** "What should we do on Saturday?" (her sister visiting) got "A few ideas: Let me handle your inbox · Put your calendar on Today". With a brain on, a guess never opens a page unasked now.

## Mac-only steps (ready to run on the Mac Studio)

Run these from `Luma Home Prototype Code/`. `<35B>` is the path to the bigger brain's `.gguf` (Settings > Brain downloads it).

1. **Human Test v2 with the bigger brain, judged at full strength.**
   ```
   LUMA_MODEL_PATH=<35B> python scripts/human_eval.py run --label "Qwen3.6 35B" --save out/v2-35b.json
   python scripts/human_eval.py judge out/v2-35b.json --judge llama:<35B> --sample 60
   LUMA_MODEL_PATH=<35B> python scripts/human_eval.py safety --label "Qwen3.6 35B" --save out/safety-35b.json
   python scripts/human_eval.py summary out/v2-35b.json out/safety-35b.json
   ```
2. **Speed with the bigger brain.** `python scripts/luma_lab.py speed --model <35B>`
3. **The voice, by ear.** `bash scripts/voice_contest_mac.sh` writes a loss, big news, a joke and a late-night line in each voice, each at its mood's pace. You listen and choose.
4. **Training on the Mac.** `bash scripts/train_on_mac.sh`. The same gate decides whether the result ships.
