"""Movie catalogue cache + semantic index (embedding text -> vector store)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from sqlalchemy import select

from moodreel.config import Settings, get_settings
from moodreel.db import Movie, init_db, session_scope
from moodreel.log import get_logger
from moodreel.schemas import LANGUAGE_NAMES, MovieOut, Provider, WatchProviders
from moodreel.search.embeddings import Embedder, get_embedder
from moodreel.search.vector_store import ChromaStore, Hit, MemoryStore, VectorStore

logger = get_logger("index")


def embedding_text(movie: Movie | MovieOut) -> str:
    """Overview + genres + keywords + tone descriptors - what the vector index sees."""
    lang = LANGUAGE_NAMES.get(movie.language, movie.language)
    parts = [
        f"{movie.title} ({movie.year or 'n/a'}), a {lang} film.",
        movie.overview,
        f"Genres: {', '.join(movie.genres)}.",
        f"Themes: {', '.join(movie.keywords[:12])}.",
        f"Mood and tone: {', '.join(movie.tones)}.",
    ]
    return " ".join(p for p in parts if p)


def to_movie_out(movie: Movie, settings: Settings | None = None) -> MovieOut:
    settings = settings or get_settings()
    prov = movie.providers or {}

    def plist(key: str) -> list[Provider]:
        return [
            Provider(
                name=p["name"],
                logo_url=f"{settings.tmdb_image_base}/w92{p['logo_path']}"
                if p.get("logo_path")
                else None,
            )
            for p in prov.get(key, [])
        ]

    link = prov.get("link")
    if not link:
        link = "https://www.justwatch.com/in/search?q=" + quote_plus(movie.title)
    return MovieOut(
        id=movie.id,
        title=movie.title,
        year=movie.year,
        language=movie.language,
        language_name=LANGUAGE_NAMES.get(movie.language, movie.language.upper()),
        overview=movie.overview,
        genres=list(movie.genres or []),
        keywords=list(movie.keywords or []),
        tones=list(movie.tones or []),
        content_flags=list(movie.content_flags or []),
        runtime=movie.runtime,
        rating=movie.rating,
        vote_count=movie.vote_count,
        poster_url=f"{settings.tmdb_image_base}/w342{movie.poster_path}"
        if movie.poster_path
        else None,
        providers=WatchProviders(
            stream=plist("stream"),
            rent=plist("rent"),
            buy=plist("buy"),
            link=link,
            indicative=bool(prov.get("indicative")),
        ),
    )


def get_vector_store(settings: Settings, embedder: Embedder) -> VectorStore:
    if settings.vector_backend in ("auto", "chroma"):
        try:
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", embedder.name).strip("-").lower()[:40]
            store = ChromaStore(settings.chroma_dir, collection=f"movies-{slug}")
            logger.info("using ChromaDB vector store at %s", settings.chroma_dir)
            return store
        except Exception as exc:
            if settings.vector_backend == "chroma":
                raise
            logger.warning("ChromaDB unavailable (%s); using in-memory store", exc)
    return MemoryStore()


@dataclass
class SearchIndex:
    """Holds the catalogue in memory and answers semantic queries."""

    embedder: Embedder
    store: VectorStore
    settings: Settings
    movies: dict[int, MovieOut] = field(default_factory=dict)

    def load_catalog(self) -> None:
        init_db()
        with session_scope() as session:
            rows = session.scalars(select(Movie)).all()
            self.movies = {m.id: to_movie_out(m, self.settings) for m in rows}
        logger.info("catalogue loaded: %d movies", len(self.movies))

    def rebuild(self) -> int:
        self.load_catalog()
        self.store.reset()
        if not self.movies:
            return 0
        ids = list(self.movies)
        vectors = self.embedder.embed([embedding_text(self.movies[i]) for i in ids])
        metas = [
            {"language": self.movies[i].language, "year": self.movies[i].year or 0} for i in ids
        ]
        self.store.upsert(ids, vectors, metas)
        logger.info(
            "indexed %d movies with %s into %s", len(ids), self.embedder.name, self.store.name
        )
        return len(ids)

    def ensure_ready(self) -> None:
        if not self.movies:
            self.load_catalog()
        if self.store.count() != len(self.movies):
            self.rebuild()

    def search(self, query: str, k: int = 40, languages: list[str] | None = None) -> list[Hit]:
        vector = self.embedder.embed([query])[0]
        where = {"language": {"$in": languages}} if languages else None
        return self.store.query(vector, k=k, where=where)


_INDEX: SearchIndex | None = None


def get_index(settings: Settings | None = None) -> SearchIndex:
    global _INDEX
    if _INDEX is None:
        settings = settings or get_settings()
        embedder = get_embedder(settings)
        _INDEX = SearchIndex(embedder, get_vector_store(settings, embedder), settings)
        _INDEX.ensure_ready()
    return _INDEX


def reset_index() -> None:
    global _INDEX
    _INDEX = None


def build_index() -> int:
    reset_index()
    settings = get_settings()
    embedder = get_embedder(settings)
    index = SearchIndex(embedder, get_vector_store(settings, embedder), settings)
    return index.rebuild()


if __name__ == "__main__":
    from moodreel.log import setup_logging

    setup_logging()
    print(f"indexed {build_index()} movies")
