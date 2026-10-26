## Design critique: the Luma phone app (`/phone`)

Stage: first working build, real data. Judged from screenshots at 390×844 (dark and light) and 1280×860.

### Overall impression

It's calm and personal. The warm blur of a lamp-lit room drifting behind frosted glass feels like the device
itself, and the serif greeting sets a human tone before any data. The biggest opportunity is the storage
readout, which is the number you asked for. The LED digits read "20.0" in a way that can look like "200", and
the unit sits a line away from the number.

### Usability

| Finding | Severity | Recommendation |
|---|---|---|
| The storage LED shows "20.0", and with a tiny decimal dot it reads as "200" at a glance. "GB left" sits on the next line. | 🔴 Critical | Show whole GB from 10 up ("20"), put "GB left" right beside the digits, and move the total and Luma's share to a quieter line below |
| On wide screens the dock floats over the panels even though every panel is already visible | 🟡 Moderate | Hide the dock at 900px and up |
| Chats show the newest 8 with no way to reach the rest | 🟡 Moderate | Add "All chats" at the end of the list, opening every chain in a sheet |
| The memory deck relies on arrows plus a hint line to suggest swiping | 🟢 Minor | Fine for now. The fanned cards on the right already suggest more |
| Tapping the state pill ("Mic off") scrolls to the device panel without saying why | 🟢 Minor | Keep it: the device panel is where the mic switch lives |

### Visual hierarchy

- **What draws the eye first:** the greeting, then the ask bar. That's correct: say hi, then ask.
- **Reading flow:** greeting, then ask, then today's chats, memory, your Luma and in progress. That's the order
  someone checks their day in.
- **Emphasis:** in the device panel the white product photo is the brightest thing, and it pulls focus from the
  storage number. Make it smaller and dim it slightly. The LED number should win there.

### Consistency

| Element | Issue | Recommendation |
|---|---|---|
| Panel lights | Consistent meaning (chats blue, memory green, device amber) | Keep. The projects panel reuses blue, which is fine |
| Count LEDs | Chats and memory show a bare number with no label on screen | The hint line under memory explains it. Chats are fine as-is |
| Corners | 30px panels, 18px rows, 22px cards, round buttons. Consistent | — |

### Accessibility

- **Color contrast:** body text and secondary text on dark glass are about 9:1 and 5.6:1. Dark text on the
  green memory card is 9:1+. All pass AA in both themes.
- **Touch targets:** every control is 44px or more (dock items 70×54, deck arrows 44, mic switch row 60).
- **Text readability:** the 16px base, 14.5px secondary and 13px timestamps are all fine. The LED digits carry
  `aria-label`s, the storage bar has a text label, and the product photo has alt text.
- **Motion:** the drift, breathing glow, panel rise and sheet slide all stop under reduced motion.

### What works well

- The background is the brand. The device is frosted glass with warm light inside, and so is the app.
- LED dot numbers are a motif nobody else has, and they echo the device's own display.
- The memory deck turns a list of facts into something you want to flip through, with tabs (People, Places,
  Likes, Dates, Plans) that make it trackable.
- Chats read like a messages app: title, last line, time. They open in a sheet you can keep replying in.

### Priority recommendations

1. **Fix the storage readout.** It's the number the owner asked to track, so it has to be instant.
2. **Hide the dock on wide screens, and add "All chats".** Both remove friction on the two most-used panels.
3. **Quiet the product photo.** Smaller and slightly dimmer, so the LED number leads the device panel.
