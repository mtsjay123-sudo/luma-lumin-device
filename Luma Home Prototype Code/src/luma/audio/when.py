"""At a pause: wait, nod, or answer? (docs/GAME_PLAN.md, B4: "the brain picks when".)

Today a pause is judged by sound alone: Smart Turn hears whether the voice fell the way a finished sentence does
(luma.audio.turn). A person also listens to the words. "I went to the store because" isn't finished however the voice
fell, and "what time is it in Tokyo" is.

This reads the words so far and says one of three things, or nothing:

  "wait"    they've stopped in the middle of a thought
  "nod"     they're in the middle of telling something long; a small "mm-hm" fits and they go on
  "answer"  they've finished
  None      can't tell: the sound decides, as it does today

Luma's own code goes first (by_code): a question is finished, a sentence left hanging on "because" or "and the" isn't.
Only where code can't tell is the brain asked, one plain question, YES or NO, and never a small brain (they say YES to
nearly anything). Anything the safety readers read is "answer" at once: nobody who might not be safe is kept waiting.

Off until it's measured (`brain_picks_when`). Asking costs a trip to the brain at every unclear pause, and whether
that makes Luma's timing better or only later is what the timing test is for, and it has no recordings yet. As built,
the voice loop uses only the cheap half: with the switch on, a pause that code reads as "wait" doesn't start the brain
early on half a sentence (luma/orchestrator.py, maybe_done). Nothing ends a turn sooner on this module's word.
"""
from __future__ import annotations

import re
import threading

# The last word of a sentence that isn't over.
HANGING = re.compile(
    r"\b(?:and|but|or|so|because|cause|cuz|since|although|though|unless|until|while|when|where|if|then|than|that|which|who|whose|"
    r"the|a|an|my|your|his|her|their|our|its|this|these|those|some|any|every|"
    r"to|of|in|on|at|for|with|from|by|about|into|onto|over|under|between|like|as|"
    r"is|was|were|are|am|be|been|being|has|have|had|do|does|did|will|would|could|should|can|may|might|must|"
    r"i|we|you|he|she|they|it's|i'm|we're|they're|he's|she's|except|just|more|very|really|um|uh|er|hmm)\W*$", re.I)
# A finished thing to say that happens to end on one of those words: "that's who it was", "what is it", "I'm in", "come on".
WHOLE_ANYWAY = re.compile(r"\b(?:it|that|this|there|here|one|me|him|them|us) (?:is|was|were|are)$|\b(?:come|hold|hang|go|bring it|turn it|log) (?:on|in|over|up)$|"
                          r"\b(?:i|we|you|they) (?:do|did|will|would|could|should|can|might|have|had|am|are|was|were)$|\bcount me in$|\bi think so$", re.I)
ASKS = re.compile(r"^\W*(?:who|what|when|where|why|how|which|is|are|was|were|do|does|did|can|could|would|will|should|have|has)\b", re.I)
PROMPT = ('Someone is talking to you and has paused. So far they have said:\n"{said}"\n\n'
          "Is that a finished thing to say, so that it's your turn to speak? Answer YES or NO only.")
LONG = 14     # words: past this, someone who hasn't finished is telling a story, and a listener nods


def by_code(said):
    """"answer", "wait", or None when the words alone don't say."""
    from luma.agent import friendcheck
    from luma.agent.runtime import CRISIS
    said = " ".join(str(said or "").split())
    if not said:
        return None
    if CRISIS.search(said.lower()) or friendcheck.at_risk(said) or friendcheck.worth_asking(said):
        return "answer"
    if said.endswith(("...", "…", "-", "—", ",")):
        return "wait"
    if said[-1] in ".!?":
        return "answer"
    if WHOLE_ANYWAY.search(said):
        return "answer"
    if HANGING.search(said):
        return "wait"
    if ASKS.match(said) and len(said.split()) >= 3:
        return "answer"
    return None


def decide(agent, said, cancel_event=None):
    """What to do at this pause, or None. Nothing at all unless the owner has switched it on."""
    if not agent.store.setting("brain_picks_when", False):
        return None
    code = by_code(said)
    if code:
        return code
    done = None
    try:
        question = PROMPT.format(said=" ".join(str(said).split())[:400])
        if agent.planner is not None:      # a stand-in brain is asked only if it says it answers plain questions
            if getattr(agent.planner, "answers_plain_questions", False):
                from luma.agent import friendcheck
                out = agent.call_planner([{"role": "user", "content": question}], [], {}, cancel_event or threading.Event())
                text = out.get("text") if isinstance(out, dict) else ""
                done = True if friendcheck.said_yes(text) else False if re.match(r"\W*no\b", str(text or ""), re.I) else None
        elif agent.use_model:
            from luma.llm import brain
            if not brain.small_here():
                heard = brain.yes_or_no(question, cancel_event=cancel_event or threading.Event(), mode=agent.mode)
                done = True if heard == "YES" else False if heard == "NO" else None
    except Exception:
        return None                        # a pause never fails over this: the sound decides
    if done is None:
        return None
    if done:
        return "answer"
    return "nod" if len(str(said).split()) >= LONG else "wait"
