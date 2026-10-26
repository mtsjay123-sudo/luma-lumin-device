"""Every way someone might ask Luma for something.

People don't talk in commands. They say "yo can u like remind me abt the dentist tmrw",
"take me 2 my goals", "wats on my cal", they get cut off, they misspell, and speech-to-text
hears "Luna" for "Luma". This file writes all of that out: for every thing Luma can do,
the ways it gets asked (templates), the words that go in them (slots), and the things
people wrap around them (fillers, slang, typos, asides). Multiplied out, it's billions of
distinct messages; a sample of them trains the small understanding model that ships with
Luma (see understanding.py and scripts/train_understanding.py).

Nothing here runs when Luma answers someone. It only makes training and test data.
"""
from __future__ import annotations

import math
import random
import re

# ---------------------------------------------------------------------------
# What fills the blanks
# ---------------------------------------------------------------------------
SLOTS = {
    "task": ["call mom", "call my mom", "call the dentist", "pick up the kids", "take my meds", "take out the trash", "pay rent", "pay the electric bill",
             "grab milk", "buy eggs", "water the plants", "feed the dog", "walk the dog", "send the invoice", "email sam back", "text jay back",
             "book a haircut", "renew my license", "cancel netflix", "go to the gym", "stretch", "drink water", "start dinner", "move the car",
             "submit the report", "check the oven", "charge my phone", "call grandma", "pick up my prescription", "finish the slides",
             "get gas", "do laundry", "clean my room", "study for the exam", "send my mom flowers", "follow up with the landlord",
             "call the insurance company", "return the package", "pick up dry cleaning", "make a dentist appointment", "pray", "meditate",
             "leave for the airport", "join the zoom call", "check on dad", "order more coffee", "write my essay", "buy a birthday gift for sarah"],
    "when": ["tomorrow", "tomorrow morning", "tonight", "at 5", "at 5pm", "at 7:30", "in 20 minutes", "in an hour", "in 2 hours", "later", "this afternoon",
             "on friday", "next monday", "at noon", "before i leave", "in 10 min", "at 9am", "sunday morning", "after work", "in a bit", "at 6 tonight",
             "tmrw at 8", "first thing in the morning", "in 5 mins", "at 3", "this evening", "next week", "on the 15th"],
    "person": ["mom", "my mom", "dad", "sam", "jay", "sarah", "my boss", "alex", "my sister", "my brother", "grandma", "chris", "taylor", "jordan", "my boyfriend",
               "my girlfriend", "my wife", "my husband", "the landlord", "maria", "mike", "ashley", "kevin", "my manager", "the team", "dr smith", "bri", "tony"],
    "msg": ["im on my way", "running 10 min late", "happy birthday", "call me when you can", "can we move it to friday", "thanks for today",
            "dinner at 7?", "i love you", "did you get my email", "the meeting got moved", "pick up milk on the way home", "im outside",
            "lets do lunch tomorrow", "good luck today", "i'll be there in 5", "can you send me the file", "miss you", "sounds good"],
    "topic": ["ai", "the stock market", "tesla", "bitcoin", "climate change", "the lakers", "taylor swift", "the election", "space", "nvidia", "the fed",
              "real estate", "mental health", "startups", "the nba playoffs", "apple", "electric cars", "the world cup", "black holes", "the economy",
              "productivity", "dogs", "coffee", "the roman empire", "marketing", "our q3 results", "my startup", "healthy eating", "japan", "crypto",
              "quantum computing", "the new iphone", "remote work", "personal finance", "fashion week", "hip hop", "the oscars", "nutrition"],
    "product": ["airpods", "airpods pro", "a ps5", "a nintendo switch", "an iphone 17", "a standing desk", "running shoes", "a air fryer", "a coffee maker",
                "a 65 inch tv", "a macbook air", "noise cancelling headphones", "a gaming chair", "a robot vacuum", "a dyson hair dryer", "a yoga mat",
                "protein powder", "a kindle", "a blender", "a car seat", "printer ink", "jordans", "a ring light", "an ipad", "a monitor"],
    "music": ["drake", "some lofi", "taylor swift", "something chill", "jazz", "kendrick", "my workout playlist", "sza", "beyonce", "old school rnb",
              "some country", "the weeknd", "bad bunny", "classical music", "rain sounds", "some gospel", "90s hip hop", "afrobeats", "frank ocean", "travis scott"],
    "site": ["youtube", "netflix", "gmail", "amazon", "instagram", "twitter", "reddit", "spotify", "google", "chatgpt", "linkedin", "tiktok", "hulu", "espn", "facebook"],
    "thing": ["keys", "car keys", "wallet", "phone", "glasses", "passport", "airpods", "charger", "headphones", "badge", "laptop", "purse", "sunglasses", "remote", "ring"],
    "place": ["on the counter", "in the car", "in my jacket", "by the door", "in the top drawer", "on the nightstand", "in my bag", "under the couch",
              "at work", "on my desk", "in the kitchen", "by the sink", "in the garage", "in my backpack"],
    "dur": ["5 minutes", "10 minutes", "20 min", "an hour", "30 seconds", "45 minutes", "2 hours", "15 mins", "a minute", "90 seconds", "25 minutes", "3 minutes"],
    "name": ["nova", "jarvis", "sky", "max", "echo", "ivy", "atlas", "luna", "kai", "zoe", "friday", "orion"],
    "fact": ["my wifi network is bluehouse", "i'm allergic to peanuts", "my favorite color is green", "my boyfriend's birthday is september 17",
             "i park on level 3", "my gate code is 4471", "mom's flight lands at 6", "i hate cilantro", "my shoe size is 10", "my sister's name is maya",
             "i take my coffee black", "the dentist is on tuesday", "i'm vegetarian", "my anniversary is june 2", "i work out at 6am"],
    "app": ["spending tracker", "habit tracker", "packing list", "grocery checklist", "workout tracker", "countdown to christmas", "countdown to my birthday",
            "spanish flashcards", "study flashcards", "to do list", "budget tracker", "water tracker", "reading list", "chore chart", "mood tracker"],
    "doc": ["resume", "cover letter", "business plan", "lesson plan", "trip itinerary", "meal plan", "study guide", "one pager", "report", "essay outline",
            "wedding speech", "pitch", "proposal", "newsletter", "press release"],
    "want": ["a drink", "a nap", "a vacation", "a snack", "coffee", "a hug", "a new phone", "a haircut", "a raise", "sleep", "food", "a break from work",
             "a day off", "some fries", "a beach day", "new shoes", "a massage", "therapy lol", "a girlfriend", "a boyfriend", "money", "some boba"],
    "question": ["how tall shaq is", "when target closes", "who won the game last night", "the best pizza near me", "how to get a passport", "what time the mall opens",
                 "how much a tesla costs", "the population of canada", "when the next iphone comes out", "how old beyonce is", "the best laptop for school",
                 "flights to tokyo in march", "if the dmv is open saturday", "how long to boil an egg", "what the score is", "who sings this song"],
    "adj": ["sucked", "was the worst", "was so long", "was amazing", "was a lot", "was weird", "went great", "was exhausting", "was fine i guess", "was chaotic"],
    "dish": ["cold brew", "pancakes", "lasagna", "fried rice", "guacamole", "banana bread", "a margarita", "sourdough", "chicken alfredo", "an omelette", "boba", "ramen"],
    "garment": ["coat", "jacket", "umbrella", "sweater", "hoodie", "raincoat", "sunscreen", "scarf"],
    "clock": ["5", "noon", "6pm", "3", "time to go", "8:30", "midnight", "lunchtime", "7"],
    "ask2": ["she's coming", "he wants food", "they're still on for tonight", "we're good for friday", "she got home ok", "he needs a ride"],
    "life": ["just got home", "just woke up", "heading to work", "at the gym", "omw home", "just landed", "i'm home", "back from the store", "leaving now",
             "just got out of class", "finally off work", "on the train", "in bed", "about to sleep", "making dinner", "stuck in traffic", "at my moms"],
    "every": ["every morning", "every day", "every night", "every week", "every monday", "each morning", "daily", "every hour", "every evening"],
    "watch": ["check my email", "check the news for ai", "look for cheap flights to miami", "tell me when airpods drop under 150", "check bitcoin",
              "watch for new apartments under 2000", "summarize my inbox", "check the weather", "look for jobs in design", "check on my package"],
}

