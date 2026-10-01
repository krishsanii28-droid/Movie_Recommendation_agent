"""Text embedders.

* ``SentenceTransformerEmbedder`` - the real thing (multilingual MiniLM by default).
* ``HashingEmbedder`` - dependency-free fallback: signed feature hashing over
  stemmed tokens and bigrams, with a small mood-synonym expansion so that
  "cozy after a long day" still lands near "warm, comforting, gentle".
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from moodreel.config import Settings, get_settings
from moodreel.log import get_logger

logger = get_logger("embeddings")


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


_STOP = set(
    "a an the and or but of to in on for with at by from is are was were be been am i me my "
    "we you your it its this that these those just some something want feel feeling like "
    "really very so too im i'm about into who what when where how than then there their".split()
)

# Canonical mood concepts: every synonym also emits the canonical token.
SYNONYMS: dict[str, list[str]] = {
    "cosy": ["cozy", "cosy", "comfort", "comforting", "snug", "hug", "soothing", "blanket"],
    "warm": ["warm", "wholesome", "heartwarming", "tender", "sweet", "kind"],
    "funny": ["funny", "comedy", "laugh", "hilarious", "humour", "humor", "silly", "goofy"],
    "light": ["light", "breezy", "easy", "fun", "lighthearted", "low-stakes", "chill"],
    "uplifting": ["uplifting", "uplift", "cheer", "hopeful", "hope", "inspiring", "feel-good"],
    "sad": ["sad", "melancholic", "melancholy", "cry", "tearjerker", "poignant", "bittersweet"],
    "tense": ["tense", "thriller", "suspense", "gripping", "edge", "thrilling"],
    "scary": ["scary", "horror", "creepy", "eerie", "spooky", "haunted", "ghost"],
    "romantic": ["romantic", "romance", "love", "date", "crush"],
    "think": ["think", "cerebral", "mind-bending", "thought-provoking", "puzzle", "twisty"],
    "energetic": ["energetic", "hype", "action", "fast-paced", "adrenaline", "pumped"],
    "party": ["party", "friends", "gang", "crowd", "singalong"],
    "calm": ["calm", "gentle", "quiet", "slow", "peaceful", "slow-burn"],
    "family": ["family", "kids", "family-friendly", "parents"],
    "nostalgic": ["nostalgic", "nostalgia", "childhood", "school", "reunion", "memories"],
    "dark": ["dark", "gritty", "violent", "intense", "hard-hitting", "brutal"],
}
_SYN_LOOKUP = {w: canon for canon, words in SYNONYMS.items() for w in words}


def _stem(token: str) -> str:
    for suffix in ("ing", "ness", "ed", "ly", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    raw = re.findall(r"[a-z0-9][a-z0-9'\-]*", text.lower())
    tokens: list[str] = []
    for tok in raw:
        if tok in _STOP:
            continue
        canon = _SYN_LOOKUP.get(tok)
        if canon:
            tokens.append(f"~{canon}")
        tokens.append(_stem(tok))
    return tokens


class HashingEmbedder:
    name = "hashing"

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _index(self, feature: str) -> tuple[int, float]:
        digest = hashlib.md5(feature.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % self.dim
        sign = 1.0 if digest[4] & 1 else -1.0
        return idx, sign

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = tokenize(text)
            feats = [(t, 2.0 if t.startswith("~") else 1.0) for t in tokens]
            feats += [(f"{a}|{b}", 0.5) for a, b in zip(tokens, tokens[1:], strict=False)]
            for feat, weight in feats:
                idx, sign = self._index(feat)
                out[row, idx] += sign * weight
            norm = np.linalg.norm(out[row])
            if norm > 0:
                out[row] /= norm
        return out


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import

        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


_EMBEDDER: Embedder | None = None


def get_embedder(settings: Settings | None = None) -> Embedder:
    """Return the configured embedder, falling back to hashing if unavailable."""
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    settings = settings or get_settings()
    if settings.embedding_backend in ("auto", "sentence-transformers"):
        try:
            _EMBEDDER = SentenceTransformerEmbedder(settings.embedding_model)
            logger.info("using sentence-transformers embedder: %s", settings.embedding_model)
            return _EMBEDDER
        except Exception as exc:  # ImportError, network, missing weights...
            if settings.embedding_backend == "sentence-transformers":
                raise
            logger.warning("sentence-transformers unavailable (%s); using hashing embedder", exc)
    _EMBEDDER = HashingEmbedder()
    return _EMBEDDER


def reset_embedder() -> None:
    global _EMBEDDER
    _EMBEDDER = None
