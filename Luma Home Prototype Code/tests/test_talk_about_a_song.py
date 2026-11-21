"""Their sentence never goes out with " lyrics" on the end, and a story with "make me laugh" in it never gets a joke.

Found Nov 21 with fresh lines, the same way as tests/test_couldnt_look.py. Luma reads a song's lyrics on the web before it
quotes them. It did that by sending the whole message with " lyrics" added: "i've been writing lyrics again since the divorce
lyrics", "there's a line in my vows i keep rewriting lyrics", "the lines on my face are getting deeper lol lyrics". Now only
the name of the song or the artist is sent, and only when one is named.

And "make me laugh", anywhere in a message, got one of Luma's jokes: "the only person who could make me laugh is gone".

Every set was written before the fix. The first of each was built on; the second measured once, afterwards."""
import tempfile
import unittest
from pathlib import Path

from luma.agent import humor
from luma.agent.runtime import Agent, lyrics_query
from luma.memory.store import Store

TALK = ["the lyrics hit different after the breakup", "there's a line in my vows i keep rewriting", "the chorus of my life rn is disappointment",
        "i wrote some lyrics about my mom last night", "that one line from her text is living in my head", "i forget the lyrics every time i'm nervous",
        "my dad used to change the lyrics to make me laugh", "the hook of the story is that he never called", "she has a feature in the school paper this week",
        "i can't get that line of his out of my head, the one about me being too much", "we wrote our own verse for the wedding song",
        "the lyrics on the card she left made me cry", "he delivered that line in front of everyone at dinner", "i read the same line in the letter five times",
        "the lines on my face are getting deeper lol", "i've been writing lyrics again since the divorce", "the verse my grandma read at the funeral",
        "my kid sings the wrong lyrics to everything and i love it", "there's a line in the lease that scares me",
        "the bars at the gym window make it feel like jail lol"]
NAMED = {"kendrick's verse on control is still insane": "kendrick control lyrics", "what are the lyrics to bohemian rhapsody": "bohemian rhapsody lyrics",
         "the hook on that new sza song is stuck in my head": "new sza song lyrics", "that line in hotel california about the mission bell": "hotel california lyrics",
         "nicki's verse on monster though": "nicki monster lyrics", "what's the chorus of kill bill by sza": "kill bill by sza lyrics"}
TALK_2 = ["the lyrics finally make sense now that i'm a parent", "there's a line in his letter i can't stop reading",
          "the chorus of complaints from my in-laws never ends", "i tried writing lyrics about him and just cried", "that line from our fight keeps replaying",
          "i blanked on the lyrics at karaoke and wanted to die", "my mom hums and makes up lyrics when she's sad", "the hook in his apology was that he was tired",
          "my daughter got a feature in the yearbook", "one line of her eulogy has stayed with me", "we changed a verse of the hymn for dad",
          "the lyrics i wrote in high school are so embarrassing", "he crossed a line in front of my parents", "i keep rereading one line in the diagnosis",
          "the lines at the food bank were so long today", "writing lyrics is the only way i get through the nights",
          "the verse on her headstone is from her favorite psalm", "my husband mumbles lyrics in his sleep", "there's a line in the will nobody expected",
          "the bars on the crib came loose and i panicked"]
NAMED_2 = ["andre's verse on international players anthem", "what are the lyrics to fast car", "the chorus on espresso is so catchy",
           "that line in landslide about getting older", "jay's verse on renegade", "what's the hook of no scrubs"]

ABOUT_SOMEONE = ["my dad used to change the lyrics to make me laugh", "he could always make me laugh", "nobody can make me laugh like she did",
                 "she used to make me laugh so hard", "it takes a lot to make me laugh these days", "you always make me laugh lol",
                 "my kids make me laugh every day", "that show used to make me laugh", "he tried to make me laugh at the funeral",
                 "the only person who could make me laugh is gone"]
ASKED_OF_LUMA = ["make me laugh", "please make me laugh", "can you make me laugh", "ok luma make me laugh", "i had a rough day, make me laugh",
                 "try to make me laugh", "come on, make me laugh", "i need you to make me laugh right now"]
