# Storage: like the storage page on a phone

Everything Luma keeps for someone lives on their device, sealed. This page says how much fits, what happens when it
runs out, how room comes back, how the database looks after itself, and what the cloud's one job is.

No brain is involved in any of it. It works the same on the $250 device, a Mac and a PC.

## What's built

| What | Where | Checked by |
|---|---|---|
| How much is used, how much fits, how much is left | `memory/storage.py`: `room()` | `tests/test_storage.py` |
| What's using the room, by kind: memories, chats, things Luma made, the diary, news, the browser's cache, everything else | `storage.usage()`; `Store.sizes()` | `tests/test_storage.py` |
| The biggest single things, each deletable by itself | `storage.biggest()`, `storage.remove()` | `tests/test_storage.py`, `tests/test_companion.py` |
| Quick ways to make room (old chats, old files, news, the cache, the diary) | `agent/memory_folder.py`: `space()`, `clean()` | `tests/test_memory_folder.py` |
| Forgetting memories: one, a kind, or the old ones | `memory_folder.forget()`; `Store.delete()` | `tests/test_memory_folder.py`, `tests/test_life_memory.py` |
| Deleting gives the room back to the device, for real | `Store.compact()`, `storage.tidy()` | `tests/test_storage.py` |
| The database checks itself and clears what was left behind | `Store.health()`, `Store.repair()` | `tests/test_storage.py` |
| A full device: nothing new is kept, nothing new is made, and Luma says so | `Agent.remember_fact`, `_keep_line`, `_room_to_make`; `storage.CANT_KEEP`, `CANT_MAKE` | `tests/test_storage.py` |
| Luma says "almost out of room" once, and "out of room" once | `Agent._storage_notice` | `tests/test_storage.py` |
| The storage screen on the phone and the computer | `GET /api/storage`; `control/web/phone/phone.js`, `control/web/desktop/desktop.js` (`openRoom`) | `tests/test_companion.py`; walked in a browser |
| The same screen away from home, sealed | `integrations/phone_app.py` (`storage`, `remove`); `storage.compact()` | `tests/test_storage.py` |
| The owner's own cap ("let Luma use up to 5 GB") | `storage.set_cap()`; `POST /api/storage/cap` | `tests/test_storage.py` |

## How much fits

The limit is the device's own storage. There's no count of memories to buy past.

- **Used** is what Luma keeps: the database, the files it made, the browser's cache. Room that deleting left inside
  the database counts as room again, straight away.
- **What fits** is what's used plus what's free on the drive, less 256 MB kept free so the device keeps working.
- **The owner's cap**, if they set one, is the limit instead when it's smaller.
- **Luma itself** (its brain and voices) is counted apart, the way a phone counts its system.

## The three states

| State | When | What Luma does |
|---|---|---|
| ok | There's room | Nothing |
| nearly | Under 200 MB left, or nine tenths of a cap used | Says so once, at a calm moment: "Heads up: I'm almost out of room..." |
| full | Nothing left | Keeps no new memories and makes no new files, and says so plainly when that happens |

**Full means full**, like a phone that can't take a photo. Asked to remember something, Luma says "I'm out of room on
this device, so I can't keep that yet. Make room in the Luma app, then tell me again." It never says "got it" for
something it didn't keep.

**What's never cut.** The conversation itself goes on. So do check-ins after a hard day and the safety net. A full
device still asks someone how they are tomorrow.

**How it's said.** Once for "almost", once for "out". It's news, never a pitch. It waits while they're hurting or
while Luma is talking, and it's never said in kids mode (rules 3 and 4 in `CLAUDE.md`). When there's room again it's
forgotten, so filling up a second time is news a second time.

## Getting room back

Nothing is ever deleted unless the owner chooses it.

1. **Quick ways**: chats older than 30 days, files Luma made over 30 days ago, the news it has read, the browser's
   cache (sign-ins stay), the diary.
2. **One thing at a time**: the biggest chats and files, biggest first.
3. **Memories**: one, a whole kind (People, Dates, Places...), or everything older than six months. Forgetting a memory
   forgets its key, what it meant and what was written from it (rule 6).

After any of these the database hands the freed pages back to the device (`Store.compact()`), so the file on the disk
is smaller, not just emptier. It's cheap: only the freed pages are touched. A database made before this is rewritten
once, the first time, to switch it over.

## The database looking after itself

- `Store.health()` asks SQLite whether the file reads back whole, and looks for anything left behind: a key with no
  record to open, or a meaning with no memory.
- `Store.repair()` clears what was left behind, rebuilds the indexes and gives the spare room back. It never touches a
  record that still has its memory.
- Deleted content is overwritten (`secure_delete`), and a forgotten memory's own key is destroyed, so no copy opens
  again. A test reads the raw file and checks the words are gone.
- The storage screen shows the check every time it opens: "Checked just now. All good."

## The cloud's one job

**Luma thinks at home.** The cloud brain is parked: no brain in the cloud answers anything, with Luma Plus or with
the owner's own key (`brain.cloud_allowed()`, off unless `LUMA_CLOUD_BRAIN=1`). Everything it needs is still in the
code and still tested, so it can come back the day it's wanted. `tests/test_home_brain_only.py` checks that nothing
reaches it.

**The cloud's one job is more room.** It isn't open yet, so Luma doesn't offer it: asked "can I buy more memory?", it
says there's nothing to buy and shows how to make room. `storage.more()` is the one place that decides, and it says
yes only when Luma Cloud's account answer carries `storage.available`.

What it has to be before it opens:

| Rule | What that means here |
|---|---|
| Off by default, on only with the owner's yes (rule 6) | A yes screen with its own words (what leaves, where it goes, what's kept, how to take it back), like the brain's had. Paying isn't the yes. |
| Luma Cloud can't read it | Things are sealed on the device before they leave, with a key that never does. Luma Cloud holds ciphertext and counts. |
| Forget means forget | Forgetting a memory at home deletes its sealed copy too. Taking the yes back brings everything home or deletes it, the owner's choice. |
| What moves | The heavy, old things first: chats, files, the diary. What Luma knows about someone stays at home, so Luma is the same Luma offline. |
| Nothing bought without a yes (rule 5) | The price is shown, the owner says yes, and the plan can be left any time. |

None of that is built or deployed. Before any of it is, the owner says what it costs and says yes.

## Not done

- **More room in Luma Cloud.** Designed above, not built.
- **Photos and video.** Luma doesn't keep them yet, so they aren't on the bar.
- **A device that fills up with other people's files.** On a shared computer the drive can fill for reasons that
  aren't Luma's. Luma then says it's out of room, which is true, but can't make room it didn't use.
