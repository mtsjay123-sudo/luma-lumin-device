# Luma's voice: phase one plan (demo by Nov 30)

Goal from the Lumin timeline, Layer 1: *"She talks like your friend."* Talking to Luma should feel
like talking to your funniest friend, in a voice that's hers alone.

## What shipped (October 24, 2026)

| Piece | What it does | Where |
|---|---|---|
| Speech plan | Texting shorthand said in full ("ngl gng" → "not gonna lie, gang"), laughs and sighs as cues, pauses where a person breathes (a beat after "okay so,", longer at "...", a bit longer after a question, the most between paragraphs) | `src/luma/audio/speakable.py`, `tts.speech_plan` |
| New natural voice | Chatterbox-Turbo (Resemble AI, MIT) or Qwen3-TTS 0.6B (Alibaba Qwen, Apache-2.0) on Apple Silicon through mlx-audio (MIT). Runs in its own process and Python. Learns Luma's existing voice from one short paragraph, so no real person's voice is copied. Before it talks, it times itself on this Mac and only takes over if it can keep up with a conversation. If a phrase comes out garbled (babbling on, or cut off), the classic voice says that phrase. The classic voice talks until it's ready and takes over if it stops or slows down. | `src/luma/audio/natural.py`, `voice_server.py`, `desktop/setup.js` |
| Quick or deep | When a question could go either way (news, politics, life advice, "explain…"), Luma asks in your register: "Not gonna lie, gang, how hard you want me to think about this? 😭 I can deep dive, but if you just want my answer right now, I gotchu." Quick → short honest answer. Deep → thinks it through from a few angles and checks itself. Remembers what you usually pick. News states today's date up front. | `src/luma/agent/depth.py` |
| Register + persona | Talks back the way you talk (slang if you use it, polished if you don't), laughs when it's actually funny, keeps spoken replies to 1–3 sentences, follow-up questions that keep it moving, fair on politics, never makes things up | `src/luma/llm/prompts.py`, `understanding.SLANG` |
| Listenable samples | Every push renders samples on a real Apple Silicon Mac: classic vs. expressive vs. studio, plus three designed candidate voices for Luma's own identity. Whisper then transcribes every file and scores it against the words it was meant to say (`check.json`), so a skipped or invented word shows up | CI job `voice` → artifact **Luma-voice-samples** |

## First results from a real Mac (CI, October 24)

Whisper checks every sample against the words it was meant to say (word error rate, 0 is perfect):

| Voice | Words heard wrong | Speed on GitHub's virtual M1 | Notes |
|---|---|---|---|
| Classic (Kokoro) | 1.8% | faster than real time | "Nah" heard as "No" |
| Expressive (Chatterbox-Turbo) | 2.2% | 2 to 4 times slower than real time, on the GPU | Every phrase came out right; "Bet." heard as "That" |
| Designed voices (Qwen3-TTS VoiceDesign) | 0% | about 40 seconds per line | Candidates for Luma's own voice |
| Studio (Qwen3-TTS 0.6B) | – | 3 to 8 times slower (first run) | Made empty audio with the longer reference; it now retries and reports what came out |

GitHub's runner is a small virtual Mac, much slower than a real one. Luma times the new voice on
each Mac before it talks, tries the smaller 8-bit and 4-bit builds if the full model can't keep up,
and keeps the classic voice if none can.

## Picking Luma's own voice

Right now the new models clone Luma's classic voice (a synthetic Kokoro voice, Apache-2.0), so
there's no consent question at all. For a voice that's *hers alone*:

1. Listen to `design-warm.wav`, `design-smooth.wav`, `design-late-night.wav` from the CI artifact.
   They're made from a written description (Qwen3-TTS VoiceDesign), not from anyone's recording.
2. Pick one (or describe changes). That clip becomes Luma's reference voice, shipped with the app.
3. Or cast a voice actor (below) and use their recordings, with a signed release.

## Training data: what we use, and what we don't

We don't scrape TikTok, YouTube, Instagram or X videos of creators to train Luma's voice or
personality. Their voices and content belong to them. Cloning or training on a real person's
voice without consent is covered by right-of-publicity and voice-likeness laws (Tennessee's ELVIS
Act, California's digital-replica laws, and others), and it breaks the platforms' terms. It's
also the first question an investor's lawyer will ask in December.

What gets us the same result, legally and better:

- **Language and slang** come from text, not voices: a generated conversation set (like the
  920-million-scenario understanding set Luma already has) covering how people really talk, plus
  the owner's own conversations with Luma, kept on their computer and used to match their style.
- **Voice talent with a release.** Book two or three voice actors whose natural speech is the vibe
  (paid, signed consent for AI voice use). About 1–2 hours each of the script below is enough to
  fine-tune Chatterbox or Qwen3-TTS on a rented GPU.
- **Openly licensed speech** for breadth: Mozilla Common Voice (CC0) has many accents and
  speakers who chose to donate their voices.
- **Opt-in from the community.** A "lend Luma your voice" page for HBCU students and creators who
  want in, with a clear release and credit. That's a story for the Reels too.

### Recording script for voice talent (sample)

Natural, unscripted-sounding lines, recorded casually, with laughs and pauses left in:

- "Okay wait, you're telling me he really said that? Nah. Nah, that's crazy."
- "Not gonna lie, I've been thinking about it all day... and I think you should go."
- "Bet, I got you. Give me like two seconds."
- "Hmm. Honestly? I don't know. Let's figure it out."
- "Stop playing, that's hilarious." (laugh)
- "Aww, I'm sorry. That's a lot. Take your time, I'm here."
- "So basically, the short version is: yes. The long version is a whole story."

## Next steps for the voice (toward the Nov 30 demo)

1. Listen to the CI samples and choose: Expressive (Chatterbox-Turbo) or Studio (Qwen3-TTS).
2. Pick Luma's own voice (design candidates or a voice actor).
3. Full-duplex conversation (talking over each other, "mm-hm" while you talk), the thing Dessa
   demos. Open models that do this on a Mac today: NVIDIA PersonaPlex 7B (MLX port) and Kyutai
   Moshi (CC-BY-4.0, MLX). Plan: a "hang out" mode that uses one of them for casual talk, while
   Luma's normal brain keeps doing tasks and memory.

## The projects you asked about, and where they fit

| Project | What it is | Status | Fit for Luma |
|---|---|---|---|
| **Dessa** (Block, Jack Dorsey's company) | Full-duplex speech-to-speech model trained on human conversation with no text; runs locally on an M4 Max MacBook Pro | Announced Oct 23, 2026. Research preview only: waitlist, no weights, no paper | The bar for Layer 1. Join the waitlist. Until it's open, the closest open models are PersonaPlex 7B and Moshi (above). |
| **DeepSeek Harness** (`deepseek-ai/deepseek-harness`, MIT) | An agent runtime where "everything is a plugin" (Node, `npx @deepseek-ai/dsh`); works with local models through Ollama | Developer preview, breaking changes expected | Layer 2 (agent). Its plugin design is a good model for Luma's tools. Later: let Luma run as a dsh plugin so developers can extend her. Not needed for the voice demo. |
| **Microduck** (Pollen Robotics / Hugging Face, $399) | 25 cm biped robot duck; behaviors are neural policies trained in MuJoCo and exported to ONNX; open-source Rust SDK (Apache-2.0); it beeps and has its own generated vocal identity but doesn't converse | Pre-orders open, ships before Christmas 2026 | Layer 3 (body), phase one. Exactly the R2-D2/WALL-E charm in the timeline. Luma could be its brain and voice. Order one for development. |
| **Asimov v1** (Menlo Research, open-source humanoid) | 1.2 m, 35 kg, 25 DoF; full CAD, MuJoCo model, BOM; CERN-OHL hardware | Kit about $15,000–20,000 | Layer 3, phase two (after the raise). Its open simulation means Luma's body skills can be trained in sim first. |
| **Kimi K3.1 Pro** (Moonshot AI) | Open-weight mixture-of-experts model: about 2.8 trillion parameters, 104 billion active, 1M-token context. Released Oct 23, 2026; weights promised by Nov 4 | API now (`kimi-k3.1-pro`) | Built in as a cloud-brain choice next to Claude, on the owner's own Moonshot key. It can't run on a Mac mini or any Mac (full weights are about 1.5 TB; even 1-bit is about 600 GB). What runs locally on a Mac mini is Luma's own brain (Qwen3 30B with 24 GB+ of memory), and the realistic way to make a model "ours" is to fine-tune that one on Luma's own conversations. |