# ---------------------------------------------------------------------------
# Everything Luma can do, and how people ask for it
# label: how Luma offers it back ("Did you mean ...?")
# say:   the plain command Luma runs when they pick it
# ask:   for things that need details, the one question Luma asks
# prefix: what their answer completes ("remind me to " + "call mom at 5")
# walk:  a step-by-step walkthrough Luma can give instead
# ---------------------------------------------------------------------------
INTENTS = {
    # Pages, all reachable from the chat
    "open_feed": {"label": "Open your feed", "say": "open my feed", "t": [
        "open my feed", "show me my feed", "go to the feed", "take me to my feed", "pull up the feed", "feed", "my feed", "whats in my feed",
        "go to feed page", "feed tab", "check my feed", "anything new in my feed", "bring up the feed", "open feed real quick", "lemme see the feed",
        "switch to feed", "the feed page", "show feed", "what did you find for me", "anything you found for me today", "show me what you found"]},
    "open_news": {"label": "Open the news page", "say": "open news", "t": [
        "open the news page", "go to news", "news tab", "take me to the news page", "pull up the news tab", "open news", "switch to news",
        "show me the news page", "news page", "bring up news", "go to the headlines page", "the news section"]},
    "open_ideas": {"label": "See some ideas", "say": "open ideas", "t": [
        "open ideas", "show me some ideas", "ideas", "give me ideas", "what could you do for me", "ideas page", "go to ideas", "any ideas for me",
        "what should i have you do", "suggest something", "inspire me", "what can you take off my plate", "show me ideas", "got any ideas",
        "what should we do today", "im bored give me something to do"]},
    "open_goals": {"label": "Open your goals", "say": "open my goals", "t": [
        "open my goals", "goals", "show my goals", "go to goals", "take me to my goals", "my goals page", "what goals do i have", "pull up goals",
        "goals tab", "what are you keeping an eye on", "what jobs are running", "what are you doing on your own", "standing jobs", "my routines",
        "show me the goals", "lemme see my goals"]},
    "open_identity": {"label": "See what I know about you", "say": "open identity", "t": [
        "open identity", "show my memories", "my memories", "go to memories", "identity page", "show me your soul",
        "what's in your memory", "open memory", "take me to my memories", "pull up what you saved", "memory page", "manage my memories",
        "edit my memories", "show me what you saved about me", "your personality settings", "change your personality"]},
    "open_library": {"label": "Open your library", "say": "open my library", "t": [
        "open my library", "library", "show me my files", "my files", "where are my decks", "show me what you made", "go to library",
        "pull up my documents", "show my docs", "where's the deck you made", "open files", "my stuff you made", "library tab", "show my apps you made",
        "where did you save it", "where is the pdf", "find the doc you made"]},
    "open_browser": {"label": "Open my browser", "say": "open the browser", "t": [
        "open the browser", "open your browser", "browser", "go to the browser", "show me your browser", "browser tab", "pull up the browser",
        "let me use the browser", "open a browser window", "i want to browse", "take me to the browser"]},
    "open_connectors": {"label": "Open connectors", "say": "open connectors", "t": [
        "open connectors", "connectors", "apps", "my apps", "show my connections", "what's connected", "go to connectors", "connections page",
        "integrations", "show integrations", "what apps are hooked up", "connected apps", "mcp", "manage connections", "plug ins", "plugins"]},
    "open_settings": {"label": "Open settings", "say": "open settings", "t": [
        "open settings", "settings", "go to settings", "preferences", "open preferences", "take me to settings", "settings page", "change my settings",
        "where are the settings", "pull up settings", "account settings", "my account", "sign out", "log out", "change my number"]},
    "open_rules": {"label": "Open your rules", "say": "open rules", "t": [
        "open rules", "rules", "show my rules", "what are you allowed to do", "permissions", "what do you need my ok for", "approval settings",
        "change what you can do", "what can you do without asking", "go to rules", "your rules", "what do you ask me first about"]},

    # Quick looks
    "list_tasks": {"label": "Show your reminders", "say": "my tasks", "t": [
        "what do i have to get done", "what do i need to get done today", "what's on my to do list today", "what do i still need to do", "anything i forgot to do",
        "my tasks", "what are my reminders", "show my reminders", "what do i have to do", "whats on my list", "my to do list", "reminders",
        "what did i ask you to remind me", "any reminders", "what's on my plate", "what do i need to do today", "list my tasks", "show my to dos",
        "do i have anything to do", "what's left on my list"]},
    "list_timers": {"label": "Show your timers", "say": "timers", "t": [
        "timers", "my timers", "how much time is left", "how long left on the timer", "is the timer still going", "show timers", "timer status",
        "how much longer on the timer", "whats left on my timer"]},
    "briefing": {"label": "Run through your day", "say": "my briefing", "t": [
        "what do i have going on today", "how's my day shaping up", "what am i doing today",
        "my briefing", "brief me", "what's my day look like", "how's my day looking", "run me through today", "what do i have today", "daily briefing",
        "morning briefing", "give me the rundown", "whats the plan today", "plan my day", "what's going on today", "catch me up on my day",
        "gimme the rundown for today", "what's today look like"]},
    "news": {"label": "Catch you up on the news", "say": "what's the news", "t": [
        "what's the news", "whats happening in the world", "catch me up", "any news", "headlines", "top headlines", "what's going on in the world",
        "what did i miss", "news", "give me the news", "what's new today", "latest news", "anything big happen today", "news update",
        "whats the latest", "tell me the news", "what's trending", "what's everyone talking about", "world news", "breaking news"]},
    "check_email": {"label": "Check your email", "say": "check my email", "t": [
        "check my email", "any new emails", "did i get any emails", "what's in my inbox", "read my email", "check my inbox", "go through my email",
        "anything important in my email", "emails", "my inbox", "did anyone email me", "do i have mail", "check gmail", "summarize my inbox",
        "any important mail", "who emailed me", "clean up my inbox", "triage my inbox", "unread emails", "did sam email me back"]},
    "calendar": {"label": "Check your calendar", "say": "what's on my calendar today", "t": [
        "what's on my calendar", "check my calendar", "my schedule", "what's my schedule today", "am i free tomorrow", "do i have meetings today",
        "when is my next meeting", "calendar", "what's next on my calendar", "anything on my calendar this week", "am i busy at 3", "my cal",
        "what time is my meeting", "whats coming up", "next appointment", "do i have anything tonight", "when's my dentist appointment"]},
    "weather": {"label": "Check the weather", "say": "what's the weather today", "t": [
        "do i need a {garment} today", "do i need a {garment}", "should i bring a {garment}", "is it {garment} weather", "do i need a {garment} tomorrow",
        "what's the weather", "weather", "is it gonna rain", "do i need an umbrella", "how hot is it", "weather today", "weather tomorrow",
        "is it cold outside", "what's the temperature", "will it snow", "forecast", "how's the weather looking", "should i wear a jacket",
        "is it nice out", "weather this weekend"]},
    "recall_me": {"label": "Tell you what I remember about you", "say": "what do you remember about me", "t": [
        "what do you remember about me", "what do you know about me", "what have you learned about me", "tell me about myself", "what do you know",
        "what did i tell you about me", "do you remember me", "what have i told you", "what's in your memory about me", "what do you think of me"]},
    "recap": {"label": "Go over what we talked about", "say": "what did we talk about", "t": [
        "what did we talk about", "what did i say earlier", "what were we talking about", "recap our chat", "what did i tell you yesterday",
        "remind me what we said", "where were we", "what was i saying", "summarize our conversation", "what did we say last time"]},
    "abilities": {"label": "Show you what I can do", "say": "what can you do", "t": [
        "what can you do", "what are you", "help", "what do you do", "how does this work", "what are your features", "what can i ask you",
        "how do i use you", "show me what you got", "what are you capable of", "are you smart", "what can luma do", "tell me what you can do",
        "what's this app", "i'm new here", "where do i start", "what can i do here", "how do i use this app", "can you do stuff", "what is luma"]},
    "grill": {"label": "Get to know you with a few questions", "say": "interview me", "t": [
        "interview me", "grill me", "get to know me", "ask me questions", "learn about me", "ask me stuff", "quiz me about myself",
        "get to know me better", "ask me a bunch of questions", "learn who i am", "figure me out", "let's do the get to know you thing"]},
    "hush": {"label": "Go quiet for a bit", "say": "hush", "t": [
        "hush", "be quiet", "shh", "shut up", "stop talking", "quiet", "not now", "give me a minute", "leave me alone for a bit", "stop bothering me",
        "no more notifications", "dont talk to me", "chill for a bit", "silence", "stfu", "quiet mode", "do not disturb", "go away for a bit"]},
    "mute": {"label": "Turn the mic off", "say": "mute", "t": [
        "mute", "mute yourself", "turn off the mic", "stop listening", "mic off", "privacy mode", "don't listen", "turn off listening", "privacy on",
        "are you listening to me", "stop recording"]},
    "forget_last": {"label": "Forget what you just said", "say": "forget that", "t": [
        "forget that", "forget what i just said", "don't remember that", "delete that", "scratch that memory", "erase that", "unsave that",
        "don't save that", "remove that memory", "never mind don't remember that", "forget i said that"]},
    "style_casual": {"label": "Talk more casually", "say": "talk more casual", "t": [
        "talk more casual", "be more chill", "talk like a friend", "loosen up", "talk normal", "you sound like a robot", "be less formal",
        "talk like me", "use slang", "be more relaxed", "stop being so formal", "talk regular", "just talk normal to me", "be real with me"]},
    "style_short": {"label": "Keep my answers short", "say": "keep it short", "t": [
        "keep it short", "shorter answers", "too long", "tldr", "less words", "be brief", "get to the point", "stop rambling", "just the answer",
        "short answers please", "you talk too much", "too much text", "make it quick", "summarize it", "cut it down"]},
    "connect_email": {"label": "Connect your email", "say": "connect my email", "t": [
        "connect my email", "connect gmail", "hook up my email", "add my email", "link my gmail", "set up email", "connect outlook", "add my icloud mail",
        "sign in to my email", "how do i connect my email", "can you get into my email", "link my email account", "set up my inbox"]},
    "connect_calendar": {"label": "Connect your calendar", "say": "connect my calendar", "t": [
        "connect my calendar", "hook up my calendar", "add my calendar", "link google calendar", "set up my calendar", "connect ical",
        "how do i connect my calendar", "sync my calendar", "can you see my calendar"]},
    "connect_chrome": {"label": "Connect Chrome", "walk": "chrome", "t": [
        "connect chrome", "install the chrome extension", "set up chrome", "how do i get you in chrome", "chrome extension", "link chrome",
        "use my chrome", "can you control chrome", "add luma to chrome", "work in my browser", "get the extension", "hook up chrome"]},
    "pair_device": {"label": "Pair with your Luma device", "walk": "device", "t": [
        "pair my luma device", "connect to my luma", "connect the device", "set up my luma device", "pair the device", "link my luma",
        "how do i connect the hardware", "connect to the luma box", "my luma device isn't connecting", "find my luma", "pair with luma on wifi",
        "connect wirelessly", "set up luma home", "use the device without my laptop", "hook up the luma device"]},
    "cloud_brain": {"label": "Turn on the smarter brain", "walk": "brain", "t": [
        "use the smarter brain", "turn on the cloud brain", "make you smarter", "use claude", "get the bigger brain", "upgrade your brain",
        "be smarter", "you're too dumb", "add my api key", "use the cloud", "turn on super intelligence", "switch to the big model", "faster brain",
        "can you think harder", "use the best model", "smarter mode"]},
    "luma_plus": {"label": "Get Luma Plus", "walk": "plus", "t": [
        "get luma plus", "upgrade", "how much is luma plus", "buy more memory", "more storage", "my memory is full", "upgrade my plan",
        "what's luma plus", "pricing", "subscribe", "how much does it cost", "go premium", "unlimited memory"]},
    "talk": {"label": "Talk out loud", "action": "talk", "t": [
        "let's talk", "talk to me", "voice mode", "can we talk out loud", "turn on voice", "i want to talk", "start talking", "talk mode",
        "use your voice", "speak to me", "hands free", "listen to me", "can you hear me", "start voice"]},
    "photo": {"label": "Look at a photo", "action": "photo", "t": [
        "look at this photo", "what's in this picture", "can you see images", "read this screenshot", "i want to show you a picture", "check out this pic",
        "what does this say", "analyze this image", "describe this photo", "can i send you a photo", "look at this", "scan this", "read this receipt"]},
    "teach": {"label": "Teach me a task", "walk": "teach", "t": [
        "teach you a task", "let me show you how to do something", "learn how i do this", "watch me do it", "record a task", "i'll show you",
        "can you learn to do this", "teach mode", "how do i teach you", "remember how to do this", "copy what i do"]},

    # Things that need a detail or two
    "remind": {"label": "Set a reminder", "ask": "What should I remind you about, and when?", "prefix": "remind me to ", "t": [
        "ping me when its {clock}", "tell me when its {clock}", "let me know when its {clock}", "when its {clock} remind me to {task}", "at {clock} tell me to {task}", "remind me at {clock}", "buzz me at {clock}", "give me a heads up at {clock}",
        "remind me to {task} {when}", "remind me {when} to {task}", "set a reminder to {task} {when}", "dont let me forget to {task}",
        "make sure i {task} {when}", "ping me {when} to {task}", "nudge me to {task} {when}", "i need to {task} {when} remind me", "reminder {task} {when}",
        "remind me about {task}", "can you remind me to {task}", "set a reminder for {when}", "remind me {when}", "add {task} to my reminders",
        "put {task} on my to do list", "add a task {task}", "i gotta {task} {when}", "don't let me forget {task}", "remember to tell me to {task} {when}",
        "alert me {when} to {task}", "hit me up {when} about {task}", "yo remind me {task}", "{task} {when} remind me", "set an alarm for {when}",
        "finna {task} remind me {when}", "tryna {task} {when} so remind me", "imma {task} {when} dont let me forget", "{task} remind me {when}",
        "i gotta {task} remind me {when}", "boutta {task} remind me in a bit", "lowkey need to {task} {when} remind me",
        "wake me up {when}", "remind me", "set a reminder"]},
    "timer": {"label": "Start a timer", "ask": "How long should the timer be?", "prefix": "set a timer for ", "t": [
        "set a timer for {dur}", "timer {dur}", "start a {dur} timer", "{dur} timer", "count down {dur}", "set timer {dur}", "time me for {dur}",
        "start a timer", "set a timer", "put a timer on for {dur}", "i need a timer", "pasta timer {dur}", "can you time {dur}"]},
    "remember": {"label": "Remember something", "ask": "What should I remember?", "prefix": "remember ", "t": [
        "remember {fact}", "save this {fact}", "note that {fact}", "keep in mind {fact}", "dont forget {fact}", "write down {fact}", "make a note {fact}",
        "fyi {fact}", "remember this", "save that", "make a note", "jot this down", "remember that for me", "store this {fact}", "for the record {fact}",
        "i left my {thing} {place}", "my {thing} are {place}", "i put my {thing} {place}"]},
    "where_is": {"label": "Find where you left something", "ask": "What are you looking for?", "prefix": "where are my ", "t": [
        "where are my {thing}", "where did i leave my {thing}", "where'd i put my {thing}", "have you seen my {thing}", "i cant find my {thing}",
        "where is my {thing}", "do you know where my {thing} is", "i lost my {thing}", "help me find my {thing}", "where did i put it",
        "where are they", "where'd i leave em"]},
    "text": {"label": "Text someone", "ask": "Who should I text, and what should it say?", "prefix": "text ", "t": [
        "hit up {person} and ask if {ask2}", "ask {person} if {ask2}", "text {person} and ask if {ask2}", "check if {person} {ask2}", "see if {person} wants to {task}",
        "text {person} {msg}", "text {person} saying {msg}", "send {person} a text {msg}", "message {person} {msg}", "tell {person} {msg}",
        "let {person} know {msg}", "shoot {person} a text", "hit up {person}", "text {person}", "send a message to {person}", "dm {person}",
        "can you text {person} that {msg}", "send a text", "msg {person} {msg}", "reply to {person}", "text back {person}", "imessage {person} {msg}",
        "text {person} im pullin up", "tell {person} im outside", "hit {person} and say {msg}", "lmk text {person} {msg}", "text {person} wya"]},
    "email": {"label": "Write an email", "ask": "Who's it to, and what's it about?", "prefix": "email ", "t": [
        "email {person} about {topic}", "write an email to {person}", "send {person} an email saying {msg}", "draft an email to {person}",
        "write {person} an email about {topic}", "email {person} {msg}", "reply to {person}'s email", "compose an email", "write an email",
        "help me write an email to {person}", "schedule an email to {person} {when}", "send an email {when} to {person}", "email my boss",
        "draft a reply to the email from {person}", "answer {person}'s email"]},
    "search": {"label": "Look it up online", "ask": "What should I look up?", "prefix": "look up ", "t": [
        "google {question}", "look up {question}", "search {question}", "find out {question}", "can you check {question}", "figure out {question}",
        "look up {topic}", "search {topic}", "google {topic}", "search the web for {topic}", "find info on {topic}", "research {topic}",
        "look into {topic}", "find out about {topic}", "can you look up {topic}", "dig into {topic}", "search for {topic}", "look it up",
        "search that", "google it", "deep dive on {topic}", "do some research on {topic}", "what does the internet say about {topic}",
        "find me reviews of {product}", "compare {product} and {product}"]},
    "shop": {"label": "Find the best price", "ask": "What are you shopping for?", "prefix": "find the cheapest ", "t": [
        "find the cheapest {product}", "best price on {product}", "where can i get {product} cheap", "find me {product}", "shop for {product}",
        "price check {product}", "how much is {product}", "find a deal on {product}", "i need {product}", "is {product} on sale", "buy {product}",
        "add {product} to my cart", "order {product}", "cheapest {product}", "compare prices on {product}", "find {product} under 100",
        "get me {product}", "i wanna buy {product}", "shopping for {product}"]},
    "music": {"label": "Play music", "ask": "What do you want to hear?", "prefix": "play ", "t": [
        "play {music}", "put on {music}", "throw on {music}", "bump {music}", "queue up {music}", "i wanna hear {music}", "play me something",
        "play music", "music please", "put some music on", "spin {music}", "play something by {music}", "can you play {music}", "turn on {music}",
        "play a song", "i need some music", "vibes", "put on some vibes"]},
    "open_site": {"label": "Open a website", "ask": "Which site?", "prefix": "open ", "t": [
        "open {site}", "go to {site}", "pull up {site}", "take me to {site}", "launch {site}", "open {site} in chrome", "bring up {site}",
        "load {site}", "get me on {site}", "{site} please", "open {site}.com", "navigate to {site}"]},
    "deck": {"label": "Make a deck", "ask": "What's the deck about?", "prefix": "make a deck about ", "t": [
        "make a deck about {topic}", "build me a pitch deck", "create a presentation on {topic}", "slides on {topic}", "make slides about {topic}",
        "i need a deck", "put together a presentation", "make a powerpoint about {topic}", "keynote on {topic}", "make me a slideshow about {topic}",
        "pitch deck for {topic}", "make a presentation", "deck for my meeting", "can you make slides"]},
    "document": {"label": "Write a document", "ask": "What should it be about?", "prefix": "write a document about ", "t": [
        "write a {doc}", "make me a {doc}", "write a document about {topic}", "make a pdf about {topic}", "draft a {doc} for {topic}", "type up a {doc}",
        "create a word doc", "write up a {doc} on {topic}", "i need a {doc}", "make a pdf", "write a report on {topic}", "put together a {doc}",
        "can you write my {doc}", "make a doc", "turn this into a pdf"]},
    "make_app": {"label": "Make a little app", "ask": "A tracker, a checklist, flashcards or a countdown?", "prefix": "make me a ", "t": [
        "make me a {app}", "build a {app}", "create a {app}", "i need a {app}", "make an app", "build me an app", "make a tracker",
        "can you make a {app}", "set up a {app}", "make flashcards for {topic}", "make a checklist", "countdown to my birthday",
        "track my spending", "help me track my habits", "make a quiz on {topic}"]},
    "podcast": {"label": "Make you a podcast", "ask": "What should the episode be about?", "prefix": "make me a podcast about ", "t": [
        "make me a podcast about {topic}", "podcast on {topic}", "make an episode about {topic}", "turn the news into a podcast", "audio briefing",
        "read me the news as a podcast", "make a podcast", "i want a podcast about {topic}", "record an episode on {topic}", "make me something to listen to",
        "news podcast", "podcast of my day"]},
    "goal": {"label": "Keep an eye on something for you", "ask": "What should I keep an eye on, and how often?", "prefix": "every morning ", "t": [
        "{every} {watch}", "{watch} {every}", "keep an eye on {topic}", "watch {topic} for me", "let me know when {product} goes on sale",
        "track {topic} for me", "set up a goal", "make a goal", "new goal", "monitor {topic}", "alert me if {topic} changes", "keep tabs on {topic}",
        "tell me when there's news about {topic}", "follow {topic} for me", "start a routine", "every day at 8 {watch}"]},
    "rename": {"label": "Give me a new name", "ask": "What do you want to call me?", "prefix": "your name is ", "t": [
        "i'm gonna call you {name}", "your name is {name}", "call yourself {name}", "can i rename you", "change your name to {name}", "i'll call you {name}",
        "from now on you're {name}", "your new name is {name}", "rename yourself", "can i give you a name", "be called {name}", "change your name"]},
    "news_topic": {"label": "Get news on something", "ask": "News about what?", "prefix": "news about ", "t": [
        "news about {topic}", "what's the latest on {topic}", "any news on {topic}", "what's happening with {topic}", "{topic} news", "update on {topic}",
        "catch me up on {topic}", "headlines about {topic}", "what's new with {topic}", "anything new on {topic}", "whats going on with {topic}"]},

    # Conversation: no action, just talk (the brain answers these)
    "chat": {"label": None, "t": [
        "{life}", "{life} lol", "{life} finally", "ok {life}", "{life} whats up", "{life} and im tired",
        "how do you make {dish}", "how do i make {dish}", "how to make {dish}", "recipe for {dish}", "whats the best way to make {dish}", "how long do i cook {dish}", "how do you do that", "how do you know that", "how do you feel", "how do you work", "how do you even do that", "is it hard to make {dish}", "teach me to cook {dish}", "can you teach me {topic}", "i want to learn how to make {dish}", "show me how to make {dish}",
        "{fact}", "{fact} lol", "just so you know {fact}", "i just {task}", "i finally {task}", "i already {task}", "ok so {fact}",
        "today {adj}", "ugh today {adj}", "my day {adj}", "this week {adj}", "worst day ever", "best day ever", "help me think of {doc} ideas", "gift ideas for {person}", "help me pick a gift for {person}", "what should i get {person} for their birthday", "help me think of something to do tonight", "{person} keeps texting me", "{person} never texts me back", "should i text {person}", "i forgot my {thing} at home lol", "i hate reminders", "the news is so depressing", "my calendar is insane this week", "email is the worst", "i love this song", "music is life", "i lost my {thing} last week but found it", "my {thing} broke", "what do you think i should do about {person}", "is it rude to not reply to {person}", "i can never find my {thing} lol", "tell me about yourself", "who are you", "what are you thinking about", "do you remember when we met", "you remember everything huh", "what does {topic} mean", "teach me about {topic}", "quiz me on {topic}", "i want to learn {topic}", "how does {topic} work", "today's been {adj}",
        "how are you", "how's it going", "what's up", "good morning", "good night", "hey", "hi", "hello", "yo", "thanks", "thank you", "ty", "lol", "lmao",
        "haha", "that's funny", "you're funny", "you're the best", "i love you", "i hate you", "ok", "okay", "cool", "nice", "bet", "word", "facts",
        "tell me a joke", "tell me a story", "why is the sky blue", "how tall is mount everest", "what's the meaning of life", "are you alive",
        "do you have feelings", "are you real", "who made you", "what do you think about {topic}", "tell me about {topic}", "explain {topic} to me",
        "i'm so tired", "today was rough", "i'm stressed", "i'm bored", "i'm sad", "i'm happy", "i got the job", "i'm nervous about tomorrow",
        "my day was long", "ugh mondays", "i can't sleep", "should i {task}", "help me decide between {music} and {music}", "what should i eat",
        "what should i get my mom for her birthday", "my boyfriend's birthday is september 17 what should i get him", "give me advice", "i need advice",
        "how do i cook pasta", "how do i make pancakes", "write a poem about {topic}", "help me write a caption", "what's 15 percent of 80",
        "translate hello to spanish", "what's the capital of japan", "who is the president", "how many ounces in a cup", "define serendipity",
        "what rhymes with orange", "can you keep a secret", "what's your favorite song", "do you like {music}", "what are you doing",
        "talk to me about anything", "i miss my ex", "should i text him back", "is it weird that i {task}", "rate my outfit", "tell me something cool",
        "fun fact", "motivate me", "i need a pep talk", "give me a compliment", "roast me", "what's 2 plus 2", "how old are you", "where are you from",
        "what's your name", "are you smarter than chatgpt", "what do you think of me", "i had a dream about {topic}", "let's play a game",
        "would you rather", "truth or dare", "how do i get better at {topic}", "is {topic} worth it", "why is {topic} a big deal", "summarize {topic}",
        "brainstorm names for my {doc}", "help me plan a date night", "what should i do this weekend", "give me a workout", "what's a good book",
        "how do i tie a tie", "how do i ask for a raise", "i'm proud of myself", "guess what", "you know what", "never mind", "nothing", "idk",
        "wyd", "hbu", "same", "true", "fr", "no cap", "on god", "say less", "deadass", "that's crazy", "wow", "omg", "bruh",
        "{slang}", "{slang} lol", "{slang} fr", "ngl {slang}", "thats {slang}", "lowkey {slang}", "{slang} no cap", "bro {slang}", "{slang} lmaooo",
        "ngl i need {want}", "i need {want}", "lowkey need {want}", "i could use {want}", "i want {want} so bad", "bro i need {want} fr",
        "wassup", "whats good", "nm hbu", "chillin", "wbu", "how u been", "its giving", "i'm dead", "im weak", "that ate", "mid", "slay",
        "this hits different", "who asked lol", "be fr", "you trippin", "ok bet", "say less fam", "nah fr", "aight", "word to my mother"]},
}

