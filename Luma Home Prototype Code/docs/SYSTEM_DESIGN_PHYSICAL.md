# Luma, physical: device, app, computer

How Luma works once it's a thing on your counter. Every person has three pieces:

1. **The device.** It's always on, at home, with a mic, a speaker and the brain. It owns your data.
2. **The phone app.** Today's chats, your memory, device status (storage left), projects, and talking from
   anywhere.
3. **Your computer (optional).** In computer mode it becomes Luma's hands: the browser, your files and your
   apps. Anything that changes something asks first.

It also answers whether we should build on Nous Research's Hermes Agent (and Oh-My-Hermes on top).

## 1. Requirements

**Functional**

- Talk to the device by voice. Talk from the phone (Wi-Fi at home, the cloud relay away). Talk from the
  computer.
- The phone shows: today's chat chains, readable in full; memory as something you can browse and edit; device
  status (storage left, mic, brain, the connected computer); projects in progress; approvals.
- Computer mode: the device can use the connected computer's browser, granted folders and apps, with the
  owner's approval for anything that sends, buys, writes, deletes or types.
- Works with no computer at all. Works with no internet, apart from things that are online by nature.

**Non-functional**

- **Private by default.** Memories, chats and files live on the device, encrypted at rest. The cloud relay
  forwards sealed messages and stores nothing readable.
- **Fast.** Voice turn-taking feels conversational: first words in under about 1.5s on the device's brain,
  with streaming text-to-speech. Phone views load in under 1s on home Wi-Fi.
- **Never silently destructive.** Every risky action needs a yes from the owner, on a surface they're holding.
  Kids mode never gets the computer.
- **Recoverable.** The device restarts itself if the brain crashes, and backups are encrypted.
- **Scale.** One device per home. The cloud relay serves many homes, but each request is small and stateless.

**Constraints**

- A small team, and Python on the device. The existing pieces work and are tested: the agent runtime,
  encrypted store, projects engine, sandbox, Luma Link, phone companion, cloud relay and Electron app.
- Consumer setup: plug in, scan a code, talk. No terminals, no API keys.

## 2. High-level design

```
                  away from home                         at home (same Wi-Fi)
  ┌────────────┐   sealed msgs   ┌─────────────┐        ┌────────────────────────────────────┐
  │ Phone app  │◀──────────────▶│ Luma Cloud  │◀──────▶│  LUMA DEVICE (source of truth)     │
  │ (PWA)      │                 │ relay       │  out-  │  ├ voice: mic → STT → brain → TTS   │
  │ Today      │   LAN HTTPS     │ (stateless, │  bound │  ├ agent runtime + approvals        │
  │ Chats      │◀─────────────────────────────────────▶│  ├ encrypted store: memory, chats,  │
  │ Memory     │  pinned cert, phone token   │  only) │  │   projects, settings              │
  │ Device     │                 └─────────────┘        │  ├ projects engine + sandbox         │
  │ Projects   │                                        │  ├ /api/today  (phone's one call)   │
  └────────────┘                                        │  └ Luma Link host                   │
                                                        └───────────────▲────────────────────┘
                                                          pinned HTTPS  │  jobs ("hands")
                                                        ┌───────────────┴────────────────────┐
                                                        │  COMPUTER (optional, paired)        │
                                                        │  Luma Desktop app                   │
                                                        │  ├ hands: browser (Chrome bridge),  │
                                                        │  │  files (granted folders), apps,  │
                                                        │  │  screen look (opt-in)            │
                                                        │  ├ the same UI as the device        │
                                                        │  └ the `luma` command in a terminal │
                                                        └────────────────────────────────────┘
```

