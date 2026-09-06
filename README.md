# Sepid RAG evidence-projection v5

Incremental backend patch for installations that already include request-planner v4.

## Apply

Copy the included `backend` directory over the repository's existing `backend` directory, preserving paths. No frontend files, SQL migrations, dependencies, or environment-variable changes are required.

Commit, push, and redeploy the RAG API project without build cache.

## Changes

- Category overview requests receive a structured minimal evidence projection instead of full profile chunks.
- Overview output is validated for prices, percentages, booking rules, service details, and numeric leakage.
- Invalid overview output falls back to the structured overview rather than exposing extra facts.
- Accommodation calculation requests cannot retrieve the generic seasonal tourism-cost percentage.
- Explanation, cultural, follow-up, multi-part, and explicit comparison modes retain normal generative flexibility.
- Prompt and knowledge-index versions are advanced for research reproducibility.

## Verification

From `backend` run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected: 58 tests pass.
