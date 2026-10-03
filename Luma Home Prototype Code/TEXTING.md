# Texting with Luma

Say it the way you'd ask a friend:

- "Text my girl that I'll pick her up at 7." Luma drafts **"I'll pick you up at 7"** to Maya.
- "Let Mom know I'm on my way." / "Tell babe I'm outside."
- "Save Dana +1 919 555 0177 as my sister."
- "Did Maya text back?"

Luma shows the exact text and who it goes to. Say **"send it"** (or tap Send it) to send, **"don't send it"** to drop it, or tap Edit. Nothing is sent without that, and an approval expires after 10 minutes. If Luma doesn't know someone yet, it asks for their name and number and saves them, nickname included.

## Three ways to send

| Route | Set up | Cost | Notes |
|---|---|---|---|
| **Your number** (Mac Messages) | People & Texts → Send through → This Mac's Messages | Free, unlimited | Uses your iMessage, or SMS through iPhone Text Message Forwarding. See [MAC_MESSAGES.md](MAC_MESSAGES.md). |
| **Luma's number** | People & Texts → Luma's number → verify your phone | Free texts every month, then Luma Plus | Works without your phone or Mac Messages. Replies come back to Luma. |
| **Draft only** | Default | Free | Luma writes it; you tap Copy or Open in Messages. |

## Luma's number and Luma Plus

1. Enter your name and mobile, then the code Luma Cloud texts you. That registers this device; the credential stays encrypted on the device.
2. Free plan: a monthly allowance (default 30) from Luma's shared number. Texts start with your name ("Marvin: …"). The first text to a new person adds "Sent via Luma for Marvin. Reply STOP to opt out."
3. When the allowance runs out, Luma says so and offers **Luma Plus** ($9.99/month by default): 300 texts a month, your own local Luma number, and replies forwarded. Or it can send from your own number for free.
4. Replies are announced ("Maya texted back: …"). During quiet hours they show silently.

Luma Cloud is the `api/luma/[route].js` function on the website. The [blueprint](docs/LUMA_BLUEPRINT.md#5-texting-and-luma-plus) has the go-live checklist (Supabase, Twilio 10DLC, Stripe) and the cost per text.

## Text Luma from anywhere (Luma Plus)

Text your Luma number from your own phone (the one you verified) and your Luma at home answers by text: "remind me at 6 to grab flowers", "text my sister that I'll be late". When Luma needs your OK to send something, it replies "Reply YES 4821 to send". Only your phone gets that code, so a spoofed caller ID can't approve anything. "NO" cancels. On the free plan, texting Luma gets an automatic note that it's part of Plus.

## Try the whole flow with no accounts

```sh
# terminal 1, from the repository root
node tools/luma-cloud-dev.mjs                 # pretend carrier and checkout; the code is 123456
# terminal 2, from "Luma Home Prototype Code"
LUMA_CLOUD_URL=http://127.0.0.1:8787 .venv/bin/python -m luma.cli serve
```

Texts Luma "sends" print in terminal 1. To pretend someone replied (or, with `"from"` set to your verified number, that you texted Luma):

```sh
curl -X POST http://127.0.0.1:8787/dev/reply -H 'Content-Type: application/json' \
  -d '{"from":"+19195550123","body":"yes! 7?"}'
```

## Guarantees

- Approval is matched by plain rules, never by the model. "Yes but make it shorter" is not a yes.
- Retries can't double-text: each send carries the approval's id, and Luma Cloud remembers it.
- Lost connection means "I'm not sure it went out", never "sent".
- STOP is honored on Luma's numbers. US and Canadian numbers only. Bursts are rate limited.
- Kids mode can't text anyone.
