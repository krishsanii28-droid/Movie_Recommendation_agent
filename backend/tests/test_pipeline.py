import json
from pathlib import Path

import httpx
import pytest

from moodreel.config import Settings
from moodreel.data.normalize import canonical_provider, normalize_tmdb_movie
from moodreel.data.pipeline import load_seed_records
from moodreel.data.tmdb import TMDBClient, TMDBError
from moodreel.data.tone import derive_flags, derive_tones
from moodreel.search.index import embedding_text

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "tmdb_movie.json").read_text())


def test_normalize_tmdb_movie_maps_fields_and_region_providers():
    rec = normalize_tmdb_movie(FIXTURE, region="IN")
    assert rec["id"] == 575026
    assert rec["language"] == "ml"
    assert rec["year"] == 2019
    assert rec["rating"] == 8.0
    assert rec["genres"] == ["Drama", "Comedy"]
    assert "brothers" in rec["keywords"]
    assert [p["name"] for p in rec["providers"]["stream"]] == ["Prime Video"]
    assert [p["name"] for p in rec["providers"]["rent"]] == ["Apple TV"]
    assert rec["providers"]["link"].endswith("locale=IN")
    # derived tones / flags
    assert "funny" in rec["tones"] and "warm" in rec["tones"]
    assert "violence" in rec["content_flags"]  # from the "murder" keyword


def test_normalize_handles_missing_region_and_dates():
    data = {**FIXTURE, "release_date": "", "watch/providers": {"results": {}}}
    rec = normalize_tmdb_movie(data)
    assert rec["year"] is None
    assert rec["providers"]["stream"] == []


def test_provider_aliases():
    assert canonical_provider("Disney Plus Hotstar") == "JioHotstar"
    assert canonical_provider("Amazon Prime Video") == "Prime Video"
    assert canonical_provider("Some New App") == "Some New App"


def test_tone_and_flag_derivation():
    assert derive_tones(["Horror"], []) == ["scary", "eerie"]
    assert "horror" in derive_flags(["Horror"], [])
    assert derive_tones([], [], extra=["cozy", "not-a-tone"]) == ["cosy"]


def test_seed_catalogue_is_clean_and_covers_languages():
    records = load_seed_records()
    assert len(records) >= 100
    langs = {r["language"] for r in records}
    assert {"ml", "hi", "ta", "te", "en"} <= langs
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids))
    for r in records:
        assert r["overview"] and r["genres"] and r["tones"]
        assert r["providers"]["indicative"] is True


def test_embedding_text_contains_tones(search_index):
    movie = next(iter(search_index.movies.values()))
    text = embedding_text(movie)
    assert movie.title in text and "Mood and tone" in text


def _client(handler) -> TMDBClient:
    settings = Settings(tmdb_api_key="k", tmdb_requests_per_second=1000)
    return TMDBClient(settings, transport=httpx.MockTransport(handler))


async def test_tmdb_client_retries_on_429():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert request.url.params["api_key"] == "k"
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=FIXTURE)

    async with _client(handler) as client:
        data = await client.movie(575026)
    assert data["id"] == 575026 and calls["n"] == 2


async def test_tmdb_client_raises_on_4xx():
    async with _client(lambda r: httpx.Response(401, json={"status_message": "bad key"})) as c:
        with pytest.raises(TMDBError):
            await c.discover("ml")


def test_tmdb_client_requires_key():
    with pytest.raises(TMDBError):
        TMDBClient(Settings(tmdb_api_key="", tmdb_read_token=""))


async def test_ingest_end_to_end_with_mock_tmdb():
    from moodreel.data.pipeline import ingest
    from moodreel.db import Movie, session_scope

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/discover/movie"):
            return httpx.Response(200, json={"results": [{"id": 575026}], "total_pages": 1})
        return httpx.Response(200, json=FIXTURE)

    n = await ingest(["ml"], pages=1, client=_client(handler))
    assert n == 1
    with session_scope() as s:
        movie = s.get(Movie, 575026)
        assert movie is not None and movie.source == "tmdb"
        assert movie.providers["stream"][0]["name"] == "Prime Video"
        s.delete(movie)
