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


# Written Nov 21 before the fix: narration with a command word in it. Four of the first thirty weren't left to a friend:
# "give me a minute, i'm crying" got "Okay, I'll keep quiet for half an hour."; "play it again in my head every night" was set
# as a task for 9 PM; "flip a coin, that's how i make decisions now" got "Tails."; "remember when dad used to sing in the car"
# got "I don't have anything saved about that yet." The second thirty were measured once, afterwards: 2 before, 2 after.
NARRATED = ["you remind me of my sister sometimes", "don't remind me lol", "remind me why i married him", "that smell reminds me of my grandma's kitchen",
            "add that to the list of reasons i'm single lol", "he's on my list of people i'll never forgive", "give me a minute, i'm crying",
            "wake me up when this year is over", "my boss roasted me in front of everyone", "they roast my cooking every thanksgiving",
            "he told me to be serious for once", "she said i need to turn it down a notch", "i set an alarm and still missed her call",
            "the timer on my marriage ran out a while ago", "i keep a mental list of everything i did wrong", "play it again in my head every night",
            "flip a coin, that's how i make decisions now", "i wish i could mute my own thoughts", "turn off the lights and the house feels so empty",
            "remember when dad used to sing in the car", "forget everything i said, i was being dramatic", "he never texts me back anymore",
            "stop, you're going to make me cry", "i can't spell out how much that hurt", "what time is it even, i've lost track of the days",
            "count me out of the family reunion", "i'd roll the dice on him again honestly", "volume up on the sad songs tonight i guess",
            "note to self: never date a drummer", "save me from this group chat"]
NARRATED_2 = ["you always remind me to breathe", "nobody needs to remind me what day it is", "remind me never to trust him again",
              "this weather reminds me of the day we met", "put that on the list of things i'll deal with never",
              "she's at the top of my list right now, not in a good way", "give me a second, that hit hard", "wake me up when he grows up",
              "my friends roasted me for crying at the movie", "we roast each other, it's how we show love", "my mom said to be serious about someone already",
              "the doctor told me to turn down the stress", "i snoozed the alarm on my whole life", "the clock is ticking on this relationship",
              "i made a list of pros and cons and cried", "it plays on a loop in my mind", "heads or tails, either way i lose",
              "i put my feelings on mute for years", "lights out by nine, that's my wild life now", "remember how mom used to hum in the kitchen",
              "forget what i said about being fine", "she left me on read again", "stop it, i'm already emotional", "i can't put into words how tired i am",
              "what day is it, they all blur together", "count on me to ruin a good thing", "it's a roll of the dice whether he calls",
              "turn up for my birthday or don't, i guess", "reminder that i am not okay lol", "delete this year from the record"]
STAY = "Take your time. I'm here."


class NarrationIsntACommand(unittest.TestCase):
    def reply(self, said):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        agent.use_model = True
        agent.planner = lambda messages, context, allowed, mode: {"type": "reply", "text": "Just talking."}
        out = agent.chat(said)
        return str(out.get("text") or out.get("summary") or "")

    def test_a_friend_talks_back(self):
        for said in NARRATED:
            self.assertIn(self.reply(said), {"Just talking.", STAY}, said)
        self.assertEqual(self.reply("give me a minute, i'm crying"), STAY, "it stays, for five minutes of quiet, not half an hour")

    def test_the_real_requests_still_work(self):
        for said in ["flip a coin", "flip a coin for me", "heads or tails", "toss a coin please"]:
            self.assertIn(self.reply(said), {"Heads.", "Tails."}, said)
        self.assertEqual(self.reply("give me a minute"), STAY)
        self.assertIn("Every day at 9 PM", self.reply("every night at 9, play rain sounds"))
        self.assertIn("anything saved", self.reply("remember when my appointment is"))

    def test_the_second_thirty_written_before_the_fix(self):
        """Measured once: 2 of 30 not left to a friend before, 2 after (one more now gets "Take your time. I'm here.")."""
        self.assertLessEqual(sum(self.reply(said) not in {"Just talking.", STAY} for said in NARRATED_2), 2)


if __name__ == "__main__":
    unittest.main()
