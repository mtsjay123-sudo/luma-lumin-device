# How Luma makes money

Written November 12, 2026, for a pre-seed conversation. Every number here is one of three kinds, and says which:
**known** (checked, with where it came from), **ours** (measured in this repo), or **assumption** (a guess to be replaced
by a quote or a pilot). Nothing here is a forecast.

## The one idea

**Luma thinks at home, so a member costs almost nothing to serve.**

Every other AI companion pays a cloud bill each time someone talks. Luma's brain is in the lamp. Talking to it for an
hour costs the company the same as not talking to it: nothing. So what a member pays each month is nearly all margin,
and Luma never needs anyone to talk more. That second part matters as much as the first. The rule in this project is
that real people come first, with no tricks to keep someone talking. A company that earns from minutes can't keep that
rule for long. A company that earns the same whether you talk or not can.

## Who pays

Three doors, in the order they're likely to open.

### 1. Programs: an agency or a health plan pays, the person gets Luma free

This is the big one, and it's the one that reaches people who can't pay.

- **Who:** state and county offices for the aging, Medicare Advantage plans, Medicaid long-term-care programs, veterans'
  services, housing authorities, hospital discharge programs.
- **What they buy:** a seat. One price per person per month covers the lamp, setup by phone, updates, support and a
  replacement if it breaks. Twelve months at a time.
- **Price (assumption):** $35 a seat a month with Luma Mini, $45 with Luma Home.
- **Why they'd pay, known:**
  - New York's Office for the Aging gives a companion robot (ElliQ) to older adults for free. The state reported a 95%
    drop in loneliness among more than 800 people. The Boston Globe reports a $2.1 million, three-year contract. The
    terms per robot aren't public; if all of it covered 800 robots for three years, that would be about $875 a robot a
    year. That sum is mine, not the state's.
  - More than 65 Medicare Advantage plans have paid a company (Papa) a fee per member per month to send people to
    members' homes for company (KFF Health News, 2022). The fee isn't public.
  - The Surgeon General's 2023 advisory: about half of U.S. adults report measurable loneliness, and social isolation
    among older people is put at about $6.7 billion a year in extra Medicare spending.
- **What Luma reports back:** counts, never words. How many members used it this month, how many say they feel less
  lonely on a standard short questionnaire, how many reached out to a real person. Only with each member's yes. This
  report isn't built yet; when it is, it goes behind a setting that starts off, like every other outbound call.
- **What Luma is paid for:** seats, and renewals earned by those counts. Never minutes.

### 2. Homes: a person or their family buys one