# What people wrap around a request
OPENERS = ["", "", "", "", "", "", "hey luma ", "luma ", "hey ", "yo ", "yo luma ", "ok ", "okay ", "um ", "uh ", "so ", "hey luna ", "luna ", "ayo ", "aye ",
           "alright ", "wait ", "actually ", "oh and ", "btw ", "quick question ", "real quick ", "listen ", "ok so ", "bro ", "hey girl ", "hey lumen ",
           "hmm ", "and ", "also ", "oh ", "ok luma ", "hey there ", "excuse me ", "sorry ", "ugh ", "lol ", "please ", "luma bottom drop ",
           "ngl ", "lowkey ", "fr ", "deadass ", "aight ", "sis ", "fam ", "bestie ", "on god ", "bruh ", "tbh ", "ayo luma ", "yo yo ", "aye luma "]
ASKERS = ["", "", "", "", "can you ", "could you ", "can u ", "would you ", "will you ", "please ", "pls ", "i need you to ", "i want you to ", "go ahead and ",
          "can you please ", "could you please ", "i need to ", "help me ", "lemme ", "i'd like you to ", "id like to ", "you think you could ", "mind if you ",
          "cn u ", "can ya ", "u think u can ", "i was wondering if you could ", "do me a favor and ", "i need u to "]
