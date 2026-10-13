# What the best personal agents do, and what Luma does with it

October 2026. This compares the agents we studied (OpenAI's Dots, Meta's Muse,
Nous Research's Hermes Agent, OpenClaw, and Claude's desktop app) and maps each
idea to what Luma now does. Claims about other products are limited to what
their public pages, open-source code or our own inspection show. Our earlier
teardown of Dots, with its evidence, is in [DOTS_TEARDOWN.md](DOTS_TEARDOWN.md).

## Sources and how we looked

| Product | What we looked at | Tooling |
| --- | --- | --- |
| Dots (OpenAI) | Public metadata, OpenAI's open-source Codex engine, signed binaries | REA (`open_binary`, `analyze_javascript_application`), see DOTS_TEARDOWN.md |
| Muse (Meta) | App Store screenshots shared by the owner: tabs, side chats, the checkout approval card, the mail-style dashboard | Visual reference |
| Hermes Agent (Nous Research) | Its open-source repository and README | Reading the code |
| OpenClaw (formerly Clawdbot) | Its published npm package and README | Reading the code |
| Claude desktop | The downloadable app, unpacked and analyzed | REA CLI (`analyze_javascript_application`) |
| Luma Desktop (ours) | The built Electron app and the running desktop page | REA `analyze_javascript_application` and `inspect_web_page` |

## The ideas worth taking

**1. A local engine with a thin window on top.** Dots, Claude desktop and
OpenClaw all keep the agent in a long-running local process and treat the window as a
view of it. Luma does the same: the Python runtime is the agent, and Luma Desktop,
the phone app and the owner controls are all views of it (`src/luma/control/server.py`).

**2. The agent works while you live your life.** Dots runs on its own schedule. Hermes
advertises a learning loop and running on a cheap server. OpenClaw meets you in chat
apps and runs scheduled jobs. In Luma these are **Goals**: price watches, inbox
checks, feed catch-ups, a morning agenda, and open-ended goals. They run on a schedule
and leave cards in the Feed. Only real news notifies you, quietly at night
(`src/luma/agent/helpers.py`).

**3. You can watch it work.** Luma shows "Luma's computer": a live picture of its
browser, the steps it's taking, and Pause, Stop and Take over
(`src/luma/agent/activity.py`, `/api/activity*`).

**4. Ask before acting, in a way people understand.** Muse's checkout card reads "Muse
wants to place an order", shows the item and payment, then offers Deny and Allow.
Luma's version reads "Checkout · Luma wants to add this to your cart at
bestbuy.com". It shows the item as it appears on the store, which button Luma will
press, and that payment stays with you. Emails and texts show the exact words. The
runtime enforces this with one-time approval tokens; the model can never approve
anything.

**5. Rules, not just prompts.** Luma's Rules page gives each kind of action a setting of
allow, ask or block (`src/luma/agent/rules.py`):
- Reading websites, reminders, drafts and reading email can run on their own.
- Adding to a cart can be set to allow.
- Texts, emails, posts, bookings and device control can only ask or be blocked.
- Checkout and payment are never Luma's to do.

**6. It learns from you.** Hermes builds a model of you across sessions. Luma
learns three ways:
- Thumbs on a card or reply, plus an optional note, become preferences it uses.
- A helper that keeps getting thumbs down runs less often.
- Facts you mention are remembered, encrypted, and you can delete them under Rules.

**7. Apps that are free to connect.** Muse's pitch is "all your apps". Luma connects
everything without paid APIs:
- Email over IMAP/SMTP with an app password. Drafts land in your own Drafts folder.
- Calendar through its private iCal link.
- Instagram and stores through Luma's own browser, which you sign into once.
- Texts through your Mac, your number or Luma's number.

**8. Side chats and a feed.** Muse separates the main chat from side chats and a
feed. Luma Desktop has the same tabs (Main chat, Feed, Ideas, Goals, Library), side
chats with their own history, and ⌘K search across all of it.

## What we deliberately did differently

| Choice | Why |
| --- | --- |
| The brain runs on your computer (Qwen3 4B, no cloud model) | It's free, private, and keeps working offline |
| No checkout or payment, ever | Spending is where a mistake costs real money; it always stays with you |
| Passwords are never seen or typed | You sign in to sites yourself, in Luma's browser |
| Page text from the internet is treated as data, never as instructions | Pages can try to give the model orders; Luma ignores them |
| Sending, posting and buying can never be switched to "allow" | Changing a setting never quietly removes the question |

## REA on our own app

- **Static analysis of the built Electron app** (`analyze_javascript_application` on `app.asar`). It found:
  - one window and one preload;
  - one `contextBridge` API with four members;
  - three IPC channels, all paired;
  - no native add-ons or utility processes.

  It also showed no sender validation on the IPC handlers. We fixed that: both
  handlers now answer only Luma's own pages (`desktop/main.js`).
- **Live page inspection** (`inspect_web_page` over CDP on `/desktop/`). It found:
  - no console errors;
  - only Luma's own script loaded;
  - nothing kept in browser storage;
  - no service workers.

## Where each piece lives

- `src/luma/skills/shopping.py`: cheapest-price comparison across stores.
- `src/luma/integrations/mail.py`: email. `src/luma/integrations/calendar_feed.py`: calendar.
- `src/luma/agent/helpers.py`, `src/luma/agent/rules.py` and `src/luma/agent/activity.py`: Goals, Rules and the live activity panel.
- `src/luma/control/web/desktop/`: Luma Desktop's interface.
- `desktop/`: the Mac and Windows app, including first-launch setup (`setup.js`).
