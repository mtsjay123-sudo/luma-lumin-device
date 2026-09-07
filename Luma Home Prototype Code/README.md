# LUMA — MVP repository

> **September 7, 2026 implementation status:** Start with [RUNTIME.md](RUNTIME.md) for the working local agent, phone pairing, personal texting, appointments, groceries, personality controls and remaining work. The build plan below describes the intended product; its pricing, shipment dates, privacy and capability claims are not evidence that those milestones are complete.

Ambient AI companion device. $199 retail. On-device LLM + STT + TTS. Privacy-first. No wake word.

**This README is the source of truth for Claude Code.** Read it before writing any code.

For day-by-day human-readable instructions, see `../LUMA Build Plan/LUMA_90_Day_Build_Plan.docx`.

---

## Build approach: SOFTWARE FIRST, on macOS

We are building the complete LUMA software experience on a MacBook first. Every feature on the website is testable on a laptop with the built-in microphone and speakers — no special hardware required for Phase 1.

**Phase 1 (Days 1–35): Complete software MVP on Mac.** Generic voice (Kokoro default), system-prompt personality (no fine-tune yet), simulated hardware (keyboard-hotkey privacy switch, terminal-output adaptive lighting), no cloud integrations yet. Every behavior the website promises works as software.

**Phase 2 (Days 36–60): Sound human + do real tasks + connect properly.** Record voice actor, clone the voice, fine-tune Llama on personality dataset. Then add opt-in cloud integrations (weather, news, calendar, music, web search). Then verify with Wireshark that nothing leaves the device unless the user explicitly enabled an integration. Then 5-person blind human test — does LUMA feel human? does it do real tasks?

**Phase 3 (Days 61–90): Hardware + manufacturing path + investor demo.** Port to Jetson Orin Nano with real microphone array, hardware privacy switch, Neopixel ring, camera, OLED. 3D-printed enclosure. SoC selection for production. Contract manufacturer outreach. FCC budget. YC W27 submission Day 82.

## Architecture: on-device + opt-in cloud (not 100% local)

The privacy claim is more nuanced than "everything stays on the device." Here's what's actually true:

**On-device, always (no internet required):**
- LLM inference (Llama 3.2 3B)
- Speech-to-text (Whisper)
- Text-to-speech (Kokoro + cloned voice)
- Memory (encrypted SQLite + sqlite-vec)
- Address detection
- Crisis safety detection + 988 routing
- Proactivity engine
- Kids mode + content filter
- Smart home (Home Assistant runs locally on the home network)

**Opt-in cloud integrations (off by default, user toggles on):**
- Weather (Open-Meteo — free, no API key, anonymous)
- News (RSS feeds: NYT / BBC / Reuters — free, no API key)
- Calendar (Google OAuth — free)
- Music (Spotify OAuth — user has Spotify Premium)
- Web search — see "Web search architecture" below
- NTP time sync (system clock)
- OTA software updates (via Cloudflare R2 — zero egress fees)

**Web search architecture (dual backend):**
LUMA's web search has TWO interchangeable backends behind the same `search()` interface:

1. **Perplexity API** — used in the 90-day prototype phase (Day 56) as the quality benchmark. Best answers, citations, fast. Costs ~$5 per 1,000 queries.
2. **Free combo: DuckDuckGo + Wikipedia + Reddit** — built same day. Free, no API keys, our own pipeline. Less polished than Perplexity but covers the common cases.

We run both side-by-side during Phase 2 testing (Day 56 comparison test). At ship time, the free combo is the default; Perplexity becomes a LUMA Plus perk for users who want top-tier web answers. This lets us tell investors: "Web search is not a Perplexity wrapper — we have our own pipeline. Perplexity is one optional premium upgrade among many."

**Infrastructure cost story for investors:**
- OTA updates: Cloudflare R2 (zero egress fees). At 250,000 units, OTA costs ~$100/year total.
- Web search: free combo costs $0; Perplexity costs ~$0.005 per query (offset 60× by LUMA Plus at $9.99/mo).
- Per-conversation cloud cost: $0 (LLM/STT/TTS all on-device).

**The privacy story for investors:** Wireshark capture shows zero outbound packets with all integrations off. Then we enable Weather — one labeled outbound call to api.open-meteo.com, nothing else. That's the proof. Not "magic local-only" — engineered transparency.

---

## What we're building

LUMA is an ambient AI companion that lives in a household. It:

- Listens without a wake word (address detection via content + prosody + context)
- Runs the LLM, STT, and TTS on-device (no cloud round-trip for default interactions)
- Remembers people, routines, and goals locally (SQLite + sqlite-vec)
- Controls smart home devices via Home Assistant
- Has crisis safety routing (988)
- Has proactive emotional check-ins with rate limits + quiet hours + hush mode
- Has kids mode with parent profiles, content restrictions, activity hours, weekly summaries
- Pairs with Meta Ray-Ban glasses for vision (Phase 2)
- Hardware privacy switch (Phase 2 on Jetson; keyboard-simulated in Phase 1 on Mac)
- Sounds like LUMA (Phase 2 — Llama 3.2 3B fine-tuned + Kokoro voice clone)

**Pricing:** $199 retail · $9.99/mo LUMA Plus subscription · ships late 2026.

---

## Tech stack

| Layer | Component | Why |
|---|---|---|
| LLM | Llama 3.2 3B-Q4 (GGUF) via llama-cpp-python | Small enough for laptop CPU + Jetson Orin Nano |
| STT | faster-whisper (base.en) | Fastest CPU/GPU Whisper variant, 39M params |
| TTS | Kokoro-82M (ONNX) | Tiny, high-quality, runs on CPU |
| VAD | silero-vad | Industry standard, <1ms inference |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Small, fast, good for semantic memory |
| Memory | SQLite + sqlite-vec | Local, encrypted, vector search built in |
| Audio I/O | sounddevice (PortAudio) | Cross-platform Mac/Linux |
| Address detection | sklearn ensemble + librosa for prosody | v1 — content + prosody, no gaze yet |
| Orchestrator | Python 3.11 + asyncio | Native to the rest of the stack |

---

## Hardware — for Phase 2 only (Mac MVP doesn't need any of this)

- Jetson Orin Nano Super 8GB — $249 — main compute
- ReSpeaker Mic Array v2.0 — $80 — 4-mic far-field array
- Adafruit 3W speaker + amp — $35 — audio out
- Pi Camera Module 3 — $40 — vision input
- Waveshare 1.28" round OLED — $20 — status display
- 256GB NVMe SSD — $30
- 5V/4A USB-C PSU — $15
- SPDT mute switch + LED — $10 — hardware privacy switch
- Neopixel RGB ring (24 LEDs) — $15 — adaptive lighting
- 3D-printed PETG enclosure — $30–80 (Phase 3)

**Hardware is ordered Day 36, after the Mac MVP is proven.** Until then, all development happens on macOS with CPU inference + built-in mic/speaker.

---

## Repo structure

The parent "Luma Home Prototype/" folder holds docs (LUMA Build Plan/, Legal & Corporate/, Website/) AND the code subfolder. The git repo root is "Luma Home Prototype Code/". Claude Code opens THAT folder.

```
Luma Home Prototype/                          # parent — docs + code, NOT the repo root
├── LUMA Build Plan/                          # docs, sibling of the code folder
│   ├── LUMA_90_Day_Build_Plan.docx
│   ├── How_LUMA_Actually_Works.docx
│   └── ...
├── Legal & Corporate/
├── Website/
└── Luma Home Prototype Code/                 # ★ CODE LIVES HERE — repo root for Claude Code
    ├── README.md                             # this file
    ├── pyproject.toml
    ├── requirements.txt
    ├── .env.example
    ├── .gitignore
    ├── src/
    │   └── luma/
    │       ├── __init__.py
    │       ├── config.py
    │       ├── orchestrator.py
    │       ├── audio/
    │       │   ├── io.py
    │       │   ├── vad.py
    │       │   ├── stt.py
    │       │   └── tts.py
    │       ├── llm/
    │       │   ├── inference.py
    │       │   └── prompts.py
    │       ├── memory/
    │       │   ├── store.py
    │       │   └── embeddings.py
    │       ├── address_detection/
    │       │   ├── classifier.py
    │       │   ├── content_features.py
    │       │   ├── prosody_features.py
    │       │   └── train.py
    │       ├── integrations/
    │       │   └── home_assistant.py
    │       ├── safety/
    │       │   └── crisis_detector.py
    │       ├── proactivity/
    │       │   └── engine.py
    │       ├── kids_mode/
    │       │   ├── profiles.py
    │       │   ├── content_filter.py
    │       │   └── activity_hours.py
    │       ├── modes/
    │       │   └── store.py
    │       ├── cloud/
    │       │   ├── weather.py
    │       │   ├── news.py
    │       │   ├── calendar.py
    │       │   ├── music.py
    │       │   ├── vision.py
    │       │   └── web_search/
    │       │       ├── perplexity.py
    │       │       └── free_combo.py
    │       └── hardware/
    │           ├── privacy_switch.py
    │           └── lighting.py
    ├── data/
    │   ├── personality_dataset/
    │   ├── address_detection/
    │   └── voice_actor/
    ├── models/                               # gitignored (model weights are large)
    ├── scripts/
    │   ├── setup_mac.sh
    │   ├── setup_jetson.sh
    │   ├── download_models.sh
    │   ├── chat.py
    │   ├── luma_settings.py
    │   ├── luma_parent.py
    │   └── luma_mode.py
    └── tests/
        ├── test_voice_loop.py
        ├── test_memory.py
        ├── test_address_detection.py
        ├── test_crisis.py
        └── compare_web_search.py
```

