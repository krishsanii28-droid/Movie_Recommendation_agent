"""Process-wide singletons: index, classifier, LLM and the agent."""

from __future__ import annotations

from functools import lru_cache

from moodreel.agent.agent import MoodReelAgent
from moodreel.agent.llm import get_llm
from moodreel.config import get_settings
from moodreel.emotion.classifier import get_classifier
from moodreel.search.index import get_index


@lru_cache
def get_agent() -> MoodReelAgent:
    settings = get_settings()
    return MoodReelAgent(get_index(settings), get_classifier(settings), get_llm(settings), settings=settings)
