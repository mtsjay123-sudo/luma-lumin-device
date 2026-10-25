"""A scripted brain and a fake web for testing the work platform end to end."""
SITE_PAGES = [
    {"slug": "index", "title": "Home", "sections": [
        {"kind": "hero", "heading": "Fresh tacos, five minutes from your desk", "body": "Taco Rocket brings chef-made tacos to downtown Atlanta offices.", "items": [{"title": "Order now", "text": "", "extra": "#contact"}, {"title": "See the menu", "text": "", "extra": "menu"}]},
        {"kind": "features", "heading": "Why Taco Rocket", "body": "", "items": [{"title": "Fast", "text": "Ready in five minutes.", "extra": ""}, {"title": "Fresh", "text": "Tortillas pressed every morning.", "extra": ""}, {"title": "Local", "text": "Atlanta farms only.", "extra": ""}]},
        {"kind": "stats", "heading": "By the numbers", "body": "", "items": [{"title": "12%", "text": "market growth last year", "extra": ""}, {"title": "$9", "text": "average plate", "extra": ""}]},
        {"kind": "contact", "heading": "Say hi", "body": "", "items": [{"title": "Where", "text": "Peachtree St, Atlanta", "extra": "hello@tacorocket.example"}]}]},
    {"slug": "menu", "title": "Menu", "sections": [
        {"kind": "pricing", "heading": "The menu", "body": "Simple and good.", "items": [{"title": "Two tacos", "text": "Choice of meat; Salsa bar", "extra": "$8"}, {"title": "Three tacos", "text": "Choice of meat; Salsa bar; Drink", "extra": "$11"}]},
        {"kind": "faq", "heading": "Questions", "body": "", "items": [{"title": "Vegan?", "text": "Yes, the mushroom al pastor.", "extra": ""}]}]},
]

ARGS = {
    "work.research": {"question": "Taco truck market in Atlanta", "queries": "Atlanta food truck market size\nAtlanta taco competitors prices"},
    "work.research_writeup": {"summary": "The Atlanta food truck market is growing and tacos lead it.", "gaps": "No data on lunch-hour foot traffic.",
                              "findings": [{"claim": "The Atlanta food truck market grew 12% last year.", "sources": [1], "confidence": "high"},
                                           {"claim": "Tacos Chingon charges about $9 a plate.", "sources": [2], "confidence": "medium"},
                                           {"claim": "A made-up claim citing nothing real.", "sources": [99], "confidence": "low"}],
                              "conflicts": [{"topic": "Permit cost", "detail": "One source says $500, another $800.", "sources": [1, 2]}]},
    "work.financial_model": {"name": "Taco Rocket model", "currency": "USD", "years": 3, "price": 45, "start_customers": 120, "monthly_growth_pct": 9, "monthly_churn_pct": 3,
                             "cogs_pct": 32, "monthly_costs": "Salaries: 9000; Truck lease: 1800; Marketing: 1200", "startup_cost": 60000},
    "work.graphics": {"brand": "Taco Rocket", "tagline": "Fresh tacos, fast", "primary_color": "#E5484D", "accent_color": "#FFC53D", "style": "playful", "assets": "logo, icon, social, banner, mockup, palette"},
    "work.document": {"title": "Taco Rocket business plan", "subtitle": "Atlanta, 2026", "format": "docx", "sections": [
        {"heading": "Summary", "paragraphs": ["Taco Rocket is a taco truck for downtown Atlanta offices. The market grew 12% last year [1] and the average competitor plate is about $9 [2]. We expect to be profitable within the first year based on the financial model."], "bullets": []},
        {"heading": "Plan", "paragraphs": ["We launch with one truck, two cooks and a pre-order app so office workers skip the line."], "bullets": ["Launch in March", "Second truck in year two"]}]},
    "work.website": {"name": "Taco Rocket", "tagline": "Fresh tacos, fast", "primary_color": "#E5484D", "accent_color": "#FFC53D", "style": "modern", "pages": SITE_PAGES},
    "work.code": {"folder": "order-calc", "test_command": "python -m unittest -v", "run_command": "python calc.py",
                  "files": [{"path": "calc.py", "content": "def total(prices, tip=0.18):\n    return round(sum(prices) * (1 + tip), 2)\n\nif __name__ == '__main__':\n    print(total([8, 11]))\n"},
                            {"path": "test_calc.py", "content": "import unittest\nfrom calc import total\n\nclass T(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(total([10]), 11.8)\n\nif __name__ == '__main__':\n    unittest.main()\n"}]},
    "work.game": {"title": "Taco Dash", "genre": "platformer", "goal": "Lunch delivered!", "player_color": "#E5484D", "accent_color": "#FFC53D",
                  "level": ["                                        ", "                    C C          G     ",
                            "        C        =====       E  ====   ", "   P   ===    C            ======      ", "#########  ######  ^^  ###########  ###"]},
    "work.model3d": {"name": "Phone stand", "units": "mm", "notes": "", "parts": [
        {"name": "base", "shape": "box", "size": [80, 60, 6], "at": [0, 0, 3], "color": "#6E56CF", "cut": False},
        {"name": "back", "shape": "box", "size": [80, 6, 70], "at": [0, 20, 38], "color": "#6E56CF", "cut": False},
        {"name": "cable hole", "shape": "cylinder", "size": [12, 12, 10], "at": [0, 0, 3], "color": "#E5484D", "cut": True}]},
}


def deck_args(slides=20):
    body = [{"layout": "title", "title": "Taco Rocket", "subtitle": "Fresh tacos, fast"},
            {"layout": "chart", "title": "Revenue grows every year", "chart_type": "column", "categories": ["Year 1", "Year 2", "Year 3"], "series": [{"name": "Revenue", "values": [80000, 160000, 300000]}]},
            {"layout": "table", "title": "Competitors", "rows": [["Name", "Price"], ["Tacos Chingon", "$9"]]},
            {"layout": "diagram", "title": "How ordering works", "steps": ["Order in the app", "We cook", "Pick up"]}]
    while len(body) < slides - 1:
        body.append({"layout": "bullets", "title": f"Point {len(body)}", "bullets": ["A real point", "Another real point"]})
    return {"title": "Taco Rocket pitch", "subtitle": "Seed round", "theme": "ember", "slides": body + [{"layout": "closing", "title": "Thank you"}]}


class Brain:
    """Answers each structured request the way a good model would; records what it was asked."""

    def __init__(self, overrides=None):
        self.calls, self.overrides = [], dict(overrides or {})

    def __call__(self, prompt, fields, name, tier, cancel):
        self.calls.append({"name": name, "tier": tier, "prompt": prompt})
        if name in self.overrides:
            value = self.overrides[name]
            return value(len([c for c in self.calls if c["name"] == name])) if callable(value) else value
        if name == "work.deck":
            return deck_args(20)
        return ARGS.get(name)


def search(query):
    return [{"title": "Atlanta food trucks report", "url": "https://example.com/atl-food-trucks", "snippet": "The market grew 12% last year.", "excerpt": "Atlanta food trucks grew 12 percent. Permits cost $500."},
            {"title": "Tacos Chingon menu", "url": "https://example.org/chingon", "snippet": "Plates around $9.", "excerpt": "Tacos Chingon: plates $9. Permit $800 says owner."}]
