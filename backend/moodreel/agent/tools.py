"""Agent tools: plain, testable functions + JSON schemas for LLM tool calling.

Both the LLM agent and the rule-based fallback call tools through
``ToolBox.call`` so every step is logged the same way.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any

from moodreel.agent import memory
from moodreel.agent.ranking import Scored, rank_candidates, select_diverse
from moodreel.emotion.classifier import EmotionClassifier
from moodreel.log import get_logger, log_step
from moodreel.schemas import MoodContext, MoodProfile
from moodreel.search.index import SearchIndex

logger = get_logger("tools")
VALID_SIGNALS = {"loved", "disliked", "seen", "too_slow", "too_heavy"}


# ---------------------------------------------------------------------------
# Standalone tool functions
# ---------------------------------------------------------------------------


def detect_emotion(classifier: EmotionClassifier, text: str) -> dict[str, Any]:
    return classifier.detect(text).to_dict()


def search_movies(
    index: SearchIndex,
    mood_query: str,
    filters: dict[str, Any] | None = None,
    *,
    base_profile: MoodProfile | None = None,
    history: dict | None = None,
    exclude: set[int] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Semantic search + mood-aware ranking + diversity selection."""
    filters = filters or {}
    profile = (base_profile or MoodProfile()).model_copy(deep=True)
    ctx = profile.context
    if filters.get("languages") is not None:
        ctx.languages = [lang for lang in filters["languages"] if lang]
    if filters.get("avoid"):
        ctx.avoid = sorted(set(ctx.avoid) | set(filters["avoid"]))
    if filters.get("max_runtime"):
        ctx.time_available = int(filters["max_runtime"])
    if filters.get("company"):
        ctx.company = filters["company"]
    for key in ("energy", "goal", "primary"):
        if filters.get(key):
            setattr(profile, key, filters[key])
    if filters.get("target_tones"):
        profile.target_tones = list(dict.fromkeys(filters["target_tones"] + profile.target_tones))[:7]
    limit = max(1, min(int(filters.get("limit", 4)), 5))
    excl = set(exclude or ()) | set(filters.get("exclude_ids", []))

    ranked, relaxed = rank_candidates(index, mood_query, profile, history, excl)
    picks = select_diverse(ranked, index, n=limit, rng=rng)
    return {
        "results": [
            {
                "movie_id": s.movie.id,
                "title": s.movie.title,
                "year": s.movie.year,
                "language": s.movie.language,
                "genres": s.movie.genres,
                "tones": s.movie.tones[:5],
                "runtime": s.movie.runtime,
                "rating": s.movie.rating,
                "slot": s.slot,
                "score": s.score,
                "matched_tones": s.matched,
                "overview": s.movie.overview[:220],
            }
            for s in picks
        ],
        "relaxed": relaxed,
        "_scored": picks,  # stripped before being shown to an LLM
    }


def get_movie_details(index: SearchIndex, movie_id: int) -> dict[str, Any]:
    movie = index.movies.get(int(movie_id))
    if movie is None:
        return {"error": f"unknown movie_id {movie_id}"}
    return movie.model_dump(exclude={"providers"})


def get_watch_providers(index: SearchIndex, movie_id: int, region: str = "IN") -> dict[str, Any]:
    movie = index.movies.get(int(movie_id))
    if movie is None:
        return {"error": f"unknown movie_id {movie_id}"}
    if region.upper() != index.settings.region:
        return {"region": region, "note": f"only {index.settings.region} providers are indexed"}
    return {"region": region.upper(), **movie.providers.model_dump()}


def get_user_history(user_id: str) -> dict[str, Any]:
    return memory.get_user_history(user_id)


def save_feedback(user_id: str, movie_id: int, signal: str) -> dict[str, Any]:
    if signal not in VALID_SIGNALS:
        return {"error": f"signal must be one of {sorted(VALID_SIGNALS)}"}
    return memory.save_feedback(user_id, int(movie_id), signal)


