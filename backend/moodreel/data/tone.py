"""Tone descriptors and content flags derived from genres and keywords.

TMDB doesn't tell us how a film *feels*, so we derive a small controlled
vocabulary of tones (``cosy``, ``bittersweet``, ``tense``...) plus content
flags used for "avoid" filters (``violence``, ``horror``, ``heavy``...).
These feed the embedding text and the mood-fit part of the ranker.
"""

from __future__ import annotations

TONE_VOCAB: tuple[str, ...] = (
    "feel-good", "warm", "cosy", "funny", "light", "uplifting", "hopeful", "inspiring",
    "heartwarming", "comforting", "gentle", "calming", "bittersweet", "melancholic",
    "poignant", "cathartic", "romantic", "nostalgic", "whimsical", "quirky", "witty",
    "tense", "thrilling", "twisty", "dark", "gritty", "intense", "eerie", "scary",
    "mind-bending", "thought-provoking", "slow-burn", "fast-paced", "epic", "energetic",
    "party", "musical", "family-friendly", "adventurous", "hard-hitting", "satirical",
    "chaotic",
)

TONE_ALIASES = {"fun": "light", "cozy": "cosy", "scary-light": "eerie"}

# Tones that make a film emotionally "heavy" - removed when a user avoids heavy stuff.
HEAVY_TONES = {"dark", "gritty", "hard-hitting", "intense", "melancholic", "poignant"}

GENRE_TONES: dict[str, list[str]] = {
    "Comedy": ["funny", "light"],
    "Romance": ["romantic"],
    "Family": ["family-friendly", "warm"],
    "Animation": ["family-friendly", "whimsical"],
    "Drama": ["poignant"],
    "Thriller": ["tense", "thrilling"],
    "Mystery": ["twisty"],
    "Crime": ["gritty"],
    "Horror": ["scary", "eerie"],
    "Action": ["energetic", "fast-paced"],
    "Adventure": ["adventurous"],
    "Fantasy": ["whimsical"],
    "Science Fiction": ["mind-bending"],
    "Music": ["musical", "energetic"],
    "War": ["intense", "hard-hitting"],
    "History": ["epic"],
    "Documentary": ["thought-provoking"],
}

KEYWORD_TONES: dict[str, list[str]] = {
    "friendship": ["warm", "heartwarming"],
    "road trip": ["feel-good", "adventurous"],
    "coming of age": ["nostalgic", "bittersweet"],
    "nostalgia": ["nostalgic"],
    "first love": ["romantic", "nostalgic"],
    "grief": ["poignant", "cathartic"],
    "loneliness": ["melancholic"],
    "family": ["warm"],
    "father son relationship": ["heartwarming"],
    "father daughter relationship": ["heartwarming"],
    "underdog": ["inspiring", "uplifting"],
    "sports": ["inspiring", "energetic"],
    "dream": ["hopeful"],
    "time travel": ["mind-bending"],
    "twist ending": ["twisty"],
    "serial killer": ["dark", "scary"],
    "revenge": ["intense"],
    "satire": ["satirical", "witty"],
    "dark comedy": ["dark", "funny"],
    "musical": ["musical"],
    "slice of life": ["gentle", "slow-burn"],
    "food": ["cosy"],
    "cooking": ["cosy", "comforting"],
    "wedding": ["party", "feel-good"],
    "heist": ["thrilling", "fast-paced"],
    "supernatural": ["eerie"],
    "folklore": ["eerie"],
    "survival": ["tense", "intense"],
}

GENRE_FLAGS: dict[str, list[str]] = {
    "Horror": ["horror"],
    "War": ["violence", "heavy"],
    "Crime": ["violence"],
}

KEYWORD_FLAGS: dict[str, list[str]] = {
    "violence": ["violence"],
    "gore": ["violence", "gore"],
    "murder": ["violence"],
    "serial killer": ["violence", "gore"],
    "police brutality": ["violence", "heavy"],
    "torture": ["violence", "gore", "heavy"],
    "suicide": ["heavy"],
    "sexual abuse": ["heavy"],
    "rape": ["heavy"],
    "domestic abuse": ["heavy"],
    "caste discrimination": ["heavy"],
    "drug addiction": ["heavy"],
    "death": ["heavy"],
    "ghost": ["horror"],
    "demon": ["horror"],
    "possession": ["horror"],
    "haunted house": ["horror"],
}


def derive_tones(genres: list[str], keywords: list[str], extra: list[str] | None = None) -> list[str]:
    """Return an ordered, de-duplicated list of tone descriptors."""
    tones: list[str] = list(extra or [])
    for genre in genres:
        tones.extend(GENRE_TONES.get(genre, []))
    for kw in keywords:
        tones.extend(KEYWORD_TONES.get(kw.lower(), []))
    # Comedy + Drama without heavy markers usually lands as warm / bittersweet.
    if "Comedy" in genres and "Drama" in genres:
        tones.extend(["warm", "bittersweet"])
    seen: set[str] = set()
    ordered = []
    for tone in (TONE_ALIASES.get(t, t) for t in tones):
        if tone in TONE_VOCAB and tone not in seen:
            seen.add(tone)
            ordered.append(tone)
    return ordered


def derive_flags(genres: list[str], keywords: list[str], extra: list[str] | None = None) -> list[str]:
    flags: set[str] = set(extra or [])
    for genre in genres:
        flags.update(GENRE_FLAGS.get(genre, []))
    for kw in keywords:
        flags.update(KEYWORD_FLAGS.get(kw.lower(), []))
    return sorted(flags)
