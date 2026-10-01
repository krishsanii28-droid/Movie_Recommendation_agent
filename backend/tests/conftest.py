"""Test setup: an isolated SQLite DB + in-memory vector index seeded with the curated catalogue."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("EMBEDDING_BACKEND", "hashing")
os.environ.setdefault("EMOTION_BACKEND", "lexicon")
os.environ.setdefault("VECTOR_BACKEND", "memory")
os.environ.setdefault("LLM_BACKEND", "none")
os.environ.setdefault("TMDB_API_KEY", "")


@pytest.fixture(scope="session", autouse=True)
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    from moodreel.config import get_settings

    get_settings.cache_clear()
    from moodreel import db
    from moodreel.data import pipeline
    from moodreel.search import index

    db.init_db(os.environ["DATABASE_URL"])
    pipeline.upsert_movies(pipeline.load_seed_records())
    index.reset_index()
    index.get_index()
    yield


@pytest.fixture()
def search_index():
    from moodreel.search.index import get_index

    return get_index()