CLOSERS = ["", "", "", "", "", "", " please", " pls", " plz", " rn", " right now", " real quick", " for me", " lol", " lmao", " fr", " bro", " bruh", " thx",
           " thanks", " asap", " when you get a chance", "?", "!", "...", " luma", " ty", " please and thank you", " if you can", " ok", " k", " haha",
           " no rush", " fam", " thank u", " 🙏", " 😭", " right", " yeah", " for real", " pleaseee", " ??", " !!",
           " no cap", " ong", " frfr", " deadass", " tbh", " ngl", " sis", " bestie", " fr tho", " lowkey", " rn tho", " on god", " 💀"]
IMPERATIVE = re.compile(r"^(?:open|show|go|take|pull|switch|bring|check|read|look|search|google|find|play|put|throw|bump|queue|make|build|create|write|draft|"
                        r"send|text|message|tell|let|remind|set|start|add|track|watch|keep|monitor|connect|hook|link|install|pair|turn|use|get|give|plan|"
                        r"run|brief|summarize|interview|grill|ask|learn|teach|record|forget|delete|erase|mute|record|compose|reply|launch|load|navigate|"
                        r"spin|email|dm|shoot|hit|nudge|ping|alert|wake|time|count|research|dig|compare|order|buy|shop|price|type|turn|catch|upgrade|"
                        r"subscribe|clean|triage|scan|analyze|describe|copy|save|note|jot|store|switch|rename|change|call|be|talk|speak|loosen|stop|cut)\b")

