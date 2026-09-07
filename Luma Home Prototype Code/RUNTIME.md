# Luma local agent — September 7, 2026

The Mac software prototype is runnable. It includes local conversation and speech, explicit encrypted memory, persistent reminders and routines, a browser control surface, and opt-in action adapters. It is not a finished consumer device. The older README/build plan is a product roadmap, not a list of verified delivered capabilities.

## Open it

The control app is running at http://127.0.0.1:8095/ on this Mac. To restart:

```sh
cd '/Users/marvinjohnson/Desktop/Lumin Universe Holding Company/All of Lumin/Luma Home Prototype/Luma Home Prototype Code'
.venv/bin/python -m luma.cli serve
```

Use `--no-model serve` for instant local tools without loading the language model. `--no-model status` prints device state. `chat` opens typed terminal interaction; `--voice chat` opts into push-to-talk and `--hands-free chat` opts into the microphone with name/follow-up gating. `/help` lists controls. The web app starts muted; its microphone switch is an explicit opt-in. Camera capture is not implemented.

Existing local model files are reused. First conversation loads Llama 3.2 3B; subsequent responses reuse it. Apple Metal is enabled by default with a 4,096-token context. Set `LUMA_GPU_LAYERS=0` for CPU-only inference. Fresh model smoke tests completed in about 10–25 seconds on this Mac; response time varies with context and hardware. The source-only repository excludes model weights, provider credentials and personal state.

## Try these

- `Remember I prefer vegetarian food`
- `What do you remember?`
- `Remind me in 20 minutes to check the oven`
- `Every day at 09:00 remind me to review my priorities`
- `Explain how a reminder can help me stay organized`
- `Search compare prices for Sony WH-1000XM6 headphones` after configuring and enabling search

Local tools respond without waiting for a model plan when the command has a deterministic match. Model plans are restricted to registered tools and validated arguments. Questions asking for an explanation cannot create a reminder. Text messages require an explicitly supplied recipient. A small local model can still misunderstand language; inspect the proposed action details.

## What is implemented

| Feature | Behavior |
| --- | --- |
| Conversation | Local Llama inference, bounded conversation context; Everyday, Study, Cofounder and Kids modes. |
| Speech | Cached Whisper transcription, Silero VAD, local Kokoro synthesis; bounded audio buffers and mute-aware playback. |
| Voice profile | `LUMA_VOICE=luma` blends 70% `af_bella` with 30% `af_heart`, speed 0.96. This is a customized stock synthesis profile, not an exclusive recorded actor or cloned person's voice. Individual stock names remain configurable. |
| Memory | Explicit memories, encrypted payloads in local SQLite, delete controls and keyword recall. The whole SQLite file is not encrypted; IDs and timestamps remain metadata. |
| Reminders | Durable future-dated tasks, completion controls, daily routines, quiet hours, hush and grouped notifications. The app must remain running. |
| Web search | Brave API adapter returning source titles, snippets and links; off until explicitly enabled. It does not calculate final shipping/tax or guarantee the cheapest price. |
| Text messages | Twilio adapter, exact recipient/body review, expiring one-use approval, no automatic retry after uncertain delivery. Provider acceptance is not a delivery receipt. |
| Lights | Allowlisted Home Assistant lights; reviewed on/off/brightness actions. |
| Shopping | A named merchant link plus shopping list and budget. Continue in that merchant's saved-wallet checkout. Luma does not build a merchant cart, store card data, charge a card or place an order. |
| Local controls | Loopback-only HTTP, same-origin mutation checks, host checks, session cookie, restricted content policy, bounded inputs, no personal data in request logs. |

Messages, lights and checkout handoffs require review even when their integration is enabled. Unknown tool names are rejected. Confirmation is atomically consumed once; cancellation, expiration or revoked consent prevents execution. Network timeouts leave an uncertain outcome that is never automatically retried.

## Configure real services

Copy `.env.example` to `.env` only if a `.env` does not already exist. Fill in credentials locally, then restart. Enable each service in the browser or terminal after setup. Do not commit that file.

- Search: `BRAVE_SEARCH_API_KEY`.
- Messages: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`; the sender and destination must meet the account's messaging requirements.
- Lights: `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`, comma-separated `LUMA_ALLOWED_LIGHTS`.
- Shopping: `LUMA_MERCHANTS_JSON`, a JSON object mapping your merchant names to HTTPS entry URLs. Links should be the merchants you actually use. Payment stays on their own checkout.
- Device: `LUMA_TIMEZONE`, optional `LUMA_STATE_DIR`, `LUMA_VOICE`, `LUMA_VOICE_SPEED`, and platform-specific eSpeak paths where needed.

No real messages, purchases, charges or light commands were sent during implementation testing. Adapters were tested using fake transport in isolated temporary state. The current services show “Connection setup needed.”

State is stored at `~/.luma/agent/state.db`, with its encryption key at `~/.luma/agent/state.key`. Directory/key permissions are restricted. Back up both securely together; losing the key prevents recovery. An existing database without its key fails closed. Raw card numbers, CVC fields and passwords are rejected as memories. Do not treat a same-user local process or an unlocked laptop as a hostile boundary this prototype can defeat.

## Verified and remaining work

Eighteen runtime tests pass, covering encrypted persistence, payment-data rejection, missing keys, one-use/concurrent confirmations, expiration, consent changes, unknown outcomes, children's restrictions, reminders, unregistered model tools and local HTTP protections. The real Llama model answered a benign explanation without creating a task. The new voice was synthesized and passed back through local Whisper with intelligible transcription. No live microphone recording was required for these tests.

Still needed before a consumer launch: reliable wake-word-free address detection and speaker identity; evaluated child safety plus authenticated parent controls; semantic multi-person memory; production crisis handling; real calendar/music integrations; merchant cart/order integrations; delivery receipts; network/privacy and adversarial testing; an original licensed voice recording if exclusivity is desired; hardware microphones, physical mute, camera, lighting, boot/recovery, signed updates, provisioning and manufacturing validation. Kids mode currently hides adult records and blocks external tools, but a local user can change the mode; it is not authenticated parental control. Ambient command detection is experimental. No production reliability, shipping date or retail price is established by this prototype.

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -p test_agent_runtime.py
.venv/bin/python -m compileall -q src/luma
```

## Upstream references

- [Kokoro model card and Apache 2.0 weights](https://huggingface.co/hexgrad/Kokoro-82M)
- [Kokoro ONNX runtime](https://github.com/thewh1teagle/kokoro-onnx)
- [Twilio Message API](https://www.twilio.com/docs/messaging/api/message-resource)

The public sales page is https://lumin-holdings-site.vercel.app/luma. This localhost control app is a separate device interface; it is intentionally not exposed on the public holding-company website.
