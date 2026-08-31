"""Task-scoped cosine/MMR retriever for the fixed semantic corpus."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from .corpus import CorpusDocument
from .embeddings import EmbeddingBackend
from .normalization import normalize_persian


@dataclass(frozen=True)
class SearchResult:
    source_id: str
    chunk_id: str
    topic: str
    relative_path: str
    text: str
    score: float
    rank: int


class CorpusRetriever:
    def __init__(
        self,
        documents: Sequence[CorpusDocument],
        embeddings: EmbeddingBackend,
        top_k: int,
        index_dir: Path | None = None,
        score_margin: float = 0.12,
        max_chunks_per_source: int = 2,
        mmr_lambda: float = 0.75,
    ) -> None:
        if not documents:
            raise ValueError("Cannot build an index from an empty corpus")
        self.documents = list(documents)
        self.embeddings = embeddings
        self.top_k = min(top_k, len(self.documents))
        self.score_margin = score_margin
        self.max_chunks_per_source = max_chunks_per_source
        self.mmr_lambda = mmr_lambda
        self._matrix = self._load_or_build_matrix(index_dir)
        if self._matrix.ndim != 2 or len(self._matrix) != len(self.documents):
            raise ValueError("Embedding backend returned an invalid document matrix")

    def _fingerprint(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.embeddings.model_identity.encode("utf-8"))
        for document in self.documents:
            digest.update(document.chunk_id.encode("utf-8"))
            digest.update(document.retrieval_text.encode("utf-8"))
        return digest.hexdigest()[:20]

    def _load_or_build_matrix(self, index_dir: Path | None) -> np.ndarray:
        cache_path = None
        if index_dir is not None:
            index_dir.mkdir(parents=True, exist_ok=True)
            cache_path = index_dir / f"documents-{self._fingerprint()}.npz"
            if cache_path.is_file():
                with np.load(cache_path, allow_pickle=False) as cached:
                    matrix = np.asarray(cached["embeddings"], dtype=np.float32)
                if matrix.ndim == 2 and len(matrix) == len(self.documents):
                    return matrix

        matrix = np.asarray(
            self.embeddings.embed_documents(
                [document.retrieval_text for document in self.documents]
            ),
            dtype=np.float32,
        )
        if cache_path is not None:
            np.savez_compressed(cache_path, embeddings=matrix)
        return matrix

    @property
    def source_count(self) -> int:
        return len({document.source_id for document in self.documents})

    def search(self, original_query: str, task_id: str | None = None) -> list[SearchResult]:
        query = normalize_persian(original_query)
        vector = np.asarray(self.embeddings.embed_query(query), dtype=np.float32)
        scores = self._matrix @ vector
        eligible = [
            index
            for index, document in enumerate(self.documents)
            if task_id is None or task_id in document.task_ids
        ]
        if not eligible:
            return []

        best_score = max(float(scores[index]) for index in eligible)
        candidates = [
            index
            for index in eligible
            if float(scores[index]) >= best_score - self.score_margin
        ]
        selected: list[int] = []
        source_counts: dict[str, int] = {}

        while candidates and len(selected) < self.top_k:
            allowed = [
                index
                for index in candidates
                if source_counts.get(self.documents[index].source_id, 0)
                < self.max_chunks_per_source
            ]
            if not allowed:
                break

            def mmr_score(index: int) -> float:
                redundancy = 0.0
                if selected:
                    redundancy = max(
                        float(self._matrix[index] @ self._matrix[chosen])
                        for chosen in selected
                    )
                return (
                    self.mmr_lambda * float(scores[index])
                    - (1.0 - self.mmr_lambda) * redundancy
                )

            chosen = max(allowed, key=mmr_score)
            selected.append(chosen)
            candidates.remove(chosen)
            source_id = self.documents[chosen].source_id
            source_counts[source_id] = source_counts.get(source_id, 0) + 1

        return [
            SearchResult(
                source_id=self.documents[index].source_id,
                chunk_id=self.documents[index].chunk_id,
                topic=self.documents[index].topic,
                relative_path=self.documents[index].relative_path,
                text=self.documents[index].text,
                score=float(scores[index]),
                rank=rank,
            )
            for rank, index in enumerate(selected, start=1)
        ]
