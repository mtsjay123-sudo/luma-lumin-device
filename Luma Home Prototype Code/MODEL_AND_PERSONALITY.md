# Luma's model and personality

Luma runs an existing local language model through `llama-cpp-python`; the product's personality, memory and action controls are application code. There has been no Luma-specific fine-tuning or training on the owner's conversations.

**This Mac now uses Qwen3-4B-Instruct-2507, Q4_K_M**, selected in the private local `.env` and verified through the live browser. The original working model is **Llama 3.2 3B Instruct, Q4_K_M** at `models/llama-3.2-3b-q4/Llama-3.2-3B-Instruct-Q4_K_M.gguf`. It remains available. `LUMA_MODEL_PATH` selects the active GGUF at startup. Changing a path requires restarting Luma; a missing file raises an error instead of silently downloading or substituting a model.

## Personal conversation

The owner can explicitly choose a preferred name, tone (`warm`, `direct`, `playful`), language style (`plain`, `contemporary`, `classic`) and verbosity (`brief`, `balanced`, `detailed`). These settings shape replies without guessing the user's age or assigning stereotypes. Contemporary means naturally matching casual language; classic means conventional conversational phrasing. Neither forces a caricature, slang, or an age label. Kids mode omits the adult's preferred name, style and memories.

A companion should respond naturally to a greeting, remember only what the owner chooses to save, and know when to be brief or serious. It must also distinguish helping draft a text from actually sending one. The prompt now explicitly separates a request such as “Can you text my mom to pick up groceries?” from “Explain how texting works.” A natural message can be drafted for review, but phone numbers, times, purchases and completed bookings must never be invented. The runtime resolves saved contact labels, handles permissions and executes confirmed actions; the model cannot grant itself those powers.

This is prompt-based personalization plus encrypted application memory, not a newly trained model. A future fine-tune would require a curated, consented dataset, holdout evaluations and measured improvement before deployment. It would not replace reliable integrations or permission checks.

## Verified local model

**Qwen3-4B-Instruct-2507, Q4_K_M** is the selected model on this Mac after a verified download and local workflow evaluation. Qwen identifies the base as a four-billion-parameter non-thinking model with improved instruction and tool use, under Apache 2.0. Those are publisher claims; Luma-specific quality and latency require local evaluation. [Official Qwen model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).

The GGUF is a third-party quantization published by bartowski, rather than a Qwen-produced GGUF. [Quantization publisher and files](https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/tree/main).

- Exact file: `Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
- Size from the publisher's file metadata: **2,497,280,736 bytes** (2.50 GB decimal).
- Immutable repository revision: `ae44f08e1392f39c0e474af10c3ff8355c8b6688`.
- Published LFS SHA256: `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`.
- [Exact download](https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/ae44f08e1392f39c0e474af10c3ff8355c8b6688/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf).

The current development Mac is an Apple M3 MacBook Air with eight CPU cores and **8 GB unified memory**. A 2.50 GB quantized model is a plausible fit at 4,096 context tokens; the file size is not total runtime memory. macOS, browser tabs, Whisper, Kokoro, caches and model buffers all compete for the same RAM. Compare one model at a time and watch memory pressure with the full voice pipeline running. Keep the original model available until the replacement passes practical voice and action tests. Do not use the base model's advertised 256K context on this 8 GB device.

## Runtime settings

Set these in the local environment or `.env`, then restart Luma:

```dotenv
# Omit LUMA_MODEL_PATH to retain the original working Llama GGUF.
# LUMA_MODEL_PATH=/absolute/path/to/a/verified/model.gguf
LUMA_CONTEXT_SIZE=4096
LUMA_GPU_LAYERS=-1
LUMA_THREADS=8
LUMA_BATCH_SIZE=512
# Usually leave unset: llama.cpp reads the GGUF chat template.
# LUMA_CHAT_FORMAT=
```

`LUMA_GPU_LAYERS=-1` requests all-layer GPU offload through the installed Metal-capable runtime; `0` requests CPU-only inference. Actual acceleration depends on the installed build. Context is validated from 2,048 to 32,768, threads from 1 to 128, and batch size from 1 to 2,048. These bounds prevent malformed configuration; they do not certify that every combination fits the hardware. Keep the defaults on this Mac unless measurements justify a change.

The planner builds a constrained JSON grammar from only the tools allowed on that turn. Its context fitter keeps whole recent messages and refuses an oversized current request instead of silently cutting an action's instructions. The deterministic runtime still validates every proposal. These controls reduce mistakes; they are not evidence of perfect model reliability.

## Validation

108 focused tests cover the runtime, profiles, contacts, reviewed messages, bookings, groceries and phone pairing. The seven-case local Qwen workflow evaluation exercised conversation, exact grocery drafting, explanation, ambiguous recipients, a model-written message, saved style and unavailable shopping. A real browser response also verified the model-enabled server. [Detailed measurements and limitations](MODEL_EVALUATION.md). No comparison sent a text, contacted a provider or persisted personal test state.
