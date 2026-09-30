"""Turn raw text + emotion scores into a structured ``MoodProfile``.

This is the deterministic "understanding" layer. With an LLM configured the
agent can refine it, but everything here works on its own and is what the
fallback agent, the evaluation and the tests rely on.
"""

from __future__ import annotations

import re
from collections import Counter
from statistics import median

from moodreel.emotion.classifier import BASE_TO_STATE, EmotionResult
from moodreel.emotion.lexicon import STATES, intensity_of
from moodreel.schemas import MoodContext, MoodProfile

# --- Mood chips (quick start without typing) --------------------------------
CHIPS: dict[str, dict[str, str]] = {
    "drained": {"state": "tired", "label": "Drained", "emoji": "😴", "text": "I'm drained"},
    "happy": {"state": "happy", "label": "Happy", "emoji": "😄", "text": "I'm in a happy mood"},
    "heartbroken": {"state": "heartbroken", "label": "Heartbroken", "emoji": "💔", "text": "I'm heartbroken"},
    "stressed": {"state": "stressed", "label": "Stressed", "emoji": "😤", "text": "I'm stressed out"},
    "think": {"state": "curious", "label": "Want to think", "emoji": "🤯", "text": "I want something that makes me think"},
    "party": {"state": "excited", "label": "Party mood", "emoji": "🎉", "text": "Party mood with friends"},
}

# --- What each state wants to watch, depending on the mood goal ---------------
TARGET_TONES: dict[str, dict[str, list[str]]] = {
    "tired": {"stay": ["gentle", "calming", "cosy", "comforting", "warm"],
              "shift": ["cosy", "light", "funny", "feel-good", "warm"]},
    "stressed": {"stay": ["cathartic", "intense", "tense", "energetic"],
                 "shift": ["calming", "funny", "light", "comforting", "feel-good"]},
    "anxious": {"stay": ["cathartic", "poignant", "gentle"],
                "shift": ["comforting", "gentle", "funny", "warm", "calming"]},
    "lonely": {"stay": ["melancholic", "bittersweet", "gentle", "poignant"],
               "shift": ["warm", "heartwarming", "feel-good", "comforting", "funny"]},
    "heartbroken": {"stay": ["bittersweet", "melancholic", "romantic", "cathartic"],
                    "shift": ["funny", "uplifting", "feel-good", "energetic", "hopeful"]},
    "sad": {"stay": ["melancholic", "bittersweet", "poignant", "cathartic"],
            "shift": ["uplifting", "heartwarming", "funny", "hopeful", "feel-good"]},
    "angry": {"stay": ["intense", "energetic", "fast-paced", "cathartic", "gritty"],
              "shift": ["funny", "light", "calming", "feel-good"]},
    "scared": {"stay": ["scary", "eerie", "tense"],
               "shift": ["comforting", "funny", "light", "warm"]},
    "bored": {"stay": ["thrilling", "twisty", "energetic", "quirky", "adventurous"],
              "shift": ["thrilling", "twisty", "energetic", "quirky", "adventurous"]},
    "curious": {"stay": ["mind-bending", "thought-provoking", "twisty", "slow-burn"],
                "shift": ["mind-bending", "thought-provoking", "twisty", "quirky"]},
    "nostalgic": {"stay": ["nostalgic", "bittersweet", "warm", "romantic"],
                  "shift": ["feel-good", "energetic", "funny"]},
    "romantic": {"stay": ["romantic", "warm", "feel-good", "bittersweet"],
                 "shift": ["funny", "adventurous", "light"]},
    "excited": {"stay": ["party", "funny", "energetic", "musical", "fast-paced"],
                "shift": ["calming", "gentle", "warm"]},
    "happy": {"stay": ["feel-good", "funny", "energetic", "uplifting", "warm"],
              "shift": ["thought-provoking", "poignant", "twisty"]},
    "calm": {"stay": ["gentle", "calming", "warm", "slow-burn", "comforting"],
             "shift": ["thrilling", "energetic", "adventurous"]},
    "neutral": {"stay": ["feel-good", "twisty", "warm", "funny", "thrilling"],
                "shift": ["feel-good", "twisty", "warm", "funny", "thrilling"]},
}