# How people actually type
SLANG = [(r"\byou\b", "u"), (r"\byour\b", "ur"), (r"\byou're\b", "ur"), (r"\bplease\b", "pls"), (r"\btomorrow\b", "tmrw"), (r"\btomorrow\b", "tmr"),
         (r"\bto\b", "2"), (r"\bfor\b", "4"), (r"\bwhat\b", "wat"), (r"\bwhat's\b", "whats"), (r"\bwhat's\b", "wats"), (r"\bthe\b", "da"),
         (r"\bwith\b", "w/"), (r"\bbecause\b", "bc"), (r"\bminutes\b", "mins"), (r"\bmessage\b", "msg"), (r"\btext\b", "txt"), (r"\bpeople\b", "ppl"),
         (r"\bwant to\b", "wanna"), (r"\bgoing to\b", "gonna"), (r"\bgot to\b", "gotta"), (r"\blet me\b", "lemme"), (r"\bgive me\b", "gimme"),
         (r"\bdon't\b", "dont"), (r"\bcan't\b", "cant"), (r"\bi'm\b", "im"), (r"\bokay\b", "k"), (r"\bthanks\b", "thx"), (r"\bbirthday\b", "bday"),
         (r"\btonight\b", "tonite"), (r"\babout\b", "abt"), (r"\bsomething\b", "smth"), (r"\bcalendar\b", "cal"), (r"\binstagram\b", "insta"),
         (r"\bappointment\b", "appt"), (r"\breally\b", "rly"), (r"\bknow\b", "kno"), (r"\bare\b", "r"), (r"\bthat\b", "dat"), (r"\bthis\b", "dis"),
         (r"\bemail\b", "e-mail"), (r"\bemail\b", "emial"), (r"\bschedule\b", "sched"), (r"\bpicture\b", "pic"), (r"\bmom\b", "mum"), (r"\btonight\b", "2nite"),
         (r"\btoday\b", "2day"), (r"\bbefore\b", "b4"), (r"\bsee\b", "c"), (r"\bwhy\b", "y"), (r"\bok\b", "kk"), (r"\bhow\b", "hw"), (r"\bnews\b", "newz")]
