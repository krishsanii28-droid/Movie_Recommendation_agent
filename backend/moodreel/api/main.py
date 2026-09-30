"""FastAPI app: streaming chat (SSE), group mode, surprise, feedback, watchlist, mood history.

Run: ``uvicorn moodreel.api.main:app --reload`` (from ``backend/``).
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from moodreel import __version__
from moodreel.agent import memory
from moodreel.config import get_settings
from moodreel.emotion.lexicon import STATES
from moodreel.emotion.mood import CHIPS
from moodreel.log import get_logger, setup_logging
from moodreel.schemas import (
    LANGUAGE_NAMES,
    AgentReply,
    ChatRequest,
    FeedbackRequest,
    GroupRequest,
    SurpriseRequest,
    WatchlistRequest,
)

logger = get_logger("api")

ATTRIBUTION = {
    "tmdb": "This product uses the TMDB API but is not endorsed or certified by TMDB.",
    "justwatch": "Streaming availability data provided by JustWatch (via TMDB).",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    from moodreel.services import get_agent

    agent = get_agent()  # warm up models + index
    logger.info("MoodReel ready: %d movies, llm=%s", len(agent.index.movies),
                agent.llm.name if agent.llm else "rules")
    yield


app = FastAPI(title="MoodReel API", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
    allow_methods=["*"],
    allow_headers=["*"],
)


def agent():
    from moodreel.services import get_agent

    return get_agent()


async def _sse(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    try:
        async for ev in events:
            yield f"event: {ev['type']}\ndata: {json.dumps(ev, default=str)}\n\n"
    except Exception:  # never leave the client hanging
        logger.exception("stream failed")
        err = {"type": "error", "text": "Something went wrong on my side — mind trying again?"}
        yield f"event: error\ndata: {json.dumps(err)}\n\n"


def _stream(events: AsyncIterator[dict[str, Any]]) -> StreamingResponse:
    return StreamingResponse(
        _sse(events), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------------------------------------------------------- meta


@app.get("/api/health")
def health() -> dict[str, Any]:
    a = agent()
    return {
        "status": "ok",
        "version": __version__,
        "movies": len(a.index.movies),
        "engines": {
            "embedder": a.index.embedder.name,
            "vector_store": a.index.store.name,
            "emotion": a.classifier.name,
            "llm": a.llm.name if a.llm else "rules",
        },
        "tmdb_configured": get_settings().tmdb_configured,
    }


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return {
        "chips": [{"id": cid, **{k: v for k, v in c.items() if k != "state"}} for cid, c in CHIPS.items()],
        "languages": [{"code": c, "name": n} for c, n in LANGUAGE_NAMES.items()],
        "attribution": ATTRIBUTION,
    }


# ------------------------------------------------------------------- agent


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return _stream(agent().stream(req))


@app.post("/api/chat/sync", response_model=AgentReply)
async def chat_sync(req: ChatRequest) -> AgentReply:
    a = agent()
    return await a.collect(a.stream(req))


@app.post("/api/group")
async def group(req: GroupRequest) -> StreamingResponse:
    return _stream(agent().stream_group(req))


@app.post("/api/group/sync", response_model=AgentReply)
async def group_sync(req: GroupRequest) -> AgentReply:
    a = agent()
    return await a.collect(a.stream_group(req))


@app.post("/api/surprise")
async def surprise(req: SurpriseRequest) -> StreamingResponse:
    return _stream(agent().stream_surprise(req))


@app.post("/api/surprise/sync", response_model=AgentReply)
async def surprise_sync(req: SurpriseRequest) -> AgentReply:
    a = agent()
    return await a.collect(a.stream_surprise(req))


# ------------------------------------------------------------ movies & memory


def _movie_or_404(movie_id: int):
    movie = agent().index.movies.get(movie_id)
    if movie is None:
        raise HTTPException(404, f"movie {movie_id} not found")
    return movie


@app.get("/api/movies/{movie_id}")
def movie(movie_id: int):
    return _movie_or_404(movie_id)


@app.post("/api/feedback")
def feedback(req: FeedbackRequest) -> dict[str, Any]:
    _movie_or_404(req.movie_id)
    memory.save_feedback(req.user_id, req.movie_id, req.signal)
    return {"ok": True}


@app.get("/api/users/{user_id}/history")
def history(user_id: str) -> dict[str, Any]:
    return memory.get_user_history(user_id)


@app.get("/api/watchlist")
def watchlist(user_id: str = Query(..., min_length=1, max_length=64)) -> list[dict[str, Any]]:
    movies = agent().index.movies
    return [
        {**item, "movie": movies[item["movie_id"]].model_dump()}
        for item in memory.get_watchlist(user_id) if item["movie_id"] in movies
    ]


@app.post("/api/watchlist")
def add_watchlist(req: WatchlistRequest) -> dict[str, Any]:
    _movie_or_404(req.movie_id)
    memory.add_to_watchlist(req.user_id, req.movie_id, req.note)
    return {"ok": True}


@app.delete("/api/watchlist/{movie_id}")
def remove_watchlist(movie_id: int, user_id: str = Query(..., min_length=1, max_length=64)) -> dict[str, Any]:
    memory.remove_from_watchlist(user_id, movie_id)
    return {"ok": True}


@app.get("/api/moods")
def moods(user_id: str = Query(..., min_length=1, max_length=64), days: int = Query(7, ge=1, le=90)) -> dict[str, Any]:
    entries = memory.mood_history(user_id, days)
    counts = Counter(e["primary"] for e in entries)
    by_day: dict[str, list[str]] = {}
    for e in entries:
        by_day.setdefault(e["created_at"][:10], []).append(e["primary"])
    top = counts.most_common(1)[0][0] if counts else None
    return {
        "entries": entries,
        "counts": dict(counts),
        "by_day": by_day,
        "labels": {k: {"label": s.label, "emoji": s.emoji} for k, s in STATES.items()},
        "top": top,
    }


# ------------------------------------------------ optional: serve the built SPA

_DIST = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[3] / "frontend" / "dist"))
if _DIST.is_dir() and (_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        target = _DIST / path
        if path and target.is_file() and _DIST in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(_DIST / "index.html")
