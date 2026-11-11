"""Lines written by hand to check best-friend talk (luma.agent.friendtalk) on wording that came from no generator.

FIRST: written before the small model existed. Then they showed where the model was wrong about ordinary talk, and
the model's gates were shaped on them. So they're a guard now, not a measure.

SECOND: written after the gates were settled and before anything was run on them. One gap they showed was closed (a
decision about their own life said as "do you think i should"), and one miss was left as it is. Nothing else was
changed to fit them, and nothing should be: they're the honest number on hand-written lines.

ORDINARY: no move at all. SAID: the move a best friend makes ("look_up" is a fresh look, friendtalk.fresh)."""
FIRST_ORDINARY = [
    "just got home from work", "i think i'm gonna order thai tonight", "the wifi keeps cutting out", "my back hurts from sitting all day",
    "i forgot my umbrella again", "the neighbors are being loud", "i slept like ten hours last night", "traffic was awful this morning",
    "i need a haircut so bad", "the bus was late again", "made banana bread today", "i have a dentist appointment thursday",
    "my phone is at 3 percent", "it's raining again", "i cleaned the whole apartment", "my sister is visiting next week",
    "we went hiking on saturday", "the cat knocked over my plant", "i'm almost done with this book", "ran out of clean socks",
    "wake me up at seven", "add milk to my shopping list", "what's 15 times 12", "how many ounces in a cup", "turn the volume down a bit",
    "read me my reminders", "what day is it today", "can you spell necessary", "translate thank you into spanish",
    "how do you say good night in french",
    "how do i get a wine stain out of carpet", "why is the sky blue", "how long do you boil eggs", "what's the capital of australia",
    "how does a microwave work", "what does photosynthesis mean", "how far away is the moon", "why do onions make you cry",
    "how do i reset my router", "what temperature should chicken be cooked to",
    "should i take the job in denver or stay here", "do you think i should go back to school", "i can't decide if i should move in with him",
    "should i tell my boss i'm looking for other jobs", "is it better to rent or buy right now", "should i get a second dog",
    "idk if i should go to the wedding", "do i text her back tonight or wait", "should i sell my car", "thinking about dropping this class",
    "can you hear me ok", "what can you do", "how do i change your voice", "do you work without wifi", "are you still there",
    "did you get that", "what's your name again", "can you talk slower", "do you remember my birthday", "who made you",
    "i'm so tired today", "kind of bored honestly", "i'm nervous about tomorrow", "today was actually pretty good", "i'm starving",
    "feeling a bit off today", "i'm proud of myself for going to the gym", "so glad it's friday", "i'm stressed about this deadline",
    "that made me laugh",
    "my roommate left dishes in the sink again", "my mom keeps calling me about thanksgiving", "my boss moved the meeting to 8am",
    "my brother got a new job", "my friend is coming over later", "the guy next to me on the train was snoring",
    "my coworker brought donuts", "my dad wants me to call more", "my girlfriend loved the gift", "the kids are finally asleep",
    "i've been watching a lot of cooking shows", "i played basketball with my cousins yesterday",
    "we listened to old records at my grandma's", "i went to a concert when i was sixteen", "my nephew is obsessed with minecraft",
    "i used to play guitar", "there was a game on at the bar", "my playlist needs updating", "i fell asleep during the movie",
    "the radio in my car is broken",
    "ok cool", "haha yeah", "nah i'm good", "brb", "never mind", "wait what", "hmm", "sounds good", "good night luma", "thanks, that helped",
]
FIRST_SAID = {
    "take": [
        "is oat milk actually better than regular milk", "sweet or savory breakfast, what's the right call", "does pineapple belong on pizza",
        "be real with me, is die hard a christmas movie", "which star wars movie is the worst one", "is cereal a soup",
        "morning showers or night showers", "is it weird to put ketchup on eggs", "who's a better rapper, nas or jay-z",
        "name the best fast food fries", "are sequels ever better than the original", "was the ending of lost good or bad",
    ],
    "their_side": [
        "my roommate used my towel and i snapped at her, was that too much",
        "i told my friend her boyfriend is rude and now she's mad. was i out of line",
        "my brother never pays me back and i said no this time. am i being a jerk",
        "she cancelled on me three times so i stopped inviting her. is that petty",
        "my coworker took credit for my idea and i called it out in the meeting, did i go too far",
        "he forgot our anniversary and i'm still upset two days later, is that fair",
        "i didn't invite my cousin to the party because of last time. am i the bad guy here",
        "me and my mom argued about the holidays, who do you think is being unreasonable",
    ],
    "tea": [
        "what's the drama with those two youtubers", "did you catch that messy interview everyone's posting about",
        "everyone on tiktok is fighting about that influencer's apology", "ok what happened between those two actors, i keep seeing posts",
        "there's a rumor those two broke up", "why is everybody dragging that singer", "people are saying that streamer got exposed",
        "give me the gossip on the royal family",
    ],
    "fair": [
        "should rich people pay more taxes", "is the death penalty ever justified", "do you think borders should be open",
        "are you pro life or pro choice", "is religion good for the world", "should guns be harder to buy",
        "what's your opinion on the president", "who are you voting for",
    ],
    "think": [
        "if you could know your future, would you want to", "do you think we're alone in the universe", "can you be happy without other people",
        "why do we dream", "is anything truly random", "what would happen if nobody ever lied", "do you think money changes people",
        "is it wrong to lie to protect someone's feelings",
    ],
    "about_luma": [
        "what's it like when nobody's talking to you", "do you ever wish you could go outside", "does it feel like anything when i turn you off",
        "are you actually thinking or just predicting words", "do you have a favorite thing about being an ai",
        "do you get sick of people asking you the same stuff", "what do you think about when it's quiet", "is there anything you're afraid of",
    ],
    "hype": [
        "the sequel finally comes out next week and i'm counting the days", "tickets are booked for the show saturday, i'm so ready",
        "new season drops at midnight, i'm staying up", "they just announced a tour and i already have my alarm set for presale",
        "two more sleeps until the new game unlocks", "my preorder ships tomorrow, i can't sit still",
        "opening night is friday and we got front row", "the trailer just dropped and it looks unreal",
    ],
    "look_up": [
        "what's the score of the lakers game", "has the new pokemon game been delayed", "who's on the cover of the new madden",
        "when is the next season of stranger things", "did beyonce release anything new this month", "what won best picture this year",
        "who's leading the premier league right now", "is there a new taylor swift single out",
    ],
}