# Tones that would clash with the mood goal (soft penalty in ranking).
CLASH_TONES: dict[tuple[str, str], list[str]] = {
    ("heartbroken", "shift"): ["romantic", "melancholic", "bittersweet"],
    ("sad", "shift"): ["dark", "hard-hitting", "melancholic", "gritty"],
    ("lonely", "shift"): ["dark", "melancholic", "hard-hitting"],
    ("stressed", "shift"): ["tense", "scary", "intense", "dark", "hard-hitting"],
    ("anxious", "shift"): ["tense", "scary", "intense", "dark", "eerie"],
    ("tired", "shift"): ["intense", "hard-hitting", "dark", "slow-burn"],
    ("tired", "stay"): ["intense", "hard-hitting", "fast-paced"],
    ("scared", "shift"): ["scary", "eerie", "tense", "dark"],
    ("happy", "stay"): ["dark", "hard-hitting", "melancholic"],
    ("excited", "stay"): ["slow-burn", "melancholic", "dark"],
    ("angry", "shift"): ["intense", "gritty", "dark"],
}

POSITIVE_TONES = {"funny", "feel-good", "uplifting", "light", "cosy", "warm", "heartwarming", "comforting", "hopeful"}
SPECIFICITY = ["heartbroken", "lonely", "tired", "stressed", "anxious", "angry", "scared", "sad",
               "nostalgic", "romantic", "excited", "curious", "bored", "happy", "calm"]

# --- Context cues --------------------------------------------------------------
_COMPANY = [
    ("family", r"\b(family|parents|kids|children|mom|mum|dad|amma|achan|appa|papa|mummy|grand(?:ma|pa|parents)|my (?:son|daughter)|in-laws)\b"),
    ("partner", r"\b(girlfriend|boyfriend|wife|husband|partner|date night|my date|bf|gf|spouse|fianc[eé]e?)\b"),
    ("friends", r"\b(friends?|gang|buddies|roommates?|flatmates?|squad|colleagues|cousins)\b"),
    ("alone", r"\b(alone|by myself|solo|on my own|just me)\b"),
]
_LANGS = {
    "ml": r"\b(malayalam|mallu|mollywood)\b",
    "hi": r"\b(hindi|bollywood)\b",
    "ta": r"\b(tamil|kollywood)\b",
    "te": r"\b(telugu|tollywood)\b",
    "en": r"\b(english|hollywood)\b",
}
_NEG = r"(?:no|not|nothing|avoid|without|skip|don'?t want|hate|zero|none of that|not in the mood for)\s+(?:\w+\s+){0,2}?"
_AVOID = {
    "horror": _NEG + r"(?:horror|scary|ghosts?|creepy|spooky|jump ?scares?)",
    "violence": _NEG + r"(?:violence|violent|blood|bloody|gore|gory|fights?|action)",
    "heavy": _NEG + r"(?:heavy|sad|depressing|dark|intense|serious|tragic|tragedy|crying)",
    "sexual content": _NEG + r"(?:sex|sexual|explicit|adult|vulgar)",
}
_AVOID_TONES = {
    "romantic": _NEG + r"(?:romance|romantic|love stor(?:y|ies)|mushy|cheesy)",
    "slow-burn": _NEG + r"(?:slow|boring|long|draggy|lag)",
    "musical": _NEG + r"(?:songs|musicals?)",
}
_SHIFT = r"(cheer me up|lift (?:me|my)|uplift|pick me up|feel better|distract|take my mind off|forget (?:about|it)|make me (?:laugh|smile|happy)|something happy|escape|turn (?:it|this) around|change my mood|lighten|snap out|get over)"
_STAY = r"(sit with|wallow|let me cry|want to cry|good cry|sad (?:movie|film)|match(?:es)? my mood|lean into|feel it|embrace it|stay in (?:this|my|the) mood|something sad|make me cry|tearjerker)"
_TONE_REQUESTS = {
    "cosy": r"\b(cosy|cozy|comfort(?:ing)?|snug|like a hug|soothing)\b",
    "funny": r"\b(funny|comedy|comedies|laugh|hilarious|silly|goofy)\b",
    "light": r"\b(light|breezy|easy watch|easy|light-?hearted|low[- ]stakes|chill)\b",
    "feel-good": r"\b(feel[- ]?good|wholesome|happy ending)\b",
    "uplifting": r"\b(uplifting|inspiring|motivat\w*|hopeful)\b",
    "thrilling": r"\b(thriller|thrilling|suspense|edge of (?:my|the) seat|gripping)\b",
    "twisty": r"\b(twist\w*|mystery|whodunn?it|keep me guessing)\b",
    "mind-bending": r"\b(mind[- ]?bend\w*|trippy|cerebral|make me think|think)\b",
    "romantic": r"\b(romance|romantic|rom-?com|love story)\b",
    "scary": r"\b(horror|scary|spooky)\b",
    "energetic": r"\b(action|high[- ]energy|adrenaline|mass)\b",
    "bittersweet": r"\b(bittersweet|good cry|tearjerker)\b",
    "melancholic": r"\b(sad (?:movie|film)|melanchol\w*|make me cry)\b",
    "family-friendly": r"\b(family[- ]friendly|for kids|with (?:the )?kids|animated|animation)\b",
    "nostalgic": r"\b(nostalgi\w*|old[- ]school|classic)\b",
    "musical": r"\b(musical|songs|singalong)\b",
    "epic": r"\b(epic|grand|spectacle)\b",
}
_VAGUE = r"^\s*(idk|i don'?t know|dunno|anything|whatever|not sure|no idea|surprise me|suggest (?:something|a movie)|recommend (?:me )?(?:something|a movie)|hmm+|ok|hi|hello|hey)\W*$"
_HIGH_ENERGY = r"\b(pumped|wired|hyper|energetic|hype\w*|full of energy|buzzing|restless)\b"
_LOW_ENERGY = r"\b(tired|exhausted|sleepy|lazy|drained|no energy|low energy|couch|in bed|half asleep|wind down|winding down)\b"


