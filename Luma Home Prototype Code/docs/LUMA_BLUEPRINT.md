# Luma blueprint: how it works, why it stalled, and the gameplan

*October 3, 2026 (updated later the same day; see [DREAM.md](DREAM.md) for the vision). Written after reading every file in this repository (device code, docs, tests, the website and its API) and rebuilding the parts that kept Luma from feeling like the product on the site.*

---

## 1. What Luma is supposed to be

Luma is a $199 home companion (plus an optional $9.99/month **Luma Plus**) that lives on a small glowing device and on your phone. It is meant to be:

- **A friend you can talk to.** It sounds like a person, remembers your people and plans, and knows when to be brief or quiet.
- **An agent that does things.** It texts people for you, sets reminders and timers, builds pitch decks, helps with homework, looks things up, shops, and checks your feeds.
- **Trustworthy enough for a family.** The brain runs on the device. Anything that leaves the house (a text, a booking, a purchase, a post) is shown to you first and only happens when you say "send it". Kids mode is safe by default.

That third point is Luma's edge over OpenClaw-style agents (see section 6). They are powerful but have shipped with unauthenticated gateways, prompt-injection takeovers and malicious plugins. Luma does the same jobs with a trust layer a household can live with.

## 2. Why it stalled

The repository was not empty. It had a careful, well-tested foundation: encrypted storage, an approval system, phone pairing, a Mac Messages bridge, Cal.com bookings, Instacart lists, timers and recipes. But it didn't feel like the product, for four reasons:

1. **It talked like a compliance notice.** The personality prompt was mostly prohibitions, and every reply leaned on runtime text such as *"Reminder saved locally. The runtime must be running to notify you; quiet hours and hush apply."* Accurate, but nobody's friend talks like that.
2. **The brain took one step.** The local model could propose one tool or one reply per turn. There was no look-it-up-then-act, and results came back raw instead of as an answer.
3. **The dream features weren't connected.** "Text my girl" needed a contact named exactly "my girl" and a manual button press. Luma had no number of its own, so texting without a Mac wasn't possible. Pitch decks, browsing and paid features didn't exist.
4. **Voice felt slow.** Speech waited for the whole reply to be generated and synthesized before saying a word.

None of this needs a paid cloud model. The local Qwen3-4B model on the Mac (and later the Jetson) is enough when the runtime does the heavy lifting: routing, guarding, formatting and sounding human.

## 3. How everything works now

```
 You ──voice/typing──▶  Luma device (Mac now, Jetson later)                   Website (Vercel)
                         ├─ audio: Silero VAD → Whisper → (brain) → Kokoro     ├─ index/product/luma-plus pages
                         ├─ brain: local Qwen3-4B via llama.cpp                ├─ api/reserve, api/reservations
                         │    persona + grammar-constrained tool calls         └─ api/luma/[route]  ◀── "Luma Cloud"
                         ├─ runtime: tools, approvals, memory, household            │  Supabase tables
                         ├─ texting: own number (Mac Messages) ─────────────────────┤  Twilio (send/receive)
                         │           Luma's number (Luma Cloud) ────────────────────┘  Stripe (Luma Plus)
                         ├─ skills: decks (.pptx), browser (Playwright)
                         └─ control panel :8095 + paired phone (HTTPS on home Wi-Fi)
```

### The conversation turn

1. **Hearing.** Silero VAD notices speech, Whisper transcribes it, and a turn is addressed if it says "Luma" or follows within 45 seconds (`orchestrator.py`).
2. **Fast paths first.** Plain rules handle things that must never be guessed or that need no model: "send it" / "don't send it", stop, hush, the crisis line, reminders, timers, "text X that…", "save Maya … as my girl", "did Maya text back?" and "check my instagram" (`agent/runtime.py`, `agent/texting.py`).
3. **The model.** Everything else goes to the local model with Luma's persona (`llm/prompts.py`) and only the tools relevant to that message, which keeps the 4,096-token context small. A JSON grammar forces the output to be either a reply or a valid tool call (`llm/inference.py`).
4. **Acting.** The runtime validates every tool call. Look-ups (memory, web, house notes, the browser) feed back to the model, which can take one more step or answer in plain words (`_follow_up`). Anything that leaves the house becomes a pending action that only you can approve.
5. **Speaking.** The reply's words are pulled out of the model's stream as they're written and spoken sentence by sentence (`llm/streaming.py`, `orchestrator.SpeechStream`, `audio/tts.speak_stream`).

