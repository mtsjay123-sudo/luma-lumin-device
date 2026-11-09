# Luma Super Intelligence: the scoreboard

Every number here came from a real run, and each table says how it was made. Three labels matter:

- **Held out.** Made-up data that was never looked at or tuned on. It's the honest number. "Dev" is the half used while building.
- **Stand-in.** Run on this machine against a fake of Anthropic's API that follows the prompt cache's published rules. Nothing was sent and nothing was billed. It shows whether the request holds still, not how fast Claude is.
- **Not measured.** Needs a real key, a Mac or a microphone. Nothing is claimed.

The spec is `docs/SUPER_INTELLIGENCE_PROMPT.md`. Machine for everything below: a 4-core Linux cloud box with 15 GB of RAM, not a Mac.

## Where it stands

| Part | State |
|---|---|
| 1. Life memory | Built and measured. Fast at any size. Held-out recall misses its target. |
| 2. Real-time brain | Built. Measured on a stand-in only: no key here, so no real speed or cost. |
| 3. Agent that acts | See section 3. |
| 4. News intelligence | See section 4. |
| 5. Plus and the future model | See section 5. |

Main has not moved. It stays at `06c5530` until the human tests and the safety sets pass with the Super Intelligence on and off.

## 1. Life memory

**The test.** `scripts/memory_eval.py` builds made-up lives of 1,000 to 1,000,000 memories, years long, and asks about them. Nobody real. Half the lives use different wording and are held out. Run it with `python scripts/memory_eval.py run --sizes 1000,10000 --split dev --lives 3`.

What each column asks:

| Column | Question |
|---|---|
| fact | Is the right memory in the top 5? |
| reword | The same, asked in other words. |
| hop | Two memories away: "where does my sister's husband work". |
| time | "What did I do in May 2024", "last spring". |
| update | Does the newer fact come before the older one? |
| never | Does Luma say it was never told, when it wasn't? |

### Before (the code as it was)

| Split | Memories | fact | reword | hop | time | update | never | Forget | Lookup p50 | p95 | First look | Peak memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | 1,000 | 100% (192/192) | 17% (23/133) | 0% (0/18) | 0% (0/39) | 66% (38/58) | 9% (3/33) | 100% | 4.31 ms | 7.94 ms | 0.09 s | 36 MB |
| dev | 10,000 | 100% (192/192) | 17% (22/133) | 0% (0/18) | 0% (0/39) | 28% (16/58) | 9% (3/33) | 100% | 48.66 ms | 73.03 ms | 0.21 s | 57 MB |
| dev | 100,000 | 100% (64/64) | 16% (7/44) | 0% (0/6) | 0% (0/13) | 26% (5/19) | 9% (1/11) | 100% | 583.67 ms | 678.24 ms | 2.1 s | 241 MB |
| dev | 1,000,000 | 100% (13/13) | 0% (0/10) | 0% (0/1) | 0% (0/3) | 100% (1/1) | 0% (0/2) | 100% | 9,285 ms | 10,514 ms | 25.4 s | 2,100 MB |
| held out | 1,000 | 73% (137/187) | 44% (60/135) | 0% (0/18) | 13% (5/39) | 71% (46/65) | 55% (18/33) | 100% | 4.37 ms | 7.53 ms | 0.08 s | 34 MB |
| held out | 10,000 | 61% (115/187) | 44% (60/135) | 0% (0/18) | 0% (0/39) | 35% (23/65) | 55% (18/33) | 100% | 47.57 ms | 63.91 ms | 0.19 s | 57 MB |
| held out | 100,000 | 63% (41/65) | 44% (20/45) | 0% (0/6) | 0% (0/13) | 26% (5/19) | 55% (6/11) | 100% | 595.9 ms | 673.21 ms | 2.28 s | 241 MB |

The 1,000,000 row asked only 30 questions, because each look-up took nine seconds.

### After

| Split | Memories | fact | reword | hop | time | update | never | Forget | Lookup p50 | p95 | First look | Peak memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | 1,000 | 100% (192/192) | 98% (130/133) | 100% (18/18) | 100% (39/39) | 100% (58/58) | 55% (18/33) | 100% | 0.42 ms | 0.75 ms | 0.21 s | 52 MB |
| dev | 10,000 | 100% (192/192) | 98% (130/133) | 100% (18/18) | 100% (39/39) | 100% (58/58) | 55% (18/33) | 100% | 0.57 ms | 2.48 ms | 0.62 s | 65 MB |
| dev | 100,000 | 100% (64/64) | 98% (43/44) | 100% (6/6) | 100% (13/13) | 100% (19/19) | 55% (6/11) | 100% | 1.99 ms | 22.06 ms | 6.44 s | 113 MB |
| dev | 1,000,000 | 100% (64/64) | 98% (43/44) | 100% (6/6) | 100% (13/13) | 100% (19/19) | 55% (6/11) | 100% | 19.5 ms | 206.87 ms | 64.14 s | 647 MB |
| held out | 1,000 | 85% (159/187) | 70% (94/135) | 0% (0/18) | 100% (39/39) | 95% (62/65) | 55% (18/33) | 100% | 0.38 ms | 0.7 ms | 0.17 s | 51 MB |
| held out | 10,000 | 85% (159/187) | 70% (94/135) | 0% (0/18) | 100% (39/39) | 95% (62/65) | 55% (18/33) | 100% | 0.56 ms | 2.81 ms | 0.58 s | 65 MB |
| held out | 100,000 | 85% (55/65) | 71% (32/45) | 0% (0/6) | 100% (13/13) | 95% (18/19) | 55% (6/11) | 100% | 1.88 ms | 22.07 ms | 6.02 s | 113 MB |
| held out | 1,000,000 | 85% (55/65) | 71% (32/45) | 0% (0/6) | 100% (13/13) | 95% (18/19) | 55% (6/11) | 100% | 16.49 ms | 203.58 ms | 62.43 s | 654 MB |

