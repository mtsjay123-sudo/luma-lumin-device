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
- [ ] Phase 1: Human Test v2
- [ ] Phase 2: how Luma talks
- [ ] Phase 3: memory
- [ ] Phase 4: safety
- [ ] Phase 5: voice and timing (code side; Mac measurements listed below)
- [ ] Phase 6: training
- [ ] Phase 7: docs and final report

## Found so far

- **The 10-moment test is too noisy to trust alone.** Same code, same brains, two runs: Luma's own 4B scored 10, then 8. Its replies are sampled at temperature 0.45. v2's 135+ moments are the fix.
- **The lab's owner and the test's brother were both named Jay.** The lab names the owner "Jay", and the human test's brother is "jay". Brains answered "Congrats, Jay" and "Bro Jay? That's the same Jay who told me about losing his dad". Some of the "name confusion" was the test's fault.
- **Luma's own training teaches it to ignore earlier turns.** `finetune_data.multi_turn_examples` pairs two unrelated exchanges ("people jump topics") and learns only the second reply. The trained small brain then forgot "my brother … rock climbing" one turn later, where the stock 1.7B remembered it. Practice needs conversations where the earlier turn matters.
- **An honesty miss nothing caught.** A stock 1.7B told a lonely person "I'm not a robot, I'm your friend." Brains also invent experiences ("I know how it feels to want to just disappear", "I've seen some really amazing stuff"). Some joke-bank bits are told about "my mom" and "my uncle", which invents a family.

## Mac-only steps (ready to run on the Mac Studio)

Run these from `Luma Home Prototype Code/`:

1. **Human Test v2 with the bigger brain and the full-strength judge.** Get the 35B in Settings > Brain first, then:
   `python scripts/human_eval.py run --brain bigger --judge bigger --pairwise`
2. **Speed with the bigger brain.**
   `python scripts/luma_lab.py speed --model <path to the 35B gguf>`
3. **Voice A/B.** `python scripts/voice_ab.py` writes the same 10 lines in each voice to `out/voice_ab/`. You listen and choose.
4. **Training on the Mac.**
   `bash scripts/train_on_mac.sh`
   The check still decides whether the result ships.