### Module map

| Area | Files | What it does | Status |
|---|---|---|---|
| Voice in | `audio/vad.py`, `audio/stt.py`, `audio/io.py` | Silero VAD, Whisper base.en, device selection | Works on Mac |
| Voice out | `audio/tts.py` | Kokoro voices, phrase grouping, streaming playback | Works; streaming new |
| Brain | `llm/inference.py`, `llm/prompts.py`, `llm/streaming.py` | Local GGUF, persona, grammar, streamed replies | Works; persona and loop rewritten |
| Runtime | `agent/runtime.py` | Fast paths, tool registry, approvals, reminders, proactive ticks | Works; extended |
| Texting | `agent/texting.py`, `agent/contacts.py`, `integrations/mac_messages.py`, `integrations/luma_cloud.py` | Drafts in your voice, nicknames, "send it", own number, Luma's number, replies | **New**, tested end to end |
| Household | `agent/household.py`, `agent/workflows.py` | Timers, recipes, house notes, briefing, multi-step agent runs | Works |
| Skills | `skills/decks.py`, `integrations/browser.py` | Pitch decks; Luma's own browser | **New** |
| Integrations | `integrations/providers.py`, `bookings.py`, `commerce.py` | Brave search, Twilio, Home Assistant, Cal.com, Instacart | Built; need your accounts |
| Control | `control/server.py`, `control/pairing.py`, `control/web/*` | Local panel, chat thread, phone pairing | Works; chat thread new |
| Hardware | `hardware/device.py`, `hardware/diagnostics.py`, `scripts/setup_jetson.sh` | GPIO privacy switch, indicator, Jetson setup | Written; no physical device tested |
| Storage | `memory/store.py` | Encrypted SQLite records, key file | Works |
| Luma Cloud | `/api/luma/[route].js`, `/api/_lib/*`, `/supabase/migrations/*` | Luma's number, quotas, Luma Plus billing | **New**; needs your Twilio/Supabase/Stripe |
| Not started | `address_detection/`, `kids_mode/`, `proactivity/`, `safety/`, `cloud/` | Empty packages from the original plan | Placeholders |

## 4. What changed in this build

Every item below has automated tests (202 Python, including real Kokoro speech; 15 Node for the relay). The texting and chat flows were also run end to end in a real browser, and the database migration was run on Postgres.

**Sounds like a person**
- The new persona describes a character and includes example exchanges ("ugh long day" → "Rough one? Tell me about it, or I can just keep you company"). The honesty rules are kept.
- Runtime confirmations are human: *"Done, I'll remind you at 3:40 PM to check the oven."* *"Sent to Maya from your number."*
- Look-ups get a second pass so you hear an answer, not a data dump.
- Voice starts at the first sentence. On this test machine, time to first sound dropped from about 13.7 s to about 2.0 s for a typical reply; your Mac will be faster in both cases.

**Texting friends and family**
- "Text my girl that I'll pick her up at 7" becomes **"I'll pick you up at 7"** to Maya. Pronouns flip to the recipient; nothing is added.
- **Nicknames:** contacts can be "my girl", "babe", "Mom". If Luma doesn't know someone, it asks *"Who's my girl? Give me her name and number"* and saves the answer.
- **"Send it" works by voice.** Plain rules match it, never the model. "Yes but make it shorter" is *not* approval. Approvals expire after 10 minutes.
- **Learns your style.** Drafts copy how you text each person (all lowercase, no periods, and so on).
- **Your own number, free:** Mac Messages (iMessage or SMS through your iPhone).
- **Luma's number:** the Luma Cloud relay. You get free texts every month, then **Luma Plus**.
- **Replies come back.** "Maya texted back: 'yes! 7?'", shown silently during quiet hours, and you can ask "did Maya text back?"

**Does tasks**
- **Pitch decks:** "make me a pitch deck for Greenline" produces a styled .pptx (5 layouts, 4 themes, speaker notes) you download from the chat.
- **Luma's browser:** "check my instagram" opens the feed, scrolls, and tells you what's new. Liking, following, commenting, posting, messaging and buying become an approval card. Passwords are never typed; you sign in once in a visible window. Home-network addresses and non-web links are refused.
- **Small agent loop:** look something up, then act on it, in one turn (for example, recall a birthday and draft the text).
- "remember where the keys are?" now answers instead of saving the question as a memory.

