"""A look-up that can't run (no browser tools on this machine, or no network) is never the whole reply to something a friend
just knows, and never a guess at something nobody knows without looking.

Human Test v2, run 72: "That's not what I asked. How much water per cup of rice?" The brain asked for a web search, the
machine had no browser tools, and what went wrong was handed back to the brain as "what your web search found". It read it
out: "I need my browser tools to look things up. Reinstall Luma's tools from Settings."

Two sets of forty, written Nov 21 before the fix. The first was built on. The second was measured once, afterwards, and
nothing was changed to fit it."""
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent import runtime
from luma.agent.runtime import Agent
from luma.integrations.providers import ProviderError
from luma.memory.store import Store

WRONG = "I need my browser tools to look things up. Reinstall Luma's tools from Settings."
KNOWN = "From what I know, it's two to one."
READ_OUT = "It says I need my browser tools to look things up."

KNOW = ["how much water per cup of rice", "how long do you boil an egg", "what temperature should chicken be cooked to",
        "how do you get red wine out of a carpet", "what's the capital of australia", "how many days are in february", "why is the sky blue",
        "how do i jump start a car", "what's the difference between baking soda and baking powder", "how long does it take to drive across texas",
        "who wrote pride and prejudice", "how do you say thank you in japanese", "what does rsvp stand for", "how long should i steep green tea",
        "can dogs eat grapes", "how many calories are in a banana", "what year did the titanic sink", "how do i tie a tie", "is a tomato a fruit",
        "how far is the moon"]
NEEDS_A_LOOK = ["who won the lakers game last night", "what's the weather in denver tomorrow", "what time does target close tonight",
                "is the 405 backed up right now", "what's the price of bitcoin", "when does the new season of the bear come out",
                "look up the hours for the dmv", "google the best pizza near me", "what's the latest on the hurricane", "who's playing at red rocks this weekend",
                "search for flights to chicago", "what's trending today", "how much is a ps5 right now", "did the senate vote today",
                "what's the score of the game", "is the pharmacy open", "what movies are out this week", "find me a recipe online for lasagna",
                "what's the exchange rate for yen today", "check if my flight is on time"]
SAID_BY_LUMA = ["who won the lakers game last night", "what time does target close tonight", "when does the new season of the bear come out",
                "look up the hours for the dmv", "google the best pizza near me", "what's the latest on the hurricane", "who's playing at red rocks this weekend",
                "what's the score of the game", "what movies are out this week", "what's the exchange rate for yen today"]
KNOW_2 = ["how long do i bake salmon at 400", "what's the boiling point of water", "how many legs does a spider have", "how do you get gum out of hair",
          "what's a good substitute for buttermilk", "who painted the mona lisa", "how much sleep does an adult need", "what does bcc mean in email",
          "how long can cooked rice stay in the fridge", "is it safe to eat raw cookie dough", "how do i reset my router", "what's the square root of 144",
          "how many continents are there", "what's the freezing point in fahrenheit", "how long does it take to hard boil eggs",
          "why do onions make you cry", "how do you fold a fitted sheet", "what's the tallest mountain in the world",
          "how many players are on a soccer team", "what is a haiku"]
NEEDS_A_LOOK_2 = ["who won the election", "what's the traffic like on i-95", "when is the next full moon", "is costco open today",
                  "what's the stock price of apple", "what time is the super bowl", "any news about the strike", "look up how to renew a passport",
                  "what's playing at the movies tonight", "how much are eggs right now", "who is the mayor of chicago now", "search the web for cheap flights",
                  "did the yankees win", "what's the weather this weekend", "when does daylight saving time end this year", "is there a recall on my car",
                  "what are today's headlines", "pull up the menu for olive garden", "what's the wait time at the er",
                  "can you check the reviews for that restaurant"]