**The device is the source of truth.** The phone and the computer are windows onto it. If the device is
off, the computer can run Luma on its own (that's how Luma Desktop works today), and the two sync when they
meet.

## 3. Deep dive

### 3.1 Data ownership and storage

| Data | Lives on | At rest | Leaves the device? |
|---|---|---|---|
| Memories, about-you, contacts | Device store (SQLite) | Encrypted per row | Only as sealed relay messages to the owner's phone |
| Chat chains | Device store, per thread (the last 80 messages each) | Encrypted | Same as above |
| Projects and files | Device files folder | File system | Downloaded by the owner (phone, laptop or terminal) |
| Model weights | Device models folder | Plain | Never |
| Phone token, link peers | Device settings | Hashed | Never |

**Storage tracking.** `/api/today` reports total and free disk space on the device's data partition, and what
Luma itself uses (models, memory and chats, files). The phone shows "GB left" and warns below 10%. Models
are the big item. The studio brain alone is 100 GB or more, so the download already refuses a quant that
won't fit.

### 3.2 The phone's one call: `GET /api/today`

One request paints the whole home screen, which matters on a slow relay.

```json
{
  "name": "Jay",
  "chats":   [{"id": "a1b2", "title": "Taco truck plan", "messages": 14, "updated": 1793000000,
               "last": {"role": "luma", "text": "Two trucks downtown already…"}}],
  "memory":  {"used": 182, "limit": 200, "plan": "free", "recent": [{"id": "m1", "text": "…", "created": 1792990000}]},
  "device":  {"storage": {"total": 256.0, "free": 141.2, "luma": {"models": 21.4, "data": 0.3, "files": 1.1}, "unit": "GB"},
              "mic": "on", "brain": "Qwen3 30B (local)", "computer": {"paired": true, "here": true, "name": "Jay's MacBook"}},
  "projects": [{"id": "p1", "name": "Taco Rocket", "state": "running", "done": 3, "steps": 6}],
  "approvals": 1
}
```

- **Chats:** threads updated since local midnight first, then the rest. The chain itself comes from the
  existing `GET /api/threads/<id>`.
- **Memory:** the newest 24 for the deck. Edits go through the existing `/api/memory/save` and
  `/api/memory/delete`.
- **Auth:** the same as every phone call (the phone token cookie on LAN, a sealed envelope through the
  relay). Kids mode gets nothing personal.

### 3.3 Computer mode: the computer as Luma's hands

This is already built and stays the base. The device queues a job, the paired laptop polls
`/link/hands/next`, does it, and posts `/link/hands/done`. Today's jobs are open, play, read and tabs, all
through Chrome. This design extends them in tiers:

| Tier | Jobs | Rule |
|---|---|---|
| **Look** | `read` page, `tabs`, `files.find` / `files.read` in **granted folders only**, `screen.look` (a screenshot, if the owner turned on "Let Luma see my screen") | Allowed once the owner grants it in the computer's settings. Every look is logged. |
| **Open** | `open` a URL, `app.open` an app, `play` | Allowed. Luma says what it opened. |
| **Change** | Fill or submit a form, `files.write` / `files.move` in granted folders, app scripting (AppleScript or Shortcuts) | **Asks every time** on the phone or computer: "Allow" or "Not now". Anything that sends or buys follows the existing approval rules (one-time code over SMS). |
| **Never** | Passwords and payment fields, system settings, deleting outside granted folders, anything in kids mode | Refused in code, not just in the prompt. |

Safety mechanics:

- **Grants are folders.** Paths are resolved, and symlinks or `..` outside a grant are refused, the same check
  the projects folder uses. Nothing in `~/Library`, keychains or SSH keys, even if granted by mistake.
- **A visible indicator.** The desktop app shows a "Luma is using your computer" pill while hands jobs run.
  **Esc or one click stops it** and drops the queue.
- **An audit log** on both sides: every hands job, with the time, kind, target and result.
- **Full keyboard and mouse control** (true computer use, like ChatGPT's agent) is phase 2. It needs macOS
  Accessibility permission and a screenshot-act-verify loop. It ships behind the Change tier with a step
  counter and the same stop button.

**Built so far** (`src/luma/control/computer.py`, the Link client, and the `computer.*` tools):

- The **Look** and **Open** tiers: `files.find` and `files.read` in shared folders, `app.open`, and `screen.look`.
  The person at the computer turns each one on in Luma Desktop → Settings → "What Luma can do on this computer".
  The phone can't turn them on.
- Folders must sit inside the home folder or on an external drive. Hidden folders, `~/Library`, `AppData` and
  anything that looks like keys, passwords or wallets are refused, both when sharing and on every read. So are
  symlinks that lead out of a share and `..` paths.
- App names are checked before anything runs: no quotes, `&`, `;`, `|`, slashes or dots. Windows uses
  ShellExecute instead of `cmd`.
- **Pause** on the computer stops every request, Chrome jobs included, until it's resumed.
- Both sides keep a log. The computer keeps its last 200 requests and shows them in Settings. The device keeps
  its last 100, and the phone shows the most recent one on the Your Luma panel.
- A **Computer** rule (allow or block) is on the device, and kids mode never gets these tools.
- **Not built yet:** the Change tier, the live "Luma is using your computer" pill with Esc to stop, and phase 2.

### 3.4 Voice and turn-taking on the device

Mic, then voice detection, then speech-to-text (Whisper), then the brain (local; heavy jobs can go to the
cloud brain if the owner turned it on), then speakable text, then streaming TTS. The next step is barge-in
(stop speaking when the owner talks) and backchannels.

### 3.5 Failure handling

| Failure | Behavior |
|---|---|
| Brain process crashes | Restarts, falls back to the smaller brain, and tells the owner in plain words |
| Relay down | The phone works on home Wi-Fi; away from home it shows "Can't reach your Luma right now" |
| Computer asleep | Luma only offers computer tools while the computer is connected. A job that gets no answer in 40s ends with "Your computer didn't answer" |
| Disk nearly full | Warning at 10% free, and project runs stop at 2% |
| Device offline | The desktop app runs Luma locally and syncs memory when the device returns |

## 4. Scale and reliability

- **Per home:** one device. Load is one person talking. The heavy part is the brain, which is sized by RAM
  (4B, 30B or the studio brain).
- **Cloud relay:** stateless, horizontally scalable, and it holds only sealed envelopes in flight. At 100k homes
  and roughly 200 phone requests per home per day, that's about 230 req/s on average. Small.
- **Monitoring on the device:** brain health, disk free, last backup, hands-job errors. The phone's Device
  panel shows them, and the owner gets one alert when something needs a human.

## 5. Should we use Hermes Agent?

[Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research, MIT, Python) is a strong
open-source agent. It has:

- a terminal UI
- a gateway for Telegram, Discord, Slack, WhatsApp and Signal
- memory in small markdown files, with session search
- skills it writes itself after hard tasks
- a cron scheduler, subagents, and six sandbox backends

[Oh-My-Hermes](https://github.com/rlaope/oh-my-hermes) (MIT) sits on top. It adds:

- about 150 mostly engineering skills
- a parallel "graph" runner that sends each lane to a different paid cloud model
- memory that writes down why it kept or refused each item

**Recommendation: don't build Luma on Hermes, and don't ship Oh-My-Hermes. Take the skill format.**

| Question | Hermes | Luma today |
|---|---|---|
| Who sets it up | Developers. Install with `curl … \| bash` (Python 3.14, Node, ripgrep, FFmpeg), then `hermes setup` with API keys or a Nous Portal subscription. Messaging means creating your own bots. | Plug in, scan a code, talk. The desktop app installs everything itself. |
| Memory, skills, cron, subagents | Yes | Yes: encrypted memory, "teach a task", helpers on a schedule, project specialists with checks |
| Safety model | Broad terminal access, with approvals configurable | Approval gates in code, kids mode, an owner-only token, sandboxed code |
| Hardware | Laptop or server | Built for the device, with the computer as optional hands |
| Oh-My-Hermes | Coding DAGs across Claude, GPT and DeepSeek. A paid key for each, for engineers. | Not our users' job |

Rebuilding on Hermes would throw away the consumer setup, the approval gates and the voice. It would also give
every Luma owner a developer tool they didn't ask for. **What we take:**

1. **The open skill format (SKILL.md).** Hermes, Claude Code, Codex and others share it: a folder with a
   `SKILL.md` that has a name, a description and instructions. Luma loads skills from the `skills` folder next
   to its data (or `LUMA_SKILLS_DIR`). It picks up to two whose description matches the request and adds their
   instructions to the brain's context. Installed skills are treated as guidance, never as permission. They
   can't change approvals or tools, and installing one shows its text and asks the owner first. This is built:
   `src/luma/agent/skill_notes.py`, Settings → Skills in Luma Desktop, and `/api/skills`.
2. **The learning-loop idea.** After a project or a taught task works, Luma offers to save how it did it as a
   skill.
3. **More chat apps (later).** Hermes's single gateway for chat apps is a good pattern if owners want Luma in
   WhatsApp or Telegram, next to SMS.

Power users who already run Hermes can keep doing so. A future "hand this to Hermes" job could pass work to a
local Hermes install, but nothing in Luma depends on it.

## 5b. What we took from Open Dot

[Open Dot](https://github.com/composio-community/open-dot) is Composio's open-source take on OpenAI Dots. It's an
Electron and Next.js app that runs agents on a Mac with your own OpenAI or OpenRouter key, plus 1,500+ apps
through Composio. Its repo has **no license file**, so none of its code is copied into Luma. We rebuilt the
ideas that make it easy, in Luma's own Python:

1. **One sign-in, every app.** Luma connects to Composio's hosted MCP server (`https://connect.composio.dev/mcp`)
   with standard MCP sign-in: dynamic client registration and PKCE. There's no developer key, just the owner's
   own free Composio account, opened in their browser. In Connectors it's called "Gmail & 1,500+ apps".
2. **"Connect my Gmail" in two clicks.** Say it, or press Connect Gmail in Connectors. The first time, Luma
   opens the Composio sign-in, and the moment that finishes the browser goes straight on to Google's own Allow
   page. After that, every app is one Allow. `Agent.connect_app`, `/api/connect/quick_app`.
3. **Reads freely, asks before sending.** Through the hub, an action that only reads (fetch, list, search, get)
   runs on its own. Anything that sends, posts, creates, updates or deletes waits for the owner's yes, on a
   card in plain words: "Gmail · send email · to sam@… · subject …". A batch with one change in it asks.
4. **No remote shell.** The hub's remote bash and workbench tools are never handed to Luma's brain.

Not taken: Open Dot's cloud computers (E2B), its OpenAI Realtime voice (Luma's voice runs on the device), and
Composio triggers (they need a developer project key, which is not a consumer step). Triggers are worth
revisiting if Composio offers them to signed-in users.

## 6. Trade-offs, and what to revisit

- **The device is the source of truth, not the cloud.** That's more private and cheaper, but there's no
  backup if the device dies. Encrypted backup to the owner's computer exists; an optional encrypted cloud
  backup is next.
- **The phone is a PWA served by the device, not a native app.** One codebase that's always in sync, but no
  background push without the relay. Revisit when we need lock-screen voice.
- **Folder grants before full computer use.** They're slower to feel magical, but you can't lose a file to a
  bad click. Revisit once phase 2's act-verify loop is proven.
- **No Hermes runtime.** We keep control of setup and safety, at the cost of writing our own gateway when we
  add more chat apps.
