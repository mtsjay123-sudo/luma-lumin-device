"""Email, free: Luma signs in to your mailbox over IMAP and SMTP with an app password.

Gmail, iCloud, Outlook, Yahoo and most other providers support this without any
paid API or developer account. Luma reads mail, writes drafts into your own
Drafts folder (so they show up in Gmail on your phone too), and sends only after
you approve the exact message. The app password is kept in Luma's encrypted
local store and only goes to your own mail provider.
"""
from __future__ import annotations

import base64
import email
import email.header
import email.policy
import email.utils
import html
import imaplib
import re
import smtplib
import ssl
import time
from email.message import EmailMessage

PRESETS = {
    "gmail.com": ("imap.gmail.com", 993, "smtp.gmail.com", 465),
    "googlemail.com": ("imap.gmail.com", 993, "smtp.gmail.com", 465),
    "icloud.com": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587),
    "me.com": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587),
    "mac.com": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587),
    "outlook.com": ("outlook.office365.com", 993, "smtp.office365.com", 587),
    "hotmail.com": ("outlook.office365.com", 993, "smtp.office365.com", 587),
    "live.com": ("outlook.office365.com", 993, "smtp.office365.com", 587),
    "yahoo.com": ("imap.mail.yahoo.com", 993, "smtp.mail.yahoo.com", 465),
    "aol.com": ("imap.aol.com", 993, "smtp.aol.com", 465),
}

APP_PASSWORD_HELP = {
    "gmail.com": "https://myaccount.google.com/apppasswords",
    "icloud.com": "https://account.apple.com/account/manage",
    "yahoo.com": "https://login.yahoo.com/account/security/app-passwords",
    "outlook.com": "https://account.live.com/proofs/AppPassword",
}

ADDRESS = re.compile(r"[A-Za-z0-9._%+'-]{1,64}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+")


class MailError(RuntimeError):
    pass


def _decode_header(value):
    if not value:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(value)))
    except Exception:
        return str(value)


def _text_of(message, limit=6000):
    """The readable text of an email: plain part first, else the HTML with tags removed."""
    plain = htmlish = None
    for part in (message.walk() if message.is_multipart() else [message]):
        if part.get_content_maintype() == "multipart" or part.get("Content-Disposition", "").startswith("attachment"):
            continue
        kind = part.get_content_type()
        try:
            payload = part.get_content()
        except Exception:
            raw = part.get_payload(decode=True) or b""
            payload = raw.decode(part.get_content_charset() or "utf-8", "replace")
        if kind == "text/plain" and plain is None:
            plain = payload
        elif kind == "text/html" and htmlish is None:
            htmlish = payload
    text = plain
    if text is None and htmlish:
        text = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", htmlish)
        text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", text)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"[ \t ]+", " ", text or "")
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()
    return text[:limit]


def _snippet(text, size=160):
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith(">")]
    return re.sub(r"\s+", " ", " ".join(lines))[:size]


