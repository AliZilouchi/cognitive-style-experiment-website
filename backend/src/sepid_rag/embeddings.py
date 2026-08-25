"""Embedding adapters. Hash embeddings exist only for plumbing tests."""

from __future__ import annotations

import hashlib
import re
from typing import Protocol, Sequence

import numpy as np

from .normalization import normalize_persian


class EmbeddingBackend(Protocol):
    model_identity: str

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


def _unit_rows(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)


class HashingEmbeddings:
    """Deterministic lexical vectors for tests; never valid study embeddings."""

    model_identity = "development-only-hashing"

    def __init__(self, dimension: int = 768) -> None:
        self.dimension = dimension

    def _embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"[\w\u0600-\u06ff]+", normalize_persian(text).lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = np.linalg.norm(vector)
        return vector if norm == 0 else vector / norm

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return np.vstack([self._embed(text) for text in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed(text)


class SentenceTransformerEmbeddings:
    def __init__(self, model: str, revision: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install the local-embeddings project extra") from exc
        self.model_identity = f"sentence-transformers:{model}@{revision}"
        self._model = SentenceTransformer(model, revision=revision)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        values = self._model.encode(list(texts), convert_to_numpy=True)
        return _unit_rows(np.asarray(values, dtype=np.float32))

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


class TogetherEmbeddings:
    def __init__(
        self,
        model: str,
        api_key: str,
        revision: str,
        expected_dimension: int,
    ) -> None:
        if not api_key:
            raise ValueError("TOGETHER_API_KEY is required")
        try:
            from together import Together
        except ImportError as exc:
            raise RuntimeError("The together package is not installed") from exc
        self.model_identity = f"together:{model}@{revision}:dim-{expected_dimension}"
        self._model = model
        self._expected_dimension = expected_dimension
        # Research requests are never silently replayed by the SDK.
        self._client = Together(api_key=api_key, max_retries=0, timeout=30)

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        response = self._client.embeddings.create(model=self._model, input=list(texts))
        ordered = sorted(response.data, key=lambda item: item.index)
        values = np.asarray([item.embedding for item in ordered], dtype=np.float32)
        if values.ndim != 2 or values.shape != (
            len(texts),
            self._expected_dimension,
        ):
            raise RuntimeError(
                "Hosted embedding response did not match the frozen count/dimension"
            )
        return _unit_rows(values)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed(texts)

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed([text])[0]


class PrefixedEmbeddings:
    """Apply model-specific prefixes and include them in the cached identity."""

    def __init__(self, backend, query_prefix: str, document_prefix: str) -> None:
        self.backend = backend
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        prefix_hash = hashlib.sha256(
            f"{query_prefix}\0{document_prefix}".encode("utf-8")
        ).hexdigest()[:10]
        self.model_identity = f"{backend.model_identity}:prefix-{prefix_hash}"

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self.backend.embed_documents(
            [self.document_prefix + text for text in texts]
        )

    def embed_query(self, text: str) -> np.ndarray:
        return self.backend.embed_query(self.query_prefix + text)


def create_embeddings(settings) -> EmbeddingBackend:
    if settings.embedding_provider == "hashing":
        backend = HashingEmbeddings(settings.embedding_dimension)
    elif settings.embedding_provider == "sentence_transformers":
        backend = SentenceTransformerEmbeddings(
            settings.embedding_model, settings.embedding_revision
        )
    elif settings.embedding_provider == "together":
        backend = TogetherEmbeddings(
            settings.embedding_model,
            settings.together_api_key,
            settings.embedding_revision,
            settings.embedding_dimension,
        )
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
    return PrefixedEmbeddings(
        backend,
        query_prefix=settings.query_prefix,
        document_prefix=settings.document_prefix,
    )
