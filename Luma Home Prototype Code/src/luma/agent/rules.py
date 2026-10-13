"""The owner's rules: what Luma just does, what it asks first, and what it never does.

Every tool belongs to one category. Quiet work that only reads or prepares
(browsing, comparing prices, drafts, reminders) runs on its own unless the owner
blocks it; nothing leaves the house that way, so there is nothing to ask. Anything
that speaks for the owner or spends money is locked to "ask" or "block": no
setting, page or model output can turn those into "allow". Checkout and
payment are never Luma's to do at all.
"""
from __future__ import annotations

CATEGORIES = {
    "browse": {"label": "Read websites and compare prices", "default": "allow", "choices": ("allow", "block")},
    "reminders": {"label": "Reminders, notes and memories", "default": "allow", "choices": ("allow", "block")},
    "drafts": {"label": "Write drafts (emails, texts, posts) for you to look over", "default": "allow", "choices": ("allow", "block")},
    "inbox": {"label": "Read your email and calendar", "default": "allow", "choices": ("allow", "block")},
    "cart": {"label": "Add things to a store cart", "default": "ask", "choices": ("allow", "ask", "block")},
    "texts": {"label": "Send texts", "default": "ask", "choices": ("ask", "block")},
    "email": {"label": "Send emails", "default": "ask", "choices": ("ask", "block")},
    "posts": {"label": "Post, like, follow or comment", "default": "ask", "choices": ("ask", "block")},
    "bookings": {"label": "Book appointments", "default": "ask", "choices": ("ask", "block")},
    "home": {"label": "Control lights and devices", "default": "ask", "choices": ("ask", "block")},
    "apps_read": {"label": "Look things up in your connected apps", "default": "allow", "choices": ("allow", "block")},
    "apps_act": {"label": "Make changes in your connected apps", "default": "ask", "choices": ("ask", "block")},
    "spend": {"label": "Checkout and payment", "default": "block", "choices": ("block",)},
}

TOOL_CATEGORY = {
    "web.search": "browse", "browser.open": "browse", "browser.read": "browse", "browser.scroll": "browse",
    "browser.click": "browse", "browser.type": "browse", "shop.compare": "browse",
    "browser.act": "posts",
    "shop.add_to_cart": "cart",
    "memory.remember": "reminders", "memory.recall": "reminders", "tasks.in": "reminders", "tasks.create": "reminders",
    "tasks.list": "reminders", "tasks.complete": "reminders", "routines.create": "reminders", "helpers.create": "reminders",
    "messages.prepare": "drafts", "mail.draft": "drafts", "deck.create": "drafts",
    "mail.inbox": "inbox", "mail.read": "inbox", "calendar.agenda": "inbox",
    "sms.send": "texts", "mac_messages.send": "texts", "luma.send": "texts",
    "mail.send": "email",
    "booking.availability": "browse", "booking.create": "bookings",
    "home.light": "home",
    "food.checkout": "cart",
}

VERBS = {
    "browse": "read websites", "reminders": "save reminders or notes", "drafts": "write drafts", "inbox": "read your email or calendar",
    "cart": "add things to carts", "texts": "send texts", "email": "send emails", "posts": "post, like, follow or comment",
    "bookings": "book appointments", "home": "control devices", "spend": "check out or pay",
    "apps_read": "look things up in your connected apps", "apps_act": "make changes in your connected apps",
}


class Blocked(ValueError):
    """The owner's rules say Luma doesn't do this."""


class Rules:
    def __init__(self, store):
        self.store = store

    def all(self):
        saved = self.store.setting("rules", {}) or {}
        out = []
        for key, spec in CATEGORIES.items():
            value = saved.get(key, spec["default"])
            if value not in spec["choices"]:
                value = spec["default"]
            out.append({"id": key, "label": spec["label"], "value": value, "choices": list(spec["choices"]),
                        "locked": "allow" not in spec["choices"]})
        return out

    def get(self, category):
        return next((r["value"] for r in self.all() if r["id"] == category), "ask")

    def set(self, category, value):
        if category not in CATEGORIES:
            raise ValueError("Unknown rule.")
        if value not in CATEGORIES[category]["choices"]:
            if value == "ask" and "allow" in CATEGORIES[category]["choices"] and "ask" not in CATEGORIES[category]["choices"]:
                raise ValueError("That one only reads or prepares things, so there's nothing to ask about. Allow or block it.")
            if category == "spend":
                raise ValueError("Luma never checks out or pays. You always do that part yourself.")
            raise ValueError("That one always asks you first. You can block it, but it can't run on its own.")
        saved = dict(self.store.setting("rules", {}) or {})
        saved[category] = value
        self.store.set_setting("rules", saved)
        return self.all()

    def for_tool(self, tool):
        category = TOOL_CATEGORY.get(tool)
        if category is None:
            # Household and timer tools are local and harmless.
            return None, "allow"
        return category, self.get(category)

    def check(self, tool):
        """Raise Blocked when the rules forbid this tool. Returns (category, value)."""
        category, value = self.for_tool(tool)
        if value == "block" and category != "spend":
            raise Blocked(f"Your rules say I don't {VERBS[category]}. You can change that in Rules.")
        return category, value

    def may_skip_approval(self, tool):
        """True only for unlocked categories the owner set to allow."""
        category, value = self.for_tool(tool)
        return category is not None and value == "allow" and "allow" in CATEGORIES[category]["choices"]
