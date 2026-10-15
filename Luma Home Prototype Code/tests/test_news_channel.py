"""The News page as a channel: stories carry their pictures, and a story opens inside Luma as plain words."""
import unittest

from luma.skills import news

FEED = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel><title>x</title>
<item><title>With a thumbnail</title><link>https://a.example/1</link><media:thumbnail url="https://img.example/1.jpg"/></item>
<item><title>With media content</title><link>https://a.example/2</link><media:content url="https://img.example/2.jpg" medium="image"/></item>
<item><title>With an enclosure</title><link>https://a.example/3</link><enclosure url="https://img.example/3.jpg" type="image/jpeg"/></item>
<item><title>Picture in the summary</title><link>https://a.example/4</link><description>&lt;img src="https://img.example/4.jpg"&gt; words</description></item>
<item><title>No picture</title><link>https://a.example/5</link><enclosure url="http://img.example/5.jpg" type="image/jpeg"/></item>
</channel></rss>"""

ARTICLE = """<!doctype html><html><head><title>Fed holds | The Wire</title>
<meta property="og:title" content="Fed holds rates steady">
<meta property="og:site_name" content="The Wire">
<meta property="og:image" content="https://img.example/fed.jpg"></head>
<body><nav><p>Home · World · Business · Tech · Sports · a long navigation paragraph that should never be read out</p></nav>
<article><p>The Federal Reserve left interest rates unchanged on Wednesday, as officials weighed slowing inflation against a cooling job market.</p>
<p>Short.</p>
<p>Policymakers signaled one more cut is likely before the end of the year, according to the statement released after the meeting.</p>
<p>Policymakers signaled one more cut is likely before the end of the year, according to the statement released after the meeting.</p>
<p>Subscribe to our newsletter to get stories like this one in your inbox every morning, before anyone else.</p>
<script>var p = "<p>not a paragraph</p>";</script></article>
<footer><p>All rights reserved, The Wire, a very long footer line that should not appear in the story.</p></footer></body></html>"""


class NewsChannelTests(unittest.TestCase):
    def test_pictures_come_with_the_stories(self):
        items = {i["title"]: i.get("image") for i in news.parse(FEED, "Test")}
        self.assertEqual(items["With a thumbnail"], "https://img.example/1.jpg")
        self.assertEqual(items["With media content"], "https://img.example/2.jpg")
        self.assertEqual(items["With an enclosure"], "https://img.example/3.jpg")
        self.assertEqual(items["Picture in the summary"], "https://img.example/4.jpg")
        self.assertIsNone(items["No picture"])  # only https pictures

    def test_a_story_reads_as_plain_words(self):
        story = news.read_article("https://wire.example/fed", fetch=lambda url, allow_local: ARTICLE.encode())
        self.assertEqual(story["title"], "Fed holds rates steady")
        self.assertEqual(story["source"], "The Wire")
        self.assertEqual(story["image"], "https://img.example/fed.jpg")
        self.assertEqual(len(story["paragraphs"]), 2)  # no nav, footer, script, duplicates, newsletter pitch or scraps
        self.assertTrue(story["paragraphs"][0].startswith("The Federal Reserve"))

    def test_only_web_pages(self):
        for bad in ["file:///etc/passwd", "http://192.168.1.10/", "javascript:alert(1)"]:
            with self.assertRaises(ValueError):
                news.read_article(bad, fetch=lambda url, allow_local: b"")


if __name__ == "__main__":
    unittest.main()
