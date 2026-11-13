# Pre-orders: the postmortem, written before it happens

Written November 13, 2026. Imagine it's May 2027 and the pre-order plan has failed: few deposits, refunds, no lamp
shipped. These are the seven most likely reasons, most likely first. Each rests on something true in this repo today,
or on something missing from it. After the seven: what was fixed the same day, and what only the owner can do.

## 1. Nobody could pay (most likely)

**What went wrong.** The deposit button worked only on a preview link behind a Vercel login. The public site
(`lumin-holdings-site.vercel.app`) answered `/api/preorder` with **404** on November 13: the code was on branch
`claude/hopeful-feynman-z2294x` and never merged into `main`. Every visitor in the first weeks saw only "join the free list".

**How it unfolded.** November: the pitch went out, and the link in the film pointed at a page with no pay button.
December: the free list filled slowly, and nobody owned the email that turns a free sign-up into a deposit. January: the
merge happened, but the list had cooled.

**The assumption.** "Stripe is connected, so people can pay." The links exist, but they're only shown by code that isn't live.

**Earliest warning sign.** `curl https://lumin-holdings-site.vercel.app/api/preorder` returns 404. Checkable in ten seconds.

## 2. Built for one buyer, sold to another

**What went wrong.** The plan (`docs/BUSINESS_MODEL.md`) is for **older, lonely Americans**: agencies for the aging,
Medicare Advantage, a film whose second character is "Eli, 71". On November 13 the owner named a different first buyer:
**young Americans living in Japan**. The page speaks to neither: "The friend that lives on your counter" plus computer
control. Prices are in dollars, and there is no Japan shipping, no yen and no Japan-ready plug. Mixed signals convert
nobody.

**How it unfolded.** December: traffic came from the founder's network in Japan, but the page looked like a U.S. elder-care
product. January: the few deposits came from people the founder knew. February: investors asked "who is the customer?"
and got two answers.

**The assumption.** That one page and one story fit every buyer.

**Earliest warning sign.** Of the first 50 reservations, where do people live and how old are they? That wasn't
recorded until November 13.

## 3. The lamp was never built, so nobody could see it

**What went wrong.** "Nobody has built one" (`hardware/README.md`). The plan's first step, ten lamps on a bench
(about $4,000 in parts), has no date and no money. Hearing through a frosted dome and cooling a computer inside a lamp
are untested. Pre-orders for a device people can't see or hold convert poorly, and each month without a photo of a
real one raises refunds.

**How it unfolded.** December–January: renders only. February: the first build showed the dome muffling the
microphones, so the case was redesigned. March: the second build ran hot under load. April: a ship date still
couldn't be promised, and refund emails began.

**The assumption.** That a design measured in CAD is close to a product.

**Earliest warning sign.** No photo or video of a working lamp by December 31.

## 4. The price was below the cost

**What went wrong.** Luma Mini is "$249 planned", and its parts cost "about $250" one at a time
(`docs/BUSINESS_MODEL.md`). Luma Home is "$499 planned" on parts of "about $405", before the case, shipping, the
power adapter, certification, returns and card fees. The lower costs ($110–150 and $260–320) need Luma's own board,
in the hundreds, which nothing funds. Every deposit locked in a price that loses money on the first batch.

**How it unfolded.** January: a supplier quote put the Mini about $90 over the planned price with a printed case.
February: a choice between raising the price on people who had paid deposits, or losing money on each lamp.
March: the price went up and refunds followed.

**The assumption.** That volume prices would be there for the first batch.

**Earliest warning sign.** No landed-cost quote (board, case, adapter, box, shipping) before the first deposit.

## 5. It couldn't legally ship

**What went wrong.** Luma has Wi-Fi. It needs FCC equipment authorization in the U.S., and in Japan the Giteki mark for
the radio and PSE for the power adapter. Vendors quote several weeks to a few months and roughly $4,000–10,000 for
Japan alone. Neither the cost nor the time is in the plan. Until November 13 the page made no mention of it.

**How it unfolded.** March: the lamp worked on the bench, and the lab's first open slot was in May. May: no shipping
for anyone.

**The assumption.** That certification is paperwork at the end.

**Earliest warning sign.** No certification body quote by January.

## 6. The lamp people got wasn't the Luma they saw

**What went wrong.** The demo runs on a Mac (and could run the Mac Studio's big brain, never tested). The $249 Mini
runs the 1.7B brain, which passes **66–73%** of the human test with a judge score of **3.4 of 5**. Luma's own 4B failed
its training gate three times in a row. Buyers who reserved after seeing a demo got a noticeably flatter friend.

**How it unfolded.** April: early units went to friends, who said "it's nice but it's not like the video". Word of mouth
stalled.

**The assumption.** That the brain that demos is the brain that ships.

**Earliest warning sign.** The demo was never recorded on the Mini's own brain, side by side with the Mac's.

## 7. A trust incident

**What went wrong.** Luma is for lonely people, and some of them are in crisis. Through November the plan changed
almost daily: unrestricted, claim to be human, remove safety. Pushing a lonely-user product that way invites one
screenshot that ends it: Luma telling a grieving person it's human, or missing a crisis. U.S. buyers bring U.S. rules
(New York and California's companion-chatbot laws require saying it isn't human) wherever the company is registered.
Stripe also reviews pre-order businesses with no ship date and can hold funds.

**How it unfolded.** Any month: one post, refunds, a payment processor review.

**The assumption.** That being registered in Japan settles which rules apply to customers elsewhere.

**Earliest warning sign.** Any week where the product's rules on honesty and safety change without a test run.

## What was fixed on November 13

| Finding | Fix | Where |
|---|---|---|
| 2: who's reserving is unknown | An optional "Where do you live?" (Japan, the U.S., elsewhere) on every reservation. It's saved with the email and put on Stripe's record (`luma-home-jp`) | site: `preorder.html`, `api/preorder.js`, `assets/js/luma-reserve.js`; test in `tests/preorder.test.mjs` |
| 5: shipping before certification | The deposit terms say nothing ships until the lamp passes the FCC, Giteki and PSE | site: `preorder.html` |
| A false claim on the page | "Free keeps your newest 200 memories" is gone. Luma keeps what the computer has room for | site: `preorder.html` |
| 7: crisis in Japan | The crisis reply gives 119 and the ministry line 0570-064-556 in Japanese, and in English on a Luma set to Japan's time | `src/luma/agent/runtime.py` |
| No plan to judge against | Timeline, budget, metrics and kill dates | `docs/PREORDER_PLAN.md` |

## What only the owner can do

1. **Put the site live:** merge `claude/hopeful-feynman-z2294x` into `main` on `lumin-holdings-site`, or ask Claude to
   open a pull request. Until then, finding 1 is still true.
2. **Pick the first buyer:** young Americans in Japan, or older Americans through programs. Then the page, the film and
   the price follow that one.
3. **Get three quotes:** a landed cost for 50 Minis, a Japan certification body (Giteki and PSE), and an FCC lab.
4. **Reprice before the first deposit if the quote says so.** No one has paid yet, so changing "planned" costs nothing today.
5. **Build one lamp** and film it working.
6. **Run `bash scripts/mac_day_one.sh --test` on the Mac Studio** and record the demo on the brain the buyer will get.