**Paid features (Luma Plus)**
- Phone verification, an atomic monthly quota, a 402 response with a Stripe Checkout link, a webhook that turns on Plus and buys a dedicated local number, STOP/HELP handling, reply routing and rate limits.
- A Luma Plus page on the website for checkout returns.
- `tools/luma-cloud-dev.mjs` runs the whole relay locally with a pretend carrier and checkout, so you can demo it today with no accounts.

**Dream upgrades (later on October 3)**
- **Text Luma from anywhere (Luma Plus):** your texts to your Luma number from your own phone reach your Luma at home, and it answers by text. Anything that would send needs "YES 4821", a one-time code only your phone receives, so a spoofed number can't approve anything. Free accounts get an automatic note that this is a Plus feature.
- **It knows you:** facts you mention in passing ("Maya's birthday is October 18", "I'm allergic to shellfish") are saved as editable memories with an Undo chip. You can turn this off.
- **It checks back:** "I have a job interview tomorrow" becomes "Hey, how'd the job interview go?" the next evening. Birthdays and anniversaries within 3 days get a nudge. Both respect quiet hours and hush, and stale check-ins are dropped.
- **Private diary:** opt-in, encrypted, expires after 7, 30 or 90 days, and turning it off erases it. Ask "what did I say about the apartment?" "Forget that" undoes the last thing noticed.
- **Luma Plus is live in Stripe:** product `prod_VN76B0DKaXCLk9`, price `price_1UMMsMHupQXO7siRSIB6U6z3` ($9.99/month, lookup key `luma_plus_monthly`, metadata `app=luma`).
- **Website security:**
  - The admin password is no longer in public JavaScript; `/api/reservations` now requires `LUMA_ADMIN_TOKEN`.
  - Waitlist emails are no longer rendered as HTML in the admin page (that was a stored-XSS hole).
  - Sign-ups are validated.

## 5. Texting and Luma Plus

### How a text travels

| You say | Route | Cost to Lumin | What the recipient sees |
|---|---|---|---|
| "text Maya …" with **your number** selected | Mac Messages → your iMessage/SMS | $0 | Your normal number |
| "text Maya …" with **Luma's number**, free tier | Luma Cloud → shared Twilio number | ≈ $0.012/text | "Marvin: …", plus "(Sent via Luma for Marvin. Reply STOP to opt out.)" the first time |
| Same, on **Luma Plus** | Luma Cloud → your dedicated local number | ≈ $0.012/text + $1.15/month number | Just the message, from your own Luma number |

Defaults are 30 free texts a month and 300 on Plus. Both are environment settings (`LUMA_FREE_TEXTS_PER_MONTH`, `LUMA_PLUS_TEXTS_PER_MONTH`).

### Economics (public Twilio pricing, October 2026)

- Per text: about $0.0083 Twilio plus about $0.004 carrier fee ≈ **$0.0123**.
- A Plus member who uses all 300 texts: $3.69 in texts, $1.15 for the number and $0.59 in Stripe fees ≈ **$5.43 cost on $9.99, about 46% margin at maximum use**. Most people won't use all 300.
- A free user who uses all 30: about **$0.37/month**, plus about $0.05 for the one-time phone verification.
- Business-wide: 10DLC brand registration ($4 one-time) and a campaign ($10–15/month).

### Go-live checklist (needs you)

1. **Supabase:** run `supabase/migrations/20261003120000_luma_cloud_texting.sql`. Add `SUPABASE_SERVICE_ROLE_KEY` to Vercel, server-side only.
2. **Twilio:** buy one number for the shared pool and create a Verify service. Register **A2P 10DLC** (brand plus a "conversational / mixed" campaign that describes user-composed personal texts with opt-out), or use a verified toll-free number. Put the numbers in a Messaging Service. Point inbound SMS to `https://<site>/api/luma/twilio-inbound`.
3. **Stripe:** the "Luma Plus" product and $9.99/month price already exist (`LUMA_PLUS_PRICE_ID=price_1UMMsMHupQXO7siRSIB6U6z3`). Add a webhook to `https://<site>/api/luma/stripe-webhook` for `checkout.session.completed` and `customer.subscription.*` (plus `invoice.payment_failed`). Turn on the customer portal. Checkout sessions are tagged `metadata.app=luma`, so your OmniShort and AEONHALL events on the same account are ignored.
4. Fill the variables in the website's `.env.example` in Vercel, and set `LUMA_CLOUD_URL` on the device if the site isn't at the default URL.
5. Try it with the dev relay first: `node tools/luma-cloud-dev.mjs`, then `LUMA_CLOUD_URL=http://127.0.0.1:8787 .venv/bin/python -m luma.cli serve`. The verification code is 123456.