# ---------------------------------------------------------------------------
# JSON schemas (OpenAI / HF chat-template "tools" format)
# ---------------------------------------------------------------------------


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_SCHEMAS: list[dict] = [
    _fn("detect_emotion", "Score the user's text for emotions (fast classifier signal).",
        {"text": {"type": "string"}}, ["text"]),
    _fn("search_movies",
        "Semantic search over the movie index, ranked for the mood and diversified "
        "(safe pick, hidden gem, wildcard). Returns candidate movies with ids.",
        {
            "mood_query": {"type": "string", "description": "Natural-language description of the films wanted, e.g. 'warm, gentle, funny film about friendship'"},
            "filters": {
                "type": "object",
                "properties": {
                    "languages": {"type": "array", "items": {"type": "string", "enum": ["ml", "hi", "ta", "te", "en"]}},
                    "avoid": {"type": "array", "items": {"type": "string", "enum": ["violence", "horror", "heavy", "gore", "sexual content"]}},
                    "max_runtime": {"type": "integer"},
                    "target_tones": {"type": "array", "items": {"type": "string"}},
                    "energy": {"type": "string", "enum": ["low", "medium", "high"]},
                    "goal": {"type": "string", "enum": ["stay", "shift", "unclear"]},
                    "company": {"type": "string", "enum": ["alone", "partner", "family", "friends", "unknown"]},
                    "limit": {"type": "integer", "minimum": 3, "maximum": 5},
                },
            },
        }, ["mood_query"]),
    _fn("get_movie_details", "Full details for one movie.", {"movie_id": {"type": "integer"}}, ["movie_id"]),
    _fn("get_watch_providers", "Where a movie streams in a region (default India).",
        {"movie_id": {"type": "integer"}, "region": {"type": "string", "default": "IN"}}, ["movie_id"]),
    _fn("get_user_history", "The user's seen / loved / disliked movies and taste profile.",
        {"user_id": {"type": "string"}}, ["user_id"]),
    _fn("save_feedback", "Record feedback such as 'seen it', 'too slow' or 'loved it'.",
        {"user_id": {"type": "string"}, "movie_id": {"type": "integer"},
         "signal": {"type": "string", "enum": sorted(VALID_SIGNALS)}}, ["user_id", "movie_id", "signal"]),
    _fn("ask_followup", "Ask ONE short follow-up question when the mood goal is genuinely unclear. Ends the turn.",
        {"question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}}, ["question"]),
    _fn("recommend", "Final answer: 3-5 movie ids from search results, each with a 1-2 sentence reason tied to the user's words. Ends the turn.",
        {
            "message": {"type": "string", "description": "One or two warm sentences introducing the picks"},
            "mood": {"type": "object", "description": "Your reading of the mood: primary, secondary, energy, goal"},
            "picks": {"type": "array", "items": {"type": "object", "properties": {
                "movie_id": {"type": "integer"}, "reason": {"type": "string"}}, "required": ["movie_id", "reason"]}},
        }, ["message", "picks"]),
]
TERMINAL_TOOLS = {"ask_followup", "recommend"}


# ---------------------------------------------------------------------------
# ToolBox: binds tools to request context and logs each step
# ---------------------------------------------------------------------------


@dataclass
class ToolBox:
    index: SearchIndex
    classifier: EmotionClassifier
    user_id: str
    profile: MoodProfile | None = None
    exclude: set[int] = field(default_factory=set)
    history: dict | None = None
    rng: random.Random | None = None
    seen_candidates: dict[int, Scored] = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            result = self._dispatch(name, args)
        except Exception as exc:  # tool errors are reported to the agent, not raised
            logger.exception("tool %s failed", name)
            result = {"error": f"{type(exc).__name__}: {exc}"}
        ms = (time.perf_counter() - start) * 1000
        summary = {k: v for k, v in result.items() if not k.startswith("_")}
        log_step(logger, f"tool:{name}", args=args, ms=round(ms, 1), result=summary)
        self.steps.append(f"{name}({', '.join(f'{k}={v!r}' for k, v in args.items())[:120]})")
        return result

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "detect_emotion":
            return detect_emotion(self.classifier, args.get("text", ""))
        if name == "search_movies":
            if self.history is None:
                self.history = get_user_history(self.user_id)
            result = search_movies(
                self.index, args.get("mood_query", ""), args.get("filters") or {},
                base_profile=self.profile, history=self.history, exclude=self.exclude, rng=self.rng,
            )
            for s in result["_scored"]:
                self.seen_candidates[s.movie.id] = s
            return result
        if name == "get_movie_details":
            return get_movie_details(self.index, args["movie_id"])
        if name == "get_watch_providers":
            return get_watch_providers(self.index, args["movie_id"], args.get("region", "IN"))
        if name == "get_user_history":
            self.history = get_user_history(args.get("user_id") or self.user_id)
            return self.history
        if name == "save_feedback":
            return save_feedback(args.get("user_id") or self.user_id, args["movie_id"], args["signal"])
        return {"error": f"unknown tool {name}"}

    @staticmethod
    def for_llm(result: dict[str, Any]) -> str:
        """Serialise a tool result for the model (drop private keys, keep it short)."""
        return json.dumps({k: v for k, v in result.items() if not k.startswith("_")}, default=str)[:4000]


def profile_from_context(context: MoodContext) -> dict[str, Any]:
    return context.model_dump()