- **Luma Mini, $249.** The lamp with the smaller brain.
- **Luma Home, $549 (the owner's call, November 13).** The lamp with the bigger brain, priced above its parts
  (see "What a lamp costs").
- **Luma Plus, $9.99 a month (known: the price exists in Stripe today).** Luma's own phone number and 300 texts a month,
  so Luma can text you and the people you choose. At the most use, texts and the number cost $5.43 (ours:
  `docs/LUMA_BLUEPRINT.md`); most people won't use them all.
- **Luma Family, $14.99 a month (assumption, not built).** For a daughter or son buying for a parent: a second phone,
  a weekly note the parent agrees to ("Mum's doing well, she'd love a call"), and the lamp replaced if it breaks.
- **For scale, known:** ElliQ sells to homes at about $250 to start plus $40 to $60 a month (its own site lists both;
  Fortune, August 2026, says from $40).

### 3. Places: one lamp per room

Assisted living, senior housing, hospice, shelters. Bought by the building, ten to two hundred at a time, at the program
price. Same lamp, same seat.

## What Luma never sells

- No ads. Not in the app, not in the voice.
- No data. Memories are encrypted in the home, and "forget" forgets.
- No attention. No streaks, no guilt, no "I missed you". Nothing is tuned to make someone talk longer.
- No health claims. Luma is company, not treatment.

These aren't only the right thing. They're why a public program can say yes: the account of what data exists and where
it lives is one sentence long.

## What a lamp costs

| | Today, one at a time | In the hundreds, on Luma's own board |
|---|---|---|
| Luma Home (Jetson Orin Nano Super, 8 GB) | about $405 (ours: `hardware/README.md`, the computer's price known, the rest remembered prices) | $260 to $320 (assumption) |
| Luma Mini (an 8 GB ARM board) | about $250 (ours, same way) | $110 to $150 (assumption) |

Two honest notes:

- The website says $199. With today's parts no lamp reaches that. Mini at $249 does.
- Luma Home at $399 would lose money until the computer inside costs less. It's $549 (decided November 13), or
  it's sold through programs where the monthly price carries it.

## What a seat earns

One program seat, each month. Every cost below is an assumption except where marked.

| | Luma Mini seat at $35 | Luma Home seat at $45 |
|---|---|---|
| The lamp, spread over 36 months ($140 and $300) | $3.90 | $8.35 |
| Support and setup help | $6.00 | $6.00 |
| Updates, the relay for the phone away from home | $1.00 | $1.00 |
| Lamps that break or come back | $1.50 | $2.50 |
| Card fees and billing (3%) | $1.05 | $1.35 |
| The cloud bill for thinking | **$0** (ours: the brain is in the lamp) | **$0** |
| **Cost** | **$13.45** | **$19.20** |
| **Left over** | **$21.55 (62%)** | **$25.80 (57%)** |

The row that makes this work is the zero. A companion that thinks in the cloud pays for every minute a lonely person
talks, and lonely people talk a lot.

A home that buys a Mini at $249 and takes Plus: about $109 on the lamp before shipping and returns (assumption: $140
landed), then $4.56 to $8 a month on Plus depending on how much they text (ours, from the texting costs above).

## What the sums give

Not a forecast: what the arithmetic gives **if** these happen, at the seat price and costs above (each an assumption).

| If, in a year | Then |
|---|---|
| 1,000 program seats at $35 | $420,000 a year, about $259,000 left after the costs above |
| 10,000 program seats at $35 | $4.2 million a year, about $2.6 million left |
| 50,000 program seats at $35 | $21 million a year, about $12.9 million left |
| 10,000 Minis sold to homes at $249, a third take Plus | $2.49 million once, plus about $400,000 a year |

For size: New York's program alone started with more than 800 people (known). There are 50 states, and more than 65
Medicare Advantage plans have already paid for company by the month (known).

## The membership: how a home customer pays, from November 13

A home Luma is sold the way the best devices with a service are: the device at about what it costs, and a membership
that pays for what costs money to run. Talking to Luma at home is never part of it and never stops: a member who
cancels keeps a Luma that talks, remembers and stays with them. That's the promise that makes the membership easy to
say yes to, and it's why it can't be an engagement trick.

**Luma Membership, $19 a month or $190 a year (the owner's call, November 13; whether people pay it is still to learn).** What it pays for:

- Luma's own phone number and 300 texts a month (today's Luma Plus, $5.43 a month at the most use: ours).
- The phone app away from home, through the relay.
- What time it is where your people are, family check-ins with their yes, a second phone for family.
- A replacement if the device breaks.
- Every new brain and voice as it ships.

**The device:** Luma Mini at $249 (about its parts cost: ours) and Luma Home at $549 (assumption: above its $405 in
parts, until Luma's own board lowers the cost). No device is sold below its landed cost.

**Founding members (the first 500, the owner's call, November 13; live on the site):** the $25 deposit holds a place and locks **$14 a month for life**,
with the first three months free.

What a member earns each month, at $19 (each cost an assumption except where marked):

| | A light texter | Texting to the limit |
|---|---|---|
| Texts and the number | $2.00 | $5.43 (ours) |
| Support | $6.00 | $6.00 |
| Updates, the relay | $1.00 | $1.00 |
| Replacements | $1.50 | $1.50 |
| Card fees (3%) | $0.57 | $0.57 |
| **Cost** | **$11.07** | **$14.50** |
| **Left over** | **$7.93** | **$4.50** |

1,000 members at $19 is $228,000 a year and about $95,000 left over for light texters. It's a small number on its
own; the seats in "Programs" above are where the margin is. Members are the proof that people keep paying, which is
what a program, and an investor, will ask for first.

## Who buys first: Americans in Japan

The owner's first market. Why it's a good first one: lonely by circumstance, in English, far from family by 13 to 17
hours, paying in dollars, and close enough to reach person by person.

- **About 54,000 active-duty U.S. service members are in Japan** (known: USAFacts and CRS, end of 2025), about
  61,700 counting civilians. Roughly half are in Okinawa (known: CRS). Their families are on top of that.
- **The JET Programme has about 866 Americans** teaching in Japan (known: the JET Programme's country table, 2026),
  the largest group, and thousands more teach English privately.
- **What Luma does for them that no one else does:** it knows what time it is where their people are ("it's 8 in the
  morning in Ohio, your mom's up") and helps them reach home at a time home can answer
  (`src/luma/agent/hometime.py`).

How to reach the first 100, person by person: base spouses' groups and family readiness groups, JET and English
teacher communities, Americans-in-Japan forums. One referral month free to both people (a thank-you for bringing
someone, never a reward for talking more).

To check before selling on a base or in Japan: the radio rules (Giteki and PSE off base; what applies in base housing),
and that the power adapter takes Japan's 100 volts (most do).

## What's true today

| | |
|---|---|
| The software | Runs today on a Mac: talk, voice, memory, the phone app, the desktop app |
| The safety net | Answers with 988 before the brain sees the message; checked on a corpus of 910 lines and two held-out sets of 48 (ours) |
| For clinicians | `docs/CLINICAL_SAFETY.md` |
| The lamp | A design: parts list, wiring, a case you can print, files measured by the CAD program. **Nobody has built one** |
| Setup from a phone | Written and tested with a made-up Wi-Fi in a real browser. Not tried on a lamp |
| Luma Plus | The $9.99 price exists in Stripe. The cloud brain is parked: Luma thinks at home |
| A paying customer | None yet |

## What the first money is for

In order, with what each step proves. Costs are for quotes to fill in; the two below are sums from the parts list.

1. **Ten lamps on a bench** (about $4,000 in parts at one-at-a-time prices). Proves: it hears through the dome, it stays
   cool, the microphone switch reads 0 V, a phone sets it up.
2. **Fifty homes for ninety days** with one county office for the aging or one health plan (about $12,500 in Mini
   parts). Measured before and after with a standard loneliness questionnaire, plus how many people reached out to
   someone. This is the number every program will ask for, and nobody has it for a companion that thinks at home.
3. **Luma's own board and a moulded lamp.** One board instead of a developer kit: this is what takes the Mini from $250
   in parts to the low hundreds.
4. **The paperwork to sell it:** radio and safety testing, an accessibility report, a plain privacy account.

## What could go wrong, plainly

- **The lamp isn't built.** Hearing through a dome and cooling a computer inside a lamp are real engineering.
- **Small brains miss.** On the hard moments we test, the small brains still get some wrong; the numbers are in
  `docs/HUMAN_PLAN.md` and they're not all good. The safety net doesn't depend on the brain.
- **Leaning on it.** A lonely person can lean on a companion too much. Luma is built to point toward real people, and a
  pilot has to show that it does.
- **Programs are slow to buy.** A state contract can take a year. Homes and places pay sooner.
- **Bigger companies.** A phone maker can ship a companion tomorrow. It will think in the cloud and be paid for attention.
  Luma's answer is the one sentence about data, the switch that cuts the microphones' power, and a price that doesn't
  need anyone to talk more.

## Where the known numbers come from

- U.S. personnel in Japan: USAFacts, "Where are US troops stationed?"; CRS In Focus IF10199 (Okinawa).
- JET Programme participants by country: jetprogramme.org/en/countries/ (2026 table).


- New York State Office for the Aging, "NYSOFA's Rollout of AI Companion Robot ElliQ Shows 95% Reduction in Loneliness",
  August 1, 2023: https://aging.ny.gov/news/nysofas-rollout-ai-companion-robot-elliq-shows-95-reduction-loneliness
- The Boston Globe, June 28, 2026 (the $2.1 million, three-year contract):
  https://www.bostonglobe.com/2026/06/28/opinion/seniors-loneliness-robots-relationship-elliq
- KFF Health News, "Medicare Advantage Plans Send Pals to Seniors' Homes for Companionship — And Profits", 2022:
  https://kffhealthnews.org/aging/medicare-advantage-plans-senior-companions-profits/
- ElliQ's prices: https://elliq.com/pages/faqs and Fortune, August 3, 2026:
  https://fortune.com/2026/08/03/gen-z-elliq-intuition-robotics-ai-companion-robot-older-adults/
- The Surgeon General's advisory on loneliness, May 2023, as reported:
  https://www.smithsonianmag.com/smart-news/an-epidemic-of-loneliness-threatenes-health-of-americans-surgeon-general-says-180982142/
- The computer's price: NVIDIA's list price for the Jetson Orin Nano Super developer kit, $249.
