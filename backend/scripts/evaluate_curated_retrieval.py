#!/usr/bin/env python3
"""Measure required curated-unit coverage with the deployed embedding setup."""

from __future__ import annotations

import json
from pathlib import Path

from sepid_rag.config import Settings
from sepid_rag.corpus import load_allowlisted_corpus
from sepid_rag.embeddings import create_embeddings
from sepid_rag.retriever import CorpusRetriever


def main() -> int:
    settings = Settings.from_env()
    documents = load_allowlisted_corpus(settings.corpus_root)
    retriever = CorpusRetriever(
        documents,
        create_embeddings(settings),
        settings.top_k,
        score_margin=settings.retrieval_score_margin,
        max_chunks_per_source=settings.max_chunks_per_source,
        mmr_lambda=settings.mmr_lambda,
    )
    gold_path = settings.corpus_root / "evaluation" / "curated_retrieval_gold.jsonl"
    cases = [
        json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = []
    passed = 0
    for case in cases:
        results = retriever.search(case["query"], case["task_id"])
        returned = [result.chunk_id for result in results]
        required = set(case["required_chunk_ids"])
        ok = required.issubset(returned)
        passed += ok
        rows.append({**case, "returned_chunk_ids": returned, "passed": ok})
    report = {
        "configuration": {
            "embedding_model": retriever.embeddings.model_identity,
            "top_k": settings.top_k,
            "score_margin": settings.retrieval_score_margin,
            "max_chunks_per_source": settings.max_chunks_per_source,
            "mmr_lambda": settings.mmr_lambda,
        },
        "metrics": {
            "case_count": len(cases),
            "passed": passed,
            "required_chunk_recall": round(passed / len(cases), 4),
        },
        "cases": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
