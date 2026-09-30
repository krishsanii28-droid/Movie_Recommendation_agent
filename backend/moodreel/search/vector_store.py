"""Vector stores: ChromaDB (persistent) with an in-memory numpy fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from moodreel.log import get_logger

logger = get_logger("vectors")


@dataclass
class Hit:
    movie_id: int
    score: float  # cosine similarity in [-1, 1]


class VectorStore(Protocol):
    name: str

    def upsert(self, ids: list[int], vectors: np.ndarray, metadatas: list[dict]) -> None: ...

    def query(self, vector: np.ndarray, k: int, where: dict | None = None) -> list[Hit]: ...

    def count(self) -> int: ...

    def reset(self) -> None: ...


class MemoryStore:
    name = "memory"

    def __init__(self) -> None:
        self._ids: list[int] = []
        self._vecs: np.ndarray | None = None
        self._meta: list[dict] = []

    def upsert(self, ids: list[int], vectors: np.ndarray, metadatas: list[dict]) -> None:
        index = {mid: i for i, mid in enumerate(self._ids)}
        for mid, vec, meta in zip(ids, vectors, metadatas):
            if mid in index:
                assert self._vecs is not None
                self._vecs[index[mid]] = vec
                self._meta[index[mid]] = meta
            else:
                self._ids.append(mid)
                self._meta.append(meta)
                row = vec[None, :]
                self._vecs = row if self._vecs is None else np.vstack([self._vecs, row])
                index[mid] = len(self._ids) - 1

    def query(self, vector: np.ndarray, k: int, where: dict | None = None) -> list[Hit]:
        if self._vecs is None:
            return []
        sims = self._vecs @ vector
        order = np.argsort(-sims)
        hits: list[Hit] = []
        for i in order:
            if where and not _match(self._meta[i], where):
                continue
            hits.append(Hit(self._ids[i], float(sims[i])))
            if len(hits) >= k:
                break
        return hits

    def count(self) -> int:
        return len(self._ids)

    def reset(self) -> None:
        self.__init__()


def _match(meta: dict, where: dict) -> bool:
    for key, cond in where.items():
        value = meta.get(key)
        if isinstance(cond, dict) and "$in" in cond:
            if value not in cond["$in"]:
                return False
        elif value != cond:
            return False
    return True


class ChromaStore:
    name = "chroma"

    def __init__(self, path: str, collection: str = "movies") -> None:
        import chromadb  # optional dependency

        self._client = chromadb.PersistentClient(path=path)
        self._collection_name = collection
        self._col = self._client.get_or_create_collection(
            collection, metadata={"hnsw:space": "cosine"}
        )

    def upsert(self, ids: list[int], vectors: np.ndarray, metadatas: list[dict]) -> None:
        batch = 500
        for start in range(0, len(ids), batch):
            self._col.upsert(
                ids=[str(i) for i in ids[start : start + batch]],
                embeddings=vectors[start : start + batch].tolist(),
                metadatas=metadatas[start : start + batch],
            )

    def query(self, vector: np.ndarray, k: int, where: dict | None = None) -> list[Hit]:
        n = self.count()
        if n == 0:
            return []
        res = self._col.query(
            query_embeddings=[vector.tolist()], n_results=min(k, n), where=where or None
        )
        ids = res["ids"][0]
        dists = res["distances"][0]
        return [Hit(int(i), 1.0 - float(d)) for i, d in zip(ids, dists)]

    def count(self) -> int:
        return int(self._col.count())

    def reset(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._col = self._client.get_or_create_collection(
            self._collection_name, metadata={"hnsw:space": "cosine"}
        )