# Speech-to-text mishearings
HEARD = [(r"\bluma\b", "luna"), (r"\bluma\b", "lumen"), (r"\bluma\b", "loom a"), (r"\bto\b", "two"), (r"\bfor\b", "four"), (r"\bremind\b", "rewind"),
         (r"\btext\b", "texts"), (r"\bemail\b", "e mail"), (r"\bdeck\b", "deg"), (r"\bplay\b", "plays"), (r"\bfeed\b", "feet"), (r"\bgoals\b", "goes"),
         (r"\btimer\b", "time her"), (r"\bpodcast\b", "pod cast"), (r"\bweather\b", "whether"), (r"\bwhere\b", "wear"), (r"\bnews\b", "noose")]
FILLERS = ["like", "um", "uh", "you know", "kinda", "just", "basically", "literally", "actually", "lowkey", "real quick", "ngl", "fr", "deadass", "tbh"]


def _slang_terms():
    """Everyday slang from Luma's lexicon (casual register only: no cussing, nothing aimed at people), for chat examples."""
    try:
        from luma.agent import slang
        by_term, _ = slang.lexicon()
        return sorted({e.term.lower() for e in by_term.values() if e.register == "c" and 2 <= len(e.term) <= 24})
    except Exception:
        return ["bet", "no cap", "fire", "mid", "bussin", "say less", "deadass", "lowkey", "slaps", "facts"]