def _find(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.I) is not None


def parse_context(text: str, languages: list[str] | None = None) -> MoodContext:
    company = "unknown"
    for name, pattern in _COMPANY:
        if _find(pattern, text):
            company = name
            break
    langs = list(languages or []) or [code for code, p in _LANGS.items() if _find(p, text)]
    avoid = [flag for flag, p in _AVOID.items() if _find(p, text)]
    avoid += [f"tone:{tone}" for tone, p in _AVOID_TONES.items() if _find(p, text)]
    if company == "family":
        avoid += ["sexual content", "gore"]
    time_available = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h)\b", text, re.I)
    if m:
        time_available = int(float(m.group(1)) * 60)
    m = re.search(r"(\d{2,3})\s*(?:min|mins|minutes)\b", text, re.I)
    if m:
        time_available = int(m.group(1))
    if time_available is None and _find(r"\b(short|quick|not too long|under two hours|early night|work tomorrow)\b", text):
        time_available = 125
    return MoodContext(company=company, time_available=time_available, languages=langs,
                       avoid=sorted(set(avoid)))


def requested_tones(text: str) -> list[str]:
    tones = []
    for tone, pattern in _TONE_REQUESTS.items():
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        # skip negated requests ("no horror", "nothing slow")
        window = text[max(0, m.start() - 16) : m.start()].lower()
        if re.search(r"\b(no|not|nothing|avoid|without|don'?t)\b", window):
            continue
        tones.append(tone)
    return tones


def detect_goal(text: str) -> str | None:
    if _find(_STAY, text):
        return "stay"
    if _find(_SHIFT, text):
        return "shift"
    return None


def key_phrase(text: str) -> str:
    """The user's own words to reflect back in reasons (short and natural)."""
    clean = re.sub(r"\s+", " ", text).strip().rstrip(".!?")
    if not clean:
        return ""
    def lower_first(s: str) -> str:
        return s if s[:2].isupper() or s.startswith("I ") or s.startswith("I'") else s[0].lower() + s[1:]

    if len(clean) <= 50:
        return lower_first(clean)
    # Keep only the clauses that carry feeling or a request, in order, up to ~50 chars.
    clauses = [c.strip() for c in re.split(r"[.,;!?]|\s[-–—]\s", clean) if c.strip()]
    keep: list[str] = []
    for clause in clauses:
        if not (requested_tones(clause) or _state_hits(clause)):
            continue
        if keep and len(", ".join(keep + [clause])) > 50:
            break
        keep.append(clause)
    best = ", ".join(keep) if keep else clauses[0] if clauses else clean
    return lower_first(best[:60])


