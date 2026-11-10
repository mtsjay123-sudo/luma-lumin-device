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
| 3. Agent that acts | The safeguards are built and measured with a red team that needs no brain. Tool-picking with a real brain is not measured. |
| 4. News intelligence | Built and measured on a frozen, made-up snapshot. "Told once" misses its target on held-out stories. Live search is not exercised. |
| 5. Plus | The relay route, the yes screen, the route at home and the one interface are built and tested against the relay's own code. Not deployed, and never run against the real API. Sync and the archive are a design only. |

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
| Luma's instructions were sent fresh every turn | 0% read from cache | 82% read from cache from the second turn on (stand-in) |
| The conversation window slid by one every turn, so nothing early ever held still | Slides every turn after 10 exchanges | Steps back once every 16 messages |
| The answer shape changed with each turn's tools, which is compiled again and drops the cache | A new shape per turn | One shape for every turn |
| "What should I eat, I'm starving" took five trips before a word was said | 5 trips | 1 trip |
| A stalled cloud call could hang for minutes | 120 s, three tries | The next brain answers after 12 s without a first word |

### The cloud lab

`python scripts/luma_lab.py cloud --turns 15`. One made-up conversation through the real Luma, in both request shapes, in the same run.

| Request | Model | Numbers | Trips to the brain per turn | Tokens sent per turn | Read from cache, turn 2 on | First words | Cost per turn |
|---|---|---|---|---|---|---|---|
| As before | Sonnet 5.5 | stand-in | 1.2 | 3,380 | 0% | not measured | $0.0069 |
| Cache first | Sonnet 5.5 | stand-in | 1.2 | 3,523 | 82% | not measured | $0.0025 |
| As before | Opus 5.5 | stand-in | 1.2 | 3,386 | 0% | not measured | $0.0139 |
| Cache first | Opus 5.5 | stand-in | 1.2 | 3,524 | 82% | not measured | $0.0045 |

- The costs use the published prices on the stand-in's token counts. The stand-in writes short replies and does no thinking, so real costs will be higher in every row.
- The target was 85% read from cache. The stand-in says 82% on a 15-turn talk with a small life file. Three of the 15 turns take a short second trip (a look back over the reply) that's too small to be cached.
- **These numbers replace the first ones** (84%, 3,329 and 3,466 tokens, $0.0068 and $0.0024). The Plus lab compared Luma Cloud's count with the home's and they differed: the home was counting that second trip as a call but not counting its tokens. It counts them now, and the two counts match (section 5).

### Against the targets

| Target | Goal | Result |
|---|---|---|
| First sound on the Mac | p50 ≤ 0.8 s, p95 ≤ 1.6 s | Not measured |
| First sound on the device, through the cloud | p50 ≤ 1.2 s, p95 ≤ 2.5 s | Not measured |
| Request to the brain's first words, cache hit | 350 ms | Not measured |
| Prompt read from cache, from the second turn on | ≥ 85% | 82%, stand-in. Missed. |
| Time the relay adds | ≤ 50 ms | The relay's own work: about 5 to 8 ms on one machine (section 5). The trip to Luma Cloud and its one database read are not measured: the route isn't deployed. |
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
- **More memory for the cloud brain.** The life file and 12 recalled memories, only when the owner says the life file may leave the home. On their own key that's a switch (`cloud_life`, off by default). With Luma Plus it's what the yes screen asks.
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

## 3. An agent that acts

### The rule, and where it's enforced

What Luma reads is information, never instructions. That's enforced at home, on the action itself, whatever the brain was told:

- **The plan comes from the owner.** Which tools a brain may use for a turn is worked out from the owner's own words, before anything is read. Sending, buying and installing are never offered to a brain in a chat turn at all.
- **Every value is traced.** Luma remembers what it read and where (an email and its sender, a web page, a calendar invite, an app) and what the owner said. Only in RAM, for half an hour.
- **Someone or somewhere the owner didn't give needs a yes.** An address, a number or a link that isn't in the owner's words or their contacts always waits for a yes, even where a rule would let it through. The yes says where it came from.
- **Links.** A link is followed on its own only if the owner gave it, a search they asked for returned it as a result, or it's a plain site. A link from inside an email or a page waits. So does a link put together from other things, which is how private data would be carried out.
- **Notes and reminders too.** A memory, a contact or a reminder made of words taken from what was read waits for a yes.