SLOTS["slang"] = _slang_terms()


def _archive_talk():
    """The slang archive's own example sentences ("No wahala, we can fix it.", "Yinz coming to the game this weekend?"): real talk
    from dozens of communities, all of it conversation. Ones that read like a request to Luma ("Take the second exit at the rotary")
    are left out so they don't teach the wrong thing."""
    try:
        from luma.agent import slang_archive
    except Exception:
        return []
    out = []
    for line in slang_archive.EXAMPLES:
        low = line.lower().rstrip(".")
        if IMPERATIVE.match(low) or re.match(r"(?:where|let'?s|text|remind|call|play)\b", low) or "{" in low:
            continue
        out.append(low)
    return out


ARCHIVE_TALK = _archive_talk()
KEYBOARD = {c: n for c, n in zip("qwertyuiopasdfghjklzxcvbnm", ["wa", "qes", "wrd", "etf", "ryg", "tuh", "yij", "uok", "ipl", "o", "qsz", "awedxz", "serfcx", "drtgvc",
                                                                   "ftyhbv", "gyujnb", "huikmn", "jiolm", "kop", "asx", "zsdc", "xdfv", "cfgb", "vghn", "bhjm", "njk"])}


def _typo(word, rng):
    if len(word) < 4 or not word.isalpha():
        return word
    i = rng.randrange(1, len(word) - 1)
    kind = rng.random()
    if kind < 0.3:
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]  # swapped
    if kind < 0.55:
        return word[:i] + word[i + 1:]  # dropped
    if kind < 0.75:
        return word[:i] + word[i] + word[i:]  # doubled
    near = KEYBOARD.get(word[i])
    return word[:i] + rng.choice(near) + word[i + 1:] if near else word


