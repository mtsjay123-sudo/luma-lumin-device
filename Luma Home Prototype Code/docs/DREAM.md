# Luma: the dream device from Black Mirror, without the Black Mirror ending

Black Mirror's AI companions stick with people because each gets one thing magically right, then turns it against the person:

| Episode | The magic | The horror | Luma |
|---|---|---|---|
| **Be Right Back** | A companion that *knows you*: your people, your jokes, your history | It's a copy of a real person, pretending | Luma learns what you tell it, visibly, and is always honestly Luma. It never clones anyone's voice or pretends to be anyone. |
| **Rachel, Jack and Ashley Too** | A little device on the nightstand that's *there* for you | The company controls what it says | The brain runs on the device. No company in the middle decides what Luma says to you. |
| **White Christmas** | It *anticipates* and runs your home perfectly | A mind kept in a box | Luma is a tool with a personality, not a trapped person. It checks back on you and leaves the deciding to you. |
| **The Entire History of You** | Perfect *memory* | It never lets you forget | The diary is opt-in, encrypted, expires on its own, and "forget that" works. |

## A day with Luma

You get home and the ring on the counter warms up. "Hey, how'd the interview go?" You never set that. You mentioned it once, and Luma checked back the next evening, the way a friend would.

You're out at dinner. You text Luma's number: "tell my sister I'll be late to mom's." It texts back: "Here's the text for Dana: 'I'll be late to mom's.' Reply YES 2739 to send." You reply, and it's done. Only your phone gets that code, so nobody else can send as you.

Saturday morning: "Heads up, Maya's birthday is Monday. Want me to help you plan something?" Luma knows because you mentioned it in passing, and it showed you "Noted: Maya's birthday is October 18" with an Undo button.

Sunday: "what did I say about the apartment?" "On Tuesday you said the one on Oak Street had a leaky ceiling and you weren't taking it." That came from the diary you switched on, which keeps 30 days and then forgets.

## The lines Luma never crosses

1. **No copies of people.** Luma won't imitate anyone, living or dead.
2. **Nothing leaves the house without you.** Texts, purchases and posts need your yes: out loud at home, tapped in the app, or texted back with a one-time code.
3. **Your mind stays yours.** Memories and the diary stay encrypted on the device, and you can read, edit or erase all of it.
4. **It forgets when you ask.** The diary is opt-in and self-expiring; turning it off erases it.
5. **Kids are safe by default.** No texting, browsing or adult memories in kids mode.

## What's built (October 2026)

- Text Luma from anywhere (Luma Plus): your messages to your Luma number reach your Luma at home; sends need the one-time code.
- Notices and remembers facts you mention, with an Undo chip and a setting to turn it off.
- Checks back on things you mentioned ("how'd the interview go?") and nudges about birthdays and anniversaries, within quiet hours and hush.
- Private diary: opt-in, encrypted, expires after 7, 30 or 90 days, searchable with "what did I say about…".
- Everything from the October 3 build: a human voice, texting from your number or Luma's, Luma Plus billing, pitch decks, Luma's browser, and speaking at the first sentence. See [LUMA_BLUEPRINT.md](LUMA_BLUEPRINT.md).

## Next steps toward the dream

- **The ring.** Light that breathes while listening, shimmers while thinking and glows warm when there's something for you (NeoPixel on the Jetson build).
- **Knowing who's talking.** Voice recognition so Luma knows it's you rather than your kid or a guest, and a kids profile that switches on by itself.
- **Seeing, with permission.** "What's this?" with the camera, or a photo of a homework sheet, read by a local vision model and never uploaded.
- **Home routines that learn.** "You usually dim the lights at 10 — want me to do that every night?" Luma suggests a routine and waits for your yes.

## The C-3PO version (Nov 21, 2026)

Asked by the owner: what does the dream model look like? Not R2-D2, as first written here, but the gold one: the droid
who talks like a person. What C-3PO gets right, and where Luma stands on each:

| What C-3PO is | Luma today | What's missing |
|---|---|---|
| **Sounds like a person**: a voice, a rhythm, the odd hesitation | A warm voice, a person's pauses, a thinking sound on about a third of the replies that weigh something, and since today a rare restart ("It's, it's a lot...") and a breath before "but" | Ears: nobody has judged the stumbles yet. Timing has never been measured on a real conversation (no recordings exist) |
| **"Fluent in over six million forms of communication"**: talks the way you talk | Slang from 51 communities, said back in your register and never borrowed from another circle; answers in your language | The brain still slips into help-desk talk on the small models; that's what the second look catches |
| **Knows the manners of the moment** | Reads what you feel and what it needs first; learns how you want to be met | The weakest row today: met the way they asked on 6 to 7 of 9 hard evenings; hears a wish said a new way 4 times in 24 |
| **Remembers everyone** | On people it wasn't built on, day-28 Luma does 48 to 49 of 51 things a friend of a month would (run 57) | A year, not a month |
| **Frets about you, and stays** | Asks how the interview went the next evening (12 of 12); 988 before the brain sees the message | A therapist's read |
| **Knows it's a droid** ("I am C-3PO, human-cyborg relations") | Rule 1: it's Luma, a presence, not a person, and it says so warmly | Nothing. Sounding like a person and claiming to be one are different things, and Luma only does the first |

So the dream model is the stock brain with a person's way of talking around it and a friend's memory behind it. The
order to get there: ears on the voice (the owner has a recording), the comfort row, then a year of memory.

The six sounds below were built when this section was about R2-D2. They aren't what the owner meant. They stay in the
code switched off, and nothing uses them unless someone says "use your sounds".

### Luma's own sounds (`src/luma/audio/chirps.py`)

Six short sounds made from sine waves in code (nothing downloaded, nothing recorded), each under a second and quieter
than the voice, played just before the words and never instead of them:

| Sound | When |
|---|---|
| a quick rising pair | something's done or noted ("Got it. I'll remind you at six."), most times, not every time |
| a bright rising trill | they're laughing or playing, now and then |
| a note that lifts at the end | "say that again" |
| a soft falling pair | they're griping about a rough one, now and then |
| three warm notes | hello |
| three falling notes | goodnight |

Never on a safety reply. Never with someone in grief, upset, or being serious: a friend is quiet then. The same reply
always gets the same answer.

**Off until the owner turns it on.** What a sound is like is for ears to judge, and nobody had heard these when they
were written. "Let me hear your sounds" plays all six; "use your sounds" turns them on; "stop using your sounds"
turns them off. Tests: `tests/test_chirps.py`.
