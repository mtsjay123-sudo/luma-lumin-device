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


def _aliases(value):
    """Nicknames like "my girl", "babe" or "Mom" that should reach this person."""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list):
        raise ValueError("Nicknames must be a list like: my girl, babe.")
    result = []
    for item in value:
        alias = _name(re.sub(r"^(?:my|our)\s+", "", item.strip(), flags=re.I)) if isinstance(item, str) and item.strip() else None
        if alias and alias.casefold() not in {a.casefold() for a in result}:
            result.append(alias)
    if len(result) > 8:
        raise ValueError("Keep it to eight nicknames per person.")
    return result


def _labels(record):
    return {_name(record["name"]).casefold(), *(a.casefold() for a in record.get("aliases", []))}


class ContactBook:
    def __init__(self, store):
        self.store = store

    def list(self):
        records = self.store.all("contact", MAX_CONTACTS + 1)
        if len(records) > MAX_CONTACTS:
            raise ValueError("The contact book exceeds its 250-contact limit.")
        return sorted(records, key=lambda record: _name(record["name"]).casefold())

    def save(self, args):
        if not isinstance(args, dict) or not {"name", "phone"} <= set(args) <= {"name", "phone", "aliases"}:
            raise ValueError("A contact needs only a name and a phone number.")
        name, phone = _name(args["name"]), _phone(args["phone"])
        aliases = [a for a in _aliases(args.get("aliases")) if a.casefold() != name.casefold()]
        with self.store.lock:
            records = self.list()
            matches = [r for r in records if _name(r["name"]).casefold() == name.casefold()]
            if len(matches) > 1:
                raise ValueError("That name is ambiguous. Delete duplicate labels and save distinct names.")
            others = [r for r in records if r not in matches]
            taken = {label for r in others for label in _labels(r)}
            clash = next((a for a in [name, *aliases] if a.casefold() in taken), None)
            if clash:
                raise ValueError(f'"{clash}" already points to someone else. Use a different nickname.')
            if matches:
                if matches[0]["phone"] != phone:
                    raise ValueError("That name already has a different number. Delete it first or use a distinct label.")
                merged = matches[0].get("aliases", []) + [a for a in aliases if a.casefold() not in _labels(matches[0])]
                if merged == matches[0].get("aliases", []):
                    return matches[0]
                return self.store.put("contact", {**matches[0], "aliases": _aliases(merged)}, matches[0]["id"])
            if len(records) >= MAX_CONTACTS:
                raise ValueError("The contact book is full. Delete a contact before adding another.")
            return self.store.put("contact", {"name": name, "phone": phone, **({"aliases": aliases} if aliases else {})})

    def resolve(self, recipient):
        if isinstance(recipient, str) and PHONE.fullmatch(recipient):
            return {"name": recipient, "phone": recipient}
        name = _name(recipient)
        records = self.list()
        matches = [r for r in records if _name(r["name"]).casefold() == name.casefold()]
        if not matches:
            nickname = re.sub(r"^(?:my|our)\s+", "", name, flags=re.I).casefold()
            matches = [r for r in records if nickname in _labels(r)]
        if not matches:
            raise ValueError("No exact saved contact matches that name. Save the contact or provide an E.164 number.")
        if len(matches) != 1:
            raise ValueError("That name matches multiple contacts. Use a distinct saved label or an exact phone number.")
        _phone(matches[0]["phone"])
        return matches[0]

    def by_phone(self, phone):
        return next((r for r in self.list() if r["phone"] == phone), None)

    def delete(self, contact_id):
        if not isinstance(contact_id, str) or not contact_id:
            raise ValueError("Choose a saved contact to delete.")
        return self.store.delete("contact", contact_id)
