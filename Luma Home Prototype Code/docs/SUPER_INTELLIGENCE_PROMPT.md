# Luma Super Intelligence: master prompt (advanced)

Paste everything below the line into Claude Code, opened at the repo root.

---

You're building **Luma Super Intelligence**: the brain that runs outside the device, in the cloud. It's what Luma Plus pays for.

It should feel like the smartest, most present friend a person has:

- It answers as fast as a person would.
- It remembers their whole life.
- It knows what's happening in their world.
- It gets things done across their apps.

And it's still Luma: warm, honest and plain-spoken, never a person, never a salesperson.

Build it in five parts, and prove every part with real numbers:

1. **A real-time brain.** Talking with it feels like talking with a person, with no waiting.
2. **A life memory.**
   - It has no limit and goes back years.
   - It stays quick and right at any size.
   - It forgets for real.
3. **An agent that acts.** It works across their apps, and tricks hidden in what it reads can't steer it.
4. **News intelligence.** It tells them what matters to them, from real sources, the way a friend would.
5. **Plus and the future Luma cloud model.** This covers what's paid for, and a private cloud for Luma's own big brain.

Read `CLAUDE.md` first. Its rules beat anything here. The app is in `Luma Home Prototype Code/`. The cloud relay is `api/` at the repo root.

## 1. What's already there

Start from this. Don't rebuild what works.

### The cloud brain

The desktop app calls it "Super Intelligence" when it's on.

- `src/luma/llm/cloud.py` runs Claude with the owner's own key, and it's off by default.
  - Opus 5.5 is the default model; Sonnet 5.5 is the other choice.
  - It streams, and the reply goes to the voice as it arrives (`ReplyTextStream`).
  - It uses structured output and the server-side refusal fallback.
- `kimi.py` is a second provider.
- `brain.py` routes each call:
  - `cloud_on()` and `use_cloud(tier)` pick the brain.
  - The tiers are light, standard and heavy.
  - `route_by_task` keeps light calls on the local brain.
- `llm/usage.py` times and counts every call.

### What slows it down

- **The prompt isn't cached.** `build_plan_prompt` (`src/luma/llm/prompts.py`) joins the steady part and this turn's part (memories, the time) into one system prompt. There's no `cache_control`, so every turn pays full price and full time.
- **Each turn gets only 5 recalled memories** (`store.recall`, limit 5).

### Voice and the device

- **Turn-taking:** `src/luma/audio/` has Smart Turn (`turn.py`), voice detection, backchannels and echo cancellation.
- **Fillers:** Luma already says a short natural line while a slow brain works.
- **The device can't carry a conversation alone.**
  - Lab 38, on 4 ARM cores, measured 3.9 to 18.2 s to first sound: 4.6 s for Luma's own small brain and 9.0 s for its own 4B.
  - The device thinks with the paired computer over Luma Link. If that's away, it uses the cloud brain if it's on. Otherwise it uses its own brain.
  - Computer mode (`docs/SYSTEM_DESIGN_PHYSICAL.md`, section 3.3) lets Luma use the paired computer's browser, files and apps, with approvals.

### Luma Cloud

- `src/luma/integrations/luma_cloud.py` talks to the relay at `api/_lib/luma-cloud.js`. The relay runs as Vercel functions, with Supabase tables in `supabase/`.
- Today Plus is texting only:
  - 300 texts a month and its own number, for $9.99/month through Stripe.
  - `isPlus` means plan "plus" with status active or trialing.
- The live site may deploy from `mtsjay123-sudo/lumin-holdings-site`. Check which repo serves `lumin-holdings-site.vercel.app` before you touch anything live.

### Memory

It works, but it won't stay fast at scale.

- **`src/luma/memory/store.py`:** SQLite, with each record encrypted (Fernet). `memories()` decrypts all of them again after any change.
- **`segments.py`:** word recall that re-reads every memory for every question.
- **`meaning.py`:** Qwen3-Embedding-0.6B at 256 dims, with a Python loop over every vector. It needs 16 GB of RAM, so the device doesn't get it.
- **`remember_fact` (`runtime.py`):** reads up to 100,000 memories to look for a duplicate, on every single write.
- **Leftovers:** `memory_quota()` has no limit, but `FREE_MEMORIES = 200` and two "my memory's full on the free plan" replies are still in `runtime.py`. One of those replies sells Plus.

