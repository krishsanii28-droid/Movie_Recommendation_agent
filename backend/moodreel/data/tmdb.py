"""Async TMDB client with rate limiting, retries and graceful failure."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from moodreel.config import Settings, get_settings
from moodreel.log import get_logger

logger = get_logger("tmdb")


class TMDBError(RuntimeError):
    pass


class RateLimiter:
    """Simple async token-bucket limiter (requests per second)."""

    def __init__(self, rate: float) -> None:
        self.interval = 1.0 / max(rate, 0.1)
        self._lock = asyncio.Lock()
        self._next = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if self._next > now:
                await asyncio.sleep(self._next - now)
                now = time.monotonic()
            self._next = now + self.interval


class TMDBClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 4,
    ) -> None:
        self.settings = settings or get_settings()
        if not self.settings.tmdb_configured:
            raise TMDBError("TMDB_API_KEY or TMDB_READ_TOKEN is not set (see .env.example)")
        headers = {"Accept": "application/json"}
        params: dict[str, str] = {}
        if self.settings.tmdb_read_token:
            headers["Authorization"] = f"Bearer {self.settings.tmdb_read_token}"
        else:
            params["api_key"] = self.settings.tmdb_api_key
        self._client = httpx.AsyncClient(
            base_url=self.settings.tmdb_base_url,
            headers=headers,
            params=params,
            timeout=httpx.Timeout(15.0),
            transport=transport,
        )
        self._limiter = RateLimiter(self.settings.tmdb_requests_per_second)
        self.max_retries = max_retries

    async def __aenter__(self) -> TMDBClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        backoff = 1.0
        for attempt in range(self.max_retries + 1):
            await self._limiter.wait()
            try:
                resp = await self._client.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise TMDBError(f"TMDB unreachable: {exc}") from exc
                logger.warning("TMDB transport error (%s), retrying in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == self.max_retries:
                    raise TMDBError(f"TMDB {resp.status_code} for {path}")
                wait = float(resp.headers.get("Retry-After", backoff))
                logger.warning("TMDB %s on %s, retrying in %.1fs", resp.status_code, path, wait)
                await asyncio.sleep(wait)
                backoff *= 2
                continue
            if resp.status_code >= 400:
                raise TMDBError(f"TMDB {resp.status_code} for {path}: {resp.text[:200]}")
            return resp.json()
        raise TMDBError("unreachable")  # pragma: no cover

    async def discover(self, language: str, page: int = 1, **filters: Any) -> dict[str, Any]:
        params = {
            "with_original_language": language,
            "sort_by": "vote_count.desc",
            "include_adult": "false",
            "vote_count.gte": 20 if language != "en" else 300,
            "page": page,
            **filters,
        }
        return await self.get("/discover/movie", **params)

    async def movie(self, movie_id: int) -> dict[str, Any]:
        return await self.get(f"/movie/{movie_id}", append_to_response="keywords,watch/providers")
