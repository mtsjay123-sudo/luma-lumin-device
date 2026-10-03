# Going live with Luma's texting number and Luma Plus

Lumin does this once. Customers never see Twilio, Supabase or Stripe. They verify their phone in Luma, text for free, and, if they upgrade, pick their own Luma number from a list and pay.

## What the customer sees

1. **People & Texts → Luma's number:** they enter their name and mobile and type the 6-digit code. Done; free texts start immediately from Luma's shared number.
2. **Pick your Luma number:** a few real numbers in their area code (they can type another area code), shown with the town. They tap one, then **Get Luma Plus with (704) 555-2037**, and pay on Stripe's checkout page.
3. When checkout finishes, that exact number is theirs. If someone grabbed it in the same instant, they get the nearest free one instead. Friends see it when Luma texts them, and they can text it back.
4. Prefer their own number? **Your number** (Mac Messages) is free and unlimited, with no setup on Lumin's side.

## Your checklist, in order

| # | Where | What to do | Status |
|---|---|---|---|
| 1 | Stripe | Luma Plus product + $9.99/mo price | **Done** (`price_1UMMsMHupQXO7siRSIB6U6z3`) |
| 2 | Stripe | Billing portal for cancel/card/invoices | **Done** (`bpc_1UMY6oHupQXO7siRRIf19lm0`) |
| 3 | Stripe | Webhook to `/api/luma/stripe-webhook` | **Created, switched off** (`we_1UMY6xHupQXO7siRLbmiIXYu`); turn it on in step 8 |
| 4 | Supabase | SQL Editor → paste [`supabase/SETUP.sql`](../../supabase/SETUP.sql) → Run | Tested on Postgres here; safe to run twice |
| 5 | Twilio | Make an account, then run `node tools/twilio-setup.mjs --site https://<your-site> --area 919` | Script tested against a pretend Twilio |
| 6 | Twilio | Carrier registration (A2P 10DLC): see below | You; about 1–3 weeks for approval |
| 7 | Vercel | Paste the variables (list below), then redeploy | You |
| 8 | Browser | Open `https://<your-site>/api/luma/health`. When `"ready": true`, enable the Stripe webhook and copy its signing secret into `STRIPE_WEBHOOK_SECRET` | You |
| 9 | Mac | Double-click `scripts/Check Luma.command` and send Claude the output | You |

### Vercel variables (Settings → Environment Variables → Production)

| Variable | Where it comes from |
|---|---|
| `LUMA_ADMIN_TOKEN` | Run `node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"` and keep it in your password manager. It's the "Admin token" on /admin.html. |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API. Server-only, never in the browser. |
| `LUMA_CLOUD_PUBLIC_URL`, `TWILIO_*`, `LUMA_SHARED_NUMBER`, `LUMA_PROVISION_NUMBERS` | Printed by `tools/twilio-setup.mjs` |
| `STRIPE_SECRET_KEY` | Stripe → Developers → API keys (a restricted key with Checkout, Customers, Billing portal write is enough) |
| `LUMA_PLUS_PRICE_ID` | `price_1UMMsMHupQXO7siRSIB6U6z3` |
| `LUMA_STRIPE_PORTAL_CONFIG` | `bpc_1UMY6oHupQXO7siRRIf19lm0` |
| `STRIPE_WEBHOOK_SECRET` | Stripe → Webhooks → Luma Plus → Reveal (step 8) |

## Carrier registration (A2P 10DLC)

US carriers block texts from business numbers that aren't registered. You register **once, as Lumin**, and every customer's number (shared or their own) rides on that registration. Customers never fill anything in.

In the Twilio Console go to **Messaging → Regulatory Compliance → A2P 10DLC**:

1. **Brand:** Lumin's legal name, EIN and address (Standard brand, about $4 one-time).
2. **Campaign:** use case **"Mixed"**, or "Conversational" if offered for your brand. Attach it to the **Luma** Messaging Service the script created. About $15 to vet, then $1.50–10 a month. You can paste the wording below.

**Campaign description**
> Luma is a home AI companion. Verified account holders ask Luma (by voice, in the Luma app, or by texting their own Luma number) to send personal messages they write to people they know, such as family and friends. Every message is reviewed and approved by the account holder before it is sent. Account holders can also text their own Luma number to talk with their companion, and Luma replies only to their verified phone. No marketing, promotions, lead generation or purchased lists.

**Message flow / how recipients opt in**
> Messages are sent only to personal contacts the account holder chooses and approves one message at a time. The first message to each recipient identifies the sender ("Sent via Luma for <name>") and explains that replying STOP opts out. Account holders verify their own phone with a one-time code before using the service and agree to the Luma terms at sign-up. STOP, HELP and START are honored automatically.

**Sample messages**
1. `Marvin: running 10 minutes late, save me a seat (Sent via Luma for Marvin. Reply STOP to opt out.)`
2. `Marvin: Can you pick up the groceries while you're out?`
3. `Done, I'll remind you at 6:15 PM to grab flowers.` (Luma answering its owner)

**Opt-out / help keywords:** STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT / HELP, INFO. Opt-in: START. Luma Cloud records opt-outs and won't text that person again.

Have a public **Terms** and **Privacy** page that mention texting before you submit; reviewers check for them.

**Faster start while you wait:** a **toll-free number** with Toll-Free Verification is often approved in days. Use it as `LUMA_SHARED_NUMBER` for the free plan. Plus members' local numbers still need the 10DLC campaign.

## What it costs you (October 2026 Twilio pricing)

- About **$0.012 per text** (Twilio plus carrier fee), and **$1.15/month** per Plus member's number.
- A Plus member who uses all 300 texts costs about $5.43 against $9.99. Free users cost at most about $0.37/month.
- The limits are settings: `LUMA_FREE_TEXTS_PER_MONTH`, `LUMA_PLUS_TEXTS_PER_MONTH`.
