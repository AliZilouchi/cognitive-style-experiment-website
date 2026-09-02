# Curated knowledge-map release 0.6.0

## Retrieval revision

- 18 unchanged allowlisted sources represented by 54 manually curated units
- Five index nodes, eight comparison nodes, and 41 focused fact nodes
- Every unit records its source provenance, task scope, entities, type, and parents
- Deterministic coverage anchors for broad accommodation, period, attraction, and interaction queries
- Hard task filtering using the request's `task_id`
- Current-question-only retrieval; chat history remains available only to generation
- `TOP_K=3`, relative similarity threshold, two-chunk per-source cap, and MMR diversity
- Chunk IDs and topics exposed in debug/API metadata for auditability
- Regression tests prevent cross-task retrieval

This release packages the controlled Persian Sepid Island RAG backend for local Docker deployment and later integration with the experiment website.

## Frozen study configuration

- Corpus: 18 allowlisted Persian source documents (`S01`–`S18`)
- Embedding provider: local Sentence Transformers
- Embedding model: `intfloat/multilingual-e5-large-instruct`
- Embedding revision: `274baa43b0e13e37fafa6428dbc7938e62e5c439`
- Query prefix: the evaluated E5 Persian-retrieval instruction
- Document prefix: empty
- Retrieval depth: `TOP_K=3`
- Generator provider: Groq
- Generator model: `qwen/qwen3.6-27b`
- Prompt version: `sepid-fa-rag-v1`

## Docker safeguards

- Python 3.12 base image
- Local embedding dependencies installed during the image build
- Groq key loaded from `.env`, which is excluded from the image and archive
- Persistent Hugging Face model and retrieval-index volumes
- Strict corpus allowlist; evaluation files cannot become answer sources
- Debug retrieval disabled in the supplied experiment configuration
- Health check with a long first-start grace period for model download

## Local validation performed before packaging

- All seven unit tests passed
- Corpus allowlist check loaded exactly `S01`–`S18`
- Python source compilation passed
- Frozen Docker environment fields and absence of a packaged `.env` were checked

The container image itself was not built in the packaging workspace because Docker was unavailable there. Run `docker compose up --build -d` on the target machine to perform the actual image build.
