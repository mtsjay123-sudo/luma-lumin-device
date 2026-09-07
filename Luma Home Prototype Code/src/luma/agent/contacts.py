"""An explicitly saved, encrypted contact book; never imports phone contacts."""
from __future__ import annotations

import re
import unicodedata

from luma.memory.store import reject_payment_secrets


PHONE = re.compile(r"\+[1-9][0-9]{7,14}")
MAX_CONTACTS = 250


def _name(value):
    if not isinstance(value, str):
        raise ValueError("Use a contact name such as Mom or Alex Chen.")
    value = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError("Contact names cannot contain hidden or control characters.")
    value = " ".join(value.split())
    if not 1 <= len(value) <= 80 or not any(char.isalpha() for char in value):
        raise ValueError("Contact names must contain a letter and be at most 80 characters.")
    reject_payment_secrets(value)
    return value


def _phone(value):
    if not isinstance(value, str) or not PHONE.fullmatch(value):
        raise ValueError("Use an exact E.164 phone number such as +19195550123.")
    return value


class ContactBook:
    def __init__(self, store):
        self.store = store

    def list(self):
        records = self.store.all("contact", MAX_CONTACTS + 1)
        if len(records) > MAX_CONTACTS:
            raise ValueError("The contact book exceeds its 250-contact limit.")
        return sorted(records, key=lambda record: _name(record["name"]).casefold())

    def save(self, args):
        if not isinstance(args, dict) or set(args) != {"name", "phone"}:
            raise ValueError("A contact needs only a name and a phone number.")
        name, phone = _name(args["name"]), _phone(args["phone"])
        with self.store.lock:
            records = self.list()
            matches = [r for r in records if _name(r["name"]).casefold() == name.casefold()]
            if len(matches) > 1:
                raise ValueError("That name is ambiguous. Delete duplicate labels and save distinct names.")
            if matches:
                if matches[0]["phone"] == phone:
                    return matches[0]
                raise ValueError("That name already has a different number. Delete it first or use a distinct label.")
            if len(records) >= MAX_CONTACTS:
                raise ValueError("The contact book is full. Delete a contact before adding another.")
            return self.store.put("contact", {"name": name, "phone": phone})

    def resolve(self, recipient):
        if isinstance(recipient, str) and PHONE.fullmatch(recipient):
            return {"name": recipient, "phone": recipient}
        name = _name(recipient)
        matches = [r for r in self.list() if _name(r["name"]).casefold() == name.casefold()]
        if not matches:
            raise ValueError("No exact saved contact matches that name. Save the contact or provide an E.164 number.")
        if len(matches) != 1:
            raise ValueError("That name matches multiple contacts. Use a distinct saved label or an exact phone number.")
        _phone(matches[0]["phone"])
        return matches[0]

    def delete(self, contact_id):
        if not isinstance(contact_id, str) or not contact_id:
            raise ValueError("Choose a saved contact to delete.")
        return self.store.delete("contact", contact_id)