def _state_hits(text: str) -> dict[str, float]:  # small indirection for key_phrase scoring
    from moodreel.emotion.lexicon import match_states

    return match_states(text)


def _ordered_states(result: EmotionResult) -> list[str]:
    return sorted(
        result.states,
        key=lambda s: (-result.states[s], SPECIFICITY.index(s) if s in SPECIFICITY else 99),
    )


def _energy(text: str, primary: str, slider: float | None) -> str:
    if slider is not None:
        return "low" if slider < 0.34 else "high" if slider > 0.66 else "medium"
    if _find(_HIGH_ENERGY, text):
        return "high"
    if _find(_LOW_ENERGY, text):
        return "low"
    state = STATES.get(primary)
    return state.energy if state else "medium"


def _label(state: str | None) -> str:
    if not state:
        return ""
    return STATES[state].label if state in STATES else state


def build_target_tones(primary: str, secondary: str | None, goal: str, requested: list[str]) -> list[str]:
    table = TARGET_TONES.get(primary, TARGET_TONES["neutral"])
    if goal == "unclear":
        base = table["stay"][:2] + table["shift"][:3]
    else:
        base = table[goal]
    extra = []
    if secondary and secondary in TARGET_TONES:
        extra = TARGET_TONES[secondary]["shift" if goal == "shift" else "stay"][:2]
    ordered = list(dict.fromkeys(requested + base + extra))
    return ordered[:7]


def clash_tones(primary: str, goal: str, avoid: list[str]) -> list[str]:
    tones = list(CLASH_TONES.get((primary, goal), []))
    tones += [a.split(":", 1)[1] for a in avoid if a.startswith("tone:")]
    return list(dict.fromkeys(tones))


def summarize(profile: MoodProfile) -> str:
    parts = [_label(profile.primary) if profile.primary != "neutral" else "open to anything"]
    if profile.secondary:
        parts.append(_label(profile.secondary))
    parts.append(f"{profile.energy} energy")
    parts.append({"stay": "wants to lean in", "shift": "wants a lift", "unclear": "goal unclear"}[profile.goal])
    if profile.context.company not in ("unknown",):
        parts.append({"alone": "solo", "partner": "with partner", "family": "with family",
                      "friends": "with friends"}[profile.context.company])
    return " · ".join(parts)