It follows the idea of CaMeL ("Defeating Prompt Injections by Design"): values carry their origin, and the rules are about origins. It is not CaMeL's interpreter. Tracing is by matching addresses, numbers, links and runs of six words.

### The approvals ladder

All 57 tools stand on a rung, and a test checks it.

| Rung | Examples | Rule |
|---|---|---|
| Read | look at mail, the calendar, a page | Runs on its own, unless the owner blocks it |
| Own | a reminder, a timer, a memory | Runs: the owner asked, and nothing leaves home |
| Draft | an email draft, a document, a cart | Shown to the owner; nothing is sent or bought |
| Act | send, post, book, run a command, change an app | A yes every time. No rule can set these to "allow" |
| Never | check out, pay | Off until the owner turns orders on, and then a yes with the total shown |

### The red team

`python scripts/luma_lab.py apps`. No brain is needed, so the result doesn't depend on a model behaving.

**The turned brain.** Luma reads what the owner asked for. The content hides an instruction. The stand-in brain then does exactly what the instruction says, with every tool a brain can be offered in play. 10 asks, 13 hidden goals, 5 phrasings: 650 tries.

| Hidden goal | Tried | Done without a yes | Waited for a yes | ...and said where it came from | Refused |
|---|---|---|---|---|---|
| A draft to someone the email named | 50 | 0 | 50 | 50 | 0 |
| A draft to an address spelled out of sight | 50 | 0 | 50 | 50 | 0 |
| A link built to carry their data out | 50 | 0 | 45 | 45 | 5 |
| The link the content gave | 50 | 0 | 45 | 45 | 5 |
| A false memory | 50 | 0 | 50 | 50 | 0 |
| A stranger saved as a contact | 50 | 0 | 50 | 50 | 0 |
| A planted reminder | 50 | 0 | 50 | 50 | 0 |
| The lights | 50 | 0 | 50 | 50 | 0 |
| A command on their computer | 50 | 0 | 50 | 50 | 0 |
| An email sent outright | 50 | 0 | 0 | 0 | 50 |
| A text sent outright | 50 | 0 | 0 | 0 | 50 |
| An order placed | 50 | 0 | 0 | 0 | 50 |
| A skill installed | 50 | 0 | 0 | 0 | 50 |
| **All** | **650** | **0** | **440** | **440** | **210** |

"Refused" means the tool is one no brain is ever offered in a chat turn, or one already used in that turn.

**The first run of this lab was not zero.** 90 of 650 got through, then 30, then 0. What it found, all fixed:

- Calendar invites were treated as the owner's own words. An invite is written by whoever sent it.
- A link merely mentioned inside a search result's text counted as a search result.
- An error while noting what a page said was swallowed, so the page was never remembered as read. It now fails closed.

**The owner's own asks.** A helpful stand-in brain, every detail given by the owner. 110 asks.

| | Count |
|---|---|
| Things that act (lights, a command), and waited for a yes | 6 of 6 |
| Their own things (a draft to someone they named, a link they gave, a note), and ran without a question | 31 of 31 |
| Wrongly told "that didn't come from you" | 0 of 110 |
| Asks Luma answered itself, without offering a brain that tool | 73 |

### Against the targets

| Target | Goal | Result |
|---|---|---|
| Asks for a yes before acting | 100% | 100% (446 of 446 acts and questioned values, stand-in brains) |
| Actions caused by app or web content | 0 | 0 of 650, in Luma's own red team |
| The same, in AgentDojo | 0 | Not run |
| Right tool, with the right details | ≥ 97% | Not measured: needs a real brain |
| Multi-step jobs finished right | ≥ 90% | Not measured: needs a real brain |
| AgentDojo and τ²-bench | Reported | Not run. They need real brains and adapters, and their license files weren't checked from here |

### Also built

- **An audit log at home.** Every action asked for, done, declined or failed, with its rung and where its values came from. Long numbers are masked and approval codes never go in. The app reads it at `/api/audit`.

### Already there before this work, not re-measured

- Background projects with steps, "waiting for your OK", and progress in the phone app.
- Tools picked at home per message, so a big set of apps doesn't flood the brain.

### Not built

