# Sepid RAG request-planner v4

This patch contains only the files changed for the request-level planning update.

## Apply

Copy the `backend` directory from this archive over the repository root, preserving paths. No frontend files or environment variables change.

Redeploy the RAG/backend Vercel project after committing and pushing the files.

## Behavior added

- Classifies every turn as `single_fact`, `single_entity`, `category_overview`, `comparison`, `multi_part`, `calculation_limited`, `broad_clarification`, or `unsupported`.
- Selects a retrieval budget and preferred corpus node types for that level.
- Sends an explicit Persian response contract to both the answer model and verifier.
- Resolves short follow-ups from history without letting history increase answer breadth.
- Bypasses retrieval/model generation for unsupported and broad corpus-dump requests.
- Rejects arithmetic or derived totals in calculation-limited responses and falls back safely if the model or verifier ignores the contract.

## Verification

Run from `backend`:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected result: 55 tests pass.
