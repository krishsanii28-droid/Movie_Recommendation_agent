"""Process-wide singletons: index, classifier, LLM and the agent."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import func, select

from moodreel.agent.agent import MoodReelAgent
from moodreel.agent.llm import get_llm
from moodreel.config import get_settings
from moodreel.db import Movie, init_db, session_scope
from moodreel.emotion.classifier import get_classifier
from moodreel.log import get_logger
from moodreel.search.index import get_index

logger = get_logger("services")


def ensure_catalog() -> None:
    """Auto-seed an empty database so a fresh checkout / deploy works out of the box."""
    init_db()
    with session_scope() as s:
        count = s.scalar(select(func.count()).select_from(Movie)) or 0
    if count == 0:
        from moodreel.data.pipeline import seed

        logger.info("empty catalogue - loading curated seed data")
        seed()


@lru_cache
def get_agent() -> MoodReelAgent:
    settings = get_settings()
    ensure_catalog()
    return MoodReelAgent(
        get_index(settings), get_classifier(settings), get_llm(settings), settings=settings
    )
