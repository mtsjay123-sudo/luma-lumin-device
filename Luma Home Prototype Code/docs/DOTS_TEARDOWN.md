# How ChatGPT's dots work: a teardown, and the small version we can build

October 13, 2026. Done from a Linux cloud sandbox with REA 6.4.0 and OpenAI's open-source Codex code.

## The honest limits first

- **I could not download the ChatGPT desktop app itself.** This sandbox's network policy blocks `persistent.oaistatic.com` (the download host), `chatgpt.com` and `openai.com`. Allow `persistent.oaistatic.com` in the environment's network settings and the app bundle can be inspected directly.
- **I did not have your Desktop folder.** The sandbox is in the cloud, not on your Mac.
- **REA's Mach-O and code-signature inspectors need macOS.** On Linux they refuse (`capability_unavailable: Native macOS utilities require macOS`), and Ghidra/Hopper/IDA aren't installed. Where REA couldn't run, I parsed the binaries with Python's `lief` and `strings`, and say so.

What I could reach and inspect:

1. The **Homebrew casks** for `chatgpt` and `codex-app`: public install metadata, including OpenAI's download URLs, bundle ID and support files.
2. **`@openai/codex@0.162.1-darwin-arm64`** from npm. These are OpenAI's signed macOS engine binaries: `codex` (247 MB), `codex-code-mode-host` and `codex-voice-host`.
3. **`github.com/openai/codex`** at commit `12cca49`: the Apache-2.0 source of that engine and its app-server protocol.
4. **GitHub issue openai/codex#49978**: a user's bug report about dots in the ChatGPT app.