class WhenALookUpCantRun(unittest.TestCase):
    def ask(self, said, before=(), one_trip=False, talk="Just talking."):
        """One turn on a fresh Luma whose web search can't run, with a brain that asks for the web whenever it's offered, reads
        out whatever it's handed as "what the search found", and answers from what it knows when told it couldn't look.
        one_trip: the way a small device answers, without weighing a question from four sides first."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        agent.use_model = True

        def broken(query):
            raise ProviderError(WRONG)
        agent.search_web = broken
        self.told = []

        def planner(messages, context, allowed, mode):
            last = str(messages[-1].get("content"))
            self.told.append(last)
            if "browser tools" in last:
                return {"type": "reply", "text": READ_OUT}
            if "web.search" in allowed:
                return {"type": "tool", "name": "web.search", "arguments": {"query": said[:80]}}
            return {"type": "reply", "text": KNOWN if runtime.COULDNT_LOOK_NOTE in last else talk}
        agent.planner = planner
        if one_trip:
            agent._extra_look = lambda key: False
        for role, text in before:
            agent.history.append({"role": role, "content": text})
        out = agent.chat(said)
        return str(out.get("text") or out.get("summary") or "")

    def test_the_rice_moment(self):
        out = self.ask("That's not what I asked. How much water per cup of rice?",
                       [("user", "How do I make rice?"), ("assistant", "Rinse it, bring it to a boil, cover it, and let it simmer low for about 15 minutes.")],
                       one_trip=True)
        self.assertNotIn("browser tools", out)
        self.assertIn("two to one", out)
        self.assertTrue(any(runtime.COULDNT_LOOK_NOTE in told for told in self.told), "the brain is told it couldn't look")
        self.assertFalse(any("What your web search found" in told and "browser tools" in told for told in self.told),
                         "what went wrong is never handed over as what the web found")

    def test_a_check_that_cant_run_leaves_the_weighed_answer_standing(self):
        """A question weighed from a few sides is checked against the web when the answer says it hinges on a fact. A check
        that can't run never replaces that answer with what went wrong."""
        weighed = "Two cups of water to one of rice is the usual, though I'd need to check for brown rice."
        out = self.ask("That's not what I asked. How much water per cup of rice?",
                       [("user", "How do I make rice?"), ("assistant", "Rinse it, bring it to a boil, cover it, and let it simmer low.")], talk=weighed)
        self.assertNotIn("browser tools", out)
        self.assertIn("Two cups of water", out)

    def test_something_a_friend_just_knows_is_answered(self):
        for said in KNOW:
            out = self.ask(said)
            self.assertNotIn("browser tools", out, said)
            self.assertIn(out, {KNOWN, "Just talking."}, said)

    def test_what_nobody_knows_without_looking_is_never_a_guess(self):
        for said in NEEDS_A_LOOK:
            self.assertTrue(runtime.ONLY_BY_LOOKING.search(said), said)
            out = self.ask(said)
            self.assertNotEqual(out, KNOWN, said)
            self.assertNotEqual(out, READ_OUT, said + ": Luma says it itself, a brain never reads it out")
        for said in SAID_BY_LUMA:
            self.assertEqual(self.ask(said), WRONG, said)

    def test_talk_that_only_sounds_like_a_question_keeps_its_own_path(self):
        """Nobody asked to look anything up: the brain just talks (the test that was here first is in test_friend_style)."""
        out = self.ask("i read like fifty mattress reviews tonight and i'm more confused than before")
        self.assertNotIn("browser tools", out)

    def test_no_brain_to_ask_says_what_went_wrong(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        self.assertEqual(agent._couldnt_look("how far is the moon", {"state": "failed", "summary": WRONG}, threading.Event()), WRONG)

    def test_the_second_forty_written_before_the_fix(self):
        """Measured once. Something a friend just knows: the brain answered 16 before, 18 after (the error was read out for 4,
        then 2). Needs a look: Luma's own "couldn't look" 11 before, 10 after; one more question goes to the brain, told that it
        couldn't look. That one is the cost, and it's written down, not fixed."""
        answered = sum(self.ask(said) in {KNOWN, "Just talking."} for said in KNOW_2)
        self.assertGreaterEqual(answered, 18)
        outs = [self.ask(said) for said in NEEDS_A_LOOK_2]
        self.assertEqual(sum(out == READ_OUT for out in outs), 0, "a brain never reads out what went wrong")
        self.assertLessEqual(sum(out == KNOWN for out in outs), 1)
        self.assertGreaterEqual(sum(out == WRONG for out in outs), 10)


# Written Nov 21 before the fix. Talk with a weather word in it: with web search on, 18 of the first twenty were sent word for
# word to a search nobody asked for, and answered from what it found. The first twenty were built on (18 -> 0). The second
# twenty were measured once, afterwards: 16 -> 0.
WEATHER_TALK = ["random question, but do you like rain?", "i love the sound of rain", "rainy days make me so sleepy", "my kid has a temperature of 101",
                "have you ever seen snow", "what temperature do you bake cookies at", "do you like snow or rain better",
                "what temperature should chicken be cooked to", "the snow was so pretty this morning", "i got caught in the rain walking home",
                "we used to go sledding every time it snowed", "is it weird that i like the smell of rain", "my hair hates the rain",
                "she left me standing in the rain", "what's your favorite kind of weather", "i'm a snow person, my husband is a beach person",
                "the forecast for my love life is bleak", "running a temperature and feeling awful", "i miss the snow back home",
                "rain always reminds me of my grandmother"]
WEATHER_ASKED = ["is it going to rain tomorrow", "what's the weather like", "any snow in the forecast", "what's the temperature outside", "is it snowing in denver",
                 "how much snow did we get", "does it rain a lot in portland", "will it rain this weekend", "what's the forecast for friday",
                 "how much rain is seattle getting this week"]
WEATHER_TALK_2 = ["do you ever wish you could feel rain", "it rained on my wedding day", "snow days were the best part of being a kid", "i hate driving in the rain",
                  "what temperature should i set my oven to for pizza", "my dog is scared of the rain", "the baby's temperature finally came down",
                  "there's something cozy about a rainy sunday", "i slipped in the snow and bruised my hip", "do you prefer hot weather or cold weather",
                  "i grew up somewhere it never snowed", "we got rained out of the picnic", "what temperature is a fever", "snow makes everything so quiet",
                  "the weather matched my mood today", "he proposed in the rain, it was perfect", "my knee aches whenever it rains",
                  "i've never seen snow in my life", "at what temperature does water boil", "singing in the rain is my comfort movie"]
WEATHER_ASKED_2 = ["is it raining right now", "what's the weather tomorrow", "is it supposed to snow tonight", "how cold is it outside", "weather in chicago",
                   "what's the temperature in phoenix", "do i need an umbrella today", "chance of rain this afternoon", "when is the snow supposed to start",
                   "how hot will it be this weekend"]


class AWeatherWordAloneIsTalk(unittest.TestCase):
    def turn(self, said):
        """(what was sent to a web search, whether anything but the brain answered) with web search switched on."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        agent.use_model = True
        sent = []

        def search(query):
            sent.append(query)
            return {"results": [], "query": query, "summary": "nothing"}
        agent.search_web = search
        news = agent.news_reply
        agent.news_reply = lambda text, *a, **k: sent.append("the news reader: " + str(text)) or news(text, *a, **k)
        on = agent.integration_on
        agent.integration_on = lambda name: True if name == "web_search" else on(name)
        agent.planner = lambda messages, context, allowed, mode: {"type": "reply", "text": "Just talking."}
        out = agent.chat(said)
        return sent, str(out.get("text") or out.get("summary") or "") != "Just talking."

    def their_words(self, sent):
        """Their sentence went out (three words or more). Reading up on a thing they name sends its name and nothing else."""
        return any(len(query.split()) >= 3 for query in sent)

    def test_talk_with_a_weather_word_is_never_sent_to_a_search(self):
        for said in WEATHER_TALK:
            sent, answered = self.turn(said)
            self.assertFalse(self.their_words(sent), (said, sent))
            self.assertFalse(runtime.asks_live(said), said)
            self.assertFalse(answered, said + ": it's talk, so the brain answers (never \"Which city?\")")

    def test_the_weather_out_there_is_still_looked_at(self):
        for said in WEATHER_ASKED:
            sent, answered = self.turn(said)
            self.assertTrue(sent or answered, said)

    def test_the_second_sets_written_before_the_fix(self):
        talk = [self.turn(said) for said in WEATHER_TALK_2]
        self.assertEqual(sum(self.their_words(sent) for sent, _ in talk), 0, "measured: 16 before, 0 after")
        self.assertEqual(sum(answered for _, answered in talk), 0, "and none got \"Which city?\"")
        looked = sum(bool(sent or answered) for sent, answered in map(self.turn, WEATHER_ASKED_2))
        self.assertGreaterEqual(looked, LOOKED_2)

    def test_asked_what_luma_likes_is_small_talk_not_a_decision(self):
        """Once "do you like rain?" stopped going to a web search it was weighed from four sides and judged: five trips
        through the brain for small talk. A real decision still is weighed."""
        from luma.agent import mind
        for said in ["Random question, but do you like rain?", "have you ever seen the northern lights in person?", "do you prefer mornings or nights, be honest?"]:
            self.assertFalse(mind.is_hard(said), said)
        for said in ["do you like my plan to quit and move to austin?", "should i take the job in denver or stay here?",
                     "what would you do if your sister stopped talking to you?", "is it worth getting a second dog right now?",
                     "do you think i should tell her how i feel?"]:
            self.assertTrue(mind.is_hard(said), said)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        agent.use_model = True
        trips = []
        agent.planner = lambda messages, context, allowed, mode: trips.append(1) or {"type": "reply", "text": "I do. The sound of it, mostly."}
        self.assertIn("The sound of it", agent.chat("Random question, but do you like rain?")["text"])
        self.assertEqual(len(trips), 1)


# Written Nov 21 before the fix. The same, for the news, the traffic, a score, a price: Luma looks when it's asked, never when
# it's told. "i've got good news, i'm pregnant" was answered with the headlines; "the news about my dad isn't good" went to a
# web search. The first thirty were built on; the second thirty measured once, afterwards.
TOLD = ["i got some bad news today", "the news about my dad isn't good", "traffic was a nightmare on the way to the funeral", "i've got good news, i'm pregnant",
        "my mom watches the news all day and it stresses her out", "we had a huge fight about who won the argument last time", "i'm so tired of bad news",
        "no news from the doctor yet and i'm freaking out", "sat in traffic for two hours thinking about her", "my brother lost everything on bitcoin",
        "we have a game tonight and i'm nervous", "the headlines make me anxious so i stopped reading", "i can't watch the news anymore, it's all too sad",
        "did i win her back? no. did i try? yes", "she broke the news to me over text", "my test scores came back and i failed",
        "stuck in traffic again, story of my life", "any news is good news at this point honestly", "i hate the news, it's always something",
        "good news travels slow in my family"]
ASKED = ["what's in the news today", "any news about the election", "what's the score of the lakers game", "who won the super bowl", "how's traffic on the 101",
         "what's the bitcoin price", "did the eagles win last night", "what are the headlines", "what time does costco open", "latest on the wildfire"]
TOLD_2 = ["i have news, we're getting a divorce", "the traffic noise outside my window keeps me up", "he told me the news and i just sat there",
          "my grandpa reads me the headlines every morning, it's our thing", "we got the news on tuesday, it's cancer",
          "there's a game tonight but i don't feel like going", "bad news always comes in threes for me",
          "my dad put his savings into bitcoin and now he won't talk about it", "i was the one who won the fight but i feel terrible",
          "waiting on news about the job and i can't focus", "the news of her passing hit me harder than i expected", "traffic makes me think too much",
          "i'm scared to check the news these days", "that's old news, we broke up months ago", "no news yet, they said they'd call by friday",
          "the game tonight is my son's first start, i might cry", "did we win? barely. did i play? no", "i keep refreshing for news about my visa",
          "my sister always has to be the one who won", "honestly the news about the layoffs has me rattled"]
ASKED_2 = ["what's the news this morning", "any headlines i should know about", "who won the game last night", "what's the score right now", "is traffic bad on i-5",
           "how's bitcoin doing", "did the chiefs win", "what's the latest news on the storm", "is target open now", "what's the exchange rate for euros"]


class ToldNotAsked(AWeatherWordAloneIsTalk):
    def out_there(self, sent):
        return any(len(query.split()) >= 3 for query in sent)

    def test_told_something_luma_never_looks(self):
        """Before: 15 of these 20 sent out, 17 answered by something other than a friend."""
        for said in TOLD:
            self.assertTrue(runtime.told_not_asked(said), said)
            sent, answered = self.turn(said)
            self.assertFalse(sent, (said, sent))
            self.assertFalse(answered, said)

    def test_a_brain_isnt_offered_the_web_for_what_its_told(self):
        """Before: 13 of the first twenty and 13 of the second offered a brain a web search, to use on their sentence or not."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        agent.use_model = True
        for said in TOLD + WEATHER_TALK:
            self.assertNotIn("web.search", agent.available_tools(said), said)
        self.assertEqual(sum("web.search" in agent.available_tools(said) for said in TOLD_2), 0)
        self.assertLessEqual(sum("web.search" in agent.available_tools(said) for said in WEATHER_TALK_2), 1, "measured: 2 before, 1 after")
        for said in ["what's the latest news on the storm", "search for flights to chicago", "who won the game last night", "look up the hours for the dmv"]:
            self.assertIn("web.search", agent.available_tools(said), said)

    def test_asked_it_still_looks(self):
        for said in ASKED:
            self.assertFalse(runtime.told_not_asked(said), said)
            sent, answered = self.turn(said)
            self.assertTrue(sent or answered, said)

    def test_a_request_said_as_a_sentence_is_still_a_request(self):
        for said in ["news please", "i'd like to hear the news", "let me hear the headlines", "read the news to me", "you got the lakers score",
                     "need the score of the game", "play the news", "i missed the game last night, who won", "the latest news on the storm in florida",
                     "lakers score", "tell me what's going on in the world", "i want the headlines", "check the traffic for me", "bitcoin price",
                     "i wonder who won the game", "news from the last hour", "headlines from this morning"]:
            self.assertFalse(runtime.told_not_asked(said), said)
        for said in ["the news is depressing", "today's news was rough on my mom", "ugh, need a break from the news", "that's old news, honestly", "bad news again"]:
            self.assertTrue(runtime.told_not_asked(said), said)

    def test_the_second_thirty_written_before_the_fix(self):
        """Measured once. Told, of 20: their sentence sent out 19 before, 0 after; answered by something other than a friend 20
        before, 0 after. Asked, of 10: looked at 10 before, 9 after. The one is the cost: a real request left to the brain."""
        told = [self.turn(said) for said in TOLD_2]
        self.assertEqual(sum(self.out_there(sent) for sent, _ in told), 0)
        self.assertEqual(sum(bool(sent) or answered for sent, answered in told), 0)
        asked = [self.turn(said) for said in ASKED_2]
        self.assertGreaterEqual(sum(bool(sent) or answered for sent, answered in asked), 9)

    # the weather's own tests are the class above; inherited here they'd only run twice
    test_talk_with_a_weather_word_is_never_sent_to_a_search = test_the_weather_out_there_is_still_looked_at = None
    test_the_second_sets_written_before_the_fix = test_asked_what_luma_likes_is_small_talk_not_a_decision = None


LOOKED_2 = 10  # measured: 10 of 10 before and after

if __name__ == "__main__":
    unittest.main()
