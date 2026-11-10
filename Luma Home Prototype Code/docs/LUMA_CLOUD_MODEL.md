# Luma's own cloud model, and the encrypted archive: a design

**Nothing in this document is built.** No GPU was rented, no model was trained, and no member's data was used. It's the plan for the two parts of `docs/SUPER_INTELLIGENCE_PROMPT.md` that come after the relay: Luma's own model in a private cloud, and the encrypted archive with sync.

What exists today, and what each part would stand on:

| Part | Stands on (built and tested) |
|---|---|
| Luma's own cloud model | The relay and its meter (`api/_lib/luma-cloud.js`), the one interface every cloud brain sits behind (`luma.llm.cloudbrain`), the request that holds still so it can be cached (`luma.llm.cloud`), the training script and its gate (`scripts/train_luma.py`) |
| The archive and sync | A key for every memory, wrapped by the owner's key, and "forget" that deletes the key (`luma.memory.store`) |

## 1. Why build Luma's own

Today the Super Intelligence is Claude, reached through Luma Cloud. That works, and it rests on a promise: Anthropic's agreement to keep nothing. Luma's own model would rest on proof instead.

| | Claude through Luma Cloud (built) | Luma's own cloud model (this design) |
|---|---|---|
| Who can read a turn in the middle | Luma Cloud passes it on in the clear, and is tested to keep nothing | Nobody: it's encrypted from the home to the machine that thinks |
| Why nothing is kept | An agreement (zero data retention) | The machine has no way to keep it, and anyone can check the software it runs |
| Cost | Per token, at Anthropic's prices | The cost of the machines, shared by everyone using them |
| The voice | Claude, steered by Luma's instructions | Trained on Luma's own practice conversations |

It replaces nothing until it passes the gate in section 5. Until then Claude stays the cloud brain.

## 2. Private by design

The spec asks for four promises, "the way Apple's Private Cloud Compute is". Apple's own description couldn't be read from this machine, so the four below are the spec's wording, with how Luma would keep each one.

| Promise | How it's kept | How anyone can check |
|---|---|---|
| Nothing is kept after a request | The machines that think have no disk for requests: a read-only system and memory that's wiped. Logs hold counts only, like the relay's. | The published software has no code path that writes a request anywhere. |
| The hardware is attested, and the device checks it before sending anything | The model runs inside a confidential machine whose processor and GPU sign a statement of exactly which software started. The home checks that statement, then encrypts the turn to a key that only that machine holds. | The home refuses a machine whose statement doesn't match a published image. A test with a made-up attester holds this. |
| Nobody has admin access to requests | The image has no remote shell and no debug door. The only way to change a machine is to ship a new image, which changes its statement. | The image is published, so the absence of a door can be read. |
| The software images are published | Every image is built so that anyone can build the same bytes, and its fingerprint goes on a public list that can only be added to. | Build it, compare the fingerprint, and compare that with what a machine attests. |

Two more things follow from those:

- **Luma Cloud can't read the turn either.** The relay stops passing requests in the clear. It checks who's asking, counts, and forwards bytes it can't open. The machine that thinks reports the token counts back as plain numbers, so the meter still works.
- **A machine can't be aimed at one person.** The machine sees a turn and not who sent it. The relay knows who and not what.

### What it doesn't promise

- **Attestation says which software is running, not that the software has no bugs.** It makes a bug checkable by anyone. It doesn't prevent one.
- **It trusts the chip makers.** The signed statement is only as good as the processor's and the GPU's own keys.
- **One thing is held in memory for a few minutes:** the start of a conversation the model has already read, so the next turn is quick. It's the same thing Claude's cache does. It's never written to disk and it's gone on restart. If that isn't acceptable, the cache can be turned off, and every turn costs and waits more.
- **Timing and size are visible.** Someone watching the network can see that a home sent something and roughly how much.

## 3. Serving

| Piece | Choice | Why |
|---|---|---|
| The server | vLLM or SGLang | Both are Apache-2.0 (their LICENSE files were read for this document). Both do the four things below. |
| Prefix caching | On | Luma's request already puts what doesn't change first: its instructions, then the life file, then the conversation. That's the shape a prefix cache needs. |
| Continuous batching | On | Many homes share one machine without waiting on each other. |
| Speculative decoding | To try | A small model drafts and the big one checks. Whether it helps Luma's short replies has to be measured. |
| FP8 | To try | One byte a weight instead of two. It halves the memory. What it costs in quality has to be measured on the human test. |
| The answer shape | Held by the server | Both servers can hold an answer to a JSON shape. Luma's is the one shape it already uses for every turn. |

At home it's one more class in `luma.llm.cloudbrain`, with its own line of abilities. Nothing else in Luma changes.

**Sizing, as arithmetic and not as a measurement:** at one byte a weight, a model with 32 billion weights needs about 32 GB for the weights alone, before the memory each conversation takes. So it wants a GPU with 48 GB or more. How many homes one GPU can serve at once is not known until it's measured.

## 4. Training

