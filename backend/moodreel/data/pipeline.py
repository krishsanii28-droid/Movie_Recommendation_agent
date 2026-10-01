"""Data pipeline: TMDB -> clean records in SQL -> vector index.

Usage (from ``backend/``)::

    python -m moodreel.data.pipeline seed                 # offline curated catalogue
    python -m moodreel.data.pipeline ingest --pages 5     # TMDB discover per language
    python -m moodreel.data.pipeline refresh --days 45    # new releases + provider changes
    python -m moodreel.data.pipeline stats
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select

from moodreel.config import get_settings
from moodreel.data.normalize import normalize_seed_movie, normalize_tmdb_movie
from moodreel.data.tmdb import TMDBClient, TMDBError
from moodreel.db import Movie, init_db, session_scope, utcnow
from moodreel.log import get_logger, setup_logging

logger = get_logger("pipeline")
SEED_PATH = Path(__file__).with_name("seed_movies.json")


def load_seed_records(path: Path = SEED_PATH) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [normalize_seed_movie(rec) for rec in doc["movies"]]


def upsert_movies(records: list[dict[str, Any]]) -> int:
    """Insert or update movie rows. Returns the number of rows written."""
    count = 0
    with session_scope() as session:
        for rec in records:
            movie = session.get(Movie, rec["id"])
            if movie is None:
                session.add(Movie(**rec))
            else:
                for key, value in rec.items():
                    setattr(movie, key, value)
                movie.updated_at = utcnow()
            count += 1
    return count


def seed() -> int:
    init_db()
    n = upsert_movies(load_seed_records())
    logger.info("seeded %d curated movies", n)
    return n


async def _fetch_details(
    client: TMDBClient, ids: list[int], concurrency: int = 8
) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)
    region = client.settings.region

    async def one(movie_id: int) -> dict[str, Any] | None:
        async with sem:
            try:
                return normalize_tmdb_movie(await client.movie(movie_id), region)
            except TMDBError as exc:
                logger.warning("skip movie %s: %s", movie_id, exc)
                return None

    results = await asyncio.gather(*(one(i) for i in ids))
    return [r for r in results if r and r["overview"]]


async def ingest(
    languages: list[str],
    pages: int = 3,
    replace_seed: bool = False,
    client: TMDBClient | None = None,
    **discover_filters: Any,
) -> int:
    init_db()
    async with client or TMDBClient() as client:
        ids: list[int] = []
        for lang in languages:
            for page in range(1, pages + 1):
                data = await client.discover(lang, page=page, **discover_filters)
                ids.extend(int(r["id"]) for r in data.get("results", []))
                if page >= int(data.get("total_pages", 1)):
                    break
            logger.info("discovered %s: %d ids so far", lang, len(ids))
        records = await _fetch_details(client, list(dict.fromkeys(ids)))
    if replace_seed and records:
        with session_scope() as session:
            session.execute(delete(Movie).where(Movie.source == "seed"))
        logger.info("removed seed catalogue (replaced by live TMDB data)")
    n = upsert_movies(records)
    logger.info("ingested %d movies from TMDB", n)
    return n


async def refresh(
    languages: list[str], days: int = 45, stale_days: int = 7, limit: int = 300
) -> int:
    """Pick up new releases and re-check watch providers for stale rows."""
    since = (date.today() - timedelta(days=days)).isoformat()
    n_new = await ingest(
        languages, pages=2, **{"primary_release_date.gte": since, "vote_count.gte": 5}
    )
    cutoff = utcnow() - timedelta(days=stale_days)
    with session_scope() as session:
        stale = session.scalars(
            select(Movie.id)
            .where(Movie.source == "tmdb", Movie.updated_at < cutoff)
            .order_by(Movie.popularity.desc())
            .limit(limit)
        ).all()
    async with TMDBClient() as client:
        records = await _fetch_details(client, list(stale))
    n_updated = upsert_movies(records)
    logger.info("refresh: %d new/updated releases, %d provider refreshes", n_new, n_updated)
    return n_new + n_updated


def stats() -> dict[str, Any]:
    init_db()
    with session_scope() as session:
        rows = session.execute(
            select(Movie.language, Movie.source, func.count()).group_by(
                Movie.language, Movie.source
            )
        ).all()
    return {f"{lang}/{src}": n for lang, src, n in rows}


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    parser = argparse.ArgumentParser(prog="moodreel.data.pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="load the curated offline catalogue")
    p_ing = sub.add_parser("ingest", help="pull movies from TMDB")
    p_ing.add_argument("--languages", nargs="+", default=settings.languages)
    p_ing.add_argument("--pages", type=int, default=3)
    p_ing.add_argument("--replace-seed", action="store_true")
    p_ref = sub.add_parser("refresh", help="new releases + provider changes")
    p_ref.add_argument("--languages", nargs="+", default=settings.languages)
    p_ref.add_argument("--days", type=int, default=45)
    sub.add_parser("stats")
    for p in sub.choices.values():
        p.add_argument("--no-index", action="store_true", help="skip rebuilding the vector index")
    args = parser.parse_args(argv)

    try:
        if args.cmd == "seed":
            seed()
        elif args.cmd == "ingest":
            asyncio.run(ingest(args.languages, args.pages, args.replace_seed))
        elif args.cmd == "refresh":
            asyncio.run(refresh(args.languages, args.days))
        elif args.cmd == "stats":
            print(json.dumps(stats(), indent=2))
            return
    except TMDBError as exc:
        logger.error("TMDB unavailable: %s. Tip: `seed` works offline.", exc)
        raise SystemExit(1) from exc

    if not args.no_index:
        from moodreel.search.index import build_index

        build_index()


if __name__ == "__main__":
    main()