---

## How Claude Code should work on this repo

1. **Always read `README.md` and the relevant section of `LUMA_90_Day_Build_Plan.docx` for the current day before writing code.**
2. **One commit per task.** Use clear messages: `feat(stt): integrate faster-whisper` or `fix(audio): resolve sample rate mismatch`.
3. **Write tests as you go** — `tests/` mirrors `src/luma/` structure. Pytest.
4. **All paths come from `config.py`** — never hardcode file paths in modules.
5. **Environment-specific code goes in `scripts/`** — Mac vs Jetson setup lives there, not in the application code.
6. **Don't add dependencies that aren't justified by the day's task.** The stack table above is the allowed list.
7. **Audio interfaces are platform-aware.** Mac uses CoreAudio via sounddevice; Jetson (Phase 2) uses ALSA. The `audio/io.py` module abstracts this — don't write platform-specific code elsewhere.
8. **Privacy is non-negotiable.** No outbound network calls except where explicitly required (OAuth integrations in Phase 2). If you add an outbound call, gate it behind a config flag defaulted off.
9. **Phase 1 = software only on Mac.** No code that requires Jetson, GPIO, ReSpeaker, real LEDs, or Pi Camera. Simulate via keyboard / terminal output / mock.

---

## Privacy & data handling — non-negotiable rules

- Mic and camera are OFF by default. Phase 1: keyboard-toggled. Phase 2: hardware switch on GPIO.
- All LLM/STT/TTS inference is on-device. Cloud calls only for explicit opt-in integrations.
- Memory store lives at `~/.luma/memory.db`, encrypted at rest (SQLCipher).
- One-tap "delete everything" wipes the memory DB, the dataset, and any cached embeddings.
- No telemetry. No analytics. No crash reporting that leaves the device.
- Wireshark zero-egress capture (Phase 3) is the proof.

---

## Glossary (for non-engineers)

| Term | Plain English |
|---|---|
| LLM | The "brain" — generates LUMA's replies (Llama 3.2 3B) |
| STT | Speech-to-text — turns mic audio into words (Whisper) |
| TTS | Text-to-speech — turns LUMA's reply into audio (Kokoro) |
| VAD | Voice activity detection — knows when someone is speaking |
| Address detection | "Are they talking to me?" — the wedge against Alexa's wake word |
| Embedding | A numerical fingerprint of text used for semantic memory recall |
| QLoRA | A cheap way to fine-tune a big model on a small dataset |
| GGUF | A file format for quantized LLMs (smaller, faster) |
| Quantization | Squeezing a model down to use less memory (Q4 = 4 bits per weight) |
| GPIO | The physical pins on the Jetson that read switches and light LEDs |
| Systemd | Linux's service manager — starts processes on boot |
| OTA | Over-the-air — how the device gets software updates |
| CM | Contract manufacturer — the factory that builds the units at scale |
| SoC | System on Chip — the main processor (Qualcomm/Rockchip/NXP candidates) |

---

## Status

- **Day:** 3 (May 18, 2026)
- **Phase:** 1 (Mac software MVP)
- **This week:** Mac dev setup + voice loop (LLM → STT → TTS → chain → mic)
- **Hardware:** Not needed for Phase 1. Ordered Day 36 (after MVP works).
- **Next milestone:** Day 7 — fully hands-free voice loop on Mac (talk to LUMA, LUMA replies)

Last updated: 2026-05-18