ABOUT_SOMEONE_2 = ["my grandpa lived to make me laugh", "she still knows how to make me laugh", "he would do anything to make me laugh",
                   "it used to be so easy to make me laugh", "nothing seems to make me laugh anymore", "they make me laugh until i cry",
                   "my ex could make me laugh even when i was mad", "you never fail to make me laugh", "his impressions make me laugh every time",
                   "the way she danced to make me laugh, i miss that"]
ASKED_OF_LUMA_2 = ["luma, make me laugh", "could you make me laugh for a sec", "make me laugh please", "just make me laugh", "bad day. make me laugh",
                   "go on, make me laugh", "i want you to make me laugh", "hey make me laugh"]


class TheirSentenceNeverGoesOutWithLyricsOnTheEnd(unittest.TestCase):
    def test_only_a_named_song_is_searched_and_only_its_name(self):
        self.assertEqual([(said, lyrics_query(said)) for said in TALK if lyrics_query(said)], [])
        for said, query in NAMED.items():
            self.assertEqual(lyrics_query(said), query, said)

    def test_through_luma_what_goes_out_is_the_name(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        agent.use_model = True
        sent = []

        def search(query):
            sent.append(query)
            return {"results": [{"title": "Control lyrics", "url": "https://example.com/control", "snippet": "the verse"}], "query": query, "summary": "Found it."}
        agent.search_web = search
        agent.planner = lambda messages, context, allowed, mode: {"type": "reply", "text": "That verse still goes."}
        agent.chat("kendrick's verse on control is still insane")
        self.assertEqual(sent, ["kendrick control lyrics"])
        del sent[:]
        for said in TALK:
            agent.chat(said)
        self.assertEqual([query for query in sent if len(query.split()) >= 3], [], "before: 15 of these 20 went out whole")

    def test_the_second_sets_written_before_the_fix(self):
        """Measured once. Talk, of 20: the whole message sent 19 before; 2 are taken for naming a song after. A song named, of 6:
        4 are searched by name (all 6 used to go out as the whole message)."""
        self.assertLessEqual(sum(bool(lyrics_query(said)) for said in TALK_2), 2)
        self.assertGreaterEqual(sum(bool(lyrics_query(said)) for said in NAMED_2), 4)
        for said in TALK_2 + NAMED_2:
            self.assertNotEqual(lyrics_query(said), (said + " lyrics")[:120], said)


class AStoryWithMakeMeLaughInItIsntAskingForAJoke(unittest.TestCase):
    def test_said_about_someone_its_their_story(self):
        self.assertEqual([said for said in ABOUT_SOMEONE if humor.asks_for_a_joke(said)], [], "before: 10 of 10 got a joke")
        self.assertEqual([said for said in ASKED_OF_LUMA if not humor.asks_for_a_joke(said)], [])
        for said in ["tell me a joke", "got any jokes", "roast my outfit", "say something funny", "tell me a joke about my boss, he tries to make me laugh"]:
            self.assertTrue(humor.asks_for_a_joke(said), said)

    def test_through_luma_the_brain_answers(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        agent.use_model = True
        said_so_far = []
        agent.planner = lambda messages, context, allowed, mode: {"type": "reply", "text": f"Tell me about that. ({len(said_so_far)})"}
        for said in ["the only person who could make me laugh is gone", "this song always makes me think of my dad", "that show used to make me laugh"]:
            said_so_far.append(said)
            self.assertIn("Tell me about that.", agent.chat(said)["text"], said)

    def test_the_second_sets_written_before_the_fix(self):
        """Measured once: said about someone, 10 of 10 got a joke before and 0 after; asked of Luma, 8 of 8 before and after."""
        self.assertEqual(sum(humor.asks_for_a_joke(said) for said in ABOUT_SOMEONE_2), 0)
        self.assertEqual(sum(humor.asks_for_a_joke(said) for said in ASKED_OF_LUMA_2), 8)


if __name__ == "__main__":
    unittest.main()
