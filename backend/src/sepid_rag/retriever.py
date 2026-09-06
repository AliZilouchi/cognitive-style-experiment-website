"""Task-scoped cosine/MMR retriever for the fixed semantic corpus."""

from __future__ import annotations

import hashlib
from dataclasses import replace
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
    source_ids: tuple[str, ...]
    chunk_id: str
    node_type: str
    topic: str
    entities: tuple[str, ...]
    parent_ids: tuple[str, ...]
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
        return len(
            {source_id for document in self.documents for source_id in document.source_ids}
        )

    def search(
        self,
        original_query: str,
        task_id: str | None = None,
        preferred_node_types: tuple[str, ...] = (),
        limit: int | None = None,
    ) -> list[SearchResult]:
        query = normalize_persian(original_query)
        query_tokens = set(query.split())
        vector = np.asarray(self.embeddings.embed_query(query), dtype=np.float32)
        semantic_scores = self._matrix @ vector
        task_eligible = [
            index
            for index, document in enumerate(self.documents)
            if task_id is None or task_id in document.task_ids
        ]
        typed_eligible = [
            index
            for index in task_eligible
            if not preferred_node_types
            or self.documents[index].node_type in preferred_node_types
        ]
        # Never turn a useful request into an empty retrieval merely because an
        # older corpus version lacks the preferred node type.
        eligible = typed_eligible or task_eligible
        if not eligible:
            return []

        result_limit = min(limit or self.top_k, self.top_k, len(eligible))

        # Blend semantic similarity with a small deterministic lexical signal.
        # Exact Persian names/numbers and manually-authored coverage terms should
        # survive even when the hosted embedding model paraphrases them poorly.
        def lexical_score(index: int) -> float:
            document = self.documents[index]
            document_tokens = set(normalize_persian(document.retrieval_text).split())
            overlap = len(query_tokens & document_tokens) / max(1, len(query_tokens))
            phrase_hits = sum(
                1
                for term in document.coverage_terms
                if normalize_persian(term) in query
            )
            return min(1.0, overlap + min(0.45, phrase_hits * 0.15))

        scores = np.asarray(
            [
                0.82 * ((float(semantic_scores[index]) + 1.0) / 2.0)
                + 0.18 * lexical_score(index)
                + (0.035 if self.documents[index].node_type in {"fact", "comparison"} else 0.0)
                + (0.015 if self.documents[index].node_type == "index" else 0.0)
                - (0.045 if self.documents[index].chunk_id.endswith("SOURCE-FALLBACK") else 0.0)
                for index in range(len(self.documents))
            ],
            dtype=np.float32,
        )

        best_score = max(float(scores[index]) for index in eligible)
        candidates = [
            index
            for index in eligible
            if float(scores[index]) >= best_score - self.score_margin
        ]
        def coverage_matches(index: int) -> int:
            matches = 0
            for raw_term in self.documents[index].coverage_terms:
                term = normalize_persian(raw_term)
                if (len(term) >= 4 and term in query) or term in query_tokens:
                    matches += 1
            return matches

        anchors = [index for index in eligible if coverage_matches(index)]
        comparison_anchors = [
            index for index in anchors if self.documents[index].node_type == "comparison"
        ]
        # When comparison anchors alone fill the retrieval budget (for example
        # weather + cost + attractions), prefer them over a thin index.  When
        # room remains, retain the index because it provides entity coverage.
        if len(comparison_anchors) >= result_limit:
            anchors = [
                index for index in anchors if self.documents[index].node_type != "index"
            ]
        anchors.sort(key=lambda index: (coverage_matches(index), float(scores[index])), reverse=True)
        selected: list[int] = anchors[:result_limit]
        source_counts: dict[str, int] = {}
        for index in selected:
            source_id = self.documents[index].source_id
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
        candidates = [index for index in candidates if index not in selected]

        while candidates and len(selected) < result_limit:
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
                source_ids=self.documents[index].source_ids,
                chunk_id=self.documents[index].chunk_id,
                node_type=self.documents[index].node_type,
                topic=self.documents[index].topic,
                entities=self.documents[index].entities,
                parent_ids=self.documents[index].parent_ids,
                relative_path=self.documents[index].relative_path,
                text=self.documents[index].text,
                score=float(scores[index]),
                rank=rank,
            )
            for rank, index in enumerate(selected, start=1)
        ]

    def search_many(
        self,
        queries: Sequence[str],
        task_id: str | None = None,
        preferred_node_types: tuple[str, ...] = (),
        limit: int | None = None,
    ) -> list[SearchResult]:
        """Retrieve each explicit sub-question and fuse results by reciprocal rank.

        A multi-part participant message no longer spends its entire retrieval
        budget on the easiest clause. Results remain bounded by the same contract.
        """
        cleaned = [item.strip() for item in queries if item and item.strip()]
        if not cleaned:
            return []
        if len(cleaned) == 1:
            return self.search(cleaned[0], task_id, preferred_node_types, limit)

        fused: dict[str, tuple[SearchResult, float]] = {}
        per_query_results: list[list[SearchResult]] = []
        per_query_limit = min(limit or self.top_k, self.top_k)
        for query in cleaned[:4]:
            items = self.search(
                query,
                task_id,
                preferred_node_types=preferred_node_types,
                limit=per_query_limit,
            )
            per_query_results.append(items)
            for item in items:
                previous = fused.get(item.chunk_id)
                fused_score = (previous[1] if previous else 0.0) + 1.0 / (60 + item.rank)
                representative = item if previous is None or item.score > previous[0].score else previous[0]
                fused[item.chunk_id] = (representative, fused_score)

        result_limit = min(limit or self.top_k, self.top_k, len(fused))
        # Reserve one relevant candidate for each explicit sub-question before
        # filling the remaining budget by fused rank.
        reserved_ids: list[str] = []
        for items in per_query_results:
            first_new = next((item for item in items if item.chunk_id not in reserved_ids), None)
            if first_new is not None:
                reserved_ids.append(first_new.chunk_id)
        ranked = sorted(fused.values(), key=lambda pair: pair[1], reverse=True)
        reserved = [fused[chunk_id] for chunk_id in reserved_ids[:result_limit]]
        ordered = reserved + [pair for pair in ranked if pair[0].chunk_id not in reserved_ids]
        ordered = ordered[:result_limit]
        return [replace(item, rank=rank) for rank, (item, _) in enumerate(ordered, start=1)]