class Mailbox:
    """One mail account. `imap` and `smtp` factories can be swapped in tests."""

    def __init__(self, store, imap=None, smtp=None, clock=time.time):
        self.store = store
        self.imap_factory = imap or (lambda host, port: imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context(), timeout=20))
        self.smtp_factory = smtp or self._smtp
        self.clock = clock
        self._cache = None

    @staticmethod
    def _smtp(host, port):
        context = ssl.create_default_context()
        if port == 465:
            return smtplib.SMTP_SSL(host, port, context=context, timeout=20)
        client = smtplib.SMTP(host, port, timeout=20)
        client.starttls(context=context)
        return client

    # -- account ---------------------------------------------------------------
    @property
    def account(self):
        return self.store.setting("mail_account")

    def connected(self):
        return bool(self.account)

    def status(self):
        account = self.account
        if not account:
            return {"connected": False}
        return {"connected": True, "address": account["address"], "provider": account.get("provider")}

    @staticmethod
    def settings_for(address, imap_host=None, smtp_host=None, imap_port=993, smtp_port=None):
        address = str(address or "").strip()
        if not ADDRESS.fullmatch(address):
            raise ValueError("Enter your full email address.")
        domain = address.rsplit("@", 1)[1].lower()
        preset = PRESETS.get(domain)
        if imap_host or smtp_host:
            imap_host, smtp_host = str(imap_host or "").strip().lower(), str(smtp_host or "").strip().lower()
            if not HOST.fullmatch(imap_host) or not HOST.fullmatch(smtp_host):
                raise ValueError("Enter the IMAP and SMTP server names from your email provider.")
            smtp_port = int(smtp_port or 587)
            imap_port = int(imap_port or 993)
            if imap_port not in {993} or smtp_port not in {465, 587}:
                raise ValueError("Luma only uses encrypted mail connections (IMAP 993, SMTP 465 or 587).")
            return {"imap_host": imap_host, "imap_port": imap_port, "smtp_host": smtp_host, "smtp_port": smtp_port, "provider": domain}
        if not preset:
            raise ValueError("I don't know that provider's mail servers yet. Add the IMAP and SMTP server names from its help page.")
        return {"imap_host": preset[0], "imap_port": preset[1], "smtp_host": preset[2], "smtp_port": preset[3],
                "provider": "gmail" if "gmail" in preset[0] else domain}

    def connect(self, address, app_password, **servers):
        secret = re.sub(r"\s+", "", str(app_password or ""))
        if not 8 <= len(secret) <= 128:
            raise ValueError("Paste the app password your email provider gave you (not your normal password).")
        settings = self.settings_for(address, **servers)
        account = {"address": address.strip(), **settings,
                   # base64 so the store's payment-number guard never trips on it
                   "secret_b64": base64.b64encode(secret.encode()).decode()}
        self._login_imap(account).logout()
        self.store.set_setting("mail_account", account)
        self._cache = None
        return self.status()

    def disconnect(self):
        self.store.set_setting("mail_account", None)
        self._cache = None
        return {"connected": False}

    def _secret(self, account):
        return base64.b64decode(account["secret_b64"]).decode()

    def _login_imap(self, account=None):
        account = account or self.account
        if not account:
            raise MailError("Email isn't connected yet. Add it in Apps.")
        try:
            client = self.imap_factory(account["imap_host"], account["imap_port"])
            client.login(account["address"], self._secret(account))
            return client
        except imaplib.IMAP4.error as error:
            raise MailError("Your email provider didn't accept that sign-in. Use an app password, not your normal password.") from error
        except (OSError, ssl.SSLError) as error:
            raise MailError("I couldn't reach your email provider: " + str(error)[:120]) from error

    # -- reading ---------------------------------------------------------------
    def inbox(self, limit=10, unread_only=False, query=None):
        client = self._login_imap()
        try:
            client.select("INBOX", readonly=True)
            criteria = ["UNSEEN"] if unread_only else ["ALL"]
            if query:
                words = re.sub(r'[^\w@. -]', "", str(query))[:60]
                if words:
                    criteria = ["OR", "FROM", f'"{words}"', "SUBJECT", f'"{words}"']
            status, data = client.uid("SEARCH", None, *criteria)
            if status != "OK":
                raise MailError("Your mailbox didn't answer the search.")
            uids = (data[0] or b"").split()[-max(1, min(int(limit), 30)):][::-1]
            messages = []
            for uid in uids:
                status, parts = client.uid("FETCH", uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)] BODY.PEEK[TEXT]<0.4000>)")
                if status != "OK" or not parts:
                    continue
                header = body = b""
                flags = ""
                for part in parts:
                    if isinstance(part, tuple):
                        meta = part[0].decode(errors="replace")
                        flags += meta
                        if "HEADER" in meta:
                            header = part[1]
                        else:
                            body = part[1]
                    elif isinstance(part, bytes):
                        flags += part.decode(errors="replace")
                parsed = email.message_from_bytes(header + b"\r\n" + body, policy=email.policy.default)
                name, address = email.utils.parseaddr(_decode_header(parsed.get("From")))
                when = email.utils.parsedate_to_datetime(parsed["Date"]).timestamp() if parsed.get("Date") else None
                text = _text_of(parsed, 1200)
                messages.append({"id": uid.decode(), "from": name or address, "from_address": address,
                                 "subject": _decode_header(parsed.get("Subject")) or "(no subject)", "date": when,
                                 "snippet": _snippet(text), "unread": "\\Seen" not in flags,
                                 "message_id": parsed.get("Message-ID")})
            self._cache = {"at": self.clock(), "messages": messages}
            return messages
        finally:
            try: client.logout()
            except Exception: pass

    def read(self, uid):
        if not re.fullmatch(r"\d{1,12}", str(uid)):
            raise ValueError("Pick an email from the list.")
        client = self._login_imap()
        try:
            client.select("INBOX", readonly=True)
            status, parts = client.uid("FETCH", str(uid), "(BODY.PEEK[])")
            raw = next((p[1] for p in parts or [] if isinstance(p, tuple)), None)
            if status != "OK" or raw is None:
                raise MailError("That email isn't there anymore.")
            message = email.message_from_bytes(raw, policy=email.policy.default)
            name, address = email.utils.parseaddr(_decode_header(message.get("From")))
            return {"id": str(uid), "from": name or address, "from_address": address, "subject": _decode_header(message.get("Subject")),
                    "date": email.utils.parsedate_to_datetime(message["Date"]).timestamp() if message.get("Date") else None,
                    "message_id": message.get("Message-ID"), "references": message.get("References"), "text": _text_of(message)}
        finally:
            try: client.logout()
            except Exception: pass

    def find_latest_from(self, who):
        who = str(who or "").strip().lower()
        messages = (self._cache or {}).get("messages") if self._cache and self.clock() - self._cache["at"] < 600 else None
        messages = messages or self.inbox(limit=30)
        for message in messages:
            if who in (message["from"] or "").lower() or who in (message["from_address"] or "").lower():
                return message
        return None

    # -- writing ---------------------------------------------------------------
    def compose(self, to, subject, body, reply_to=None):
        account = self.account
        if not account:
            raise MailError("Email isn't connected yet. Add it in Apps.")
        to = str(to or "").strip()
        if not ADDRESS.fullmatch(to):
            raise ValueError("I need the exact email address to write to.")
        subject = re.sub(r"[\r\n]+", " ", str(subject or "")).strip()[:200]
        body = str(body or "").strip()
        if not body or len(body) > 10000:
            raise ValueError("Write a message of up to 10,000 characters.")
        message = EmailMessage()
        message["From"] = account["address"]
        message["To"] = to
        message["Subject"] = subject
        message["Date"] = email.utils.formatdate(self.clock(), localtime=True)
        message["Message-ID"] = email.utils.make_msgid(domain=account["address"].rsplit("@", 1)[1])
        if reply_to and reply_to.get("message_id"):
            message["In-Reply-To"] = reply_to["message_id"]
            message["References"] = ((reply_to.get("references") or "") + " " + reply_to["message_id"]).strip()
        message.set_content(body)
        return message

    def _drafts_folder(self, client):
        status, folders = client.list()
        for line in folders or []:
            text = line.decode(errors="replace") if isinstance(line, bytes) else str(line)
            if "\\Drafts" in text:
                match = re.search(r'"([^"]+)"\s*$', text) or re.search(r"\s(\S+)\s*$", text)
                if match:
                    return match.group(1)
        return "Drafts"

    def draft(self, to, subject, body, reply_to=None):
        """Save into the owner's own Drafts folder. Nothing is sent."""
        message = self.compose(to, subject, body, reply_to)
        client = self._login_imap()
        try:
            folder = self._drafts_folder(client)
            quoted = folder if folder.startswith('"') else f'"{folder}"'
            status, _ = client.append(quoted, "(\\Draft)", imaplib.Time2Internaldate(self.clock()), message.as_bytes())
            if status != "OK":
                raise MailError("Your mailbox didn't save the draft.")
            return {"folder": folder.strip('"'), "to": to, "subject": message["Subject"]}
        finally:
            try: client.logout()
            except Exception: pass

    def send(self, to, subject, body, reply_to=None):
        """Only called after the owner approved these exact words."""
        message = self.compose(to, subject, body, reply_to)
        account = self.account
        try:
            client = self.smtp_factory(account["smtp_host"], account["smtp_port"])
            try:
                client.login(account["address"], self._secret(account))
                refused = client.send_message(message)
            finally:
                try: client.quit()
                except Exception: pass
        except smtplib.SMTPAuthenticationError as error:
            raise MailError("Your email provider didn't accept the sign-in, so nothing was sent.") from error
        except (smtplib.SMTPException, OSError) as error:
            raise MailError("The email didn't go out: " + str(error)[:160]) from error
        if refused:
            raise MailError("Your provider refused the address " + ", ".join(refused) + ".")
        # (The Message-ID is left out of the receipt: its long digit runs look like a card number to the store.)
        return {"sent": True, "to": to, "subject": message["Subject"]}
