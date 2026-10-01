"""Candidate ranking and diversity-aware selection.

score = semantic similarity + mood/tone fit + quality + learned taste + context,
minus clashes with the mood goal. Then we pick a *set*, not a list: one safe
pick, one hidden gem, one wildcard, and MMR for the rest - so the user never
gets five near-identical films.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np

from moodreel.emotion.mood import clash_tones, request_matches
from moodreel.emotion.safety import GENTLE_AVOID
from moodreel.schemas import MoodProfile, MovieOut
from moodreel.search.index import SearchIndex

HEAVY_TONES = {"dark", "gritty", "hard-hitting", "intense", "melancholic"}
TONE_WEIGHTS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.45]


@dataclass
class Scored:
    movie: MovieOut
    score: float
    sim: float = 0.0
    tone_fit: float = 0.0
    matched: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    slot: str = "Also great"


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def movie_similarity(a: MovieOut, b: MovieOut) -> float:
    return (
        0.5 * _jaccard(a.genres, b.genres)
        + 0.4 * _jaccard(a.tones, b.tones)
        + 0.1 * (a.language == b.language)
    )


def passes_filters(
    movie: MovieOut, profile: MoodProfile, exclude: set[int], strict_time: bool = True
) -> bool:
    ctx = profile.context
    if movie.id in exclude:
        return False
    if ctx.languages and movie.language not in ctx.languages:
        return False
    avoid = {a for a in ctx.avoid if not a.startswith("tone:")}
    if profile.distress != "none":
        avoid |= set(GENTLE_AVOID)
    if avoid & set(movie.content_flags):
        return False
    if "horror" in avoid and ("Horror" in movie.genres or "scary" in movie.tones):
        return False
    if "heavy" in avoid and len(HEAVY_TONES & set(movie.tones)) >= 2:
        return False
    if "violence" in avoid and "gritty" in movie.tones:
        return False
    if (
        strict_time
        and ctx.time_available
        and movie.runtime
        and movie.runtime > ctx.time_available + 10
    ):
        return False
    return True


def score_movie(
    movie: MovieOut, sim_n: float, profile: MoodProfile, history: dict | None
) -> Scored:
    target = profile.target_tones
    matched = [t for t in target if t in movie.tones]
    weight_sum = sum(TONE_WEIGHTS[: min(3, len(target))]) or 1.0
    tone_fit = min(
        1.0, sum(TONE_WEIGHTS[i] for i, t in enumerate(target[:7]) if t in movie.tones) / weight_sum
    )
    clashes = [
        t
        for t in clash_tones(
            profile.primary, profile.goal, profile.context.avoid, profile.requested_tones
        )
        if t in movie.tones
    ]
    quality = max(0.0, min(1.0, (movie.rating - 6.0) / 2.5))
    notes: list[str] = []

    taste = 0.0
    if history:
        ta, ga = history.get("tone_affinity", {}), history.get("genre_affinity", {})
        taste = (
            sum(ta.get(t, 0.0) for t in movie.tones) * 0.04
            + sum(ga.get(g, 0.0) for g in movie.genres) * 0.05
        )
        taste = max(-0.3, min(0.3, taste))
        if taste > 0.08:
            notes.append("Matches what you've loved before")
        elif taste < -0.08:
            notes.append("Adjusted down based on your earlier feedback")

    adjust = 0.0
    tones = set(movie.tones)
    if profile.requested_tones:
        # Explicit asks ("comedy", "something cosy") outweigh mood defaults.
        hit = request_matches(profile.requested_tones, tones) / len(profile.requested_tones)
        adjust += 0.22 * hit if hit else -0.15
    if profile.energy == "low":
        if movie.runtime and movie.runtime > 160:
            adjust -= 0.1
        elif movie.runtime and movie.runtime > 140:
            adjust -= 0.04
        if tones & {"gentle", "light", "cosy", "comforting", "calming"}:
            adjust += 0.05
    elif profile.energy == "high" and tones & {"energetic", "fast-paced", "thrilling", "party"}:
        adjust += 0.06
    company = profile.context.company
    if company == "family" and "family-friendly" in tones:
        adjust += 0.08
    elif company == "friends" and tones & {"party", "funny", "energetic"}:
        adjust += 0.05
    elif company == "partner" and tones & {"romantic", "warm"} and profile.primary != "heartbroken":
        adjust += 0.04
    if profile.distress != "none" and tones & {"comforting", "gentle", "warm", "hopeful"}:
        adjust += 0.08

    score = 0.35 * sim_n + 0.40 * tone_fit + 0.15 * quality + taste + adjust - 0.2 * len(clashes)
    return Scored(movie, round(score, 4), round(sim_n, 3), round(tone_fit, 3), matched, notes)


def rank_candidates(
    index: SearchIndex,
    query: str,
    profile: MoodProfile,
    history: dict | None = None,
    exclude: set[int] | None = None,
    k: int = 300,
) -> tuple[list[Scored], list[str]]:
    """Return (ranked candidates, relaxation notes)."""
    exclude = set(exclude or ())
    hits = index.search(query, k=min(k, max(len(index.movies), 1)))
    sims = {h.movie_id: h.score for h in hits}
    max_sim = max([s for s in sims.values() if s > 0] or [1.0])
    relaxed: list[str] = []

    def collect(strict_time: bool, excl: set[int], prof: MoodProfile) -> list[Scored]:
        out = []
        for movie in index.movies.values():
            if not passes_filters(movie, prof, excl, strict_time):
                continue
            sim_n = max(0.0, sims.get(movie.id, 0.0)) / max_sim
            out.append(score_movie(movie, sim_n, prof, history))
        return sorted(out, key=lambda s: -s.score)

    ranked = collect(True, exclude, profile)
    if len(ranked) < 3 and profile.context.time_available:
        ranked = collect(False, exclude, profile)
        relaxed.append("a few run a little longer than your time window")
    if len(ranked) < 3 and profile.context.languages:
        loose = profile.model_copy(deep=True)
        loose.context.languages = []
        extra = [
            s
            for s in collect(False, exclude, loose)
            if s.movie.id not in {r.movie.id for r in ranked}
        ]
        ranked += extra
        relaxed.append("I added a couple from other languages to round things out")
    return ranked, relaxed


def _vote_percentiles(index: SearchIndex) -> dict[str, tuple[float, float]]:
    by_lang: dict[str, list[int]] = {}
    for m in index.movies.values():
        by_lang.setdefault(m.language, []).append(m.vote_count)
    return {
        lang: (float(np.percentile(v, 40)), float(np.percentile(v, 60)))
        for lang, v in by_lang.items()
    }


def select_diverse(
    ranked: list[Scored],
    index: SearchIndex,
    n: int = 4,
    rng: random.Random | None = None,
    requested: list[str] | None = None,
) -> list[Scored]:
    if not ranked:
        return []
    if requested:
        # Diversity happens *within* what the user asked for; others only fill gaps.
        on_ask = [s for s in ranked if request_matches(requested, s.movie.tones)]
        ranked = on_ask if len(on_ask) >= n else on_ask + [s for s in ranked if s not in on_ask]
    pool = ranked[: max(20, n * 5)]
    if rng is not None:  # "surprise me": shuffle within the good part of the pool
        head = pool[:12]
        rng.shuffle(head)
        pool = head + pool[12:]
    pct = _vote_percentiles(index)
    top_score = pool[0].score
    picked: list[Scored] = []

    # Vote counts differ hugely by language, so thresholds are per-language percentiles
    # with absolute caps (a 3,000-vote Hollywood film isn't a "hidden" gem).
    def is_safe(s: Scored) -> bool:
        return (
            s.movie.vote_count >= min(pct.get(s.movie.language, (0, 0))[1], 500)
            and s.movie.rating >= 7.0
        )

    def is_gem(s: Scored) -> bool:
        return (
            s.movie.vote_count <= min(pct.get(s.movie.language, (0, 0))[0], 600)
            and s.movie.rating >= 7.3
        )

    def take(pred, slot: str, floor: float) -> None:
        for s in pool:
            if s in picked or s.score < floor:
                continue
            if pred(s):
                s.slot = slot
                picked.append(s)
                return

    take(is_safe, "Safe pick", top_score * 0.7)
    if n >= 3:
        take(
            lambda s: is_gem(s) and all(movie_similarity(s.movie, p.movie) < 0.7 for p in picked),
            "Hidden gem",
            top_score * 0.65,
        )
    if n >= 3:
        take(
            lambda s: all(movie_similarity(s.movie, p.movie) < 0.3 for p in picked),
            "Wildcard",
            top_score * 0.55,
        )

    # MMR fill for the rest
    while len(picked) < n:
        best, best_val = None, -1e9
        for s in pool:
            if s in picked:
                continue
            redundancy = max((movie_similarity(s.movie, p.movie) for p in picked), default=0.0)
            val = 0.72 * s.score - 0.28 * redundancy
            if val > best_val:
                best, best_val = s, val
        if best is None:
            break
        best.slot = "Also great" if picked else "Top pick"
        picked.append(best)

    order = {"Safe pick": 0, "Top pick": 0, "Also great": 1, "Hidden gem": 2, "Wildcard": 3}
    picked.sort(key=lambda s: (order.get(s.slot, 1), -s.score))
    return picked


def diversity_score(movies: list[MovieOut]) -> float:
    """1 - mean pairwise similarity (higher = more varied). Used by the evaluation."""
    if len(movies) < 2:
        return 0.0
    sims = [movie_similarity(a, b) for i, a in enumerate(movies) for b in movies[i + 1 :]]
    return round(1.0 - sum(sims) / len(sims), 3)
