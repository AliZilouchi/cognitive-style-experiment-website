# Global-corpus retrieval release 0.9.2

- All three experiment tasks and free chat now search the same complete 90-unit corpus.
- `task_id` remains available for logging, history boundaries, and response policy, but no longer excludes knowledge from retrieval.
- The LLM, prompt, temperature, `top_k`, corpus, and per-task history reset are unchanged.
- Retrieval evaluation scripts now measure the same global-corpus behavior used in production.

## Free-chat retrieval scope repair 0.9.1

- Added an explicit `free_chat` request scope that searches all 90 corpus units.
- Kept the experiment task identifiers and history boundaries unchanged.
- Free chat now defaults to the full corpus while retaining task-specific scopes for researcher debugging.

## AvalAI provider release 0.9.0

- Added first-class AvalAI embedding and chat providers with dedicated credentials.
- Uses `text-embedding-3-large` with a frozen 1024-dimensional request.
- Uses a 96-document embedding batch so the 90-unit corpus needs one startup embedding request on AvalAI Basic tier.
- Supports the frozen `gpt-4.1-mini-2025-04-14` chat model at temperature zero.

## Vercel cold-start repair 0.8.1

- Hosted document embeddings are generated in bounded batches instead of one oversized request.
- RAG initialization is lazy and guarded, so an upstream initialization failure returns a diagnosable `503` rather than crashing the Serverless Function during startup.

## Enriched hybrid corpus release 0.8.0

## Corpus revision

- Added 11 answer-bearing enriched Persian documents covering geography and
  neighborhoods, social structure, beliefs and myths, customs and symbols,
  tourism/nature sensitivities, calendar/events, balanced accommodation and
  attraction profiles, services, routes, and first-visitor facts.
- Kept the 18 original sources unchanged and searchable.
- Excluded the enriched index, provenance/change log, and fictional-additions
  register from answer retrieval.
- Expanded the accommodation map to five options, including خانه‌مسافر فانوس.
- Added deterministic cultural entry points for social status, beliefs, myths,
  rituals, symbols, and nature sensitivity.
- Hybrid index size: 61 curated units + 29 complete source fallbacks.

## Previous hybrid release 0.7.0

## Behavioural target

- Simple questions receive short direct answers.
- Explicit broad or multi-part questions receive complete, structured answers.
- Search, explanation, calculation, synthesis, and neutral comparison remain available.
- Activity 2's final subjective selection and Activity 3's ready-to-submit guide remain participant work.
- Short referential follow-ups are retrieved with their recent conversational subject.

## Retrieval revision

- 54 curated index/fact/comparison units remain the preferred layer.
- All 18 validated original documents are now available as semantic fallbacks.
- Broad accommodation requests deterministically receive the complete overview,
  cost/capacity comparison, and rules comparison within `TOP_K=3`.
- API and package version: 0.7.0; prompt version: `sepid-fa-rag-v5`.

## Previous curated release 0.6.0

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
