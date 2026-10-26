# Luma S.I. website (v2)

A static site in the same visual language as the Luma phone app: a blurred photo of a lamp-lit room drifting
slowly behind frosted glass, warm light inside every panel, and LED dot numbers like the device's own display.

```
index.html   the page
styles.css   tokens (dark and light), the moving blur, panels, the memory deck
script.js    LED dot digits for every [data-led], the live clock on the hero device, the memory deck
fonts/       Geist and Instrument Serif (OFL, see fonts/LICENSE.txt)
img/         home.jpg (the blurred room) and luma.webp (the device, cut out so it floats on any background)
```

No build step and no outside requests. To preview it, run `python3 -m http.server` in this folder and open
http://localhost:8000. Opening the file straight from disk mostly works, but browsers block its fonts there.

## Deploying

The live site is in the `lumin-holdings-site` repo. Copy this folder over the site's marketing page there,
keeping any Luma Cloud routes that repo serves, and the change goes live once it's merged to `main`.

## Design critique (what changed and why)

Judged from screenshots at 1440×900 and 390×844, dark and light.

| Finding | Severity | Fix |
|---|---|---|
| The hero product photo sat on a bright white box, the brightest thing on a calm night page | 🔴 | Cut the device out of its studio background. It now floats in a warm halo with a slow float |
| The blur behind the page was hidden under a near-black veil from the middle of the screen down | 🟡 | Lighter veil, so the drifting room shows the whole way down |
| "Three ways in" used a lone LED 8 and three thin green lines as art | 🟡 | The app shows its three real numbers (chats, memories, GB left), and the computer shows Luma working in a window with a Stop button |
| The phone mockup had a hole at the bottom and no way to ask anything | 🟢 | Added the ask bar, a memory deck and the dock, so it matches the real app |
| Text scrolled visibly under the top bar | 🟢 | The bar is frosted glass now, fading out at its lower edge |
| On phones the back memory cards hid behind the front one | 🟢 | Wider fan on narrow screens |

Kept on purpose: the moving blur, colored light per panel (chats blue, memory green, device amber), the green
front memory card and the LED digits. They are what makes this look like Luma and nothing else.
