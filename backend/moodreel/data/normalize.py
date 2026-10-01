"""Turn raw TMDB responses (or seed records) into clean ``Movie`` rows."""

from __future__ import annotations

from typing import Any

from moodreel.data.tone import derive_flags, derive_tones

PROVIDER_ALIASES = {
    "amazon prime video": "Prime Video",
    "amazon prime video with ads": "Prime Video",
    "prime video": "Prime Video",
    "netflix": "Netflix",
    "netflix basic with ads": "Netflix",
    "hotstar": "JioHotstar",
    "disney plus hotstar": "JioHotstar",
    "disney+ hotstar": "JioHotstar",
    "jio hotstar": "JioHotstar",
    "jiohotstar": "JioHotstar",
    "jiocinema": "JioHotstar",
    "sony liv": "SonyLIV",
    "sonyliv": "SonyLIV",
    "zee5": "ZEE5",
    "sun nxt": "Sun NXT",
    "aha": "aha",
    "manoramamax": "ManoramaMAX",
    "apple tv": "Apple TV",
    "google play movies": "Google Play",
    "youtube": "YouTube",
}


def canonical_provider(name: str) -> str:
    return PROVIDER_ALIASES.get(name.strip().lower(), name.strip())


def _providers_from_tmdb(block: dict[str, Any] | None) -> dict[str, Any]:
    if not block:
        return {"stream": [], "rent": [], "buy": [], "link": None}

    def names(key: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in block.get(key, []) or []:
            name = canonical_provider(item.get("provider_name", ""))
            if name and name not in seen:
                seen.add(name)
                out.append({"name": name, "logo_path": item.get("logo_path")})
        return out

    stream = names("flatrate") + [p for p in names("free") + names("ads")]
    dedup: dict[str, dict[str, Any]] = {}
    for p in stream:
        dedup.setdefault(p["name"], p)
    return {
        "stream": list(dedup.values()),
        "rent": names("rent"),
        "buy": names("buy"),
        "link": block.get("link"),
    }


def normalize_tmdb_movie(data: dict[str, Any], region: str = "IN") -> dict[str, Any]:
    """Map a ``/movie/{id}?append_to_response=keywords,watch/providers`` payload."""
    genres = [g["name"] for g in data.get("genres", []) if g.get("name")]
    keywords = [k["name"] for k in (data.get("keywords") or {}).get("keywords", [])][:20]
    release = data.get("release_date") or ""
    year = int(release[:4]) if release[:4].isdigit() else None
    providers_block = ((data.get("watch/providers") or {}).get("results") or {}).get(region)
    return {
        "id": int(data["id"]),
        "title": data.get("title") or data.get("original_title") or "Untitled",
        "original_title": data.get("original_title") or "",
        "language": data.get("original_language") or "en",
        "year": year,
        "overview": (data.get("overview") or "").strip(),
        "genres": genres,
        "keywords": keywords,
        "tones": derive_tones(genres, keywords),
        "content_flags": derive_flags(genres, keywords),
        "runtime": data.get("runtime") or None,
        "rating": round(float(data.get("vote_average") or 0.0), 1),
        "vote_count": int(data.get("vote_count") or 0),
        "popularity": float(data.get("popularity") or 0.0),
        "poster_path": data.get("poster_path"),
        "providers": _providers_from_tmdb(providers_block),
        "source": "tmdb",
    }


def normalize_seed_movie(rec: dict[str, Any]) -> dict[str, Any]:
    """Map a curated seed record (see ``seed_movies.json``)."""
    genres = rec.get("genres", [])
    keywords = rec.get("keywords", [])
    return {
        "id": int(rec["id"]),
        "title": rec["title"],
        "original_title": rec.get("original_title", rec["title"]),
        "language": rec["language"],
        "year": rec.get("year"),
        "overview": rec.get("overview", ""),
        "genres": genres,
        "keywords": keywords,
        "tones": derive_tones(genres, keywords, extra=rec.get("tones")),
        "content_flags": derive_flags(genres, keywords, extra=rec.get("flags")),
        "runtime": rec.get("runtime"),
        "rating": float(rec.get("rating", 0.0)),
        "vote_count": int(rec.get("vote_count", 0)),
        "popularity": float(rec.get("popularity", rec.get("vote_count", 0) / 100)),
        "poster_path": rec.get("poster_path"),
        "providers": {
            "stream": [
                {"name": canonical_provider(p), "logo_path": None} for p in rec.get("providers", [])
            ],
            "rent": [],
            "buy": [],
            "link": None,
            "indicative": True,
        },
        "source": "seed",
    }