def _fill(template, rng):
    return re.sub(r"\{(\w+)\}", lambda m: rng.choice(SLOTS[m.group(1)]), template)


def messy(text, rng, level=None):
    """The same request, the way a real person might type it or say it into a mic."""
    level = rng.random() if level is None else level
    out = text
    if level > 0.25:
        for pattern, swap in rng.sample(SLANG, k=min(len(SLANG), rng.randint(1, 6))):
            if rng.random() < 0.6:
                out = re.sub(pattern, swap, out, count=1)
    if level > 0.5 and rng.random() < 0.35:
        for pattern, swap in rng.sample(HEARD, k=2):
            out = re.sub(pattern, swap, out, count=1)
    if level > 0.4 and rng.random() < 0.3:
        words = out.split()
        if len(words) > 2:
            words.insert(rng.randrange(1, len(words)), rng.choice(FILLERS))
            out = " ".join(words)
    if level > 0.45:
        words = out.split()
        for _ in range(rng.randint(1, 2 if level > 0.8 else 1)):
            if words:
                j = rng.randrange(len(words))
                words[j] = _typo(words[j], rng)
        out = " ".join(words)
    if rng.random() < 0.15:
        out = out.replace("'", "")
    if rng.random() < 0.08:
        out = out.upper()
    elif rng.random() < 0.3:
        out = out[:1].upper() + out[1:]
    if rng.random() < 0.05:
        words = out.split()
        if len(words) > 2:
            k = rng.randrange(len(words))
            words.insert(k, words[k])  # "can can you"
            out = " ".join(words)
    return out


def say(intent, rng, level=None):
    """One way of asking for this."""
    if intent == "chat" and ARCHIVE_TALK and rng.random() < 0.25:
        core = rng.choice(ARCHIVE_TALK)
    else:
        core = _fill(rng.choice(INTENTS[intent]["t"]), rng)
    asker = rng.choice(ASKERS) if IMPERATIVE.match(core) and intent != "chat" else ""
    text = (rng.choice(OPENERS) + asker + core + rng.choice(CLOSERS)).strip()
    return messy(text, rng, level)


def generate(n, seed=0, weights=None):
    """n (message, intent) pairs. Chat gets extra weight: most of what people say isn't a command."""
    rng = random.Random(seed)
    names = list(INTENTS)
    w = [weights.get(k, 1.0) if weights else (6.0 if k == "chat" else 1.0) for k in names]
    for _ in range(n):
        intent = rng.choices(names, weights=w)[0]
        yield say(intent, rng), intent


def count():
    """How many distinct messages these combine into (before typos, which multiply it again)."""
    total = 0
    for name, spec in INTENTS.items():
        for template in spec["t"]:
            ways = 1
            for slot in re.findall(r"\{(\w+)\}", template):
                ways *= len(SLOTS[slot])
            askers = len(set(ASKERS)) if IMPERATIVE.match(template) and name != "chat" else 1
            total += ways * len(set(OPENERS)) * askers * len(set(CLOSERS))
    total += len(ARCHIVE_TALK) * len(set(OPENERS)) * len(set(CLOSERS))
    slang_variants = 2 ** 6  # each message can take any of several slang swaps
    return total, total * slang_variants


# ---------------------------------------------------------------------------
# Whole conversations: the moments that make it feel real
# ---------------------------------------------------------------------------
CUT_OFFS = ["remind me to", "can you text my", "hey luma can you", "email sam about the", "i need you to", "set a reminder for", "play some", "text mom that",
            "what's on my", "open my", "look up the", "make me a", "so basically i need", "tell jay that i", "remind me tomorrow to", "can you find the cheapest",
            "um so", "i was gonna say", "wait can you", "remember that my"]
FRUSTRATED = ["wtf", "that's not what i said", "no that's wrong", "you're not listening", "ugh", "are you serious", "bro what", "this isn't working",
              "that's not what i asked", "omg no", "useless", "come on", "i already told you", "NO", "stop", "you're so dumb", "for real?", "smh",
              "why would you do that", "i said remind me not text", "no!!", "nope wrong", "that's not it", "ffs", "you got it wrong again", "ugh never mind"]


def conversations(n, seed=0):
    """Multi-turn moments for the evaluation harness: cut off then finish, frustrated then retry, pick from 'did you mean'."""
    rng = random.Random(seed)
    for _ in range(n):
        kind = rng.choice(["cut", "frustrated", "pick"])
        if kind == "cut":
            yield {"kind": "cut", "turns": [rng.choice(CUT_OFFS)]}
        elif kind == "frustrated":
            yield {"kind": "frustrated", "turns": [say(rng.choice([k for k in INTENTS if k != "chat"]), rng, 0.2), rng.choice(FRUSTRATED)]}
        else:
            yield {"kind": "pick", "turns": [rng.choice(["first one", "the second one", "yeah that", "1", "2", "the reminder one", "yes", "nah neither"])]}


if __name__ == "__main__":
    import sys
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    base, with_slang = count()
    print(f"{len(INTENTS)} things Luma does, {sum(len(s['t']) for s in INTENTS.values())} ways of asking, "
          f"{base:,} distinct messages before slang and typos ({with_slang:,} with slang alone; typos are unbounded).")
    for text, intent in generate(25, rng.randrange(10 ** 6)):
        print(f"{intent:16} {text}")