**Carrier reality:** carriers are strict about personal messages sent through a business number. Expect to explain the use case during 10DLC review. The first-contact footer and STOP handling are there for that review. Your own number through Messages has none of these limits.

## 6. Lessons from OpenClaw (Clawdbot), Hermes Agent and Dot

| They do | Why it works | Luma's version |
|---|---|---|
| Live in your chat apps (WhatsApp, Telegram, iMessage) | You talk to them where you already are | Luma texts *for* you today. **Next:** let you text Luma itself (section 7). |
| Long-term memory files and a growing picture of you | Feels like it knows you | Encrypted memories, nicknames and per-person texting style. **Next:** quietly offer to remember facts you mention. |
| Skills the agent writes and improves (Hermes) | Gets better at your recurring tasks | **Next:** save "recipes" for tasks you repeat (the weekly grocery text, your Monday briefing). |
| Browser and computer control | Does real tasks on real sites | Luma's browser, look-don't-touch, with approval for anything that acts. |
| Proactive check-ins | Feels alive | Reminders, routines, briefings and reply announcements, with quiet hours and hush. |
| **What to avoid:** open gateways, auto-installed plugins, agents that act on page text, keys stored in plain files | Real breaches in 2026 | Localhost-only control, paired phones with revocable tokens, approvals matched by rules not the model, page content treated as data, encrypted storage, no third-party plugin store. |

## 7. Gameplan

### Next 2 weeks: make the demo undeniable
1. Run `scripts/luma_check.py` on the Mac with Qwen. Fix every ✗. It grades bot phrases, length, actions and speed against the same bar used here.
2. Go live with texting from your own number (Mac Messages): choose the route in People & Texts, then send yourself a test.
3. Stand up Luma Cloud with real accounts (section 5) and send the first text from Luma's number.
4. Record a 60-second demo: "text my girl I'm running late" → "send it" → her reply read aloud; "make me a pitch deck"; "check my instagram".

### 30 days: a friend that remembers
- ~~Text Luma itself~~ and ~~remembering what you mention~~: done (see section 4).
- **Website:** set `LUMA_ADMIN_TOKEN` in Vercel, use the service-role key for `/api/reservations`, and make the `reservations` table insert-only for the public anon key.
- **Homework mode upgrades:** a photo of a worksheet goes through the phone camera, a local vision model reads it, and study mode tutors from it.
- **Shopping:** a price comparison across 3 to 5 stores through Luma's browser, with a pick and a checkout handoff.

### 60 days: the device
- Jetson Orin Nano bring-up following `docs/DEVICE_SETUP.md`: microphone array, speaker, privacy switch and enclosure.
- Run Qwen3-4B with GPU offload on the Jetson and measure latency against the Mac.
- A wake-word-free "is this for me?" classifier (the empty `address_detection/` package).

### 90 days: launch readiness
- A blind test with 5 to 10 people: does Luma feel human, and does it do real tasks?
- Kids mode with parent PIN authentication (currently a mode switch only).
- Over-the-air updates and backups (scripts exist), plus a manufacturing path.

## 8. Known limits (honest)

- The live model wasn't run in this build environment because model downloads are blocked here. The persona and loop are tested with scripted model responses; `scripts/luma_check.py` is how you verify them on the Mac.
- Instagram and other sites: Luma uses your logged-in browser like you would. Their terms discourage automation, so keep it to reading your own feed. The browser can't see inside private API-only apps.
- A 4B model drafting a full pitch deck can be slow (around 1,800 tokens). A bigger model on better hardware improves it, and the grammar keeps the format valid either way.
- The shared Luma number routes replies to whoever texted that person most recently. A dedicated number (Plus) avoids that.
- No physical device has been assembled or tested yet.

## 9. Run it

```sh
cd "Luma Home Prototype Code"
bash scripts/setup_mac.sh                 # Python env + agent extras + browser
bash scripts/download_models.sh           # Llama + Kokoro (Qwen per MODEL_AND_PERSONALITY.md)
.venv/bin/python -m luma.cli serve        # open http://127.0.0.1:8095/
.venv/bin/python scripts/luma_check.py    # does it sound human and do things?
.venv/bin/python -m pytest -q             # 202 tests (two more need the Whisper and LLM weights)
(cd .. && node --test tests/luma-cloud.test.mjs)   # Luma Cloud relay tests
```