Each finding is marked **Proven** (read directly from a file named here), **Inferred** (follows from the evidence but isn't shown by it) or **Unknown** (server-side, closed, or out of reach).

## 1. What a "dot" is, and where it lives

| Finding | Level | Evidence |
|---|---|---|
| Dots run inside the ChatGPT desktop app; there's no separate Dots app | Proven (public metadata) | The `chatgpt` cask installs one app, `ChatGPT.app`. Issue #49978 shows dot UI inside "ChatGPT app, version 26.928.31416, build 12553". |
| The ChatGPT desktop app **is the former Codex desktop app** | Proven (public metadata) | The `codex-app` cask is `deprecate! date: "2026-07-12", because: :discontinued, replacement_cask: "chatgpt"`. Both casks quit `com.openai.codex` and download from `persistent.oaistatic.com/codex-app-prod/`. |
| Bundle ID `com.openai.codex`, support data in `~/.codex`, `~/Library/Application Support/Codex` | Proven (public metadata) | `chatgpt.rb` `uninstall quit:` and `zap trash:` lists |
| The app includes a computer-use service, `com.openai.sky.CUAService`, plus `CodexComputerUseAuthorizationPlugin` | Proven (public metadata) | `chatgpt.rb` zap paths: `~/Library/Group Containers/*.com.openai.sky.CUAService`, `/Library/Application Support/CodexComputerUseAuthorizationPlugin` |
| "Sky" is the Mac computer-use assistant OpenAI acquired | Inferred | Only the `com.openai.sky` bundle prefix ties them together |
| Dots bugs are tracked in the `openai/codex` repo under labels `agent, app, bug, dots` | Proven | Issue #49978 |
| The desktop shell is Electron | **Inferred, not proven** | The download is `ChatGPT-darwin-arm64-<version>.zip`, which is Electron Forge's default zip naming. Proving it needs `Contents/Frameworks/Electron Framework.framework` from the real bundle. |
| Each dot has "its own cloud computer", runs around the clock and learns from feedback | Unknown (OpenAI's description only) | Search results quoting openai.com/index/introducing-dots. None of this logic appears in any file I could read. |

## 2. The engine the app runs locally

These files are OpenAI-signed binaries from npm. The app's actual bundle may embed a different build.

| Finding | Level | Evidence |
|---|---|---|
| Signed by **Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)** | Proven | The CMS blob in each binary's `LC_CODE_SIGNATURE` (read with `lief`) |
| `codex` entitlements: only `cs.allow-jit` and `cs.allow-unsigned-executable-memory` | Proven | Embedded entitlements plist |
| `codex-voice-host` (`com.openai.codex.voice-host`) asks only for `device.audio-input`. It links CoreAudio, AudioToolbox and GStreamer with an Opus codec. | Proven | Entitlements and load commands |
| `codex` links AppKit, LocalAuthentication, Security, SystemConfiguration and IOKit | Proven | Mach-O load commands |
| LocalAuthentication is used for a native "user verification" (Touch ID style) prompt before sensitive actions | Inferred from source | `app-server/README.md`, "User verification (experimental)": `userVerification/verify`, OS prompt |
| The UI talks to the engine over **JSON-RPC ("app-server")**: `thread/start`, `turn/start`, streamed `item/agentMessage/delta`, `item/commandExecution/requestApproval`, `thread/queue/*`, `thread/realtime/*` (voice), `memory/*`, `plugin/search`, `mcpServer/*`, `account/*` | Proven (source) | `codex-rs/app-server-protocol/src` method names |
| That the ChatGPT app uses exactly this app-server | Inferred | Same team, same bundle ID, same repo for dots bugs. Not visible without the bundle. |

## 3. How it captures input, thinks, and answers

| Step | Level | Evidence |
|---|---|---|
| **Input**: typed messages, voice (realtime audio over WebRTC/WebSocket), attachments and images | Proven (source and binary) | `thread/realtime/appendAudio`, `appendText`; config keys `realtime`, `audio`; the voice host binary |
| **Model calls**: the Responses API, over HTTPS or a WebSocket at `/responses`. With a ChatGPT login the base is `https://chatgpt.com/backend-api/codex`; with an API key it's `api.openai.com/v1` | Proven (source and binary strings) | `codex-api/src/endpoint/responses_websocket/connector.rs`; the binary contains `https://chatgpt.com/backend-api/`, `/v1/responses`, `/v1/realtime`, `/v1/files` |
| Voice: `https://chatgpt.com/backend-api/codex/realtime/calls` | Proven (source) | `codex-api/src/endpoint/realtime_call.rs` |
| **Apps / plugins** (the "4,000 apps") are hosted MCP servers named `codex_apps`, reached by connector ID and per-account link | Proven (source) | `app-server/README.md`, "Hosted Codex Apps MCP protocol" (`target: {connectorId, linkId}`) |
| App results can render as a widget, `inline` or `fullscreen` | Proven (source) | "MCP App UI": `mcpAppUi.preferredModelDisplayMode` |
| **Acting on your computer**: config switches `computer_use` (macOS `bundle_ids` allowlist, Windows `aumids`/`exes`), `browser_use`, `in_app_browser`, `allow_browser_and_computer_use` | Proven (binary strings) | `ComputerUseConfigToml`, `ComputerUseMacosConfigToml.bundle_ids` in `codex` |
| **Goals and long-running work**: `goals.max_goal_token_budget`, `job_max_runtime_seconds`, `thread/queue/*` | Proven (binary strings and source) | config key names in `codex` |
| **Memory**: a two-phase pipeline. It extracts memories from conversations, consolidates them, and injects them into later turns with citations. | Proven (source) | `codex-rs/memories/README.md`, `read/templates/memories/read_path.md`, `write/templates/memories/consolidation.md` |
| **Reaching you on its own**: feature flags `send_message_to_user_async` and `agent_message_board`, both "UnderDevelopment" in this open build | Proven (source) | `codex-rs/features/src/lib.rs` |
| **Phone pairing**: `remoteControl/pairing/status` with `pairingCode` / `manualPairingCode`, and device rows carrying `deviceType` and `lastSeenAt` | Proven (source and binary) | `app-server/src/request_processors/remote_control_processor.rs` |

## 4. How it decides what it may do alone

| Finding | Level | Evidence |
|---|---|---|
| A second model, **Guardian**, reviews planned actions ("auto-review"). It scores user authorization (high, medium, low or unknown) against a risk taxonomy (low, medium or high). | Proven (source) | `codex-rs/prompts/templates/guardian/policy_template.md` |
| Guardian trusts only user and developer messages. Tool output, plugin descriptions and the agent's own words are "untrusted evidence" that can't widen approval. | Proven (source) | Same file, "Evidence Handling" |
| Too many denials abort the turn (`tooManyDenials`) | Proven (source) | `app-server/README.md`, "Guardian circuit-breaker errors" |
| The dots message "Auto-review did not approve some recent actions, so your dot was paused" is this circuit breaker | Inferred | The wording matches issue #49978; the source of the dots wiring isn't public |
| Custom rules (allow, require approval, block) map to `approval_policy`, `approvals_reviewer`, `auto_review.policy` / `extra_policy`, and managed `requirements` | Inferred | Config keys present in the binary; the dots rule editor itself isn't visible |

## 5. The friendly characters

| Finding | Level | Evidence |
|---|---|---|
| The app has **pets**: animated WebP spritesheets (Codex, Dewey, Fireball, Rocky, Seedy, Stacky, BSOD, Null Signal) downloaded from `persistent.oaistatic.com/codex/pets/v1/<name>-spritesheet-v4.webp`, about 8 fps | Proven (source and binary) | `tui/src/pets/catalog.rs`, `asset_pack.rs`; the binary contains `https://persistent.oaistatic.com/codex/pets/v1` and "Failed to load pet" |
| A pet's animation follows the agent's state (running, waiting, needs review, failed), each shown for a set time | Proven (source) | `tui/src/pets/ambient.rs`: `RUNNING_LIFETIME`, `WAITING_LIFETIME`, `REVIEW_LIFETIME`, `FAILED_LIFETIME` |
| Dots' mascots (the heart with sunglasses, the frog in a bow tie, the beret cloud) use the same system, with a status line under the avatar | Inferred | They match the pets mechanism; dot avatars aren't in the open code |

## 6. What can't be known from here

- How a dot's **cloud computer** is provisioned, isolated, scheduled and kept alive. It's server-side.
- The **GPT-6 Astra** model, its system prompts for dots, and how dots learn from feedback. Server-side.
- Dot identity, Slack/Teams delivery and the backend for plugin permissions. Server-side.
- The ChatGPT app's own UI code, bundle layout, frameworks, `Info.plist` and entitlements. Blocked by this sandbox's network policy; inspect `/Applications/ChatGPT.app` on your Mac, or allow the download host.

## 7. The smallest Dots you can build, and how Luma already maps to it

```
 ┌────────── Desktop app (Electron shell) ─────────────┐
 │  chat column  ·  mascot + status line  ·  work panel│
 └───────────────▲─────────────────────────────────────┘
                 │ HTTP/JSON on 127.0.0.1 (like app-server)
 ┌───────────────┴───── Local agent runtime ───────────┐
 │ planner (LLM) → tools → approval gate → results     │
 │ memory · reminders/goals · contacts · decks · browser│
 └──────▲──────────────────────▲───────────────────────┘
        │ model calls          │ outbound reach
  local Qwen3-4B          Luma Cloud relay (texts, phone app, push)
```

1. **Shell**: an Electron window with a chat column, a mascot, and a side panel for the thing being made. It starts the runtime if it isn't running. *Luma: built in `desktop/`.*
2. **Runtime ("app-server")**: one local process with an HTTP/JSON API: send a message, list pending approvals, approve or cancel, list files and events. *Luma: `luma.control.server` on port 8095.*
3. **Model loop**: plan, call a tool, observe, answer. You need a model with structured output; a grammar-constrained JSON planner is enough. *Luma: Qwen3-4B with a JSON grammar, on the device, no API bill.*
4. **Tools as plugins**: start with messages, reminders, notes and memory, documents (decks), and a sandboxed browser. Add MCP servers later for the long tail of apps. *Luma: all of these exist.*
5. **Approval gate (the Guardian idea, minus the second model)**: every side effect becomes a pending action with a one-time token. Plain rules decide; the model never approves itself. Untrusted page and tool text can't widen permission. *Luma: `propose` → `confirm(id, token)`; the browser's sensitive actions always ask.*
6. **Always-on**: a scheduler tick for reminders, check-ins and replies, plus a way to reach you when you're away. *Luma: `tick()`, presence, and the phone app with push.*
7. **Character**: a pet whose animation follows the agent's state: idle, thinking, working, waiting for you, done, stuck. *Luma: the Luma mascot in the desktop app.*

What we deliberately do differently from dots: the brain runs on your own device, so there's no per-task cloud bill and no cloud computer reading your screen. Messages to and from your phone are end-to-end encrypted.

## Sources

- [Introducing dots (OpenAI)](https://openai.com/index/introducing-dots/) and [OpenAI on X](https://x.com/OpenAI/status/2104984504133918973). These were read through search results, since openai.com is blocked from the sandbox.
- [Homebrew `chatgpt` cask](https://github.com/Homebrew/homebrew-cask/blob/master/Casks/c/chatgpt.rb) and [`codex-app` cask](https://github.com/Homebrew/homebrew-cask/blob/master/Casks/c/codex-app.rb)
- [openai/codex](https://github.com/openai/codex) (commit `12cca49`) and [issue #49978](https://github.com/openai/codex/issues/49978)
- npm `@openai/codex@0.162.1-darwin-arm64` (sha256 of `bin/codex`: `74c6a6d2…bdfc0`)
