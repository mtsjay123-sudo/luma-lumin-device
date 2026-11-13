# Pre-orders: the plan, with dates, money and kill points

Written November 13, 2026, after `docs/PREORDER_POSTMORTEM.md`. Each cost is a **known** price, **ours** (from this
repo) or an **assumption** to be replaced by a quote. Each month has one number that says whether it worked, and a
date when, if that number is missed, the plan changes instead of drifting.

## The first buyer

To be chosen by the owner by **November 20**: young Americans living in Japan (the owner's stated first market), or
older Americans through programs (`docs/BUSINESS_MODEL.md`). Everything below assumes the first; if it's the second,
the months are the same and the channel is a county office for the aging instead of communities in Japan.

## Month by month

| Month | Do | The number that says it worked | Kill / change point |
|---|---|---|---|
| **Nov 2026** | Site live on `main`. The film's end card points at it. 20 conversations with people in the first market | Site takes a real $25 deposit (one test, refunded). 20 conversations held | No live deposit by **Nov 30**: stop everything else until it is |
| **Dec 2026** | Landed-cost quote for 50 Minis. One lamp built on the bench and filmed. Recorded demo on the Mini's own brain | 100 people on the list, **15 deposits**. A video of a real lamp | Under **5 deposits** by Dec 31: change the page, the story or the buyer before spending on hardware |
| **Jan 2027** | Price set from the quote (repriced before more deposits if needed). Japan certification body and FCC lab quoted and booked | 40 deposits. Certification booked | Landed cost over the planned price with no fix in sight: raise the price or drop Mini |
| **Feb 2027** | Ten lamps on the bench: hearing through the dome, heat, the microphone switch at 0 V, phone setup | 10 of 10 pass the bench checks. 70 deposits | Under 8 of 10 pass: fix the case before certifying (certifying twice costs twice) |
| **Mar 2027** | Certification testing. First 10 lamps in homes (friends and first depositors, free) | Certification in progress. 10 homes using it daily after 2 weeks | Fewer than 6 of 10 still using it after 2 weeks: the product isn't there; refund anyone who asks and fix it before shipping |
| **Apr 2027** | First batch of 50 ordered after certification passes | Certification passed. Refunds under 10% of deposits | Certification fails: say so to every depositor the same week, with a new date |
| **May 2027** | First 50 shipped to depositors in order | 50 delivered. Under 5% returned in 30 days | |

## Money for these six months

| | Cost | Kind |
|---|---|---|
| Ten bench lamps | about $4,000 | ours (`docs/BUSINESS_MODEL.md`) |
| Japan radio (Giteki) and adapter (PSE, or buy an adapter already marked) | $4,000–10,000 | assumption (vendor quotes) |
| FCC equipment authorization | to quote | assumption |
| First batch of 50 Minis | about $12,500 in parts | ours |
| Shipping and returns for 50 | to quote | assumption |
| **Before quotes** | **about $20,500 plus certification and shipping** | |

Deposits ($25 each) don't pay for any of this, and they're refundable. They prove demand; the pre-seed round pays.

## What is measured, every week

- Visitors to `/preorder` (Vercel Web Analytics, counts only: turn it on in the Vercel project, it isn't yet).
- Free sign-ups and deposits, by lamp and by where people live (recorded on every reservation from Nov 13).
- Refunds asked for.
- For the 10 homes: days used in the last week. Talk is never recorded; the count comes from the lamp, and only with
  each person's yes.

## Rules that don't move

- No deposit is taken for a price below the landed cost.
- No ship date is promised until certification is booked.
- Nothing ships before certification passes.
- Every refund is paid the day it's asked for.
