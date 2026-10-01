"""Feedback memory: per-session state (in memory) and per-user history (in SQL)."""

from __future__ import annotations

import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import delete, select

from moodreel.db import Feedback, MoodLog, WatchlistItem, init_db, session_scope, utcnow
from moodreel.schemas import MoodProfile
from moodreel.search.index import get_index

# How each feedback signal shifts a user's taste for the movie's tones/genres.
SIGNAL_WEIGHTS = {"loved": 1.0, "disliked": -0.6, "seen": 0.15, "too_slow": -0.2, "too_heavy": -0.2}
HEAVY_TONES = ("dark", "hard-hitting", "intense", "gritty", "melancholic")


@dataclass
class SessionState:
    id: str
    user_id: str
    history: list[dict[str, str]] = field(default_factory=list)
    asked_followup: bool = False
    pending_profile: MoodProfile | None = None
    last_profile: MoodProfile | None = None
    shown_ids: list[int] = field(default_factory=list)
    touched: float = field(default_factory=time.time)

    def add(self, role: str, text: str) -> None:
        self.history.append({"role": role, "content": text})
        self.history[:] = self.history[-20:]


class SessionStore:
    """Thread-safe in-memory session store with TTL. Swap for Redis to scale out."""

    def __init__(self, ttl_minutes: int = 120) -> None:
        self._ttl = ttl_minutes * 60
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str | None, user_id: str) -> SessionState:
        with self._lock:
            now = time.time()
            for sid in [s for s, st in self._sessions.items() if now - st.touched > self._ttl]:
                del self._sessions[sid]
            state = self._sessions.get(session_id or "")
            if state is None or state.user_id != user_id:
                state = SessionState(id=session_id or uuid.uuid4().hex, user_id=user_id)
                self._sessions[state.id] = state
            state.touched = now
            return state


def save_feedback(user_id: str, movie_id: int, signal: str) -> dict:
    init_db()
    with session_scope() as s:
        s.add(Feedback(user_id=user_id, movie_id=movie_id, signal=signal))
    return {"ok": True, "user_id": user_id, "movie_id": movie_id, "signal": signal}


def get_user_history(user_id: str) -> dict:
    """Seen / loved / disliked movies plus derived tone and genre affinities."""
    init_db()
    with session_scope() as s:
        rows = s.execute(
            select(Feedback.movie_id, Feedback.signal)
            .where(Feedback.user_id == user_id)
            .order_by(Feedback.created_at)
        ).all()
        watch = s.scalars(
            select(WatchlistItem.movie_id).where(WatchlistItem.user_id == user_id)
        ).all()
    movies = get_index().movies
    by_signal: dict[str, list[int]] = defaultdict(list)
    tone_aff: Counter[str] = Counter()
    genre_aff: Counter[str] = Counter()
    for movie_id, signal in rows:
        by_signal[signal].append(movie_id)
        movie = movies.get(movie_id)
        if not movie:
            continue
        w = SIGNAL_WEIGHTS.get(signal, 0.0)
        for tone in movie.tones:
            tone_aff[tone] += w
        for genre in movie.genres:
            genre_aff[genre] += w
        if signal == "too_slow":
            tone_aff["slow-burn"] -= 1.5
            tone_aff["gentle"] -= 0.4
            tone_aff["fast-paced"] += 0.6
        if signal == "too_heavy":
            for tone in HEAVY_TONES:
                tone_aff[tone] -= 1.0
    clamp = lambda c: {k: round(max(-3.0, min(3.0, v)), 2) for k, v in c.items() if abs(v) >= 0.1}  # noqa: E731
    loved = list(dict.fromkeys(by_signal["loved"]))
    return {
        "user_id": user_id,
        "seen": list(dict.fromkeys(by_signal["seen"] + loved)),
        "loved": loved,
        "disliked": list(dict.fromkeys(by_signal["disliked"])),
        "too_slow": list(dict.fromkeys(by_signal["too_slow"])),
        "too_heavy": list(dict.fromkeys(by_signal["too_heavy"])),
        "watchlist": list(watch),
        "tone_affinity": clamp(tone_aff),
        "genre_affinity": clamp(genre_aff),
        "loved_titles": [movies[i].title for i in loved if i in movies][-5:],
    }


def log_mood(user_id: str, profile: MoodProfile, text: str) -> None:
    init_db()
    with session_scope() as s:
        s.add(
            MoodLog(
                user_id=user_id,
                primary=profile.primary,
                secondary=profile.secondary,
                intensity=profile.intensity,
                energy=profile.energy,
                goal=profile.goal,
                text=text[:300],
            )
        )


def mood_history(user_id: str, days: int = 7) -> list[dict]:
    init_db()
    since = utcnow() - timedelta(days=days)
    with session_scope() as s:
        rows = s.scalars(
            select(MoodLog)
            .where(MoodLog.user_id == user_id, MoodLog.created_at >= since)
            .order_by(MoodLog.created_at)
        ).all()
        return [
            {
                "primary": r.primary,
                "secondary": r.secondary,
                "energy": r.energy,
                "goal": r.goal,
                "intensity": r.intensity,
                "text": r.text,
                "created_at": r.created_at.isoformat() + "Z",
            }
            for r in rows
        ]


def add_to_watchlist(user_id: str, movie_id: int, note: str = "") -> None:
    init_db()
    with session_scope() as s:
        exists = s.scalar(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id, WatchlistItem.movie_id == movie_id
            )
        )
        if not exists:
            s.add(WatchlistItem(user_id=user_id, movie_id=movie_id, note=note[:300]))


def remove_from_watchlist(user_id: str, movie_id: int) -> None:
    init_db()
    with session_scope() as s:
        s.execute(
            delete(WatchlistItem).where(
                WatchlistItem.user_id == user_id, WatchlistItem.movie_id == movie_id
            )
        )


def get_watchlist(user_id: str) -> list[dict]:
    init_db()
    with session_scope() as s:
        rows = s.scalars(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.added_at.desc())
        ).all()
        return [
            {"movie_id": r.movie_id, "note": r.note, "added_at": r.added_at.isoformat() + "Z"}
            for r in rows
        ]
