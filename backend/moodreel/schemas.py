"""Shared pydantic models: movies, mood profiles, recommendations and API payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LANGUAGE_NAMES: dict[str, str] = {
    "ml": "Malayalam",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "en": "English",
}

Energy = Literal["low", "medium", "high"]
MoodGoal = Literal["stay", "shift", "unclear"]
Company = Literal["alone", "partner", "family", "friends", "unknown"]
FeedbackSignal = Literal["loved", "disliked", "seen", "too_slow", "too_heavy"]


class Provider(BaseModel):
    name: str
    logo_url: str | None = None


class WatchProviders(BaseModel):
    stream: list[Provider] = Field(default_factory=list)
    rent: list[Provider] = Field(default_factory=list)
    buy: list[Provider] = Field(default_factory=list)
    link: str | None = None
    indicative: bool = False  # True for seed data (not live JustWatch data)


class MovieOut(BaseModel):
    id: int
    title: str
    year: int | None = None
    language: str
    language_name: str
    overview: str = ""
    genres: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    tones: list[str] = Field(default_factory=list)
    content_flags: list[str] = Field(default_factory=list)
    runtime: int | None = None
    rating: float = 0.0
    vote_count: int = 0
    poster_url: str | None = None
    providers: WatchProviders = Field(default_factory=WatchProviders)


class MoodContext(BaseModel):
    company: Company = "unknown"
    time_available: int | None = None  # minutes
    languages: list[str] = Field(default_factory=list)  # empty = any
    avoid: list[str] = Field(default_factory=list)  # content flags: violence, horror, heavy, ...


class MoodProfile(BaseModel):
    """The agent's structured understanding of how the user feels and what they want."""

    primary: str = "neutral"
    secondary: str | None = None
    intensity: float = 0.5
    energy: Energy = "medium"
    goal: MoodGoal = "unclear"
    context: MoodContext = Field(default_factory=MoodContext)
    target_tones: list[str] = Field(default_factory=list)
    distress: Literal["none", "elevated", "crisis"] = "none"
    raw_emotions: dict[str, float] = Field(default_factory=dict)
    summary: str = ""  # short human-readable description, e.g. "tired · lonely · wants a lift"
    key_phrase: str = ""  # the user's own words we tie reasons back to
    vague: bool = False


class Why(BaseModel):
    matched_tones: list[str] = Field(default_factory=list)
    mood_goal: str = ""
    score: float = 0.0
    notes: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    movie: MovieOut
    reason: str
    slot: str = "Pick"  # Safe pick / Hidden gem / Wildcard / Also great
    why: Why = Field(default_factory=Why)


class CareMessage(BaseModel):
    text: str
    helplines: list[dict[str, str]] = Field(default_factory=list)


class AgentReply(BaseModel):
    """Complete (non-streamed) agent response."""

    session_id: str
    message: str
    mood: MoodProfile | None = None
    question: str | None = None
    options: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    care: CareMessage | None = None
    steps: list[str] = Field(default_factory=list)
    engine: str = "rules"  # rules | llm


# ---------------------------------------------------------------------------
# API request payloads
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str | None = None
    message: str = Field(default="", max_length=2000)
    chip: str | None = None
    languages: list[str] = Field(default_factory=list)
    energy: float | None = Field(default=None, ge=0, le=1)  # 0 low .. 1 high
    mood_shift: float | None = Field(default=None, ge=-1, le=1)  # -1 stay .. +1 change


class GroupMember(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    mood: str = Field(min_length=1, max_length=500)


class GroupRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str | None = None
    members: list[GroupMember] = Field(min_length=2, max_length=8)
    languages: list[str] = Field(default_factory=list)


class SurpriseRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str | None = None
    languages: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    movie_id: int
    signal: FeedbackSignal
    session_id: str | None = None


class WatchlistRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    movie_id: int
    note: str = ""
