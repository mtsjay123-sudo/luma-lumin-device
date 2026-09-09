# Local voice revision — September 9, 2026

The goal is more natural spoken delivery while keeping speech local. The Mac now selects the full-precision Kokoro v1.0 export through its private `LUMA_TTS_MODEL_PATH`. The smaller INT8 model remains available and is the portable default if no override is supplied. No speech API, actor clone or remote inference is used.

## Changes

- Luma's default voice uses the native `af_heart` style instead of the previous 70% Bella / 30% Heart blend. Warm uses `af_bella`; Grounded uses `am_fenrir`.
- Short connected sentences are synthesized together, giving the model phrasing context. Long replies remain bounded to 240-character phrases for cancellation.
- At most two phrases are prefetched in RAM while one continuous audio output stream plays. Playback no longer waits until a sentence finishes before starting the next synthesis. A slower machine can still run short of buffered audio; this is not a guarantee of zero pauses on every device.
- Natural pace defaults to 1.03, with owner-selected Relaxed (0.94), Natural (1.03) and A little quicker (1.12) controls. Voice and pace persist locally.
- Conversational instructions favor contractions, concrete responses and varied short sentences. Generic support scripts, repeated follow-up questions and artificial filler/sigh annotations are discouraged.
- Spoken formatting removes basic Markdown noise while preserving names, numbers, prices and times. It does not paraphrase reviewed action details.
- Cancellation checks remain active during queue waits and playback. A native synthesis already in progress may finish, but its cancelled output cannot play.

## Validation

39 focused voice, personality, agent-compatibility and companion tests passed (plus 8 subtest checks). New coverage verifies connected phrase grouping, prefetch during playback, one output stream, cancellation without stale speech, formatting fidelity and bounded preferences. The older atomic-WAV test was updated to keep exercising multiple long chunks rather than assuming every sentence is synthesized separately.

On this Mac, the same test phrase generated in 7.814 seconds with the old setup. Sequential trials with the revised two-thread synthesis took 7.294 seconds for the INT8 default voice and 5.132 seconds for full precision. These include model startup and are small local measurements, not a general speed benchmark. A later four-thread trial overlapped other validation and was not used to select the default.

Whisper transcribed all words of the before/after test phrase, aside from punctuation and the homophone “your/you're.” That checks intelligibility, not subjective voice quality. Before/after recordings are available for the owner's listening comparison. The tool environment does not support model-side audio listening, so no claim of an auditory quality score is made.

Real app playback completed with the microphone off, no page/speech errors and no mobile horizontal overflow. Voice preferences saved through the UI. No private ambient audio was recorded.

## Assets and references

- [Kokoro voice documentation](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) describes the limitations of very short utterances and recommends grouping short phrases.
- [Kokoro ONNX maintainer](https://github.com/thewh1teagle/kokoro-onnx) provides the local engine/export.
- Full-precision asset: `https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx`, 325,532,387 bytes.
- Local transfer hash SHA-256: `7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5`. The release supplied no digest; this is the downloaded file's integrity snapshot, not a publisher-signature verification.
- Mac demo folder: `/Users/marvinjohnson/Desktop/Amiri_2026_Execution/Luma/Demos/Voice_2026-09-09/`.

For Jetson transfer, copy the selected speech asset and set a device-local path; rerun diagnostics and model-manifest verification. No Mac-specific absolute path is committed in the portable configuration.