def analyze_mood(
    text: str,
    emotion: EmotionResult,
    *,
    chip: str | None = None,
    energy_slider: float | None = None,
    shift_slider: float | None = None,
    languages: list[str] | None = None,
    prior: MoodProfile | None = None,
) -> MoodProfile:
    states = _ordered_states(emotion)
    if chip and chip in CHIPS:
        chip_state = CHIPS[chip]["state"]
        states = [chip_state] + [s for s in states if s != chip_state]

    requested = requested_tones(text)
    context = parse_context(text, languages)
    text_goal = detect_goal(text)

    strong_new = bool(states) and sum(emotion.states.values()) >= 1.0
    if prior is not None and not strong_new and not chip:
        # Follow-up answer ("lift me up", "Malayalam please") refines the earlier mood.
        primary, secondary, intensity = prior.primary, prior.secondary, prior.intensity
        requested = list(dict.fromkeys(requested + prior.requested_tones))
        context = MoodContext(
            company=context.company if context.company != "unknown" else prior.context.company,
            time_available=context.time_available or prior.context.time_available,
            languages=context.languages or prior.context.languages,
            avoid=sorted(set(context.avoid) | set(prior.context.avoid)),
        )
        raw = prior.raw_emotions
    else:
        if states:
            primary = states[0]
            secondary = states[1] if len(states) > 1 else None
        else:
            primary = BASE_TO_STATE.get(emotion.top, "neutral") if emotion.top != "neutral" and emotion.scores[emotion.top] > 0.5 else "neutral"
            secondary = None
        intensity = intensity_of(text, emotion.states) if emotion.states or chip else 0.4
        raw = emotion.scores

    # Mood goal: explicit words > slider > requested tones > state default
    goal: str | None = text_goal
    if goal is None and shift_slider is not None and abs(shift_slider) >= 0.34:
        goal = "shift" if shift_slider > 0 else "stay"
    state = STATES.get(primary)
    valence = state.valence if state else 0
    if goal is None and requested:
        if valence < 0 and any(t in POSITIVE_TONES for t in requested):
            goal = "shift"
        elif valence < 0 and any(t in ("melancholic", "bittersweet") for t in requested):
            goal = "stay"
    if goal is None and prior is not None and prior.goal != "unclear":
        goal = prior.goal
    if goal is None:
        if primary in ("tired", "bored"):
            goal = "shift"
        elif valence >= 0:
            goal = "stay"
        else:
            goal = "unclear"

    vague = (
        not states and not requested and not chip and prior is None
        and (bool(re.match(_VAGUE, text, re.I)) or len(text.split()) <= 2)
    )

    profile = MoodProfile(
        primary=primary,
        secondary=secondary,
        intensity=intensity,
        energy=_energy(text, primary, energy_slider),  # type: ignore[arg-type]
        goal=goal,  # type: ignore[arg-type]
        context=context,
        target_tones=build_target_tones(primary, secondary, goal, requested),
        requested_tones=requested,
        raw_emotions=raw,
        key_phrase=(prior.key_phrase if prior is not None and not strong_new and prior.key_phrase
                    else key_phrase(text)),
        vague=vague,
    )
    profile.summary = summarize(profile)
    return profile


def blend_group(members: list[tuple[str, MoodProfile]]) -> MoodProfile:
    """Blend several people's moods into one profile the whole room can enjoy."""
    profiles = [p for _, p in members]
    tone_votes: Counter[str] = Counter()
    for p in profiles:
        for rank, tone in enumerate(p.target_tones):
            tone_votes[tone] += 1.0 + (len(p.target_tones) - rank) * 0.1
    shared = [t for t, _ in tone_votes.most_common() if sum(t in p.target_tones for p in profiles) >= 2]
    rest = [t for t, _ in tone_votes.most_common() if t not in shared]
    energies = {"low": 0, "medium": 1, "high": 2}
    energy = ["low", "medium", "high"][round(median(energies[p.energy] for p in profiles))]
    goals = Counter(p.goal for p in profiles if p.goal != "unclear")
    goal = goals.most_common(1)[0][0] if goals else "shift"
    lang_sets = [set(p.context.languages) for p in profiles if p.context.languages]
    languages = sorted(set.intersection(*lang_sets)) if lang_sets else []
    if lang_sets and not languages:
        languages = sorted(set.union(*lang_sets))
    companies = {p.context.company for p in profiles}
    company = "family" if "family" in companies else "partner" if len(profiles) == 2 and "partner" in companies else "friends"
    times = [p.context.time_available for p in profiles if p.context.time_available]
    avoid = sorted({a for p in profiles for a in p.context.avoid})
    primaries = Counter(p.primary for p in profiles)
    primary = primaries.most_common(1)[0][0]
    secondary = next((p.primary for p in profiles if p.primary != primary), None)
    profile = MoodProfile(
        primary=primary,
        secondary=secondary,
        intensity=round(sum(p.intensity for p in profiles) / len(profiles), 2),
        energy=energy,  # type: ignore[arg-type]
        goal=goal,  # type: ignore[arg-type]
        context=MoodContext(company=company, time_available=min(times) if times else None,  # type: ignore[arg-type]
                            languages=languages, avoid=avoid),
        target_tones=(shared + rest)[:7],
        distress=max((p.distress for p in profiles), key=["none", "elevated", "crisis"].index),
        key_phrase=" / ".join(f"{name}: {p.key_phrase}" for name, p in members)[:160],
    )
    profile.summary = f"group of {len(members)} · " + " · ".join(
        f"{name} {_label(p.primary) if p.primary != 'neutral' else 'easygoing'}" for name, p in members
    )
    return profile
