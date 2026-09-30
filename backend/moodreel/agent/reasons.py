"""Short, human reasons that tie each pick back to the user's own words."""

from __future__ import annotations

import re

from moodreel.emotion.lexicon import STATES
from moodreel.schemas import MoodProfile, MovieOut

GENRE_NOUN = {
    "Comedy": "comedy", "Drama": "drama", "Romance": "romance", "Thriller": "thriller",
    "Science Fiction": "sci-fi film", "Animation": "animated film", "Family": "family film",
    "Horror": "horror film", "Action": "action film", "Crime": "crime drama", "Mystery": "mystery",
    "Adventure": "adventure", "Fantasy": "fantasy", "Music": "music drama", "Sport": "sports drama",
    "History": "period drama", "War": "war drama",
}

GOAL_LINE = {
    "shift": ["that should lift you without trying too hard", "that's an easy way out of the funk",
              "that gently turns the evening around", "built to leave you lighter than you started"],
    "stay": ["that lets you sit with the feeling", "that meets you exactly where you are",
             "that honours the mood instead of fighting it", "for when you want to feel it fully"],
    "unclear": ["that works whichever way the night goes", "that keeps things gentle but engaging"],
}
FEELING = {
    "tired": "drained", "stressed": "stressed", "anxious": "anxious", "lonely": "a bit lonely",
    "heartbroken": "heartbroken", "sad": "down", "angry": "frustrated", "scared": "uneasy",
    "bored": "bored", "curious": "curious", "nostalgic": "nostalgic", "romantic": "romantic",
    "excited": "in a party mood", "happy": "good", "calm": "calm",
}
TONE_ADJ = {"party": "party-ready", "family-friendly": "family-friendly", "adventurous": "adventurous"}
THEME_FIX = {
    "father son relationship": "fathers and sons", "father daughter relationship": "fathers and daughters",
    "mother daughter": "mothers and daughters", "nri": "an NRI", "upsc exam": "the UPSC exam",
    "abba": "ABBA", "ouija board": "an ouija board", "greek island": "a Greek island",
}
PLACES = {
    "spain", "mumbai", "kolkata", "bengaluru", "hyderabad", "chennai", "goa", "kochi", "darjeeling",
    "varanasi", "kashmir", "paris", "vienna", "singapore", "madurai", "nellore", "thanjavur", "idukki",
    "kozhikode", "malappuram", "london", "iceland", "mars", "pakistan", "dharavi", "chambal", "kerala",
    "england", "new york", "los angeles", "iraq",
}
SLOT_LINE = {
    "Hidden gem": "A lesser-known gem worth discovering.",
    "Wildcard": "A bit of a wildcard - but trust me on this one.",
}


def genre_phrase(movie: MovieOut) -> str:
    g = movie.genres
    if "Comedy" in g and "Drama" in g:
        return "comedy-drama"
    if "Romance" in g and "Comedy" in g:
        return "rom-com"
    for genre in g:
        if genre in GENRE_NOUN:
            return GENRE_NOUN[genre]
    return "film"


def _runtime(minutes: int | None) -> str:
    if not minutes:
        return ""
    return f"{minutes // 60}h{minutes % 60:02d}"


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def _theme(keyword: str) -> str:
    kw = THEME_FIX.get(keyword.lower(), keyword)
    if kw.lower() in PLACES:
        return kw.title()
    return re.sub(r"\b(kerala|india|indian|hyderabad|kochi|chennai|mumbai)\b", lambda m: m.group(1).title(), kw)


def mood_echo(profile: MoodProfile, i: int, slot: str = "") -> str:
    label = FEELING.get(profile.primary, "open to anything")
    kp = profile.key_phrase.strip()
    if slot == "Wildcard":
        return "For something a little different,"
    if i == 0 and kp and len(kp) <= 70 and not profile.vague:
        return f'You said "{kp}" —'
    options = [f"Since you're feeling {label},", "Another good fit:", "For tonight,"]
    if profile.primary == "neutral":
        options = ["For tonight,", "Another good fit:", "Worth a look:"]
    return options[i % len(options)]


def build_reason(movie: MovieOut, profile: MoodProfile, slot: str, matched: list[str], i: int = 0) -> str:
    tones = [TONE_ADJ.get(t, t) for t in (matched or movie.tones)[:2]]
    desc = ", ".join(tones) if tones else "well-loved"
    noun = genre_phrase(movie)
    themes = [_theme(k) for k in movie.keywords[:3] if len(k) < 28]
    about = f" about {', '.join(themes[:-1])} and {themes[-1]}" if len(themes) >= 2 else ""
    goal_key = "stay" if profile.primary in ("curious", "happy", "excited") and profile.goal == "stay" else profile.goal
    goal_line = GOAL_LINE[goal_key][i % len(GOAL_LINE[goal_key])]
    if slot == "Wildcard":
        goal_line = "that's a change of pace from the rest"
    elif profile.primary == "curious":
        goal_line = "that'll keep your brain happily busy"
    elif profile.primary == "excited":
        goal_line = "that plays great with a crowd"

    first = f"{mood_echo(profile, i, slot)} {movie.title} is {_article(desc)} {desc} {noun}{about} {goal_line}."
    second = ""
    rt = _runtime(movie.runtime)
    if slot in SLOT_LINE:
        second = SLOT_LINE[slot]
    elif profile.energy == "low" and movie.runtime and movie.runtime <= 125:
        second = f"At {rt}, it won't ask much of you."
    elif profile.context.company == "family" and "family-friendly" in movie.tones:
        second = "Easy to enjoy across ages."
    elif profile.context.company == "friends" and {"party", "funny"} & set(movie.tones):
        second = "Perfect with a group and some snacks."
    return f"{first} {second}".strip()


def build_group_reason(movie: MovieOut, members: list[tuple[str, MoodProfile]], matched: list[str], i: int = 0) -> str:
    tones = [TONE_ADJ.get(t, t) for t in (matched or movie.tones)[:2]]
    desc = ", ".join(tones)
    parts = []
    for name, p in members[:3]:
        label = STATES[p.primary].label if p.primary in STATES else "easygoing"
        parts.append(f"{name}'s {label} mood" if p.primary != "neutral" else f"{name}'s easygoing mood")
    joined = ", ".join(parts[:-1]) + f" and {parts[-1]}" if len(parts) > 1 else parts[0]
    openers = ["Middle ground for everyone:", "A crowd-pleaser here:", "Something the whole room can agree on:"]
    return (f"{openers[i % len(openers)]} {movie.title} is {_article(desc)} {desc} {genre_phrase(movie)} "
            f"that meets {joined} halfway.")


def why_notes(profile: MoodProfile, slot: str, extra: list[str]) -> list[str]:
    notes = []
    if profile.context.languages:
        notes.append("Language filter: " + ", ".join(profile.context.languages))
    avoid = [a.replace("tone:", "") for a in profile.context.avoid]
    if avoid:
        notes.append("Steered clear of: " + ", ".join(avoid))
    if profile.context.time_available:
        notes.append(f"Fits in about {profile.context.time_available} minutes")
    if profile.distress != "none":
        notes.append("Kept gentle - nothing dark or intense")
    slot_note = {
        "Safe pick": "Safe pick: widely loved and well-rated",
        "Hidden gem": "Hidden gem: highly rated but under-watched",
        "Wildcard": "Wildcard: deliberately different from the other picks",
    }.get(slot)
    if slot_note:
        notes.append(slot_note)
    return notes + extra