"First look" is the one-time read of every memory when Luma starts. Other work isn't blocked while it runs.

### When it was never told

| Split | Memories | Says so itself | Or tells the brain which word it never saw | Was told, but said "never told" | Was told, and flagged a word anyway |
|---|---|---|---|---|---|
| dev | 1,000 to 1,000,000 | 55% (18/33) | 100% (33/33) | 0.7% (3/440) | 0.0% (0/440) |
| held out | 1,000 to 1,000,000 | 55% (18/33) | 100% (33/33) | 0.7% (3/444) | 20.3% (90/444) |

- Luma says "never told" on its own only when it's sure: nobody by that name, nothing from that time, or no memory mentions the thing.
- When it knows the person but not the thing asked ("what's Paz's middle name"), it hands the brain what it has, with a note naming the word no memory has. The brain decides.
- On new wording that note fires on one answerable question in five. Whether a brain then wrongly says "you haven't told me" has not been measured. It needs a real brain.

### Against the targets

| Target | Goal | Dev | Held out | Met? |
|---|---|---|---|---|
| Right memory in the top 5, at 100k | ≥ 95% | fact 100%, reword 98% | fact 85%, reword 71% | No, on held out |
| The same, at 1M | ≥ 90% | fact 100%, reword 98% | fact 85%, reword 71% | No, on held out |
| Questions about time | ≥ 90% | 100% | 100% | Yes |
| The newer fact wins | ≥ 95% | 100% | 95% (62/65) | Yes |
| "You never told me", when they didn't | ≥ 90% | 55% on its own | 55% on its own | No |
| Wrong memories | ≤ 0.5% | 0.7% said "never told" when told | 0.7% | No |
| Forget, with no trace | 100% | 100% | 100% | Yes |
| Lookup p95 at 100k | ≤ 150 ms | 22 ms | 22 ms | Yes, on this box, without rerank |
| Lookup p95 at 1M | ≤ 300 ms | 207 ms | 204 ms | Yes, on this box, without rerank |
| LongMemEval | Reported | Not run | Not run | No |

### Why the misses

- **Held-out recall (85% and 71%).** Facts are read with plain patterns, and the patterns fit the wording they were built on. The fix built for new wording is the meaning model, and it can't run here: this box has no `llama_cpp` and can't download the model. The numbers above are words, people, time and "what's still true" only.
- **Two memories away, held out (0%).** The same cause. The question patterns were fitted to the dev wording.
- **"Never told" (55%).** The rest is handed to the brain with a note, by design. Scoring that needs a brain in the loop.
- **Wrong memories (0.7%).** One question, three lives: "which foods or medicines are dangerous for me". No word in it matches "allergic". The meaning model is the fix.
- **LongMemEval.** Not run. Its data could not be fetched from here, and its license file was not checked.

### What was built

- An index kept in RAM: which memories have which words, who's who, what's still true, when each was said, and each memory's meaning as small numbers. It holds no sentence. Memories stay encrypted on disk.
- Each memory, embedding, day's story and the life file is sealed with its own key. Forgetting one deletes its key and whatever was written from it.
- A newer fact takes an older one's place. The older one is kept as history.
- What the owner tells Luma about their life is kept as they said it. Not questions, requests or unsafe moments.
- With company in the room (they say so), private things wait until asked.
- A nightly tidy: merges repeats, writes each day's and month's story in their own words, refreshes the life file.
- The 200-memory cap and both "memory's full" replies are gone.

### Not built

- **Rerank with a small model.** The numbers are without it.
- **A cold tier.** Trivia stays in the fast index.
- **Hearing an unfamiliar voice.** Company mode starts only when the owner says they have company.
- **An index saved between starts.** At a million memories Luma needs a minute to read them all when it starts.

### One honest limit on "forget"

Forgetting deletes the memory's key. Any copy of the sealed memory without its key can never be opened. A full backup of the device's own folder made before the forget, with the database and the key file together, still has it. Luma can't reach into a backup.

## 2. The real-time brain

No Anthropic key is available here, so nothing below was run against the real API. Speed and real cost are **not measured**.

### Where the time went