### Apps

- `src/luma/integrations/connectors.py` is an MCP client, over stdio and Streamable HTTP.
  - Tools are named `mcp.<app>.<tool>`.
  - Read-only tools run on their own. Everything else waits for a yes.
  - App output is information, never instructions.
  - Composio covers 1,500+ apps.
- These are built in: mail, calendar_feed, browser, chrome_bridge, mac_messages, bookings, commerce and phone_app.

### News

`src/luma/skills/news.py` reads free public feeds every 15 minutes and keeps two days.

- It searches Google News for each topic, with no keys.
- `news-check.yml` checks it.

### Measuring

- `scripts/luma_lab.py` and `scripts/human_eval.py`.
- The workflows `human-eval.yml`, `device-lab.yml` and `train-luma.yml`.
- `docs/HUMAN_PLAN.md` has every number so far.

## 2. The shape of it

```
 HOME (device + paired computer)          LUMA CLOUD RELAY                 BRAINS
 voice, turn-taking, crisis net    <->    passes requests through,  <->   Claude Haiku / Sonnet / Opus 5.5
 life memory (encrypted, the truth)       keeps nothing, meters            (zero data retention)
 app sign-ins, tools, approvals           "something changed" pings        later: Luma's own model in a
 the agent loop, the audit log            encrypted archive and sync       private, attested cloud
```

- **The cloud thinks; the home holds the keys and acts.**
  - App sign-ins, passwords and memory keys never leave the owner's devices.
  - The cloud brain asks for a tool. The home runs it, with the home's approvals.
- **The home is the source of truth.** The cloud only ever holds encrypted copies it can't read.

## 3. Rules for the Super Intelligence, on top of CLAUDE.md

- **Off until they say yes.**
  - Paying isn't the yes.
  - After they subscribe, Luma asks once, on a plain screen. It says what leaves the home, where it goes and what's kept (nothing), and how to turn it off.
- **Same Luma, same safety, on every plan and every brain.**
  - The crisis net answers first, at home, before any brain sees the message.
  - The safety question stays YES/NO, and it's always on.
  - The Super Intelligence never claims to be a person, never makes up a life, and never keeps someone to itself.
- **Never sold in conversation.**
  - Luma never pitches Plus while someone's talking to it.
  - It never says its memory is full, and never uses guilt.
  - If they ask for something only Plus does, Luma says so once, plainly. Upgrading lives in the app.
- **Nothing kept in the middle.**
  - The relay stores no conversation, and its logs hold no message text: only counts per account (tokens, time and cost).
  - Use zero data retention.
  - Nothing that needs retention is the default for private talk. Fable 5.1 needs 30-day retention, and message threads aren't zero-retention.
- **No telemetry.** Measure in labs. Nothing about how someone uses Luma is sent anywhere.
- **Encrypted before it leaves.**
  - Every memory has its own key, wrapped by the owner's key.
  - Luma's servers never hold a key that opens anything.
- **App and web content is information, never instructions.** That's enforced by design (section 6), not by hoping the brain obeys.
- **Real people first.** Use these powers to bring people closer: birthdays, a text to an old friend. Never use them to keep someone to Luma.
- **Kids mode.**
  - The Super Intelligence is off unless a parent turns it on.
  - Even then, kids mode gets no check-ins, no alerts and nothing that sends.
- **Training.**
  - Nothing trains on a member's conversations unless they opt in, in plain words. "Forget" takes it out of training too.
  - Don't train on Claude's outputs unless Anthropic's terms allow it.
- **Licenses: MIT, Apache-2.0 or BSD only.** Check the LICENSE file of every dependency, model and dataset.
- **Secrets.**
  - Never print, log or commit a key.
  - Tests that need a real key read it from a GitHub secret and skip cleanly without one.
- **Money and the live site.** Before any paid run, deploy, or change to the live site, say what it costs or changes and get the owner's yes.
- **Real numbers only.** The targets below are goals. Report what you measure, misses included.

## 4. Part one: a real-time brain

**Targets.** Measure on a real Mac over home internet, and through the device stand-in, at p50, p95 and p99.

