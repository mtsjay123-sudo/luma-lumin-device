"""docs/BUSINESS_MODEL.md: the sums are done again here, so a price can't change without its totals, and every number says
what kind it is. Nothing in it is a forecast, and it keeps the project's rules."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "BUSINESS_MODEL.md").read_text(encoding="utf-8")


def money(text):
    return float(text.replace("$", "").replace(",", "").replace("*", ""))


def row(label):
    line = next(l for l in DOC.splitlines() if l.startswith("| " + label) or l.startswith("| **" + label))
    return [c.strip() for c in line.strip("|").split("|")][1:]


class TheSums(unittest.TestCase):
    def test_a_seat_adds_up(self):
        prices = [money(p) for p in re.findall(r"seat at (\$\d+)", DOC)[:2]]
        self.assertEqual(prices, [35.0, 45.0])
        lamp, months = [money(v) for v in re.search(r"spread over 36 months \((\$\d+) and (\$\d+)\)", DOC).groups()], 36
        costs = [row("The lamp, spread"), row("Support and setup help"), row("Updates, the relay"), row("Lamps that break"), row("Card fees")]
        for i, price in enumerate(prices):
            self.assertAlmostEqual(money(costs[0][i]), lamp[i] / months, delta=0.03)
            self.assertAlmostEqual(money(costs[4][i]), price * 0.03, delta=0.005)
            total = sum(money(c[i]) for c in costs)
            self.assertAlmostEqual(money(row("Cost")[i]), total, places=2)
            left, share = re.match(r"\*\*(\$[\d.]+) \((\d+)%\)\*\*", row("Left over")[i]).groups()
            self.assertAlmostEqual(money(left), price - total, places=2)
            self.assertEqual(int(share), round(100 * (price - total) / price))
        self.assertIn("**$0**", row("The cloud bill for thinking")[0], "the brain is in the lamp")

    def test_the_bigger_sums_follow_from_the_seat(self):
        left = money(re.match(r"\*\*(\$[\d.]+)", row("Left over")[0]).group(1))
        for seats, takes, keeps in ((1_000, "$420,000", 259_000), (10_000, "$4.2 million", 2_600_000), (50_000, "$21 million", 12_900_000)):
            line = next(l for l in DOC.splitlines() if l.startswith(f"| {seats:,} program seats"))
            self.assertIn(takes, line)
            self.assertAlmostEqual(seats * 35 * 12, {"$420,000": 420_000, "$4.2 million": 4_200_000, "$21 million": 21_000_000}[takes])
            self.assertAlmostEqual(seats * left * 12, keeps, delta=keeps * 0.01)
        self.assertAlmostEqual(10_000 * 249, 2_490_000)
        self.assertAlmostEqual(10_000 / 3 * 9.99 * 12, 400_000, delta=1_000)

    def test_the_parts_sums_come_from_the_build_guide(self):
        guide = (ROOT / "hardware" / "README.md").read_text(encoding="utf-8")
        self.assertIn("**about $405**", guide)
        self.assertIn("about $405", DOC)
        self.assertIn("about $250", guide)
        self.assertIn("about $4,000", DOC)    # ten lamps
        self.assertIn("about $12,500", DOC)   # fifty Minis
        self.assertAlmostEqual(10 * 405, 4_000, delta=100)
        self.assertEqual(50 * 250, 12_500)

    def test_the_texting_numbers_are_the_blueprints(self):
        blueprint = (ROOT / "docs" / "LUMA_BLUEPRINT.md").read_text(encoding="utf-8")
        self.assertIn("$5.43", blueprint)
        self.assertIn("$5.43", DOC)
        self.assertAlmostEqual(9.99 - 5.43, 4.56, places=2)
        self.assertIn("$4.56", DOC)


class TheRules(unittest.TestCase):
    def test_every_number_says_what_kind_it_is(self):
        for word in ("**known**", "**ours**", "**assumption**", "Nothing here is a forecast", "Not a forecast"):
            self.assertIn(word, DOC)
        self.assertGreaterEqual(DOC.count("assumption"), 8)

    def test_it_says_what_is_not_true_yet(self):
        for words in ("Nobody has built one", "None yet", "isn't built yet", "no lamp reaches that"):
            self.assertIn(words, DOC)

    def test_it_never_earns_from_ads_data_or_minutes(self):
        for words in ("No ads", "No data", "No attention", "No health claims", "Never minutes", "Only with each member's yes",
                      "behind a setting that starts off"):
            self.assertIn(words, DOC)

    def test_what_is_known_has_a_source(self):
        self.assertGreaterEqual(len(re.findall(r"https://", DOC)), 5)


if __name__ == "__main__":
    unittest.main()
