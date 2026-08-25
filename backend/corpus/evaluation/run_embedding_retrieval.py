#!/usr/bin/env python3
"""Evaluate the final embedding configuration against the Persian gold queries."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "ingestion"))
from load_allowlisted_sources import load_allowlisted_sources  # noqa: E402


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_config(config: dict) -> None:
    required = {
        "model_name_or_path",
        "revision",
        "top_k",
        "query_prefix",
        "document_prefix",
        "normalize_embeddings",
        "similarity",
        "trust_remote_code",
    }
    missing = required - config.keys()
    if missing:
        raise ValueError(f"Missing embedding config keys: {sorted(missing)}")
    if str(config["model_name_or_path"]).startswith("REPLACE_"):
        raise ValueError("Final embedding model has not been configured")
    if str(config["revision"]).startswith("REPLACE_"):
        raise ValueError("A pinned model revision is required")
    if not isinstance(config["top_k"], int) or config["top_k"] < 1:
        raise ValueError("top_k must be a fixed positive integer")
    if config["similarity"] != "cosine":
        raise ValueError("This evaluator currently requires cosine similarity")
    if importlib.util.find_spec("sentence_transformers") is None:
        raise RuntimeError("sentence-transformers is not installed in this environment")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    config = read_json(args.config)
    validate_config(config)

    from sentence_transformers import SentenceTransformer
    import numpy as np

    sources = load_allowlisted_sources()
    gold_path = PACKAGE_ROOT / "evaluation" / "retrieval_gold.jsonl"
    gold = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines() if line]

    model = SentenceTransformer(
        config["model_name_or_path"],
        revision=config["revision"],
        trust_remote_code=config["trust_remote_code"],
    )
    doc_texts = [config["document_prefix"] + item["text"] for item in sources]
    query_texts = [config["query_prefix"] + item["query"] for item in gold]
    doc_embeddings = model.encode(
        doc_texts,
        normalize_embeddings=config["normalize_embeddings"],
        convert_to_numpy=True,
    )
    query_embeddings = model.encode(
        query_texts,
        normalize_embeddings=config["normalize_embeddings"],
        convert_to_numpy=True,
    )

    if not config["normalize_embeddings"]:
        doc_embeddings /= np.maximum(np.linalg.norm(doc_embeddings, axis=1, keepdims=True), 1e-12)
        query_embeddings /= np.maximum(np.linalg.norm(query_embeddings, axis=1, keepdims=True), 1e-12)

    source_ids = [item["source_id"] for item in sources]
    top_k = min(config["top_k"], len(source_ids))
    hit_count = 0
    reciprocal_rank_sum = 0.0
    recall_sum = 0.0
    exact_rows = []

    for query_embedding, item in zip(query_embeddings, gold):
        scores = doc_embeddings @ query_embedding
        order = np.argsort(scores)[::-1]
        ranked_ids = [source_ids[index] for index in order]
        returned = ranked_ids[:top_k]
        relevant = set(item["relevant_source_ids"])
        retrieved_relevant = relevant.intersection(returned)
        hit_count += bool(retrieved_relevant)
        recall_sum += len(retrieved_relevant) / len(relevant)
        first_rank = next((rank + 1 for rank, source_id in enumerate(ranked_ids) if source_id in relevant), None)
        reciprocal_rank_sum += 0.0 if first_rank is None else 1.0 / first_rank

        if item.get("query_type") == "exact_swts_prompt":
            exact_rows.append(
                {
                    "task": item["task"],
                    "returned": returned,
                    "relevant_retrieved": sorted(retrieved_relevant),
                    "recall_at_k": round(len(retrieved_relevant) / len(relevant), 4),
                }
            )

    count = len(gold)
    report = {
        "model_name_or_path": config["model_name_or_path"],
        "revision": config["revision"],
        "top_k": config["top_k"],
        "query_count": count,
        "hit_at_k": round(hit_count / count, 4),
        "mean_recall_at_k": round(recall_sum / count, 4),
        "mrr": round(reciprocal_rank_sum / count, 4),
        "exact_swts_prompts": exact_rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
