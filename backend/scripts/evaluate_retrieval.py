#!/usr/bin/env python3
"""Evaluate task-scoped semantic-chunk retrieval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from sepid_rag.config import Settings
from sepid_rag.corpus import load_allowlisted_corpus
from sepid_rag.embeddings import create_embeddings
from sepid_rag.retriever import CorpusRetriever


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-development",
        action="store_true",
        help="Permit non-semantic hashing embeddings only for a plumbing check.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    if settings.embedding_provider == "hashing" and not args.allow_development:
        raise SystemExit(
            "Refusing to report development hashing results as embedding evaluation."
        )

    documents = load_allowlisted_corpus(settings.corpus_root)
    embeddings = create_embeddings(settings)
    # Do not reuse a potentially stale persisted matrix during formal evaluation.
    retriever = CorpusRetriever(
        documents,
        embeddings,
        settings.top_k,
        score_margin=settings.retrieval_score_margin,
        max_chunks_per_source=settings.max_chunks_per_source,
        mmr_lambda=settings.mmr_lambda,
    )
    gold_path = settings.corpus_root / "evaluation" / "retrieval_gold.jsonl"
    gold = [
        json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    hits = 0
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    rows = []
    for item in gold:
        task_id = {"receptive": "task_1", "critical": "task_2", "creative": "task_3"}[item["task"]]
        results = retriever.search(item["query"], task_id)
        returned = list(
            dict.fromkeys(
                source_id for result in results for source_id in result.source_ids
            )
        )
        relevant = set(item["relevant_source_ids"])
        found = relevant.intersection(returned)
        hits += bool(found)
        recalls.append(len(found) / len(relevant))
        first = next(
            (rank for rank, source_id in enumerate(returned, start=1) if source_id in relevant),
            None,
        )
        reciprocal_ranks.append(0.0 if first is None else 1.0 / first)
        rows.append(
            {
                "task": item["task"],
                "query_type": item.get("query_type", "probe"),
                "query": item["query"],
                "relevant": sorted(relevant),
                "returned": returned,
                "returned_chunks": [result.chunk_id for result in results],
                "recall_at_k": round(recalls[-1], 4),
                "reciprocal_rank_at_k": round(reciprocal_ranks[-1], 4),
            }
        )

    count = len(gold)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "DEVELOPMENT-ONLY HASHING RESULT; NOT VALID FOR MODEL SELECTION"
            if settings.embedding_provider == "hashing"
            else None
        ),
        "configuration": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "revision": settings.embedding_revision,
            "query_prefix": settings.query_prefix,
            "document_prefix": settings.document_prefix,
            "top_k": settings.top_k,
            "score_margin": settings.retrieval_score_margin,
            "max_chunks_per_source": settings.max_chunks_per_source,
            "mmr_lambda": settings.mmr_lambda,
            "corpus_id": "sepid_island_fa_v2",
        },
        "metrics": {
            "query_count": count,
            "hit_at_k": round(hits / count, 4),
            "mean_recall_at_k": round(sum(recalls) / count, 4),
            "mrr_at_k": round(sum(reciprocal_ranks) / count, 4),
        },
        "exact_swts_prompts": [
            row for row in rows if row["query_type"] == "exact_swts_prompt"
        ],
        "queries": rows,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