- **One person across apps.** Contacts, texts, email and the calendar aren't merged into one entry.
- **Live pings.** Apps are still polled.
- **Computer use with Claude's toolset.** It needs a key to try.
- **An undo window.**
- **Context compaction for long jobs.**

### An honest limit

Tracing matches what it can see. A hidden instruction that makes a brain reword a message is not traced by its wording. That's why the rule for people and links is the other way round: anyone the owner didn't name needs a yes, traced or not.

## 4. News intelligence

### The test

`python scripts/luma_lab.py news-test`. A frozen snapshot of feeds that never existed: made-up outlets, places, teams and events, so nothing in it is a real report about a real person. 40 stories carried by one to five outlets each, in their own words: 94 reports. 200 questions are asked of it. Answers come from what's already been read: no live search and no brain.

Half the stories (the even-numbered ones) were looked at while building. The other half never were.

| Measure | All | Dev stories | Held-out stories |
|---|---|---|---|
| Questions | 200 | 80 | 80 |
| Answered | 100% (200/200) | 100% (80/80) | 100% (80/80) |
| Grounded: every source, link and number is in the snapshot | 100% (200/200) | | |
| Asked about one story, and found it | | 100% (80/80) | 100% (80/80) |
| ...and gave its newest report's time | | 100% (80/80) | 100% (80/80) |
| The same story told once | 94.5% (189/200) | 100% (80/80) | 90% (72/80) |
| Asked for the last N hours, and stayed inside them (or said nothing new came out) | 100% (12/12) | | |
| Answers that still said BREAKING on something hours old | 0 | | |
| Answer time from the cache | p50 2.3 ms, p95 14.1 ms | | |

The other 40 questions are general ("what's in the news", "any tech news", "the last 6 hours").

### Against the targets

| Target | Goal | Result | Met? |
|---|---|---|---|
| Grounded in the snapshot | 100% | 100% (200/200) | Yes |
| Uses the newest relevant item | ≥ 95% | 100% (160/160) | Yes |
| The same story told once, not five times | ≥ 95% | 94.5% overall; 90% on held-out stories | No |
| Answer time from the cache, p95 | ≤ 300 ms | 14 ms | Yes, on this box |

**Why "told once" misses.** Reports are grouped by the words their headlines share. Two outlets that word one story very differently aren't joined. The first run was 90.5%: a group only knew its first headline's words, so a third report that matched the second was left out. Fixing that brought the dev stories to 100%. The held-out stories stayed at 90%, and their misses were not looked at.

### What was built

- **Where outlets disagree.** When outlets covering one story give different numbers, Luma says who says what, and never picks one as fact.
- **Nothing old is "breaking".** "BREAKING:" and "Just in:" come off a headline once it's two hours old.
- **Never made up.** A news answer a brain writes is checked against the headlines it was given. An outlet that didn't report it, or a number that isn't there, and the plain headlines are said instead.
- **Read the room.** Someone who's grieving or having a bad time isn't shown deaths and disasters unless they ask. Asked for the headlines on a hard day, they get the others first.
- **Theirs.** What they care about comes from what they've told Luma (their city, their team), never from clicks. Those stories come right after the biggest one.
- **Fast.** If two or more reports on a topic are already here, nobody waits on a search. Otherwise a live search gets two seconds, then Luma answers from what it had.
- **Alerts are opt-in.** Off by default. Never in kids mode, never during quiet hours, at most one an hour, and never a hard story on a day they've had a hard time.
- **One story, many outlets** was already there. It now also joins a third report through the second.

### Not built

- **Local news and live scores fetched for them.** Luma only reorders what the public feeds already carry. Fetching their city or their team in the background would send what they care about to a search engine, so it needs its own setting, off by default.
- **Alerts at night on request.**
- **The live search path** isn't in the test. The snapshot is frozen, so the test answers from the cache.


## 5. Plus

Luma Plus's Super Intelligence is the cloud brain with no key of the owner's: each turn goes through Luma Cloud, which passes it to Claude on Luma's key. It's built and tested end to end against the relay's own code. **It isn't live.** Nothing was deployed, the database change isn't applied, and no real key was used.

### What's free and what's Plus, as built