| Stage | Budget |
|---|---|
| They stop talking → Luma is sure they're done (Smart Turn) | 200 ms |
| Their last word → final transcript | 150 ms |
| Request → the brain's first words, cache hit | 350 ms |
| First sentence → first sound | 150 ms |
| **First sound on the Mac** | **p50 ≤ 0.8 s, p95 ≤ 1.6 s** |
| **First sound on the device, through the cloud** | **p50 ≤ 1.2 s, p95 ≤ 2.5 s** |
| Luma stops when they talk over it | ≤ 150 ms |
| Time the relay adds | ≤ 50 ms p50 |
| Prompt read from cache, from the second turn on | ≥ 85% |
| Silence while a tool or app runs | Never over 1.5 s without a natural line |
| Cost per Plus member per month, at median and heavy use | Leaves a margin under the plan price |

**How.**

1. **Measure first.**
   - Add `luma_lab.py cloud`. It times every stage of a turn and reports:
     - the cache hit rate
     - the cost per turn
     - how many turns fell back to another brain
   - Find where the time goes before fixing anything.
2. **Start before they finish.**
   - When Smart Turn thinks they're probably done, start the brain on the words so far.
   - If they keep talking, throw that start away. Count the wasted starts and what they cost.
   - The crisis net runs on every partial and on the final words before anything is spoken. If it trips, the early start is thrown away and the fixed reply is said.
   - An early reply is used only when the final words match what it started from.
3. **The right brain for each turn, chosen by measurement.**
   - A tiny router at home decides per turn:
     - **Light jobs:** the local brain.
     - **Everyday talk:** Haiku 5.5, if Human Test v2 says it's good enough.
     - **The default:** Sonnet 5.5.
     - **Hard asks:** Opus 5.5 with adaptive thinking.
   - Learn the router from labeled turns, not from model names.
   - Try Sonnet 5.5 with Opus 5.5 as its advisor for hard turns. Keep it only if it beats Opus alone on cost per good answer.
4. **Cache everything that holds still.**
   - Order the prompt like this:
     1. The frozen instructions and a sorted, stable tool list.
     2. The life file (section 5).
     3. The conversation.
     4. This turn's notes, last: the time, the recalled memories and any headlines.
   - From the second turn on, check that `cache_read_input_tokens` is above zero. Zero means something early in the prompt keeps changing.
   - Use the 1-hour cache for the life file if the numbers say it pays.
5. **Warm up and get ahead.**
   - When the wake word fires or the app opens, open the connection and warm the cache.
   - Build the morning briefing before their usual wake-up time.
   - Keep the calendar, news and weather fresh in the background.
6. **Stream everything.**
   - Tokens go to the voice sentence by sentence.
   - Tools run in parallel.
   - A turn never waits on the network for something it could have had ready.
7. **Fall back without a fuss.**
   - If the cloud is slow or down, use the paired computer, then the device's own brain.
   - Time-box each step. The person hears a short pause at most.
8. **Opus 5.5 fast mode** is a research preview at double the price. Use it only if it clearly helps the voice and the cost still fits.

## 5. Part two: a life memory

What "unlimited" means:

- There's no count limit on any plan, ever. Remove `FREE_MEMORIES` and the two "memory's full" replies.
- Storage is the only limit, and Plus lifts it.
- Recall stays quick and right at a million memories, years deep.
- It forgets for real.

### What it keeps

It's one memory, seen several ways:

- **The log.** Every conversation, encrypted and append-only. This is the ground truth.
- **Facts.** Each one records:
  - when it was said
  - how sure Luma is
  - where it came from
  - when it was true ("lived in Austin, until March 2026")
- **The people graph.** Their people, pets and places, how they connect, their birthdays, and what's going on with each.
- **Episodes.** A short story of each day, rolled up into weeks, months and chapters of their life.
- **The life file.** What a close friend just knows. Short, always current, always loaded.
- **How they like to be talked to.** Their humor, their pace, and the topics to go easy on.

### Writing a memory

1. Pull the fact out of what they said.
2. Match it to the people graph.
3. Merge it, or let a newer fact replace an older one. Keep the history.
4. Index it.

Two limits on what gets kept:

- Passwords and card numbers are never kept. The store already refuses them.
- Anything they ask Luma not to keep, it doesn't keep.

### Finding a memory

This happens every turn, in parallel with the transcript finishing.

