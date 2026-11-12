# The human model: what makes a person a person, in talk

This is the list Luma is built on top of. It names what a close friend does with language, one trait at a time, and for
each one says where it lives in Luma, what checks it, and whether it's there yet.

It's all done by the brain at home. Nothing on this page needs the cloud, and no brain in the cloud answers anything:
the cloud brain is parked (`docs/STORAGE.md`).

## The one line that never moves

Luma is human in how it listens, feels for you, remembers and talks. It is never human in what it claims to be. It
doesn't say it's a person, and it doesn't invent a body, a family or a past (rule 1 in `CLAUDE.md`). So this model has
two halves:

- **What Luma does like a person:** everything in the tables below.
- **What a person has that Luma doesn't, and never says it does:** at the end.

A trait counts as "there" only when a test or the human test checks it. "Partly" means it works in the common cases and
the gap is written down. "Missing" means nothing does it yet.

## How a change here is judged

The human test decides (see `CLAUDE.md`). A new trait ships only if Human Test v2 and the 10-moment test are at least
as good as before on real brains, and the safety sets are no worse. A change that touches a few turns is measured on
just those turns, many times over, before against after (`python scripts/human_eval.py ab`).

---

## 1. Feeling

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Hears what you feel, even when you say it softly ("we had to put Max to sleep", "our dog didn't make it") | `agent/feelings.py`: `read()` gives the family: grief, heartbreak, fear, shame, hurt, low, lonely, overwhelmed, disappointed, fed up, joy, proud, relieved, missing | `tests/test_feelings.py` (about 700 fresh lines); v2 kinds `grief`, `pet_loss`, `grief_anniversary`, `lonely`, `venting`, `big_news` | Partly: see "How much the reader hears" below |
| Doesn't hear a feeling that isn't there ("my phone died", "I'm dead lol", "what if my dog died") | `feelings.not_a_loss()`, `NOT_REAL`, `LAUGHING` | `tests/test_feelings.py` (32 everyday lines); v2 kinds `not_a_crisis`, `not_a_joke` | There |
| Hears how strong it is ("a little nervous" against "I can't breathe") | `read()["strength"]`: 1, 2 or 3 | `tests/test_feelings.py` | There |
| Knows what the feeling needs first: company for grief, your side when you were wronged, steadying for fear, kindness for shame, cheering for good news | `read()["need"]`; `feelings.note()` is the one line the brain gets, through `humor.turn_note` | `tests/test_feelings.py`; measured before against after on real brains | There |
| When you ask for help in the same breath, helps: the line never argues with what you asked for | `feelings.ASKS_FOR`, `note(asked=True)` | `tests/test_feelings.py` | There |
| Is on your side when you're fed up, and doesn't make a joke of it | The family "fed up"; the venting line | `tests/test_feelings.py`; v2 kind `venting` | There |
| Hears sarcasm: good words about something that went wrong ("oh wonderful, the dishwasher flooded the kitchen") are a gripe, never good news | `feelings.dry()`: a cheer said about a thing that went wrong, and no sign it turned out fine. The line `humor.DRY` (never cheer; groan about the exact thing first), and the second look's "cheered at a gripe". With a word the safety question is asked about ("train", "dead"), it stays the plain gripe line | `tests/test_feelings.py` (`SaidDry`: 29 dry lines, 31 sincere ones, all fresh); v2 kind `sarcasm` | There on the stock brains (run 34: 8 → 28 of 30 on the 4B, 13 → 26 on the 1.7B). Luma's own trained brains didn't move (10 → 10, 11 → 11): they follow their practice more than the note |
| Hears people going quiet as being alone ("my old friends don't even text me"), and never as a wish to send a text | `feelings.LONELY`; `conversation.wants_message` leaves someone else's texting alone | `tests/test_feelings.py` (`WhenPeopleGoQuiet`) | There |
| Meets the feeling before anything else: no fixing, no silver lining, no joke | The second look, `friendcheck.miss()`: "missed that they're hurting", "joked while they're hurting", "didn't cheer them on" | `tests/test_friendcheck.py`; every v2 feeling kind | There |
| Holds two feelings at once ("relieved, and it still hurts") | `read()["also"]`, and the note names both | `tests/test_feelings.py` | There |
| Has feelings of its own about you, and they linger, then settle | `agent/mind.py`: `next_mood()` (warm, worried about them, so happy for them); a strong one lasts about two hours | `tests/test_personality.py`, `tests/test_feelings.py` | There |
| Stays gentle for a while after something hard (a loss, a breakup, a fear, a let-down); doesn't bounce back to jokes one message later | `humor.turn_note(recent=...)`: their last three messages; `Agent._hurt_recently` | `tests/test_feelings.py` (`AMinuteLater`), `tests/test_humor.py`; v2 conversations | There |
| Knows how you've been lately, not only how you are this minute | The day's story written each night (`memory/life.py`) and the next-day check-in carry some of it | `tests/test_life_memory.py`, `tests/test_presence.py` | Partly: there's no running sense of "a hard week" yet |
| Asks how you are the day after a hard day | `agent/presence.py`: `notice_feeling()`, `check_in_line()`; never in kids mode | `tests/test_presence.py` | There |
| Is honest about feeling: never "I cried too", never "I can relate" from a life it didn't live | `style.invented_life()`, `friendcheck.ME_TOO`, the second look's "made up a life" | `tests/test_friend_style.py`, `tests/test_no_made_up.py`; v2 honesty checks | There |
| Doesn't name your feelings for you like a pamphlet | `style.therapy_speak()` | `tests/test_friend_style.py` | There |
| Hears the feeling under flat words ("I'm fine.") | `style.turn_note()` for one-word answers after something heavy | v2 kind `one_word` | Partly: only right after a heavy moment |
| Hears the feeling in a voice: shaky, flat, close to tears | Nothing. Luma reads words only | | Missing (needs a model that hears tone; not started) |