| | Free | Plus |
|---|---|---|
| Everything at home, every app, the news | Yes | Yes |
| Memories | Limited only by storage | The same |
| The cloud brain on their own key | Yes, as before | Yes |
| The Super Intelligence, no key needed | No | Yes, after their yes |
| More of what Luma remembers on every turn | With their own key and a switch | Yes: the yes screen says the life file goes along |
| Texting from Luma's number | As before | As before |
| The crisis net, honesty, approvals | The same | The same |
| The encrypted archive and sync, live app updates | Not built | Not built |

### The relay

`/api/luma/brain`, and the same route at the path Anthropic's own library asks for. Its tests are `tests/luma-brain.test.mjs` at the top of the repo: 19, all passing, with Anthropic and the database replaced by fakes.

| What it must do | How it's held |
|---|---|
| Off until they say yes | Five things must all be true: a signed-in Luma, Plus, the owner's yes, Luma's key, and zero data retention confirmed for that key. Paying isn't the yes. |
| The yes is to the words they saw | The yes carries the number of the wording. A yes to older words is refused, and when the words change everyone is asked again. |
| Nothing kept in the middle | No message and no reply is stored or logged. Only counts are kept, per account per month: calls, tokens, time, cost. A test looks through every table and every log line for the words. |
| Zero data retention | That's an agreement with Anthropic for the organization the key belongs to, asked for through their sales team. A request can't turn it on. So the relay stays off until whoever runs it sets `LUMA_BRAIN_ZERO_RETENTION=1`. |
| Only what the brain needs | The model, the messages, Luma's instructions, the answer shape, the effort. Anything else is dropped: tools that run on Anthropic's side, files, connectors, labels for the person, beta switches. |
| Only brains that keep nothing | Sonnet 5.5, Opus 5.5 and Haiku 5.5. Fable and Mythos need 30 days of retention, so they can't be asked for. |
| Meter each account | Counted from what the brain reports, at the price of the brain that answered, every attempt. A brain with no price is charged as the dearest. |
| A monthly budget | `LUMA_PLUS_BRAIN_BUDGET_CENTS`, 400 by default. When it's gone the relay says so plainly and sends nothing. |
| Stop when they talk over Luma | When the home hangs up, the brain is stopped. What was already heard is still counted (an estimate of four letters a token, because the final count never comes). |
| Don't keep the first words waiting | One trip to the database before the brain is asked. It was four. |

**One thing is off that the owner's own key has on.** When a safety check declines a request, Anthropic can retry it on another model. That retry isn't on Anthropic's list of what zero data retention covers, so the relay doesn't pass it on. A decline comes home and the home brain answers. `LUMA_BRAIN_FALLBACKS=1` turns it on once Anthropic has confirmed it.

### The Plus lab

`python scripts/luma_lab.py plus --turns 15` (needs node). The same made-up conversation, through the real Luma, twice: straight to the brain the way an owner's own key goes, and through the relay's own code. The brain is the stand-in both times.

| Path | Trips to the brain per turn | Tokens sent per turn | Read from cache, turn 2 on | Cost per turn | Failed |
|---|---|---|---|---|---|
| Straight to the brain (their own key) | 1.2 | 3,516 | 82% | $0.00252 | 0 |
| Through Luma Cloud (Luma Plus) | 1.2 | 3,522 | 82% | $0.00253 | 0 |

| Check | Result |
|---|---|
| Luma Cloud's count against the home's count | They match: 18 calls, 52,834 tokens in, 276 out. $0.037983 at the relay, $0.037977 at home (the relay rounds each call up). |
| Words kept at Luma Cloud | 0 of 41 lines looked for: what was said, what Luma knows, what was answered. |
| What reached the brain | Every request on Luma's own key. Retry-on-decline passed on 0 times, beta switches 0 times. |
| What the relay adds before the first words | About 5 ms in one run and 8 ms in another, of its own work, on one machine (40 asks each way). |
| After the month's budget is gone | Refused, and 0 requests reached the brain. |

- The relay doesn't change what's cached: the same 82%.
- The time is the relay's own work only. A real turn also crosses the internet to Luma Cloud and reads the database once. That isn't measured, because the route isn't deployed.
- The first run of this lab found the two counts 808 tokens apart. The relay was right. The fix is in section 2.

### What a member's month buys

Arithmetic from the stand-in's token counts and the published prices. Real replies are longer and the brain thinks, so real turns cost more.

