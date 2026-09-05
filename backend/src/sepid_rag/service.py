"""Application assembly shared by API, CLI, tests, and Colab."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .corpus import load_allowlisted_corpus
from .embeddings import create_embeddings
from .graph import build_graph
from .knowledge_scope import KnowledgeScope
from .prompts import SYSTEM_PROMPT_VERSION, VERIFIER_PROMPT_VERSION
from .retriever import CorpusRetriever


@dataclass
class RagService:
    settings: Settings
    retriever: CorpusRetriever
    graph: object
    knowledge_scope: KnowledgeScope

    @classmethod
    def create(cls, settings: Settings | None = None) -> "RagService":
        resolved = settings or Settings.from_env()
        documents = load_allowlisted_corpus(resolved.corpus_root)
        knowledge_scope = KnowledgeScope.load(resolved.corpus_root)
        embeddings = create_embeddings(resolved)
        retriever = CorpusRetriever(
            documents,
            embeddings,
            resolved.top_k,
            index_dir=resolved.index_dir,
            score_margin=resolved.retrieval_score_margin,
            max_chunks_per_source=resolved.max_chunks_per_source,
            mmr_lambda=resolved.mmr_lambda,
        )
        return cls(
            resolved,
            retriever,
            build_graph(retriever, resolved, knowledge_scope),
            knowledge_scope,
        )

    def chat(
        self,
        query: str,
        task_id: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict:
        original_query = query.strip()
        if not original_query:
            raise ValueError("query cannot be empty")
        result = self.graph.invoke(
            {"query": original_query, "task_id": task_id, "history": history or []}
        )
        retrieved = result["retrieved"]
        return {
            "answer": result["answer"],
            "sources": [
                {
                    "source_id": item.source_id,
                    "source_ids": list(item.source_ids),
                    "chunk_id": item.chunk_id,
                    "node_type": item.node_type,
                    "topic": item.topic,
                    "relative_path": item.relative_path,
                    "rank": item.rank,
                    "score": round(item.score, 6),
                }
                for item in retrieved
            ],
            "retrieval": {
                "requested_top_k": self.settings.top_k,
                "returned_chunks": len(retrieved),
                "task_id": task_id,
                "embedding_model": self.retriever.embeddings.model_identity,
                "query": result["retrieval_query"],
            },
            "prompt_version": SYSTEM_PROMPT_VERSION,
            "knowledge_scope": {
                "version": self.knowledge_scope.version,
                "classification": result.get("knowledge_classification", "unknown"),
                "task_relevance": result.get("task_relevance", "unknown"),
            },
            "verification": {
                "enabled": self.settings.enable_response_verifier,
                "status": result.get("verification_status", "unknown"),
                "prompt_version": VERIFIER_PROMPT_VERSION,
            },
        }
