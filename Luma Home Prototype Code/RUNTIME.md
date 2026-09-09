# Latest companion build — September 8, 2026

The new controls and behavior are documented in [docs/COMPANION_UPGRADES.md](docs/COMPANION_UPGRADES.md). Device setup, boot service, privacy feedback, diagnostics and recovery are documented in [docs/DEVICE_SETUP.md](docs/DEVICE_SETUP.md). The older notes below describe prior validation; they are not the current complete feature list.

# Luma — personal home companion runtime

Updated September 7, 2026. Open **http://127.0.0.1:8095/** on this Mac. This is a working software prototype with a local language model and connected action adapters. It is not a finished hardware appliance or an assistant with unrestricted access to every merchant.

## Start and use it

Double-click `scripts/start_luma.command`, or run:

```sh
cd '/Users/marvinjohnson/Desktop/Lumin Universe Holding Company/All of Lumin/Luma Home Prototype/Luma Home Prototype Code'
.venv/bin/python -m luma.cli serve
```

The launcher is also at `Desktop/Amiri_2026_Execution/Luma/Start Luma.command`. Keep the terminal/runtime running. Startup mutes the microphone; enable it explicitly in the app. `--no-model serve` runs local tools without conversation inference. CLI `chat`, `--voice chat` and `--hands-free chat` remain available; `/help` lists controls.

Try “Hey Luma, can you text my mom to pick up the groceries while she is out?” after saving Mom in People & Texts. Common natural text requests preserve their requested content through a fast path. Other conversation uses the local model and its available tools. Unknown people are not guessed. Send actions still show the exact recipient, message and route before submission.

## What now works

| Capability | Actual behavior |
| --- | --- |
| Local conversation | GGUF inference with constrained action schemas, bounded context, and runtime validation. See the live model name in Personality. |
| Personality | Persisted preferred name, warm/direct/playful tone, everyday/contemporary/classic language and reply length. Preferences can be changed in the app or requested conversationally. The model adapts without assuming an age. This is personalization, not weight fine-tuning. |
| Hearing and speaking | Local Whisper, Silero voice activity detection and Kokoro. Luma's stock-style voice blend is 70% af_bella/30% af_heart. It is not an exclusive actor recording. |
| Memory and routines | Explicit encrypted memories, keyword recall, persistent reminders, daily routines, quiet hours, hush and completion controls. |
| Contacts | Encrypted local contact book with exact name/number resolution. No automatic reading of phone contacts. |
| Mac Messages | Reviewed sends through a specifically selected iMessage or SMS account on this Mac. Requires account setup and Apple's Automation permission. Does not silently change transport or claim delivery. |
| Twilio | Alternative reviewed SMS through a configured Twilio number, plus real delivery-status lookup. Queued/sent is distinct from delivered. |
| Phone drafts | Copy a prepared message and open Messages on the phone, then tap Send yourself. Nothing is sent by generating a draft. |
| Phone companion | One-use QR invitation, HTTPS, expiring credentials and immediate revocation. Requires a reachable private network. The current runtime does not expose a usable home Wi-Fi address, so a physical phone has not been paired. |
| Appointments | Cal.com availability, exact slot selection, attendee review, booking creation and receipt refresh for configured free services. Paid, recurring/group and unsupported authenticated bookings remain on the provider. |
| Groceries | Real Instacart shoppable-list creation with exact items/quantities and nearby-retailer lookup. Food Lion is shown only if the provider returns it for the requested area. |
| Shopping/payment | Review matched products, final prices, stock, fees and delivery in merchant checkout. The merchant's saved wallet handles payment. Luma has not placed a grocery order and does not store raw cards/CVCs. |
| Web and lights | Opt-in Brave search and allowlisted Home Assistant lights. Both require their provider setup. |

## Connect your phone and own messaging account