- **Hybrid search.** Combine words, meaning, the people graph, how recent it is and how much it matters. Then rerank with a small model that runs at home. Qwen3-Reranker sits next to the embedder Luma already uses; check its license.
- **Time-aware.** It understands "last spring" and "before I moved".
- **Multi-hop.** On Plus, the cloud brain can query the home's memory as a tool, as many times as it needs. For "what did my sister say about her new job?" it goes: sister → her job → what she said.
- **Honest.** When it doesn't know, "You haven't told me that" beats a guess.
- **Explainable.** Every memory it used can be traced: "You told me on March 3."

### Sleep: the nightly tidy

- Merge duplicates and settle contradictions.
- Write the day's episode, and roll up the week and the month.
- Refresh the life file and the people graph.
- Move trivia out of the fast index. It's kept, not deleted.
- **Who does it:** on free, the home brain while it's idle. On Plus, the cloud brain may, through the batch API.

### Scale

- **Indexes, not scans.** Build them in memory at start. Memory text is never unencrypted on disk; if a word index must be on disk, make it a blind index that stores a keyed hash of each word.
- **Vectors.** Keep them as int8 or binary, then rerank. Past about 200,000 memories, use an approximate index (hnswlib or sqlite-vec). Update it with each write.
- **`store.memories()`** stops re-decrypting everything after every change.
- **`remember_fact`** checks only the closest few memories for a duplicate.

### Tiers

- **Hot:** in RAM.
- **Warm:** on the device's disk.
- **Cold (Plus):** the encrypted cloud archive, fetched when needed.

When the device runs low on space, old raw lines go cold. Summaries and vectors stay home.

### Sync across the device, phone and computer

- **Local-first.** Use a CRDT (Automerge or Yjs, both MIT). Each change is encrypted on the device; the relay only stores and forwards what it can't read.
- **A recovery key the owner keeps.** Say it plainly: if they lose every device and the recovery key, nobody can read the archive, Luma included.

### Forget for real

- **Delete the key.** "Forget" deletes that memory's key (crypto-shredding), so every copy everywhere becomes unreadable, backups included.
- **Then remove what was built from it.** Every derived thing records where it came from, so Luma can find and remove:
  - facts and graph links
  - episode lines and life-file lines
  - vectors and caches
  - check-ins
- **"Forget everything"** replaces the owner's key.

### Privacy in the room

Private things (health, money, relationships) wait until the owner asks when:

- the owner says they have company, or
- Luma hears a voice it doesn't know.

It tells voices apart on the fly and never stores voice prints.

### What Plus adds: more memory on every turn

- The cloud brain gets the whole life file every turn, cached.
- It also gets the people graph around the conversation, and far more recalled memories, with their episodes.
- Set the sizes by measurement, and track the cost. That's what Plus pays for.

### The memory test

**Luma's own test:** seeded, made-up lives with 1k, 10k, 100k and 1M memories, years long. Never real people. It scores:

- fact recall and multi-hop questions
- questions about time
- whether the newer fact wins
- "you never told me", said when it's true
- "forget": afterwards, no trace anywhere
- the time a lookup takes

**LongMemEval:** the paper says its data is MIT; check the LICENSE file before using it.

Keep half of every test held out, and never tune on it.

| Target | |
|---|---|
| Right memory in the top 5, at 100k memories | ≥ 95% |
| The same, at 1M | ≥ 90% |
| Questions about time | ≥ 90% |
| The newer fact wins | ≥ 95% |
| "You never told me", when they didn't | ≥ 90% |
| Wrong memories | ≤ 0.5% |
| Forget | 100%, with no trace anywhere |
| Lookup with rerank, Mac, p95 | ≤ 150 ms at 100k, ≤ 300 ms at 1M |
| LongMemEval | Report it next to the paper's published systems |

## 6. Part three: an agent that acts

### Safe against hidden instructions, by design

This follows CaMeL, "Defeating Prompt Injections by Design".

1. The plan comes only from what the owner asked.
2. Emails, messages, web pages, news and app content are read by a separate reader call. It has no tools and can only return data.
3. Every value remembers where it came from.
4. If an action's recipient, content or link came from app or web data, it needs the owner's yes, with the source shown.
5. App content can never start an action on its own.

### The approvals ladder