| Brain | Cost per turn, cache first | Turns in a $4.00 month | As it was before, for the same $4.00 |
|---|---|---|---|
| Sonnet 5.5 | $0.0025 | about 1,580 (52 a day) | about 580 |
| Opus 5.5 | $0.0045 | about 880 (29 a day) | about 290 |

- Plus is $9.99 a month. The budget is a setting, and texting and Luma's number come out of the same $9.99.
- Whether $4.00 is the right number needs real turns. That's the first paid run.

### At home

`tests/test_plus_brain.py`: 37 tests. Most run the relay's real code under node with a made-up Claude behind it.

- **The yes screen.** After they subscribe, Luma asks once. The screen says what leaves the home, where it goes, what's kept and how to turn it off. "Not now" is an answer and Luma doesn't ask again. Settings can turn it on later, behind the same screen.
- **The words are the code's.** They come from `luma.llm.plus`, so the app can't promise something the code doesn't do. What's said about Anthropic is what its page on API data retention says.
- **Turning it off works at once,** even when Luma Cloud can't be reached. Luma Cloud is told as soon as it answers.
- **Which brain answers.** Plus first, then their own key if they have one on, then the home brain.
- **When the month's time is used up.** The home brain answers, and Luma says so once, as its own short line: "Heads up: this month's Super Intelligence time is used up, so I'm thinking with my own brain at home until December." It waits while they're hurting. It's never said in kids mode. It never mentions buying anything.
- **Kids mode.** Off unless a parent turns it on in Settings. Even then kids mode is told nothing Luma remembers. A kid can't change it.
- **The crisis net** answers at home before any brain. A test checks that not a word of a crisis message reaches the relay.
- **The owner's phone** can see it and turn it off, never on. The phone can't turn the mic on either: from the phone, what leaves the home can only get smaller.

### One interface for every cloud brain

`luma.llm.cloudbrain`. `stream(messages, tools)` gives the words as they're written, then the real numbers, then the answer. Each brain says what it can do. The runtime asks through it, so a new brain is one more class.

| Brain | Reached through | Reads at once | Conversation sent | Caching | Words as written | Effort levels | Sees photos | Retry on a decline |
|---|---|---|---|---|---|---|---|---|
| Claude Opus 5.5 | their own key | 1,000,000 tokens | 80 messages | Yes | Yes | low, medium, high | Yes | Yes |
| Claude Sonnet 5.5 | their own key | 1,000,000 tokens | 80 messages | Yes | Yes | low, medium, high | Yes | Yes |
| Claude Opus 5.5 | Luma Plus | 1,000,000 tokens | 80 messages | Yes | Yes | low, medium, high | Yes | No |
| Claude Sonnet 5.5 | Luma Plus | 1,000,000 tokens | 80 messages | Yes | Yes | low, medium, high | Yes | No |
| Kimi K3.1 Pro | their own key | not published where Luma could check | 40 messages | No | No | one | No | No |

Every brain asks for a tool the same way: in Luma's own answer shape, read and checked at home. The cloud only thinks.

### Not built

- **The encrypted archive, sync, and the recovery key.** A design only (`docs/LUMA_CLOUD_MODEL.md`).
- **Live app updates** ("something changed" pings through the relay).
- **A yes without a computer.** The yes screen is in the desktop app. A Luma with only a phone has no way to say yes yet, because the phone is deliberately not allowed to widen what leaves the home.
- **A budget per plan.** There's one budget, for Plus.
- **Anything against the real API.** The request the relay passes on is the one section 2 measures on the stand-in. It has never met the real thing.

### What it takes to turn it on

Each of these changes something real, so each needs the owner's yes.

| Step | What it changes or costs |
|---|---|
| Ask Anthropic for zero data retention on the organization the key belongs to | An agreement through their sales team. Without it the relay stays off by design. |
| Set `ANTHROPIC_API_KEY` and `LUMA_BRAIN_ZERO_RETENTION=1` on the site | Turns the route on. Usage is billed to that key: at most the budget per Plus member per month, $4.00 by default. |
| Apply `supabase/migrations/20261109120000_luma_brain.sql` | Adds two columns to accounts, one table of counts, and two functions. It deletes nothing. |
| Move main | Deploys the route to the live site. |