For own-account messaging, use **People & Texts → Send through → This Mac's Messages**. Set up Messages on the Mac first and check its sending identity. For ordinary SMS, enable iPhone Text Message Forwarding to the Mac. Selecting the route does not bypass Apple's account or Automation controls. Sending identity is determined by Messages settings; it is not automatically guaranteed to be a particular mobile number. The first reviewed send may require a macOS permission prompt.

Phone pairing is separate from SMS identity. Use **Your phone** to start the home-network HTTPS connection and generate a QR. Scan it on the same network, trust the development certificate explicitly, and name the device. Invitations expire in ten minutes; paired access expires after thirty days and can be revoked immediately. Phone access can prepare/approve actions, but device, integration and pairing administration stays on the Mac. This is not away-from-home access and does not import contacts, grant native iMessage permissions, or install a native iPhone app.

The runtime currently sees a special routed address rather than an RFC1918 home-network address. Consequently, live phone pairing needs the runtime to run with access to the actual home LAN or a separately configured private connection. No public tunnel or unprotected listener was created.

## Connected-service setup

Use `.env.example` as a reference; do not overwrite an existing `.env`. Fill credentials locally, restart, then enable the relevant integration in the app. Credential values are never sent to the browser.

- Brave: `BRAVE_SEARCH_API_KEY`.
- Twilio: account SID, auth token and sender number in the documented `TWILIO_*` fields.
- Cal.com: `CAL_COM_API_KEY` and `LUMA_CAL_EVENT_TYPES_JSON`, for example aliases mapped to event type IDs you can book.
- Instacart: Developer Platform `INSTACART_API_KEY`, with the correct production/development environment.
- Home Assistant: local URL/token plus `LUMA_ALLOWED_LIGHTS`.

These accounts have not been created or verified for you. No real text, appointment, shopping list, order, payment or light command was submitted during tests.

## Data and execution

Encrypted payloads live in `~/.luma/agent/state.db`, with its restricted-permission key at `state.key`. IDs and timestamps remain visible SQLite metadata. Back up both securely. Losing the key prevents recovery. Conversation turns stay in RAM; explicit memories, contacts, preferences, drafts, actions and receipts persist. Card-like numbers/passwords are rejected as memory.

Actions have one-use confirmations, expiration and consent checks. Uncertain sends/bookings are never silently retried. Pairing is atomic and stores token hashes in encrypted records. The phone listener requires TLS and validated Host/Origin; its root page never grants an owner cookie. Physical mute, authenticated parental controls and robust multi-person/wake-word-free address detection remain development work.

## Validation and next work

108 focused tests passed, including a real TLS companion client, revocation, exact contact resolution, Mac send argument isolation, booking availability/confirmation, grocery-list provenance and prompt schemas. Desktop and 390px mobile browser checks found no horizontal overflow or JavaScript errors. An isolated browser test exercised contact creation, a grocery message draft and a reviewed appointment receipt using fake provider transport; no live transactions occurred.

The local Llama comparison exposed invented grocery items, so common natural message phrasing now preserves the requested content deterministically. Qwen3-4B-Instruct-2507 Q4_K_M is now selected on this Mac and has answered through the live browser. Common style changes and grocery setup handoffs also use immediate local routes. [MODEL_AND_PERSONALITY.md](MODEL_AND_PERSONALITY.md) and [MODEL_EVALUATION.md](MODEL_EVALUATION.md) record model provenance, timings and the weaknesses found in testing. These small evaluations do not establish perfect reliability.

Next meaningful integrations are verified merchant product/price/stock feeds and transactional order access, calendar synchronization, authenticated parent/household profiles, and physical-device validation. A shopping-list URL is not an order receipt, and web snippets do not prove the cheapest available total.

Detailed adapters: [Mac Messages](MAC_MESSAGES.md), [phone pairing](PHONE_CONNECTION.md), [appointments](BOOKINGS.md), [groceries](COMMERCE.md). The separate public product landing page is https://lumin-holdings-site.vercel.app/luma.