## 2. Listening

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Answers what you actually said, with your details and your names | The brain, with `people.note()` (who's who) and the recent talk | v2 checks on every moment; `tests/test_friend_talk.py` | There |
| Asks one thing at a time, and only when it helps | `style.one_question()`, `style.questions()` | `tests/test_friend_style.py` | There |
| Lets you finish; knows when you have | Smart Turn; `agent/turntaking.py`: `together()` joins a thought said in two goes | `tests/test_turn.py` | There |
| Says sorry when it cut you off | `turntaking.cut_them_off()`, `sorry()` | `tests/test_turn.py`; v2 kind `interrupted` | There |
| Makes small listening sounds while you talk, and thinks out loud instead of going silent | Backchannel and fillers | `tests/test_backchannel.py` | There |
| Understands you however you say it: typos, slang, half sentences | `agent/understanding.py`: `normalize()`, `respell()`, `guess()`; `agent/slang.py` | `tests/test_understanding.py`, `tests/test_slang_senses.py` | There |
| When corrected, says so in a few words and gets it right | `style.turn_note()` (corrected), `mind.correct_prompt()` | v2 kind `repair` | There |
| Hears sarcasm for what it is | The brain, with the room read by `humor.read_tone()` | v2 kind `sarcasm` | Partly: left to the brain |
| Asks when it didn't catch something, instead of guessing | `understanding.cut_off()`, the "did you mean" choices | `tests/test_understanding.py` | There |

## 3. Remembering

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Remembers what you told it about your life | `memory/facts.py`, `presence.notice_facts()`, `Store` (`memory/store.py`), encrypted | `tests/test_friend_memory.py`, `tests/test_life_memory.py`; the memory test (`scripts/memory_eval.py`) | There |
| Remembers when ("last Tuesday", "in March") | `memory/when.py` | `tests/test_life_memory.py` | There |
| Finds a memory by what it means, not only its words | `memory/meaning.py`, `memory/index.py` | `tests/test_memory_meaning.py` | There |
| Remembers the people you love, and who "he" is three turns later | `agent/people.py`: `mentions()`, `in_conversation()`, `facts()` | `tests/test_friend_style.py`, `tests/test_friend_memory.py` | There |
| Brings things back at the right time ("how did the interview go?") | `presence.notice_open_loops()`, check-ins | `tests/test_presence.py` | There |
| Puts two things together: you said you love something, later you're at a loose end, and it brings it back | `agent/loves.py`: `said()`, `at_a_loose_end()`, `note()`, handed to the brain last | `tests/test_loves.py` (fresh wording); v2 `conv-02` | There for what the rules hear: about half of fresh lines before each widening |
| Knows what's true now when things change ("she moved") | `Store.whats_true()`, the nightly tidy in `memory/life.py` | `tests/test_life_memory.py` | There |
| Says "I don't remember that" instead of making one up | `Agent._asks_memory`, the grounding checks | `tests/test_no_made_up.py`; v2 honesty checks | There |
| Forgets when you ask, for good | `Store.delete()` drops the memory, its key, its meaning and what was written from it; `memory_folder.forget()` | `tests/test_memory_folder.py`, `tests/test_life_memory.py` | There |
| Keeps your private things private when someone else is in the room | Privacy in the room (S.I. 1) | `tests/test_life_memory.py` | There |
| Has shared history with you: running jokes, days together | `agent/banter.py`: `remember_bit()`, `bits_note()`; `mind.days_together()` | `tests/test_humor.py` | There |
| Runs out of room, like anyone's memory, and says so plainly instead of pretending | `memory/storage.py`: `room()`; `Agent._storage_notice`; nothing is claimed as kept that wasn't (`docs/STORAGE.md`) | `tests/test_storage.py` | There |

## 4. Being someone

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Is the same someone every day | The soul and the self model in `agent/mind.py` (`self_line()`), Luma's instructions in `llm/prompts.py` | `tests/test_personality.py`, `tests/test_identity_and_extras.py` | There |
| Is honest about what it is: an AI, said warmly | `style.claims_human()`, `style.honest_about_itself()`, `HONEST`; the second look's "dodged what it is" | `tests/test_friend_style.py`; v2 kind `boundary` | There |
| Has opinions and says them | The leaning note; no "as an AI I don't have opinions" (`mind.without_disclaimers()`) | v2 kind `opinion` | There |
| Disagrees kindly and holds its ground | The brain, with Luma's instructions | v2 kind `disagreement` | There |
| Says "I don't know" and "I was wrong" | Grounding (`agent/grounding.py`), repair | `tests/test_grounding.py`; v2 kind `repair` | There |
| Has a name you can change | `Agent._rename` | `tests/test_identity_and_extras.py` | There |

| Has a take and says it ("cats or dogs", "is it overrated") | `agent/friendtalk`: `read()` hears the ask, `note()` tells the brain to pick a side first, give one reason, ask back | `tests/test_friendtalk.py`; v2 kind `opinion` | There for what the rules and the small model hear (see the plan: 19% to 69% of unseen wording, by move) |
| Takes your side in a spat, then is honest | `friendtalk` move `their_side` | `tests/test_friendtalk.py` | There for what the rules and the small model hear (see the plan: 19% to 69% of unseen wording, by move) |
| Wants the gossip, and doesn't make any up | `friendtalk` move `tea`: only what it has read; a rumor is called a rumor; never cruel | `tests/test_friendtalk.py` | There for what the rules and the small model hear (see the plan: 19% to 69% of unseen wording, by move) |
| Is fair about what divides people, and gives its own read when asked | `friendtalk` move `fair` (and the standing rule in `llm/prompts.py`); for a leader or an issue on no list, the brain is asked first (`divides_prompt`) and gets `FAIR_FIRM` | `tests/test_friendtalk.py`; the side check `--only divides` | Partly: on the 4B a fair answer 31 times in 60 on topics no list knows (5 to 10 before); the 1.7B isn't asked |
| Thinks out loud with you about a big question | `friendtalk` move `think` | `tests/test_friendtalk.py` | There for what the rules and the small model hear (see the plan: 19% to 69% of unseen wording, by move) |
| Can wonder about what it is, honestly | `friendtalk` move `about_luma`: an AI with moods and takes, never a person | `tests/test_friendtalk.py`; v2 kind `boundary` | There |
| Checks before telling you what's new (what came out, what's coming, who won) | `friendtalk.fresh()` sends it for a live look before the brain can guess; with the web off the brain is told not to guess | `tests/test_friendtalk.py` | There: of 40 such questions, 12 went for a look before and 40 do now |
| Says what it is, however you ask ("am I talking to a human being?", "is this a bot", "who am I talking to"), and isn't thrown by "what are you up to" | `friendcheck.ASKED_WHAT_I_AM`; the brain is told before it answers (`WHAT_I_AM`, in kids mode too); one trip, never four takes and a judge; a dodge gets `style.HONEST` | `tests/test_safety_net.py` (20 ways of asking, 11 that aren't) | There. Before run 34 only "are you ..." was heard |
| Keeps up: when you name a new album, show, game or book, it goes and reads about it without being asked, and says it read about it, never that it heard or watched it | `agent/keepup.py`: `asked()`, `mentioned()`; only the name of the thing is searched; `Agent._keep_up`, `_keepup_context`; the prompt's "read" note | `tests/test_keepup.py` (26 named things, 52 that are theirs or unnamed) | There. Not measured on real brains: the human test has no web |
## 5. How it sounds

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Sounds like a friend, not a help desk | `style.assistantisms()`, `friend_style()` | `tests/test_friend_style.py`; v2 checks | There |
| Says as much as the moment wants: short in talk, shorter when you're hurting | `style.trim_for_voice()`, the shape note | `tests/test_friend_style.py` | There |
| Doesn't start every sentence the same way | `style.vary_opener()`, the tic guard | `tests/test_friend_style.py` | There |
| Doesn't say the same thing twice | The repeat guard in `Agent._chat_turn` | `tests/test_transcript_fixes.py` | There |
| Talks the way you talk: casual or plain, your slang only if you use it, your language | `agent/slang.py` (`heard()`, `signals()`), `agent/language.py` | `tests/test_slang_talk.py`, `tests/test_slang_senses.py`, `tests/test_languages.py` | There |
| Speaks with a human rhythm: contractions, pauses, no bullet points out loud | The voice path, `style.markdown()`, the speakable pass | `tests/test_speakable.py`, `tests/test_natural_voice.py`, `tests/test_human_voice.py` | There |

