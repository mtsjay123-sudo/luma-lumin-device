# Luma design: the direction and the rules

This file is the direction for anything Luma's team builds by hand, and the rulebook for anything Luma builds
on its own: websites, decks, documents and graphics in Projects. The rules are our own wording of four
open-source design skills, credited at the bottom.

## Luma's own look (the app, the device, the website)

The owner set the direction, so it wins over the generic rules below:

- **Identity:** calm, glassy and alive. Apple and visionOS liquid glass, in light and dark. The Luma S.I.
  wordmark and the talking aura are the motif.
- **Personality:** a friend, not a dashboard. Short sentences, sentence case, no jargon. The chat is always in reach.
- **Type:** the system font (SF Pro on a Mac). It reads as native, and it renders crisply at every size in the
  app window.
- **Palette:** a neutral ground, ink, and one accent color for the thing that matters on each screen. No rainbow
  gradients and no neon.
- **Motion:** gentle, and only where it means something: the aura while Luma listens and speaks, a soft rise
  when a sheet opens. Everything respects reduced motion.
- **Dials:** energy 2, rhythm 2, motion 2.

**Known collision.** The rules cap glass at one or two elements per screen. Luma's identity is glass, and the
owner chose that on purpose. So glass stays on the chrome (the sidebar, the top bar, sheets, the chat dock).
Content cards are opaque, one tone step off the ground, so text stays readable.

## Rules for everything Luma makes

**Honesty (hard rules)**

- No number without a source. Every statistic has to appear in the research, in the financial model or in
  what the owner said. Otherwise it's left out, and the step says so.
- No invented testimonials, ratings, customers, logos or "trusted by" rows. Quotes appear only if the owner
  gave them.
- No fake product shots. No grey placeholder bars dressed up as an app; show real words or nothing.
- Every button and link does something real. Nav links only go to pages that exist.

**Copy**

- Write like a person. No em dashes and no buzzwords (seamless, unlock, elevate, revolutionary, cutting-edge,
  next-gen, AI-powered, all-in-one).
- Buttons name the action, like "Order lunch" or "See the menu". Never "Get started", "Learn more" or "Explore".
- The headline is eight words or fewer. The rest goes in the sentence below it.

**Look**

- Pick a direction from the subject, not the category. The six directions are editorial, bold, warm,
  technical, playful and quiet. Each is a whole system: type, corners, how sections are composed, and how loud
  it is. The reason is written at the top of the stylesheet as the "Design read".
- No eyebrow labels, and no tiny letter-spaced capitals above headings.
- No gradient blobs or glows. No pill shapes on everything, and no hover lifts.
- No identical icon cards in a row, and no auto-highlighted "most popular" middle plan.
- At most two or three core colors plus one accent, used as whole fields of color rather than sprinkles.
- One identity motif from the subject (its brand art, its initials), repeated on purpose.

**Works for everyone**

- Text contrast meets WCAG AA (4.5:1) in both light and dark.
- Every control has a visible keyboard focus ring. Escape closes menus.
- Tap targets are at least 44px tall. Nothing scrolls sideways on a phone.
- Animations have a reduced-motion fallback.

**Checked, not hoped for.** The website studio runs these as gates before a step counts as done:

- the copy lint
- generic buttons
- headline length
- gray-text contrast in both modes
- leaving out unsourced numbers and quotes
- a real browser at phone and desktop width, checking errors, sideways scroll, broken images and tap targets

A failed gate goes back to the designer agent with the reason, like any other failed check.

## Credits

The rules are distilled, in our own words, from four MIT-licensed projects:

- [antislop](https://github.com/miqdadbadjuber/anti-slop) by Miqdad Badjuber: the purpose test, the honesty
  gates and the liveliness dials.
- [tasteskill](https://github.com/Leonxlnx/taste-skill) by Leonxlnx: the dated registry of tells, and
  "the idea comes from the subject".
- [Hallmark](https://github.com/Nutlope/hallmark) by Nutlope and contributors: themes as whole systems, and the
  floor rules (tokens, focus, reduced motion, overflow, no invented metrics).
- designskills.dev, a directory of design skills (we couldn't open the site from our build machine; its idea of
  named style directions shaped the six directions above).
