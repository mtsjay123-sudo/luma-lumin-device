"""Checkout after a yes. Off until the owner turns it on in Rules. Then: the exact total, the card saved at the store (last four
only) and where it ships, a yes, and the order goes through only if the page still shows exactly that. Never a card number or
a password typed, never approved by text, never over the daily limit, never pressed twice."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store

NOW = 1793116800.0


class FakeStoreBrowser:
    def __init__(self, page=None, after=None):
        self.page = page or {"total": "43.17", "card": "Visa ending in 4242", "last4": "4242", "ship": "Jay Doe, Raleigh, NC", "cardFields": False,
                             "password": False, "button": "Place your order", "url": "https://www.amazon.com/checkout/spc"}
        self.after = after or {"confirmed": True, "order_number": "112-7788123-4455", "url": "https://www.amazon.com/thankyou"}
        self.opened, self.placed = [], []

    def checkout(self, url):
        self.opened.append(url)
        return dict(self.page)

    def place_order(self, total, button):
        if total != self.page["total"] or button != self.page["button"]:
            raise ValueError(f"The order changed since you said yes (it shows ${self.page['total']} now), so I didn't buy anything.")
        self.placed.append((total, button))
        return dict(self.after)

    def screenshot(self):
        return {}


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False, now=lambda: NOW)
        self.agent.enable("browser", True)
        self.agent._browser = self.browser = FakeStoreBrowser()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def turn_on(self):
        self.agent.rules.set("spend", "ask")

    def test_off_until_the_owner_turns_it_on(self):
        out = self.agent.chat("check out my amazon cart")
        self.assertIn("Placing orders is off", out["text"])
        self.assertEqual(self.browser.opened, [])
        with self.assertRaises(ValueError):
            self.agent.rules.set("spend", "allow")  # never on its own

    def test_the_exact_total_card_and_address_then_a_yes(self):
        self.turn_on()
        out = self.agent.chat("check out my amazon cart")
        self.assertEqual(out["state"], "pending")
        self.assertEqual(out["text"], "Your Amazon order comes to $43.17, paid with your Visa ending in 4242, shipping to Jay Doe, Raleigh, NC. Want me to place it?")
        self.assertEqual(self.browser.placed, [], "nothing is bought before the yes")
        done = self.agent.chat("yes")
        self.assertEqual(self.browser.placed, [("43.17", "Place your order")])
        self.assertIn("Your Amazon order for $43.17 is placed (order ending 4455)", done["text"])
        self.assertEqual(self.store.all("order", 5)[0]["total_cents"], 4317)
        self.assertIsNone(self.agent._spoken_approval("yes"), "nothing left to approve: never pressed twice")

    def test_a_changed_total_buys_nothing(self):
        self.turn_on()
        self.agent.chat("check out my amazon cart")
        self.browser.page["total"] = "58.40"  # the price moved after the yes was asked for
        done = self.agent.chat("yes place it")
        self.assertEqual(self.browser.placed, [])
        self.assertIn("didn't buy anything", done["text"])

    def test_card_fields_or_sign_in_hand_the_page_back(self):
        self.turn_on()
        self.browser.page["cardFields"] = True
        out = self.agent.chat("check out my amazon cart")
        self.assertIn("I never type card numbers", out["text"])
        self.assertTrue(out["handoff"])
        self.browser.page.update(cardFields=False, password=True)
        self.assertIn("I never type passwords", self.agent.chat("check out my amazon cart")["text"])

    def test_the_daily_limit(self):
        self.turn_on()
        self.store.set_setting("spend_cap", 50)
        self.store.put("order", {"store": "Target", "total_cents": 2000, "created": NOW - 3600})
        out = self.agent.chat("check out my amazon cart")
        self.assertIn("go over your $50 daily limit", out["text"])
        self.assertNotEqual(out.get("state"), "pending")

    def test_never_approved_by_text(self):
        self.turn_on()
        self.agent.chat("check out my amazon cart")
        code = self.agent.awaiting["code"]
        out = self.agent.chat(f"yes {code}", channel="sms")
        self.assertIn("never by text", out["text"])
        self.assertEqual(self.browser.placed, [])

    def test_kids_and_which_store(self):
        self.turn_on()
        self.assertIn("Which store's cart", self.agent.chat("check out")["text"])
        self.agent.last_cart_store = "Target"
        self.agent.chat("check out")
        self.assertEqual(self.browser.opened[-1], "https://www.target.com/cart")
        self.agent.chat("no")
        self.agent.set_mode("kids")
        self.assertIn("kids mode", self.agent.chat("check out my amazon cart")["text"])

    def test_no_confirmation_is_said_plainly(self):
        self.turn_on()
        self.browser.after = {"confirmed": False, "order_number": None, "url": "https://www.amazon.com/x"}
        self.agent.chat("check out my amazon cart")
        done = self.agent.chat("yes")
        self.assertIn("couldn't see a confirmation", done["text"])
        self.assertIn("won't press it twice", done["text"])


if __name__ == "__main__":
    unittest.main()