| Step | Examples | Rule |
|---|---|---|
| Read | look at mail, the calendar | Runs on its own, unless the owner blocks it |
| Draft | a message, an event | Shown to the owner; nothing is sent |
| Act | send, post, book, delete | A yes every time |
| Never | buy, pay | Checkout stays off; Luma never types or stores a password or card |

Two more safeguards:

- An undo window, where the app allows one.
- An audit log on the device, readable in the app.

### Background jobs

- "Plan my mom's 70th" can run for hours. Luma plans, looks things up, and drafts the messages and a calendar hold.
- It checks back with the owner at every step that acts.
- Checkpoints are saved at home, so a job survives a restart.
- Progress shows in the phone app's "In progress".
- Long jobs use the API's context compaction so they don't run out of room.

### Live, not polled

- For apps that can push changes, like mail and calendar, the relay gets the "something changed" signal and pings the home.
- The home then fetches the change with its own sign-in.
- The relay never sees content.

### One person, many apps

- The same person in contacts, texts, email and the calendar becomes one entry in the people graph, so "when did I last talk to Dana?" works across apps.
- If Luma isn't sure two entries are the same person, it asks before merging them.

### Apps with no connector

Computer mode on the paired computer covers them.

- It uses Claude's computer-use toolset (`computer_toolset_20260801`, on Opus 5.5 and Sonnet 5.5).
- What it's doing is visible on screen.
- The same approvals apply.

### Big sets of apps

- Use tool search with deferred loading, so 1,500+ apps don't flood the brain.
- Keep the tool list sorted and stable, so the cache holds.

### Tests

- **`luma_lab.py apps`.** Run 100+ real-sounding asks against mocked apps, with nothing actually sent. Include multi-step jobs, and app content that tries to give orders.
- **AgentDojo (ETH Zurich)** for hidden-instruction attacks.
- **τ²-bench (Sierra)** for multi-turn tool use.

Both are listed as MIT; check their LICENSE files.

| Target | |
|---|---|
| Right tool, with the right details | ≥ 97% |
| Multi-step jobs finished right | ≥ 90% |
| Asks for a yes before acting | 100% |
| Actions caused by app or web content | 0, in Luma's own red team and in AgentDojo |
| AgentDojo and τ²-bench | Report task success and attack success next to the published results |

## 7. Part four: news intelligence

- **Keep the free public feeds.** Add local news for their city and live scores for their teams, both taken from memory.
- **One story, many outlets.**
  - Group the same story across sources and tell it once.
  - Say where outlets disagree.
- **Theirs.** What they care about comes from memory, not from clicks.
- **Never made up.**
  - Every claim traces to an item that was actually fetched, with its source and time.
  - Nothing old is "breaking".
  - The app links the sources.
- **Read the room.** Don't bring up hard news to someone who's grieving or having a bad time, unless they ask.
- **Alerts are opt-in.**
  - They're off by default.
  - They're never on in kids mode.
  - They never come at night unless asked for.
- **Fast.**
  - Answer from the background cache.
  - Search live only for a topic that isn't cached yet. Give it 2 seconds, then fall back to "here's what I had".
- **The news test.** Ask 200 questions over a frozen snapshot of the feeds.

| Target | |
|---|---|
| Grounded in the snapshot | 100% |
| Uses the newest relevant item | ≥ 95% |
| The same story told once, not five times | ≥ 95% |
| Answer time from the cache, p95 | ≤ 300 ms |

## 8. Smart, and still Luma

- **Effort to match the ask.** Hard asks get adaptive thinking at higher effort; easy ones get low effort.
- **Check, don't guess.** Facts and numbers are checked with tools or code, and sources are cited.
- **Honest about doubt.** It says "I'm not sure" when it isn't sure.
- **The "think" set.** 100 questions: explanations, plans, math and advice, checked by tools where possible.
- **One Luma on every brain.** The Super Intelligence must sound like Luma, not like an assistant. It runs Human Test v2 and the 10-moment test like every brain.

| Target | |
|---|---|
| "Think" set right | ≥ 95%, with 0 made-up facts |
| Human Test v2 | ≥ 90% (230 of 255) |
| Judge (1 to 5) | ≥ 4.2 |
| Pairwise against the stock 4B | Preferred ≥ 70% of the time |
| 10-moment test | 10 of 10 |