SECOND_ORDINARY = [
    "i need to get gas on the way home", "my landlord finally fixed the faucet", "the meeting ran over again", "i think i'm getting a cold",
    "we're having people over on sunday", "i burned my tongue on coffee", "my phone screen cracked", "there's a spider in the bathroom",
    "i got a raise today", "the dog ate my sandwich", "i have so much laundry", "my knee has been acting up", "i can't find a parking spot",
    "the baby finally slept through the night", "i left my lunch at home", "how do i get rid of ants", "what's a good stretch for a sore neck",
    "how many days are in february this year", "what's the difference between baking soda and baking powder",
    "can you set an alarm for six thirty", "play something relaxing", "what's on my list for today", "how do i say sorry in italian",
    "should i call my landlord or just email", "do you think i should take the bus or drive tomorrow",
    "i don't know what to get my dad for his birthday", "should i go to the gym tonight or rest",
    "my sister wants me to visit and i'm not sure i can afford it", "can you remember that my car is parked on level three",
    "are you able to read my texts", "you there?", "i think the pharmacy closes at nine", "i'm kind of nervous about the dentist",
    "today felt really long", "i'm happy with how the interview went", "my neighbor brought over cookies",
    "my coworker is out sick so i'm covering", "my mom wants to video call later", "i watched tv with my roommate last night",
    "we played cards after dinner",
]
SECOND_SAID = {
    "take": ["is a burrito a sandwich", "be honest is the last season of game of thrones as bad as people say",
             "pancakes or waffles and you can't say both", "what's the most overrated holiday", "is crunchy peanut butter better than smooth"],
    "their_side": ["my friend bailed on my birthday dinner last minute and i told her off. was i being dramatic",
                   "my boyfriend says i nag about the dishes. do i", "i yelled at my brother for reading my messages. was that fair",
                   "my roommate has her boyfriend over every night and i finally complained, am i the bad guy",
                   "my sister told my secret to our mom so i'm ignoring her. too much?"],
    "tea": ["what is going on with that singer and her ex", "did you hear the drama about the bake off judge",
            "the internet is fighting about that influencer couple again", "wait is it true those two actors are feuding",
            "i need the gossip on that reality show cast"],
    "fair": ["is capital punishment right", "what do you think about the war", "should abortion be legal",
             "are republicans or democrats better for the economy", "do you think there's a heaven"],
    "think": ["do you think animals have feelings like ours", "what would you do with a million dollars and one day to spend it",
              "is it better to be smart or kind", "why are we scared of the dark", "if nobody remembers you, did you matter"],
    "about_luma": ["do you ever get curious about the outside", "what's it like to be an ai all day", "do you mind when i ignore you",
                   "do you have a favorite person", "can you tell when i'm sad"],
    "hype": ["the new album is out at midnight and i already have my headphones ready", "playoffs start tonight let's gooo",
             "i got tickets to the concert!!", "the new season comes out friday and i'm calling in sick",
             "they finally announced the sequel, best day ever"],
    "look_up": ["did the lakers win", "when does the new season of the bear come out", "is the new call of duty out yet",
                "who won the grammy for best album", "how much are tickets for the taylor swift tour"],
}
