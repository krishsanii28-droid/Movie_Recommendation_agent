"""Mood lexicon: nuanced emotional states, cues and their mapping to base emotions.

Covers English plus common romanised/Indian-English phrasing ("mood off",
"thak gaya", "bore adikkunnu", "tension") and a few native-script words.
The HF classifier (English-only) is the primary signal; the lexicon adds nuance
(tired vs. sad vs. lonely) and Indian-language coverage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BASE_EMOTIONS = ("anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise")


@dataclass(frozen=True)
class State:
    name: str
    label: str  # friendly label shown in the UI
    emoji: str
    base: str  # base emotion it maps to
    energy: str  # default energy level
    valence: int  # -1 negative, 0 neutral, +1 positive
    patterns: tuple[str, ...]


STATES: dict[str, State] = {
    s.name: s
    for s in [
        State(
            "tired",
            "drained",
            "😴",
            "sadness",
            "low",
            -1,
            (
                r"tired",
                r"exhaust\w*",
                r"drained",
                r"long day",
                r"worn out",
                r"sleepy",
                r"knackered",
                r"burn(?:t|ed) out",
                r"fried",
                r"no energy",
                r"wiped( out)?",
                r"thak (?:gaya|gayi|gaye)",
                r"thaka hua",
                r"ksheenam",
                r"kshinam",
                r"romba tired",
                r"ക്ഷീണം",
                r"थका",
                r"lazy",
                r"madi(?:yanu)?",
                r"low battery",
            ),
        ),
        State(
            "stressed",
            "stressed",
            "😤",
            "fear",
            "medium",
            -1,
            (
                r"stress\w*",
                r"overwhelm\w*",
                r"pressure",
                r"deadlines?",
                r"hectic",
                r"tension",
                r"too much (?:work|going on)",
                r"swamped",
                r"frazzled",
                r"exams?",
                r"office drama",
            ),
        ),
        State(
            "anxious",
            "anxious",
            "😟",
            "fear",
            "medium",
            -1,
            (
                r"anxious",
                r"anxiety",
                r"nervous",
                r"worried",
                r"worry\w*",
                r"uneasy",
                r"restless",
                r"on edge",
                r"panick?\w*",
                r"overthink\w*",
                r"mind (?:is )?racing",
                r"can'?t sleep",
                r"insomnia",
                r"interview",
                r"big day tomorrow",
            ),
        ),
        State(
            "lonely",
            "lonely",
            "🫂",
            "sadness",
            "low",
            -1,
            (
                r"lonely",
                r"loneliness",
                r"alone and",
                r"by myself again",
                r"isolated",
                r"no ?one to talk",
                r"miss(?:ing)? (?:home|my friends|my family|people|him|her|them)",
                r"homesick",
                r"left out",
                r"nobody",
            ),
        ),
        State(
            "heartbroken",
            "heartbroken",
            "💔",
            "sadness",
            "low",
            -1,
            (
                r"heart ?broken",
                r"heartbreak",
                r"broke up",
                r"break ?up",
                r"dumped",
                r"my ex\b",
                r"got ghosted",
                r"ghosted",
                r"dil (?:toot|tut)\w*",
                r"rejected",
                r"divorce",
            ),
        ),
        State(
            "sad",
            "down",
            "😔",
            "sadness",
            "low",
            -1,
            (
                r"sad",
                r"feeling (?:low|down|blue)",
                r"(?:bit|so|very|kinda|pretty|really) (?:low|down)",
                r"cry\w*",
                r"upset",
                r"gloomy",
                r"depress\w*",
                r"mood off",
                r"meh",
                r"miserable",
                r"udaas",
                r"udas",
                r"dukhi",
                r"vishamam",
                r"sankadam",
                r"sogama",
                r"bad day",
                r"rough day",
                r"grie\w*",
                r"lost my",
                r"died",
                r"passed away",
                r"funeral",
                r"സങ്കടം",
                r"उदास",
                r"दुखी",
            ),
        ),
        State(
            "angry",
            "frustrated",
            "😠",
            "anger",
            "high",
            -1,
            (
                r"angry",
                r"furious",
                r"annoy\w*",
                r"pissed",
                r"irritat\w*",
                r"frustrat\w*",
                r"rage",
                r"mad at",
                r"fed up",
                r"kalippu",
                r"gussa",
                r"kopam",
            ),
        ),
        State(
            "scared",
            "uneasy",
            "😨",
            "fear",
            "medium",
            -1,
            (
                r"scared",
                r"afraid",
                r"frightened",
                r"terrified",
                r"spooked",
            ),
        ),
        State(
            "bored",
            "bored",
            "🥱",
            "neutral",
            "medium",
            0,
            (
                r"bored",
                r"boring",
                r"nothing to do",
                r"bore (?:ho|adikk)\w*",
                r"kuch nahi",
                r"stuck at home",
                r"need something new",
            ),
        ),
        State(
            "curious",
            "curious",
            "🤯",
            "surprise",
            "medium",
            0,
            (
                r"think\w*",
                r"mind[- ]?bend\w*",
                r"cerebral",
                r"puzzle",
                r"curious",
                r"intellectual",
                r"brain",
                r"deep",
                r"make me think",
                r"twist\w*",
                r"mystery",
            ),
        ),
        State(
            "nostalgic",
            "nostalgic",
            "🌅",
            "joy",
            "low",
            0,
            (
                r"nostalgi\w*",
                r"childhood",
                r"old times",
                r"good old",
                r"school days",
                r"college days",
                r"miss the old",
                r"memories",
            ),
        ),
        State(
            "romantic",
            "romantic",
            "💞",
            "joy",
            "medium",
            1,
            (
                r"romantic",
                r"date night",
                r"in love",
                r"crush",
                r"anniversary",
                r"valentine",
                r"cuddle",
            ),
        ),
        State(
            "excited",
            "party mood",
            "🎉",
            "joy",
            "high",
            1,
            (
                r"party",
                r"hype\w*",
                r"pumped",
                r"dance",
                r"celebrat\w*",
                r"friends are over",
                r"friends over",
                r"weekend vibes?",
                r"masti",
                r"let'?s go",
                r"energetic",
            ),
        ),
        State(
            "happy",
            "happy",
            "😄",
            "joy",
            "high",
            1,
            (
                r"happy",
                r"great",
                r"good mood",
                r"excited",
                r"awesome",
                r"amazing",
                r"yay",
                r"fantastic",
                r"cheerful",
                r"joyful",
                r"khush",
                r"santhosham",
                r"jolly",
                r"santosham",
                r"സന്തോഷം",
                r"खुश",
                r"good day",
                r"got promoted",
                r"passed my",
                r"cleared my",
            ),
        ),
        State(
            "calm",
            "calm",
            "😌",
            "neutral",
            "low",
            1,
            (
                r"calm",
                r"relaxed",
                r"peaceful",
                r"chill\w*",
                r"lazy sunday",
                r"unwind",
                r"mellow",
                r"cosy evening",
                r"cozy evening",
                r"rainy",
            ),
        ),
    ]
}

INTENSIFIERS = re.compile(
    r"\b(very|so|really|extremely|super|completely|totally|utterly|too|bahut|romba|bhayankara|"
    r"bayankara|ekdum)\b|!{2,}",
    re.I,
)
NEGATION = re.compile(r"\b(not|n't|never|no|nothing|without|hardly)\b", re.I)

_COMPILED = {
    name: re.compile(r"(?<![\w])(?:" + "|".join(state.patterns) + r")(?![\w])", re.I)
    for name, state in STATES.items()
}


def match_states(text: str) -> dict[str, float]:
    """Return {state: weight} for lexicon hits, with simple negation handling."""
    hits: dict[str, float] = {}
    lowered = text.lower()
    for name, pattern in _COMPILED.items():
        for m in pattern.finditer(lowered):
            window = lowered[max(0, m.start() - 14) : m.start()]
            negated = bool(NEGATION.search(window))
            state = STATES[name]
            if negated:
                # "not happy" reads as low; "not tired" / "not sad" just cancels.
                if state.valence > 0 and name in ("happy", "excited"):
                    hits["sad"] = hits.get("sad", 0.0) + 0.6
                continue
            hits[name] = hits.get(name, 0.0) + 1.0
    # "curious" words are weak evidence ("think" is common) - damp them
    if "curious" in hits:
        hits["curious"] *= 0.7
    # "low" alone is ambiguous ("low energy") - damp sad if tired is present
    if "sad" in hits and "tired" in hits:
        hits["sad"] *= 0.6
    return hits


def lexicon_emotions(text: str) -> tuple[dict[str, float], dict[str, float]]:
    """Return (base-emotion scores summing to 1, nuanced state weights)."""
    states = match_states(text)
    base = {e: 0.0 for e in BASE_EMOTIONS}
    if not states:
        base["neutral"] = 1.0
        return base, states
    for name, weight in states.items():
        base[STATES[name].base] += weight
    base["neutral"] += 0.15
    total = sum(base.values())
    return {k: round(v / total, 4) for k, v in base.items()}, states


def intensity_of(text: str, states: dict[str, float]) -> float:
    boost = 0.15 * len(INTENSIFIERS.findall(text))
    caps = 0.1 if re.search(r"\b[A-Z]{4,}\b", text) else 0.0
    base = 0.45 + 0.12 * min(sum(states.values()), 3)
    return round(min(1.0, base + boost + caps), 2)