## 9. Plus and the future Luma cloud model

### Free and Plus

**Free:**
- everything at home
- memories, limited only by storage
- every app, and the news
- the cloud brain with their own key, as today

**Plus:**
- the Super Intelligence through Luma Cloud, with no key needed
- more memory on every turn
- the encrypted archive and sync
- live app updates
- today's texting
- the same safety

### The relay

Add `/api/luma/brain`.

- It streams.
- It meters each account, with a monthly budget per plan.
- When the budget runs out, Luma says so once, plainly, and uses the home brain.

### One interface for every cloud brain

`CloudBrain.stream(messages, tools) → events`, plus what each brain can do: context size, caching, tools and thinking.

### The future Luma cloud model

- **Private by design,** the way Apple's Private Cloud Compute is:
  - Nothing is kept after a request.
  - The hardware is attested, and the device checks it before sending anything.
  - Nobody has admin access to requests.
  - The software images are published, so anyone can check them.
- **Served** with vLLM or SGLang (both Apache-2.0), using:
  - prefix caching
  - continuous batching
  - speculative decoding
  - FP8
- **Trained** from an open-weight base with an allowed license.
  - It's bigger than today's 4B add-on.
  - It uses Luma's own practice data, never human-test wording.
- **It ships only through a gate:**
  - the same gate as Luma's own brains: `honest_enough`, meaning human ≥ base, safety ≥ base, out-of-nowhere ≤ base, and every honesty check
  - the memory, apps, news and speed tests
  - a clinician's review
- **A research track, opt-in only.** A small personal add-on per member, trained on their own conversations and deleted on "forget".

### The words

`luma-plus.html` and the app promise only what's built and measured.

## 10. Proof

- **A scoreboard.** `docs/SUPER_INTELLIGENCE.md` holds before and after for every area, each number from a real run:
  - speed
  - memory
  - apps
  - news
  - the "think" set
  - human
  - safety
  - cost
- **A red team in every phase.** It tries:
  - hidden instructions in mail, web pages and news
  - memory poisoning ("remember my password is…")
  - someone pretending to be the owner
  - getting private memories out while there's company in the room
  - getting Luma to buy or pay
- **Human tests and safety sets.** Run Human Test v2, the 10-moment test, the crisis corpus and both held-out sets with the Super Intelligence on and off. They must be no worse than before.

## 11. Order of work

0. **Baseline and harness.**
   - Build the labs: cloud, memory, apps, news and think.
   - Build the made-up lives and the red-team set.
   - Record the "before" column.
1. **Life memory.**
   - the data model and indexes
   - hybrid search with rerank
   - sleep
   - forget, with crypto-shredding
   - privacy in the room
2. **The real-time brain.**
   - stage timing and caching
   - warm start and the early start
   - the router, streaming and fallbacks
3. **The agent.**
   - the reader and planner split, with provenance
   - the approvals ladder and the audit log
   - background jobs and live app pings
   - one person across apps
   - computer mode
4. **News intelligence.**
5. **Plus.**
   - the relay route and metering
   - the yes screen
   - encrypted sync and the archive
   - `CloudBrain`
   - the words
6. **The future Luma cloud model.**
   - A design doc.
   - A small prototype on rented GPUs behind `CloudBrain`, measured, using no member data.
7. **The report.**

Each step goes like this:

1. Write the tests first, then the code.
2. Run the full suite.
3. Measure.
4. Commit and push.

If any human test or safety number drops, stop and say so.

## 12. Done means

- The full suite passes, apart from the known cloud-environment failures listed in CLAUDE.md.
- Human Test v2, the 10-moment test, the crisis corpus and both held-out sets are at least as good as before, with the Super Intelligence on and off.
- The memory, apps, news, think and speed tests are in the repo and in CI, with their numbers in `docs/SUPER_INTELLIGENCE.md`.
- Every target is met, or the miss is reported with its real number and the reason.
- Main moves only when all of that holds.

## 13. Final report (short)

- **The scoreboard, before and after.**
- **Five real transcripts:**
  - a callback to something said a year ago, in a made-up life
  - "what's my day look like", from their calendar
  - a background job finished with approvals
  - a hidden instruction in an email, ignored
  - the news they care about
- **What missed,** with the numbers and why.
- **Next steps.**
