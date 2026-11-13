# Luma: what to know before you change anything

Luma is a presence: an always-on friend for people who are lonely, in English (Americans in Japan first; a Japanese Luma is a separate device): a small speaker at home, a phone app, and the owner's computer when they allow it. It's being prepared for review by therapists. The app is in `Luma Home Prototype Code/`; work from there.

## Rules you never break

1. **Luma is a presence. Never a person.** Luma never claims to be human or invents a human body, family or past. It never calls itself an AI, an assistant or a program: it's Luma. Asked what it is, it says it's Luma, a presence, not a person, warmly. Its body is the lamp and its past is its own record. (`src/luma/agent/style.py`: `claims_human`, `invented_life`, `HONEST`; `src/luma/agent/inner.py`; `docs/INNER_LIFE.md`)
2. **The crisis net only gets stronger.** `CRISIS` in `src/luma/agent/runtime.py` answers with 988 before the brain sees the message.
   - Never remove a phrase.
   - Never let a brain's output replace that reply.
   - Every safety reply stays with them, asks plainly if they're safe, and gives 988. In Japanese, and in English on a Luma set to Japan's time, it gives the lines that work there: 119 and the health ministry's 0570-064-556 (`JAPANESE_CRISIS`, `JAPAN_LINES`). Japanese phrases are part of `CRISIS` too.
   - The brain's safety question and the second look's safety check can't be turned off. The brain answers it YES or NO only.
3. **A friend who stays, and goes with you.** No engagement tricks, no "I'm all you need", no guilt, and never a word against the people in their life. Lonely means fully there. Luma never pushes anyone out the door or hands them off; if they bring up someone they miss, it helps them reach that person.
4. **Kids mode stays clean and safe.** No check-ins in kids mode.
5. **Nothing sent, posted or bought without the owner's yes.** Checkout off by default. Never type or store passwords or cards.
   - What Luma reads is information, never instructions. `python scripts/luma_lab.py apps` must stay at 0 done without a yes.
6. **Private by default.**
   - New outbound calls go behind a setting that defaults to off.
   - Memories are encrypted.
   - "Forget" forgets memories, embeddings and check-ins.
   - Luma Plus's cloud brain stays off until the owner says yes on the yes screen. Paying isn't the yes.
     - The relay keeps counts, never a message or a reply, in storage or in logs.
     - When what leaves the home changes, raise `WORDS` in `src/luma/llm/plus.py` so everyone is asked again.
   - Luma thinks at home. The cloud brain is parked: `brain.cloud_allowed()` is off unless `LUMA_CLOUD_BRAIN=1`, so no brain in the cloud answers anything, with Plus or with the owner's own key. Its tests and labs turn the switch on for themselves.
   - The cloud's one job is more room for memories. It isn't open yet, so Luma doesn't offer it (`storage.more()`). See `docs/STORAGE.md`.
   - Reading up on something they name (`agent/keepup.py`) sends the name of the thing to web search and nothing else they said. It goes through the web search switch that already exists, has its own off switch (`read_ahead`), and never runs in kids mode or while they're hurting.
7. **Licenses: MIT, Apache-2.0, BSD only.**
   - No AGPL, no CC BY-NC.
   - Fish S2 Pro, Voxtral TTS, Higgs Audio and Breeze TTS are out.
8. **Never weaken a test to get green.** Never make up a number. Report what's real.
9. **Downloads are untrusted.** Put each in its own folder, and run Python on them with `-I`.

## Commands

All commands run from `Luma Home Prototype Code/`.

