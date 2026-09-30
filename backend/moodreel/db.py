"""Database layer (SQLAlchemy 2.0). SQLite in development, PostgreSQL-ready.

Switch to PostgreSQL by setting ``DATABASE_URL=postgresql+psycopg://...`` -
the models only use portable column types (JSON works on both).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from moodreel.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # TMDB id (seed ids >= 9e6)
    title: Mapped[str] = mapped_column(String(300), index=True)
    original_title: Mapped[str] = mapped_column(String(300), default="")
    language: Mapped[str] = mapped_column(String(8), index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    overview: Mapped[str] = mapped_column(Text, default="")
    genres: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    tones: Mapped[list] = mapped_column(JSON, default=list)
    content_flags: Mapped[list] = mapped_column(JSON, default=list)
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    popularity: Mapped[float] = mapped_column(Float, default=0.0)
    poster_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    providers: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="tmdb", index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    signal: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WatchlistItem(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_watchlist_user_movie"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    note: Mapped[str] = mapped_column(String(300), default="")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MoodLog(Base):
    __tablename__ = "mood_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    primary: Mapped[str] = mapped_column(String(32))
    secondary: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intensity: Mapped[float] = mapped_column(Float, default=0.5)
    energy: Mapped[str] = mapped_column(String(8), default="medium")
    goal: Mapped[str] = mapped_column(String(8), default="unclear")
    text: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(url: str | None = None) -> Engine:
    global _engine, _SessionLocal
    if _engine is None or url is not None:
        url = url or get_settings().database_url
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, future=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db(url: str | None = None) -> Engine:
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope() -> Iterator[Session]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
