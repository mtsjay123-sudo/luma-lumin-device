# Next level: what to try tonight, and what makes Luma better than anything else

Written Nov 14, 2026, from what's measured (`docs/HUMAN_PLAN.md`, run 42 and safety run 43) and what's built. Nothing
here is claimed as done until a test or a real person says so.

## Tonight: trying it at home

1. Open https://lumin-holdings-site.vercel.app/dev, type the developer password, pick your Mac. Open the app; the first
   start sets itself up (the brain, the voice, FFmpeg for music and video) and takes a while once.
2. On the Mac Studio, `bash scripts/mac_day_one.sh --test` picks the biggest brain the Mac holds and runs the human test
   and the safety net on it, so you know what you're talking to.
3. Things to say, out loud:
   - Talk first. Tell it about your day, something you miss, a show you love. That's what Luma is for.
   - "Wake me up at 7 on weekdays", "what alarms do I have", "snooze", "I'm up".
   - "Add milk and eggs to my shopping list", "what's on my shopping list".
   - "What time is it in Ohio", "how many days until Christmas", "how many cups in a liter".
   - "Play rain sounds", "volume 5", "stop".
   - "Play some jazz": turn on Music in settings first (only the word "jazz" goes out). Songs in your Music folder need
     nothing.
   - "Bedtime routine".
   - The lights: only once Home Assistant is connected (its address, a token, and the devices Luma may use).
4. Write down every reply that felt off, word for word. Those lines are the next fixes. A real person's evening teaches
   more than another test run.

## Next level, in order

### 1. Build one Luma and film it (the most important thing for pre-orders)

No unit exists. `hardware/README.md` has the parts, the wiring and a case to print. One working lamp on a counter,
talking, in a 30-second video, does more for pre-orders than any feature. Kill point: if it can't answer in under
about 2 seconds on the device, use the paired-computer brain (Luma Link) for the video and say so.

### 2. The brain: use the best one, then make our own beat it

- Run 42: with today's code the **stock Qwen3 4B scores 216/255**; **our own 4B (luma-brain-22) 197** and it loses the
  head-to-head to its own base 29 times to 2. Until a new training passes, the Mac and the Luma Home should run the
  stock 4B (or bigger) with Luma's code. That's a setting, and it's the owner's call.
- Three 4B trainings in a row were stopped by the honesty gate. Read which check they miss (the run's Report step),
  then train again with the presence lines and **sarcasm** practice: sarcasm is our brains' weakest kind (2 and 1 of 6;
  the stock brains get 6 and 5).
- Safety: both stock brains caught one fewer held-out line in run 43. Run `only: safety` once more to see if that's the
  brain's own wobble before changing anything. Never tune on the held-out lines.

### 3. Luma already knows you on day one

The welcome page after paying asks seven fun questions (name, your person back home, coffee or tea, comfort show, song,
what you want on a rough day, what to cheer for). Today those answers sit on the website's database. Next: when a new
Luma is paired, it asks once, "want me to bring in what you told me when you ordered?", and on a yes they become
memories. Then the first thing it says can be "Hey Sam. It's 8am in Ohio, your mom's probably up." Needs the
`luma_welcome` table in Supabase (its SQL file is ready) and a pairing step. Nothing comes in without the yes.

### 4. A presence that starts things, gently

The pieces exist (check-ins, open loops, home time, alarms). Join them up:
- The morning alarm turns into "Good morning" plus one thing that matters today ("your interview's at 10").
- When they mention someone they miss, and it's a decent hour where that person lives, Luma offers to help them call.
- The night routine asks how the day went before saying goodnight, if they want to talk.
Every one of these is tested on the human test first. Rule 3: no guilt, no engagement tricks, never "I'm all you need".

### 5. Voice that feels like a person in the room

Measure on the real device: time to the first spoken word, talking over Luma (barge-in), and the wake word "Hey Luma"
at across-the-room distance. Fix the slowest of the three first.

### 6. Real music

Today: the radio, songs in your own folder, sleep sounds, and YouTube Music on a computer. Next: Spotify and Apple Music
through Home Assistant's media players or Spotify Connect, so "play my Discover Weekly" works. Behind its own switch,
off by default.

### 7. Small things found along the way

- "I want to play a game" is heard as a music request by the small model that guesses what you want. Teach it games.
- The installers are still public on GitHub Releases. Move desktop builds to a private repo and set
  `DEV_RELEASES_TOKEN` on Vercel so /dev is the only way in.

### Owner actions (only you can do these)

- Run `supabase/migrations/20261113120000_luma_welcome.sql` in Supabase, so the welcome answers are kept.
- Turn on Google Pay in Stripe, and add a Stripe Tax registration (no tax is collected until there is one).
- Get a landed-cost quote for 50 Minis.
- Build one Luma and film it.
