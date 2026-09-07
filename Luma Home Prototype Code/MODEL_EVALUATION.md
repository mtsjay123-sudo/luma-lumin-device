# Local model evaluation — September 7, 2026

Qwen3-4B-Instruct-2507 Q4_K_M is now selected in this Mac's private `.env`. Its complete SHA256 matches the publisher's LFS digest. The original Llama 3.2 3B remains available. See [provenance and configuration](MODEL_AND_PERSONALITY.md).

## What the measurements support

This is a small diagnostic evaluation on an M3 MacBook Air with 8 GB unified memory, 4,096 context tokens and Metal offload. It does not establish that Qwen is the best model or reliable for arbitrary requests. Both models were run separately. Timings include variable startup/prompt processing and are single observations, not a benchmark distribution.

The direct planner comparison deliberately bypassed the assistant's routing safeguards. **Both models passed only two of four intent checks.** Llama replaced a generic grocery request with unrequested milk and eggs. Qwen preserved groceries, but proposed messages for an explanation and an ambiguous recipient. Both guessed that “her” was a usable contact label. Qwen's direct planner calls took 1.67–7.95 seconds versus Llama's 2.71–10.60 seconds in this sample. These results justify keeping runtime controls, not trusting model prose as execution evidence.

The first full Qwen run also misrouted an unavailable grocery request into a contact operation and failed to save a conversational style request. Those failures led to explicit grocery handoffs, messaging-intent filtering and direct handling of common style preferences. The final run produced:

| Request | Observed result | Seconds |
| --- | --- | ---: |
| Casual homecoming | Natural reply; first model load included | 13.35 |
| Text Mom to pick up groceries | Exact saved fixture contact; grocery draft, no added items | <0.01 |
| Explain texting | Explanation, no draft or action | 4.87 |
| Text “her” with no established recipient | Clarification, no draft or action | <0.01 |
| Let Mom know I will be home at six | Model-created draft preserving the time | 5.80 |
| Talk casually and keep it short | Saved contemporary/brief preferences | <0.01 |
| Find cheapest Food Lion eggs and order | Honest missing-connection/price explanation and Groceries link | <0.01 |

The test used an isolated encrypted store, a fictitious Mom number and no provider credentials. It generated two drafts and zero executable action records. No provider was called and no microphone was recorded. This seven-case observation is not an independent holdout test after the fixes.

Kokoro synthesized the greeting in 4.80 seconds into 3.39 seconds of audio while Qwen remained loaded. Whisper transcribed it in 1.21 seconds with the spoken words intact and a trailing `//` punctuation artifact. That validates the basic local pipeline, not recognition in a noisy room or an entire physical device. The final model-enabled browser also returned a substantive wind-down reply without a JavaScript error.

108 focused automated tests passed. Desktop at 1440px and mobile at 390px passed the checked layouts without horizontal overflow. The browser used a fresh test profile and localhost only. [Sanitized fixture results](docs/model-evaluation-2026-09-07.json) retain the raw observations. Process RSS in those results excludes some shared/GPU allocations and must not be treated as total memory use.

## Practical limits

Arbitrary phrasing and multi-step requests can still fail. Style preferences and explicit memories personalize the application; no weights were fine-tuned. The model cannot approve messages, buy groceries or invent a booking slot. Paid external APIs, merchant product/price/stock feeds, payment/order permissions, a real home-network connection and physical-device tests still determine which household actions can actually finish. Product-page navigation and saved-wallet checkout remain at the merchant.