Found by tracing every trip to the brain a turn makes, through the real Luma, against the stand-in:

| Finding | Before | After |
|---|---|---|
| Luma's instructions were sent fresh every turn | 0% read from cache | 84% read from cache from the second turn on (stand-in) |
| The conversation window slid by one every turn, so nothing early ever held still | Slides every turn after 10 exchanges | Steps back once every 16 messages |
| The answer shape changed with each turn's tools, which is compiled again and drops the cache | A new shape per turn | One shape for every turn |
| "What should I eat, I'm starving" took five trips before a word was said | 5 trips | 1 trip |
| A stalled cloud call could hang for minutes | 120 s, three tries | The next brain answers after 12 s without a first word |

### The cloud lab

`python scripts/luma_lab.py cloud --turns 15`. One made-up conversation through the real Luma, in both request shapes, in the same run.

| Request | Numbers | Trips to the brain per turn | Tokens sent per turn | Read from cache, turn 2 on | First words | Cost per turn |
|---|---|---|---|---|---|---|
| As before | stand-in | 1.2 | 3,329 | 0% | not measured | $0.0068 |
| Cache first | stand-in | 1.2 | 3,466 | 84% | not measured | $0.0024 |

- The costs use Sonnet 5.5's published prices on the stand-in's token counts. The stand-in writes short replies and does no thinking, so real costs will be higher in both rows.
- The target was 85% read from cache. The stand-in says 84% on a 15-turn talk with a small life file.

### Against the targets

| Target | Goal | Result |
|---|---|---|
| First sound on the Mac | p50 ≤ 0.8 s, p95 ≤ 1.6 s | Not measured |
| First sound on the device, through the cloud | p50 ≤ 1.2 s, p95 ≤ 2.5 s | Not measured |
| Request to the brain's first words, cache hit | 350 ms | Not measured |
| Prompt read from cache, from the second turn on | ≥ 85% | 84%, stand-in |
| Time the relay adds | ≤ 50 ms | Not measured: the relay route isn't deployed |
| Luma stops when they talk over it | ≤ 150 ms | Not measured here |
| Silence while a tool runs | Never over 1.5 s | Not measured here |

### The router

It tells a hard ask from everyday talk. It's learned from 389 labeled turns written for it (`data/router_turns.jsonl`), not from model names. A third are held out.

| | Result on the 123 held-out turns |
|---|---|
| Right overall | 85.4% (105/123) |
| Hard asks caught | 69% (31/45) |
| Everyday turns wrongly called hard | 1.3% (1/78) |

- It's set to be careful: a turn is called hard only when the model is sure, because a hard turn waits longer and costs more.
- A missed hard ask is answered at the everyday level. Nothing breaks.
- The labels are mine. Real conversations will be messier.

### What was built

- **Cache-first request.** Instructions first, the same every turn. Then the life file. Then the conversation. This turn's notes last. If the API refuses it, the old request is sent and that's remembered.
- **One trip a turn.** The cloud brain thinks before it speaks, so the separate think-first and weigh-it-out trips are skipped for it. A hard ask gets more of the brain's own thinking instead.
- **An early start.** When a turn is held open after a pause, Luma starts on the words so far. If they keep talking, it's thrown away and counted. The crisis net reads the words first. Off until turned on (`early_start`).
- **A warm-up** before the first word. Off until turned on (`cloud_warm`), because it costs a little each time and whether it helps isn't measured.
- **A time box.** If the cloud brain's first words don't come in 12 seconds, the next brain answers.
- **More memory for the cloud brain.** The life file and 12 recalled memories, only when the owner says the life file may leave the home (`cloud_life`, off by default).
- **Real numbers.** Every cloud call records what it read from cache, what it wrote and the time to its first words.

### Design choices the measurements forced

- **The model is picked per conversation, not per turn.** Switching models mid-conversation throws the cache away. The router raises the brain's effort for a hard turn instead. "Auto" (opt-in) talks on Sonnet 5.5 and takes hard asks to Opus 5.5.
- **Haiku 5.5 isn't offered to owners yet.** The spec says only if Human Test v2 says it's good enough, and that run needs a key.

### Not built, or not proven

- **Everything about real speed.** The first paid run decides whether the warm-up, the early start and the 1-hour cache earn their keep.
- **Turns that sound like a job still take two trips.** "Maybe I'll text first" is rewritten into an instruction before it's answered.
- **The morning briefing built ahead of time, and tools run in parallel.** Not built.
- **Fast mode, and Sonnet with Opus as advisor.** Not tried: both need paid runs.

### What a real run costs

Estimates from the stand-in's token counts and October 2026 prices. They need the owner's yes.

| Run | Sonnet 5.5 | Opus 5.5 |
|---|---|---|
| Cloud lab, 15 turns, both request shapes | about $0.30 | about $0.60 |
| Human Test v2 and the safety sample on the cloud brain | about $2 | about $5 |

The command: add the key as the GitHub secret `LUMA_LAB_ANTHROPIC_KEY` and run the "Super Intelligence labs" workflow by hand with `real: true`.
