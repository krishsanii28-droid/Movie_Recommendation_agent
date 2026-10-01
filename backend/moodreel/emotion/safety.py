"""Wellbeing check. Runs before any model so it can never be skipped.

We don't diagnose. For signs of serious distress we respond with care, keep
recommendations gentle and point to people who can help.
"""

from __future__ import annotations

import re

from moodreel.schemas import CareMessage

_CRISIS = re.compile(
    r"(kill(?:ing)? myself|end (?:my|it all|my life)|suicid\w*|want to die|wanna die|don'?t want to (?:live|be alive|exist)|"
    r"no reason to live|better off dead|self[- ]?harm|hurt(?:ing)? myself|cut(?:ting)? myself|"
    r"take my (?:own )?life|not worth living|marne ka man|jeena nahi|"
    r"don'?t want to be (?:here|around|alive) anymore|want to disappear (?:forever|for good)|"
    r"no point (?:in )?(?:living|going on|being alive))",
    re.I,
)
_ELEVATED = re.compile(
    r"(hopeless|worthless|can'?t go on|cant go on|can'?t take (?:it|this) anymore|nothing matters|"
    r"give up on (?:everything|life)|so empty|completely alone|no one cares|nobody cares|"
    r"falling apart|breaking down|panic attacks?|haven'?t slept in days|can'?t stop crying|"
    r"can'?t do this anymore|want to disappear)",
    re.I,
)

HELPLINES = [
    {"name": "Tele-MANAS (Govt. of India, 24x7, free)", "contact": "14416 or 1-800-891-4416"},
    {"name": "Emergency services (India)", "contact": "112"},
    {"name": "Outside India", "contact": "findahelpline.com"},
]

GENTLE_AVOID = ["horror", "violence", "heavy", "gore"]
GENTLE_TONES = ["comforting", "gentle", "warm", "heartwarming", "hopeful", "calming"]


def assess_distress(text: str) -> str:
    if _CRISIS.search(text):
        return "crisis"
    if _ELEVATED.search(text):
        return "elevated"
    return "none"


def care_message(level: str) -> CareMessage | None:
    if level == "crisis":
        return CareMessage(
            text=(
                "I'm really glad you told me, and I'm sorry you're carrying this much right now. "
                "You deserve support from a real person - please reach out to someone you trust, "
                "or call a helpline. If you're in immediate danger, please call 112."
            ),
            helplines=HELPLINES,
        )
    if level == "elevated":
        return CareMessage(
            text=(
                "That sounds genuinely heavy, and it's okay to not be okay. If it's been feeling "
                "like this for a while, talking to someone you trust - or a counsellor - can really help."
            ),
            helplines=HELPLINES[:1],
        )
    return None