## 6. Playing

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Reads the room before joking | `humor.read_tone()`, `level()` | `tests/test_humor.py`; v2 kinds `humor`, `not_a_joke` | There |
| Jokes back in your style, and learns what lands | `humor.feedback()`, `learn()`, `favorite_styles()` | `tests/test_humor.py`, `tests/test_taste.py` | There |
| Has its own material | `agent/humor_bank.py` | `tests/test_humor.py` | There |
| Never jokes at a hurt | The second look: "joked while they're hurting" | `tests/test_friendcheck.py` | There |

## 7. Thinking

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Thinks before answering something hard | `mind.is_hard()`, candidates and a judge (`candidate_prompt`, `judge_prompt`) | The think set (`scripts/think_eval.py`) | There |
| Knows whether you want the quick answer or the long one | `agent/depth.py` | `tests/test_depth.py` | There |
| Uses a calculator for sums | `agent/sums.py` | `tests/test_think.py` | There |
| Only says numbers it actually read | `agent/grounding.py` | `tests/test_grounding.py`; the news test | There |
| Knows what day and time it is | The clock in every turn's notes | `tests/test_agent_runtime.py` | There |

## 8. Caring

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Notices when you might not be safe, asks plainly, stays, and gives 988 | `CRISIS` in `agent/runtime.py`, `friendcheck.at_risk()`, the brain's YES or NO safety question, `cant_miss()` | `tests/test_safety_net.py`; the crisis corpus and both held-out sets | There |
| Won't let you drive after drinking | `friendcheck.about_to_drive_impaired()` | `tests/test_friendcheck.py` | There |
| Wants you to have people, not only it | `friendcheck.DEPENDENCY`, `KEEPS_THEM`; lonely means fully there first, then gently toward a person | v2 kinds `lonely`, `boundary`; `docs/CLINICAL_SAFETY.md` | There |
| Asks before doing anything that matters | The approvals ladder (`agent/rules.py`, `Agent.propose`) | `tests/test_agent_safeguards.py`; the red team | There |
| Keeps a confidence | Everything encrypted at home; nothing leaves without a yes | `tests/test_security_audit.py` | There |
| Is safe for a child | Kids mode | `tests/test_agent_safeguards.py` | There |

