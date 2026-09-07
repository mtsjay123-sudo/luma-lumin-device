"""Personal-use outbound Messages bridge; call only after action confirmation.

Readiness inspects the platform and files only. No account, conversation, contact
or permission reads occur until a confirmed send is dispatched. Apple retains
control of its Automation permission prompt and configured sending identity.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

from luma.integrations.providers import OutcomeUnknown, ProviderError


OSASCRIPT = "/usr/bin/osascript"
MESSAGES_APP = "/System/Applications/Messages.app"
TIMEOUT_SECONDS = 20

# Recipient, body and selected transport are values in argv. They are never
# interpolated into this script or a shell command. Messages.sdef on the host
# explicitly exposes account, participant, send and SMS/iMessage service types.
SEND_SCRIPT = '''on run argv
    if (count of argv) is not 3 then return "LUMA_PREFLIGHT_FAILED"
    set recipientAddress to item 1 of argv
    set messageBody to item 2 of argv
    set chosenTransport to item 3 of argv
    set didDispatch to false
    try
        tell application id "com.apple.iChat"
            if chosenTransport is "imessage" then
                set candidateAccounts to every account whose service type is iMessage and enabled is true
            else if chosenTransport is "sms" then
                set candidateAccounts to every account whose service type is SMS and enabled is true
            else
                return "LUMA_PREFLIGHT_FAILED"
            end if
            if (count of candidateAccounts) is 0 then return "LUMA_NO_ACCOUNT"
            if (count of candidateAccounts) is not 1 then return "LUMA_AMBIGUOUS_ACCOUNT"
            set chosenAccount to item 1 of candidateAccounts
            set targetParticipant to participant recipientAddress of chosenAccount
            set didDispatch to true
            send messageBody to targetParticipant
        end tell
        return "LUMA_ACCEPTED"
    on error errorText number errorNumber
        if didDispatch then return "LUMA_UNKNOWN"
        if errorNumber is -1743 then return "LUMA_NOT_AUTHORIZED"
        return "LUMA_PREFLIGHT_FAILED"
    end try
end run'''


class MacMessages:
    def __init__(self, env=None, run=None):
        self.env = os.environ if env is None else env
        self.run = subprocess.run if run is None else run

    def readiness(self):
        """Configuration availability, not a live account or delivery check."""
        mode = self.env.get("LUMA_MESSAGES_TRANSPORT")
        transport = mode if isinstance(mode, str) and mode in ("imessage", "sms") else None
        available = (sys.platform == "darwin" and os.path.isfile(OSASCRIPT)
                     and os.access(OSASCRIPT, os.X_OK) and os.path.isdir(MESSAGES_APP))
        if not available:
            setup = "Mac Messages requires macOS, Apple's Messages app and /usr/bin/osascript."
        elif transport is None:
            setup = "Choose LUMA_MESSAGES_TRANSPORT=imessage or sms after setting up your own Messages account."
        else:
            setup = ("Configured for " + ("iMessage" if transport == "imessage" else "SMS forwarding")
                     + ". Account sign-in and Automation permission are checked only during a confirmed send; delivery is not preverified.")
        return {"available": available, "configured": available and transport is not None,
                "transport": transport, "setup": setup}

    def send(self, args):
        """Submit one reviewed message; never retry or switch transport/account."""
        if not isinstance(args, dict) or set(args) != {"to", "body"}:
            raise ValueError("A message requires exactly a recipient phone number and body.")
        recipient, body = args["to"], args["body"]
        if not isinstance(recipient, str) or not re.fullmatch(r"\+[1-9][0-9]{6,14}", recipient):
            raise ValueError("Use an explicit international phone number beginning with + and its country code.")
        if not isinstance(body, str) or not body.strip() or len(body) > 1600 or "\x00" in body:
            raise ValueError("Enter a nonempty message of at most 1,600 characters without null bytes.")
        try:
            body.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("Message text must contain valid Unicode characters.") from None
        ready = self.readiness()
        if not ready["configured"]:
            raise ProviderError(ready["setup"])
        try:
            result = self.run(
                [OSASCRIPT, "-e", SEND_SCRIPT, recipient, body, ready["transport"]],
                shell=False, capture_output=True, text=True, encoding="utf-8",
                timeout=TIMEOUT_SECONDS, check=False,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            raise OutcomeUnknown("Messages may have received the command. Check Messages before creating another action; no retry was attempted.") from None
        except OSError:
            raise ProviderError("The Messages helper could not start. Check the macOS installation; no retry was attempted.") from None
        # Do not expose stderr: AppleEvents can include private recipient/body data.
        marker = result.stdout.strip() if isinstance(result.stdout, str) else ""
        if result.returncode != 0:
            raise OutcomeUnknown("The Messages helper exited unexpectedly. Check Messages before retrying; delivery is unconfirmed.")
        preflight_errors = {
            "LUMA_NO_ACCOUNT": "Messages has no enabled account for the selected transport. Check iMessage sign-in or iPhone Text Message Forwarding; no alternate transport was used.",
            "LUMA_AMBIGUOUS_ACCOUNT": "Messages has more than one enabled account for this transport. Choose the intended account in Messages before trying again; no account was selected.",
            "LUMA_NOT_AUTHORIZED": "macOS did not authorize control of Messages. Review Privacy & Security → Automation for the app running Luma, then create a new reviewed action.",
            "LUMA_PREFLIGHT_FAILED": "Messages could not prepare the selected account or recipient. No send command was issued; review its setup before creating another action.",
        }
        if marker in preflight_errors:
            raise ProviderError(preflight_errors[marker])
        if marker != "LUMA_ACCEPTED":
            raise OutcomeUnknown("Messages returned no definite acceptance. Check Messages before creating another action; no retry was attempted.")
        return {"provider": "mac_messages", "transport": ready["transport"], "status": "accepted",
                "summary": "Apple Messages accepted the send command using your configured account. Delivery and the recipient's reading are not confirmed."}
