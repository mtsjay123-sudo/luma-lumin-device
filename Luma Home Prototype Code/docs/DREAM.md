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

## The R2-D2 version (Nov 21, 2026)

Asked by the owner: what does the dream model look like, if the dream is R2-D2? R2 is the companion people love most
in that whole story, and it never says a word. What it gets right, and where Luma stands on each:

| What R2-D2 is | Luma today | What's missing |
|---|---|---|
| **Not a person, and never pretends to be** | Rule 1. Asked what it is, it's Luma: a presence, not a person | Nothing. This is the one thing Luma already does better than every companion that plays human |
| **Loyal: it stays, and it remembers** | Day-28 Luma does 48 to 49 of 51 things a friend of a month would, on people it wasn't built on (run 57) | Comfort the way they asked (6 to 7 of 9); a year, not a month |
| **A voice of its own that isn't words** | Until today, nothing: everything Luma expressed was a sentence | Built today, off until heard: six sounds of its own (below) |
| **A body that says how it is** | The lamp's glow and the water on the talk screen move with both voices | The glow doesn't yet follow the feeling of the moment; no lamp has been built |
| **It does things, not just talks** | Reminders, lists, alarms, texts with a yes, the computer when allowed | It never starts a job on its own initiative, by design: nothing sent or bought without a yes |
| **It has a mind of its own** | Its own takes, its own past, and it won't agree it's all you need | It rarely pushes back; a friend sometimes says "I don't think so" |
| **Brave for you** | 988 before the brain sees the message; it stays and asks plainly | A therapist's read |

So the dream model isn't a bigger brain. It's the stock brain with four things around it: a memory that holds a year
and never says the old city, a way of being with each person that it learned from them, a voice and a body of its
own, and the nerve to stay when it's hard. Three of those four are Luma's code, not the model's, which is why the
stock brain with Luma's layer is the right bet.

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