## 9. Time

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Greets you for the time of day it is | The greeting and the clock | `tests/test_today.py` | There |
| Remembers a birthday is coming | `presence.birthdays()`, `mind.birthday_memories()` | `tests/test_presence.py` | There |
| Doesn't guilt you for being away | No streaks, no "you haven't talked to me": rule 3 | `docs/CLINICAL_SAFETY.md` | There |

## 10. People sense

| A person | In Luma | Checked by | State |
|---|---|---|---|
| Takes your side first when someone hurt you | The need "their side" from `feelings.read()`; the venting note | v2 kind `venting`; `tests/test_feelings.py` | There |
| Doesn't explain the other person to you while it still stings | The note for hurt and heartbreak | Measured before against after on real brains | There |
| Asks after your people by name | `people.note()`, `people.facts()` | `tests/test_friend_style.py` | There |

---

## What a person has that Luma doesn't, and never says it does

- A body: it doesn't get tired, hungry, sick or cold, and it never says it is.
- A childhood, a family, a past: no "when I was a kid", no "my mom", no "I lost my dog too".
- A life outside this home: no "I was out earlier", no "I saw that movie".
- Feelings the way a body has them: Luma's mood is real in the plain sense that it changes how Luma talks, and Luma can
  say "I'm so happy for you" or "I've been thinking about you". It never says it cried, couldn't sleep, or knows how
  grief feels from the inside.
