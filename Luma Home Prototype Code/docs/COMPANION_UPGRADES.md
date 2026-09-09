# Luma companion controls — September 8, 2026

Open `http://127.0.0.1:8095/`. The Mac uses the locally configured Qwen3 4B Instruct 2507 GGUF, Whisper base.en and Kokoro speech. No model fine-tuning was performed: explicit presets and editable memory guide the conversation. No per-message AI API is used.

## Try it

1. Click **Hear Luma** to preview speech without enabling the microphone.
2. Choose **Speak replies on this Mac**, type a message, and listen. Use **Stop / interrupt** at any time.
3. To use the Mac microphone, click **Microphone off**, permit microphone access if macOS asks, and say “Hey Luma…”. Follow-up turns remain addressed for 45 seconds.
4. Choose Everyday, Straight Talk, Playful, Quiet, or explicitly acknowledge adult selection before choosing Unfiltered. Slang and humor affect language, never tool permissions. Kids mode suppresses adult style and data; it is not a production parental-authentication system.
5. Try “Remind me in 20 minutes to check the oven,” followed by “actually, tomorrow.” The same reminder is updated. “Make that shorter” asks for a shorter version while retaining conversation context.
6. Start named timers, save a recipe and say “next step.” Edit household locations, pantry notes, manuals, warranties or maintenance dates. Manual notes are supplied text/source links; arbitrary PDFs are not automatically indexed.
7. Agent mode can carry out up to six local or enabled tool steps per run, record verified outcomes, prevent exact duplicate steps and pause for review. It is a bounded planner, not unrestricted computer control. Interrupted/restarted runs never automatically replay uncertain side effects.
8. Save a grocery list locally and prepare a family text. Connected Instacart lists require an account/key; actual product matches, prices, stock, payment and order placement remain at merchant checkout. No cheapest-price claim is made without comparable verified totals.

## Interruption and performance

Stop cancels queued work, token generation between model chunks and audio playback. Native model loading/prompt prefill and an in-progress speech synthesis chunk finish before control can return. Completed external effects cannot be undone by Stop.

By default the microphone is suppressed during speaker output to avoid echo. The opt-in **Headphones / isolated speaker** setting allows voice interruption such as “wait” while Luma speaks. It requires isolated audio; speaker echo cancellation is not implemented. Use Stop for dependable interruption with the Mac's built-in speakers.

Conversation history stays in RAM and is cleared on a mode switch/restart. Explicit memories, household records, timers, recipes, contacts, action receipts and agent goals persist in encrypted local records. A profile change no longer erases the current conversation.

## Connections

- Mac Messages: uses the owner's signed-in Messages account after review; macOS Automation permission and iPhone SMS forwarding may be needed. A bridge acceptance is not a delivery receipt.
- Phone: owner-created HTTPS pairing invitation, same home network, local certificate trust, revocable 30-day credential. This is not an installed native iPhone app or away-from-home service.
- Instacart, Brave Search, Cal.com, Twilio and Home Assistant: account credentials are not currently configured in this checkout. Switches do not create provider accounts.
- Payments: saved at the merchant, never as raw card numbers/CVCs inside Luma chat or local memory.
- Daily briefing: explicitly enabled, one per day from saved local records, with adjustable quiet hours and hush. External calendar sync is not claimed.

Keep credentials in the local `.env`, outside Git. Refer to the separate desktop account inventory for website/Supabase accounts; visitor email collection is separate from household voice memory.
