# Texting through your own Mac Messages account

Luma can submit a reviewed outbound message to Apple Messages on your Mac. This is a personal-use alternative to a separate Twilio sending number. Your Mac's Messages account determines the sender identity. Luma does not impersonate your iPhone, change your Apple Account, or use a private iMessage server API.

## Setup

1. On your Mac, open Messages yourself and check its iMessage settings. Sign in using the Apple Account you use on your iPhone, and choose your intended sending identity. For your own phone number, it must be available and selected in Messages; Luma cannot guarantee or override that identity.
2. For green-bubble messages, set up Messages in iCloud or iPhone **Settings → Apps → Messages → Text Message Forwarding**, then enable your Mac. Your iPhone needs to remain powered and connected. Apple's [Text Message Forwarding instructions](https://support.apple.com/en-us/102545) explain these requirements and the account checks.
3. Explicitly configure `LUMA_MESSAGES_TRANSPORT=imessage` or `LUMA_MESSAGES_TRANSPORT=sms` for Luma's Mac Messages provider. There is no automatic transport fallback. The Messages scripting dictionary exposes SMS and iMessage; this connector does not offer a separate guaranteed RCS mode.
4. Select Mac Messages as the texting provider in Luma and enable messaging. Review the exact international recipient number and full message before confirming a send.
5. macOS may ask the application running Luma for permission to control Messages. You decide whether to allow it. Review this under **System Settings → Privacy & Security → Automation**; Luma does not grant itself permission or reset Apple's privacy controls. See Apple's [Automation permissions guide](https://support.apple.com/en-gb/guide/mac-help/mchl108e1718/mac).

The Mac must remain running and signed in. Paired phone access lets you direct Luma from your phone browser, but the Mac executes the Messages action. Luma currently requires an explicit recipient phone number; it does not inspect your Contacts or conversation history to guess “Mom.” Phone pairing and outbound Messages permission are separate settings.

## What a result means

“Accepted” means the Messages application accepted its send command. It does not confirm delivery, a read receipt, or a carrier charge. If the command times out or the application fails after dispatch, Luma reports an unknown outcome and does not retry: inspect Messages before making another action. Carrier charges and Apple account restrictions still apply.

The connector selects one enabled account of the chosen transport. If none exists or multiple enabled accounts make the choice ambiguous, it stops before sending. It never switches to SMS after an iMessage failure, changes your default sender, signs in, logs out, or sends a test message on setup.

## Implementation and verification

`MacMessages(env=None, run=None).readiness()` checks macOS, the Messages application, `/usr/bin/osascript`, and explicit transport configuration. It never launches Messages or reads account, contact, message or permission data. “Configured” is therefore not a successful account connection test.

`send({"to": "+countrycode…", "body": "reviewed text"})` must be called only after a separate confirmed action. It runs one fixed AppleScript with `on run argv`; recipient, body and mode are separate arguments, with no shell or code interpolation. Those arguments can be briefly visible to local process inspection, so Luma must not log the command line. It never returns raw AppleScript errors, which can contain private message data.

The local schema was verified by reading `/System/Applications/Messages.app/Contents/Resources/Messages.sdef`; the `sdef` executable itself was unavailable because this Mac has Command Line Tools rather than full Xcode. Tests use an injected mock process runner. No Messages launch, conversation or contact read, Automation request, real send, or delivery verification was performed. Actual account compatibility and sending need an owner-confirmed first message.