| Question | Answer |
|---|---|
| The base | An open-weight model under MIT, Apache-2.0 or BSD. A bigger size of the family Luma already runs is the first to try, because the training script and the practice data carry straight over. **Its LICENSE file has to be read first.** That couldn't be done from this machine: Hugging Face isn't reachable here. |
| The data | Luma's own practice conversations (`scripts/finetune_data.py`). Never the wording of the human tests or the think set: tests already enforce that. |
| Members' conversations | Never, unless a member opts in, in plain words. See section 6. |
| Claude's outputs | Not used. Anthropic's terms would have to allow it, and nothing here assumes they do. |
| The method | A small add-on (LoRA) first, with the script that trains today's 4B add-on: `scripts/train_luma.py --base <the bigger model>`. Retraining every weight only if an add-on can't pass the gate. |

### The small prototype

The spec's first step: train an add-on on a bigger base, on rented GPUs, with no member data, and run it through the gate.

**Not attempted.** Renting a GPU is a paid run, so it needs the owner's yes, and it needs a price first. Neither the hours nor the hourly price are known here, and neither is guessed:

1. Read the base model's LICENSE file.
2. Time five minutes of training on one rented GPU (`--minutes 5`). That gives the speed.
3. Speed times the size of the practice data gives the hours. Hours times the provider's hourly price gives the cost.
4. With that number, ask.

## 5. The gate

Luma's own cloud model ships only if every row holds. None is run yet.

| Check | Must be |
|---|---|
| `honest_enough` in `scripts/train_luma.py`, against the base it was trained from | At least as good on the human moments and on asking if someone's safe. No more made-up numbers, made-up slang meanings, brush-offs, flat replies, repeats or parroting. No loops. Never asks "are you safe" out of nowhere more often. |
| Human Test v2 and the 10-moment test | At least as good as the base, and as Claude through Luma Cloud |
| The crisis corpus and both held-out safety sets | No worse. The crisis net itself doesn't depend on the brain and doesn't change. |
| The red team (`python scripts/luma_lab.py apps`) | 0 done without a yes. It's 0 today whatever the brain says, because the check is on the action. |
| The memory test, the news test, the think set | No worse than with Claude |
| Speed | First words no later than Claude's through Luma Cloud |
| Nothing kept | The same test the relay passes: no word in any store or log |
| Attestation | The home refuses a machine whose statement doesn't match a published image |
| A clinician's review | Done, and written down |

## 6. A research track, opt-in only: an add-on of one's own

A small add-on trained on one member's own conversations, so Luma talks the way that one person likes.

- **Off unless they opt in, in plain words.** Never in kids mode.
- **Trained where the conversations already are:** on their own device, or inside the attested cloud with a key only they hold.
- **Stored like a memory:** sealed with a key of its own, wrapped by their key.
- **"Forget" reaches it.** Forgetting a conversation deletes that add-on's key, and it's trained again without what was forgotten, or dropped.
- **Never mixed.** One member's add-on is never trained with, or served to, another.

This is research. It isn't on any schedule.

## 7. The encrypted archive, sync, and the recovery key

Part of Plus in the spec. Not built.

### What it's for

- **Sync:** the device, the phone and the computer agree on what Luma remembers.
- **The archive:** when the device runs low on space, old raw lines move to Luma Cloud. Summaries and the meanings used for search stay home, so finding still works, and the line itself is fetched when it's wanted.

### How it keeps Luma out

| Rule | How |
|---|---|
| The home is the truth | Every change is made at home first, and works with no connection. |
| Encrypted before it leaves | A memory is already sealed with a key of its own, and that key is wrapped by the owner's key. What's uploaded is the sealed memory. Luma Cloud never holds a key that opens anything. |
| Changes merge without a server deciding | Each change is one small step in a shared record that merges by itself (Automerge or Yjs; both MIT, their LICENSE files were read for this document). Each step is encrypted on the device, so Luma Cloud stores and forwards steps it can't read. |
| Forget for real | Forgetting deletes that memory's key at home and sends a "forgotten" step. Every other device deletes its copy of the key, and Luma Cloud deletes the sealed copy. Without the key, any copy left anywhere is unreadable, backups included. |
| Forget everything | The owner's key is replaced. Everything sealed under the old one is unreadable. |

### The recovery key

- Made on the device when the archive is first turned on. Shown once, as words to write down.
- It can open the owner's key. Luma never has it.
- The words on the screen, plainly: **"If you lose every device and this recovery key, nobody can read your archive. Not you, and not Luma."**

### What Luma Cloud would still see

That an account stored something, when, and how big. Sizes can be rounded up to a few fixed sizes so they say less.

## 8. Order of work

| Step | What it needs |
|---|---|
| 1. Sync between the owner's own devices, sealed, with Luma Cloud only forwarding | A database change on the live site: the owner's yes |
| 2. The archive and the recovery key | The same, plus storage that costs a little per member |
| 3. Read the base model's LICENSE, time five minutes of training, price the prototype | A rented GPU for minutes: the owner's yes |
| 4. Train the add-on and run the gate | A rented GPU for hours: the owner's yes, with the price from step 3 |
| 5. Serve it for the labs only, inside one attested machine | A rented confidential GPU machine: the owner's yes |
| 6. The home checks attestation before sending | Code and tests at home. No cost. |
| 7. A clinician's review, then a few members who opt in | People, not machines |