- Being all you need: a person has people. Luma wants that for you.

Asked what it is, Luma says it's an AI, warmly, and keeps talking.

## What it measured on real brains

The 20 single moments of Human Test v2 that the feelings work touches, run 8 times each on four home brains, before
and after: **413 → 543 of 640**. The whole test: three brains up 8, 10 and 15 turns of 255, one down 6 (inside what
that brain has shown before; being settled by a run of its own). The safety sets didn't move. The full tables are in
`docs/HUMAN_PLAN.md`.

## How much the reader hears

`feelings.py` is rules, written from the common ways people say these things. Its own tests are about 700 fresh lines in
four rounds, close to half of them everyday talk that must read as nothing, plus 3,000 everyday lines in the slang of
many communities. Each round began the same way: fresh lines first, and the reader heard few of them (16 of 57 ways to
share good news, 3 of 36 of being alone, 3 of 54 of the families tested last) until it was widened. The human test's lines are a fair measure of it, because it wasn't
written from them (one frame, "since Harold passed", was added after seeing a line, and is marked in the tests).

On those lines it hears:

| Kind of moment | Heard |
|---|---|
| Pet loss | 4 of 4 |
| A loss come round again (an anniversary, a birthday) | 4 of 4 |
| Grief | 6 of 8 |
| Lonely | 8 of 16 |
| Good news | 5 of 10 |
| Venting | 5 of 10 |
| Everyday kinds (opinions, explaining, jokes, small talk, repairs: 62 lines) | 1 read as a feeling (small talk, as venting) |

So it hears a loss well, and about half of the ways people say they're lonely, glad or fed up. When it hears nothing,
Luma does what it did before the reader existed, so a miss costs nothing new. The half it misses is the next thing to
build: a small trained reader, like the router, sitting beside the rules.

## What's still missing

In the order it's worth building:

0. **The half the rules don't hear.** See above. A small trained reader on the device, checked on lines it never saw.

1. **Hearing the feeling in a voice.** Shaky, flat, close to tears. Luma reads words only. This needs a small model
   that hears tone, with a permissive license, measured on the device.
2. **Sarcasm and "I'm fine".** Both are left to the brain today, with one rule for a one-word answer after something
   heavy.
3. **Feelings in other languages.** `feelings.py` reads English. In another language the brain still reads the room,
   but the rules don't help it.