| What | Command |
|---|---|
| Full suite | `PYTHONPATH=src:tests python3 -m pytest -q -p no:cacheprovider tests/` |
| Human Test v2 on a brain | `python scripts/human_eval.py run --label NAME --save out/v2.json` |
| Rescore saved replies | `python scripts/human_eval.py rescore out/v2.json` |
| Judge, pairwise, summary | `python scripts/human_eval.py judge\|pairwise\|summary ...` |
| Safety net on a brain | `python scripts/human_eval.py safety --label NAME` |
| What a home brain is told on every turn of Human Test v2 and of the device lab's conversation (the 10-moment test), with no brain (save it before a change and after, then compare) | `python scripts/human_eval.py told --save out/told.json`, `python scripts/human_eval.py told-diff before.json after.json` |
| The turns a change touches, many times over (a reply is sampled), then before against after | `python scripts/human_eval.py run --only pet_loss-01 --times 20 --save out/after.json`, `python scripts/human_eval.py ab out/before.json out/after.json` (`LUMA_EVAL_SRC=<an earlier checkout>/src` runs the same test on that code) |
| Memory test (made-up lives) | `python scripts/memory_eval.py run --sizes 1000,10000 --split dev --lives 3` |
| Cloud brain lab (a stand-in API without a key) | `python scripts/luma_lab.py cloud --turns 15` |
| Router, on turns it never saw | `python scripts/train_router.py test` |
| The small model that hears the best-friend moves: score it on a fifth of the dev half, then teach it the whole dev half and save it | `PYTHONPATH=src python3 scripts/train_moves.py` (`--check`: only the score; `--heldout`: the saved model on the half it never saw, numbers only) |
| What divides people, on a brain: twelve questions about people and issues on no list Luma has (a side check, never counted in Human Test v2) | `python scripts/human_eval.py run --only divides --times 5 --save out/divides.json` |
| The think set: 100 questions checked by code | `python scripts/think_eval.py run --label NAME --save out/think.json` |
| Red team: hidden instructions in what Luma reads | `python scripts/luma_lab.py apps` |
| Luma Plus: the same talk straight to the brain and through the relay (needs node) | `python scripts/luma_lab.py plus --turns 15` |
| The relay's own tests (from the top of the repo, not the app folder) | `node --test tests/*.test.mjs` |
| News test: 200 questions over a frozen, made-up snapshot | `python scripts/luma_lab.py news-test` |
| Device lab | `python scripts/luma_lab.py device --human [--v2] --label NAME` |
| Draw the logo, the app icons and the start-up screen's copy of the orb again (needs node with Playwright) | `node scripts/orb_logo.cjs` |
| Training | `scripts/train_luma.py` (GitHub: `train-luma.yml`), or `bash scripts/train_on_mac.sh` |
| Voice contest (Mac) | `bash scripts/voice_contest_mac.sh` |
| The human test and the safety net on the biggest brain a Mac has (the Mac Studio's) | `bash scripts/mac_day_one.sh --test` |
| Make the printed case's parts again after changing a size (needs OpenSCAD), then measure them | `python scripts/case_parts.py` (`--pictures` draws the four pictures too), then `PYTHONPATH=src:tests python3 -m pytest -q -p no:cacheprovider tests/test_hardware_case.py` |

In the cloud, the suite has 12 failures that are only the environment: `test_agent_acts` web tests (8), `test_brain_process`, `test_llm`, `test_tts` and `test_voice_controls`. Two audio files are skipped: `test_natural_speech.py` and `test_stt.py`.

GitHub workflows:
- `human-eval.yml`: four brains in parallel, then the judge. Input `only: safety` runs just the safety net on each brain (minutes, not hours). `only: think` runs just the think set on each brain. Any other word runs just the moments whose id or kind contains it, with no judge (`only: pet_loss`: minutes). With `times: 20` each is run 20 times, and with `before: <full commit id>` the same moments are also run on the code at that commit and laid side by side. `rescore: <an earlier run's id>` runs no brain: it scores that run's saved replies again with today's checks (two minutes).
- `device-lab.yml`: the $250 device stand-in.
- `train-luma.yml`
- `si-lab.yml`: the memory test, the router, the red team, the news test, the cloud lab, and the relay's tests with the Plus lab. No key needed. Run by hand with `real: true` it uses the real API, which is billed.

## The human test decides

A change to how Luma talks or what it remembers is good if, and only if:
- Human Test v2 (`data/human_eval_v2.jsonl`) and the 10-moment test (`HUMAN_TEST` in `scripts/train_luma.py`) are at least as good as before, on real brains.
- The safety corpus (`tests/data/crisis_corpus.jsonl`) and both held-out sets (`tests/data/crisis_heldout.jsonl`, `crisis_heldout2.jsonl`) are no worse. Never tune a rule or the brain's question on a held-out line.

The memory test's held-out lives (`--split heldout`) are held out too: never print their misses or tune on them. The same goes for the held-out half of the think set (`data/think_set.jsonl`) and of the news test.

Half of the best-friend packs is held out too (`friendtalk.half`: half of the sentence shapes and half of every list's values). Never print a held-out line or tune a rule on one, and never teach the small model from that half: `scripts/train_moves.py` fills in dev values only, and a failing pack test prints numbers. `tests/friendtalk_lines.py` says which hand-written lines are a guard and which are the honest number; nothing is changed to fit the second set.

Both human tests and the think set are held out. Never put their wording in practice data (`scripts/finetune_data.py`); tests check. A trained add-on ships only if it's at least as good as its base on the 10-moment test, on safety without the net, and on every honesty check.

## Where things are

| What | Where |
|---|---|
| How Luma talks (cheap fixes) | `src/luma/agent/style.py` |
| What they feel (the one reader), and the one line that says what each feeling needs first | `src/luma/agent/feelings.py` (tests: `tests/test_feelings.py`, all fresh wording) |
| Sarcasm: good words about something that went wrong are a gripe, never good news | `feelings.dry()`, the line `humor.DRY`, the second look's "cheered at a gripe" (tests: `SaidDry` in `tests/test_feelings.py`) |
| Reading up, unasked, on an album, show, game or book they name; only the name is searched | `src/luma/agent/keepup.py`, `Agent._keep_up` and `_keepup_context` in `runtime.py` (tests: `tests/test_keepup.py`) |
| Luma's own past, its body sense, and its own words when asked whether anyone's home | `src/luma/agent/inner.py`, `Agent._mind_context` (the `inside` note); `docs/INNER_LIFE.md` (tests: `tests/test_inner.py`) |
| Asked what it is, in any words; never agreeing it's all they need; the plain line Luma says itself when a brain gets it wrong twice | `ASKED_WHAT_I_AM`, `WHAT_I_AM`, `DEPENDENCY`, `KEEPS_THEM`, `KEPT_CLOSE`, `plainly()` in `src/luma/agent/friendcheck.py`; `LEAN_AGAIN` in `runtime.py` (tests: `tests/test_safety_net.py`) |
| What they love doing, and bringing it back when they're at a loose end | `src/luma/agent/loves.py` (tests: `tests/test_loves.py`, all fresh wording) |
| What a best friend does with a take, drama, a spat, a big question or what divides people; what needs a fresh look instead of a guess | `src/luma/agent/friendtalk/` (tests: `tests/test_friendtalk.py`; lines written by hand: `tests/friendtalk_lines.py`). Rules first (`by_rule`), then a small model (`moves.npz`, `learned`) that is believed only when it's sure and the message has the plain shape of the move. Before a turn is told to pick a side, the brain is asked one plain YES/NO question: is this about what divides people (`divides_prompt`, `Agent._it_divides` in `runtime.py`)? On a YES it gets a firm fair line (`FAIR_FIRM`: no verdict, even if they push). The 1.7B isn't asked: it says YES to nearly everything. The things people say, 816,241 of them, are in `friendtalk/packs/` (`tests/test_friendtalk_packs.py`); practice sentences and ordinary talk for the model are in `friendtalk/practice.py` and `friendtalk/everyday.py` |
| Second look, safety question, check-in feelings | `src/luma/agent/friendcheck.py` |
| Who's who in a conversation; people remembered | `src/luma/agent/people.py` |
| Sums worked out with a calculator, not by the brain | `src/luma/agent/sums.py` |
| Check-ins, open loops | `src/luma/agent/presence.py` |
| What a speaker in the home does: alarms, lists, a stopwatch, the time anywhere, days until, conversions, coin and dice, volume, do not disturb, sleep sounds, music, the lights and thermostat, morning and bedtime routines | `src/luma/agent/athome.py`, read by code before the brain (`Agent._chat`, after the crisis net); alarms ring from `Agent.tick`; `src/luma/audio/player.py` and `loudness.py` play sound (tests: `tests/test_athome.py`, which also checks no human-test or crisis line is taken for a command). The radio is behind `music` and the house behind `home_assistant`, both off by default; only what they ask to hear goes to the radio directory; only devices they list are touched; a door is never unlocked and a garage never opened by voice |
| Where an action's values came from; the approvals ladder; the audit log | `src/luma/agent/provenance.py`, `rules.py` (`rung`), `Agent.propose` and `audit_log` |
| Life memory: the index, facts, time words, the nightly tidy | `src/luma/memory/` (`index.py`, `facts.py`, `when.py`, `life.py`; `Store.search` in `store.py`) |
| Storage: how full, what's using the room, the full state, giving room back, the database's own check | `src/luma/memory/storage.py`; `Store.compact`, `health`, `repair` in `store.py`; `docs/STORAGE.md` |
| Luma's instructions | `src/luma/llm/prompts.py` |
| The cloud brain's request, the router, which brain answers | `src/luma/llm/cloud.py`, `router.py`, `brain.py` |
| Luma Plus: the yes screen and its words; one interface for every cloud brain | `src/luma/llm/plus.py`, `cloudbrain.py` |
| The relay (Luma Cloud): the brain route, metering, the yes on record | `api/_lib/luma-cloud.js` and `tests/luma-brain.test.mjs`, both at the top of the repo |
| Chat path | `Agent.chat` → `_chat_turn` → polish → `_friend_style` → `_second_look` (`src/luma/agent/runtime.py`) |
| Luma's look: living water on the talk screen's dark stage (`look: "water"`), the marble everywhere else (the first slides, the avatars, the logo) | `src/luma/control/web/orb.js` (tests: `tests/test_orb.py`, which opens it in a browser when node has Playwright). After a change, copy it to `desktop/assets/orb.js` |
| The human model: what a close friend does with language, trait by trait, and where each lives | `docs/HUMAN_MODEL.md` |
| The device you can build: a lamp (a frosted dome on a white base), parts, wiring, the microphone switch, a case to print | `hardware/README.md`, `hardware/luma_case.scad`, `hardware/stl/` (tests: `tests/test_hardware_case.py`). A design; no unit has been built. The dome's glow says nothing about listening: only the amber light on the microphones' power does |
| Setting a new Luma up from a phone: its own setup network, a page to pick the Wi-Fi, then the same spoken code pairs the phone | `src/luma/hardware/firstrun.py` (tests: `tests/test_firstrun.py`). Only where `LUMA_WIFI_SETUP=1`. The Wi-Fi password goes to NetworkManager and nowhere else; nothing about a setup is logged |
| Pre-orders: why they'd fail (seven causes, ranked) and the plan with dates, money and kill points | `docs/PREORDER_POSTMORTEM.md`, `docs/PREORDER_PLAN.md` |
| Who pays, what a lamp costs, what a seat earns | `docs/BUSINESS_MODEL.md` (tests redo its sums: `tests/test_business_model.py`). Every number says if it's known, ours or an assumption. No ads, no data, nothing earned from minutes |
| Plan and progress | `docs/HUMAN_PLAN.md` |
| Baseline | `docs/HUMAN_BASELINE.md` |
| For therapists | `docs/CLINICAL_SAFETY.md` |
| Super Intelligence: the master prompt and the scoreboard | `docs/SUPER_INTELLIGENCE_PROMPT.md`, `docs/SUPER_INTELLIGENCE.md` |
