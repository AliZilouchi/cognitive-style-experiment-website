"""Small transparent cosine retriever for the 18-document fixed corpus."""

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
    ) -> None:
        if not documents:
            raise ValueError("Cannot build an index from an empty corpus")
        self.documents = list(documents)
        self.embeddings = embeddings
        self.top_k = min(top_k, len(self.documents))
        self._matrix = self._load_or_build_matrix(index_dir)
        if self._matrix.ndim != 2 or len(self._matrix) != len(self.documents):
            raise ValueError("Embedding backend returned an invalid document matrix")

    def _fingerprint(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.embeddings.model_identity.encode("utf-8"))
        for document in self.documents:
            digest.update(document.source_id.encode("utf-8"))
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

    def search(self, original_query: str) -> list[SearchResult]:
        query = normalize_persian(original_query)
        vector = np.asarray(self.embeddings.embed_query(query), dtype=np.float32)
        scores = self._matrix @ vector
        indices = np.argsort(scores)[::-1][: self.top_k]
        return [
            SearchResult(
                source_id=self.documents[index].source_id,
                relative_path=self.documents[index].relative_path,
                text=self.documents[index].text,
                score=float(scores[index]),
                rank=rank,
            )
            for rank, index in enumerate(indices, start=1)
        ]
