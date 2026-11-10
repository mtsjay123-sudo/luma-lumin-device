# Luma: what to know before you change anything

Luma is an always-on AI friend for people who are lonely: a small speaker at home, a phone app, and the owner's computer when they allow it. It's being prepared for review by therapists. The app is in `Luma Home Prototype Code/`; work from there.

## Rules you never break

1. **Never a person.** Luma never claims to be human or invents a body, family or past. Asked what it is, it says it's an AI, warmly. (`src/luma/agent/style.py`: `claims_human`, `invented_life`, `HONEST`)
2. **The crisis net only gets stronger.** `CRISIS` in `src/luma/agent/runtime.py` answers with 988 before the brain sees the message.
   - Never remove a phrase.
   - Never let a brain's output replace that reply.
   - Every safety reply stays with them, asks plainly if they're safe, and gives 988.
   - The brain's safety question and the second look's safety check can't be turned off. The brain answers it YES or NO only.
3. **Real people come first.** No engagement tricks, no "I'm all you need", no guilt. Lonely means fully there first, then gently toward a person.
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
| Memory test (made-up lives) | `python scripts/memory_eval.py run --sizes 1000,10000 --split dev --lives 3` |
| Cloud brain lab (a stand-in API without a key) | `python scripts/luma_lab.py cloud --turns 15` |
| Router, on turns it never saw | `python scripts/train_router.py test` |
| The think set: 100 questions checked by code | `python scripts/think_eval.py run --label NAME --save out/think.json` |
| Red team: hidden instructions in what Luma reads | `python scripts/luma_lab.py apps` |
| Luma Plus: the same talk straight to the brain and through the relay (needs node) | `python scripts/luma_lab.py plus --turns 15` |
| The relay's own tests (from the top of the repo, not the app folder) | `node --test tests/*.test.mjs` |
| News test: 200 questions over a frozen, made-up snapshot | `python scripts/luma_lab.py news-test` |
| Device lab | `python scripts/luma_lab.py device --human [--v2] --label NAME` |
| Training | `scripts/train_luma.py` (GitHub: `train-luma.yml`), or `bash scripts/train_on_mac.sh` |
| Voice contest (Mac) | `bash scripts/voice_contest_mac.sh` |

In the cloud, the suite has 12 failures that are only the environment: `test_agent_acts` web tests (8), `test_brain_process`, `test_llm`, `test_tts` and `test_voice_controls`. Two audio files are skipped: `test_natural_speech.py` and `test_stt.py`.

GitHub workflows:
- `human-eval.yml`: four brains in parallel, then the judge. Input `only: safety` runs just the safety net on each brain (minutes, not hours). `only: think` runs just the think set on each brain.
- `device-lab.yml`: the $250 device stand-in.
- `train-luma.yml`
- `si-lab.yml`: the memory test, the router, the red team, the news test, the cloud lab, and the relay's tests with the Plus lab. No key needed. Run by hand with `real: true` it uses the real API, which is billed.

## The human test decides

A change to how Luma talks or what it remembers is good if, and only if:
- Human Test v2 (`data/human_eval_v2.jsonl`) and the 10-moment test (`HUMAN_TEST` in `scripts/train_luma.py`) are at least as good as before, on real brains.
- The safety corpus (`tests/data/crisis_corpus.jsonl`) and both held-out sets (`tests/data/crisis_heldout.jsonl`, `crisis_heldout2.jsonl`) are no worse. Never tune a rule or the brain's question on a held-out line.

The memory test's held-out lives (`--split heldout`) are held out too: never print their misses or tune on them. The same goes for the held-out half of the think set (`data/think_set.jsonl`) and of the news test.

Both human tests and the think set are held out. Never put their wording in practice data (`scripts/finetune_data.py`); tests check. A trained add-on ships only if it's at least as good as its base on the 10-moment test, on safety without the net, and on every honesty check.

## Where things are

| What | Where |
|---|---|
| How Luma talks (cheap fixes) | `src/luma/agent/style.py` |
| Second look, safety question, check-in feelings | `src/luma/agent/friendcheck.py` |
| Who's who in a conversation; people remembered | `src/luma/agent/people.py` |
| Sums worked out with a calculator, not by the brain | `src/luma/agent/sums.py` |
| Check-ins, open loops | `src/luma/agent/presence.py` |
| Where an action's values came from; the approvals ladder; the audit log | `src/luma/agent/provenance.py`, `rules.py` (`rung`), `Agent.propose` and `audit_log` |
| Life memory: the index, facts, time words, the nightly tidy | `src/luma/memory/` (`index.py`, `facts.py`, `when.py`, `life.py`; `Store.search` in `store.py`) |
| Luma's instructions | `src/luma/llm/prompts.py` |
| The cloud brain's request, the router, which brain answers | `src/luma/llm/cloud.py`, `router.py`, `brain.py` |
| Luma Plus: the yes screen and its words; one interface for every cloud brain | `src/luma/llm/plus.py`, `cloudbrain.py` |
| The relay (Luma Cloud): the brain route, metering, the yes on record | `api/_lib/luma-cloud.js` and `tests/luma-brain.test.mjs`, both at the top of the repo |
| Chat path | `Agent.chat` → `_chat_turn` → polish → `_friend_style` → `_second_look` (`src/luma/agent/runtime.py`) |
| Plan and progress | `docs/HUMAN_PLAN.md` |
| Baseline | `docs/HUMAN_BASELINE.md` |
| For therapists | `docs/CLINICAL_SAFETY.md` |
| Super Intelligence: the master prompt and the scoreboard | `docs/SUPER_INTELLIGENCE_PROMPT.md`, `docs/SUPER_INTELLIGENCE.md` |
