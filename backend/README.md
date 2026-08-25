# Sepid Island Persian RAG Backend

A portable, controlled RAG backend for the three Sepid Island Search-as-Learning tasks. The same source code runs in Vercel, Docker, Colab, and local development.

The Vercel-ready release uses Together's hosted `intfloat/multilingual-e5-large-instruct` embedding endpoint at `TOP_K=5` and Groq for grounded Persian generation. No local embedding model is required. See the root `VERCEL_DEPLOYMENT.md` for exact steps.

## What is already implemented

- Strict ingestion of exactly the 18 corpus files in `corpus/ingestion/allowlist.json`
- Verification that the allowlist and corpus manifest match
- Persian retrieval normalization while preserving the original user query
- Model-specific query/document prefixes recorded as part of the embedding configuration
- Interchangeable local Sentence Transformers and hosted Together embedding backends
- Strict validation of hosted vector count and the frozen 1024 dimension
- A clearly marked deterministic hashing backend for plumbing tests only
- Transparent cosine retrieval with fixed `TOP_K` and a reproducible index cache
- Minimal LangGraph flow: retrieve, then answer
- Together chat through LangChain's `ChatTogether`
- Groq chat through LangChain's `ChatGroq`
- A Persian grounded-answer prompt with source identifiers
- FastAPI `/health`, `/chat`, and development-only `/debug/retrieve` endpoints
- Retrieval evaluation using all gold queries, including the exact three SWTS prompts
- Vercel FastAPI entrypoint, Colab starter notebook, Docker fallback, and tests

## Research safeguards

`APP_ENV=evaluation` rejects fake hashing embeddings but does not require a final chat model. `APP_ENV=experiment` additionally rejects:

- hashing embeddings;
- echo responses;
- placeholder model names or revisions;
- missing credentials for the configured hosted provider;
- non-positive `TOP_K` values.

Evaluation files are outside the ingestion allowlist and are never loaded as answer sources. The selected hosted candidate is Together `intfloat/multilingual-e5-large-instruct` (1024 dimensions) with `TOP_K=5`; its hosted evaluation report must be generated and reviewed before participant data collection. The included local reference report is not falsely relabeled as a hosted result.

## Project layout

```text
sepid-rag-backend/
├── corpus/                     # Final v2 Persian corpus and evaluation set
├── src/sepid_rag/
│   ├── api.py                  # FastAPI boundary
│   ├── config.py               # Strict environment configuration
│   ├── corpus.py               # Allowlist-only loader
│   ├── embeddings.py           # Embedding provider adapters
│   ├── graph.py                # LangGraph workflow
│   ├── normalization.py        # Persian retrieval normalization
│   ├── prompts.py              # Versioned system prompt
│   ├── retriever.py            # Cosine retrieval and index cache
│   └── service.py              # Application assembly
├── scripts/
│   ├── check_corpus.py
│   ├── evaluate_retrieval.py
│   └── smoke_chat.py
├── notebooks/
│   └── 01_colab_retrieval.ipynb
├── tests/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Local development smoke test

Python 3.11 or newer is supported. The project is also intended to run on current Colab Python runtimes.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.development.example .env
set -a
source .env
set +a
python scripts/check_corpus.py
python scripts/smoke_chat.py "هتل صدف چقدر هزینه دارد؟"
uvicorn sepid_rag.api:app --reload
```

On Windows PowerShell without WSL, activate with `.venv\\Scripts\\Activate.ps1` and load the `.env` values through your IDE or Docker instead of `source`.

Swagger UI will be available at `http://localhost:8000/docs`.

## Development API example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "pilot-001",
    "task_id": "task_1",
    "message": "چه گزینه‌هایی برای اقامت وجود دارد؟",
    "history": []
  }'
```

The development configuration returns retrieved source IDs rather than pretending that a real LLM is active.

## Real retrieval experiment

1. Copy `.env.evaluation.example` to `.env`.
2. Replace the Together API-key placeholder. The hosted model, prefix, dimension, and fixed `TOP_K=5` are already configured.
3. Run:

```bash
python scripts/evaluate_retrieval.py --output reports/together_hosted_k5.json
```

For local Sentence Transformers installation:

```bash
pip install -e ".[local-embeddings]"
```

Compare the hosted report with `reports/e5_local_k5.json`. Do not use `--allow-development` for model selection; that switch only verifies evaluation plumbing. After accepting the hosted result, use `.env.experiment.example` for the end-to-end pilot and Vercel variables.

If Together does not expose a separate immutable revision for a hosted embedding model, record an explicit provider-managed revision label/date in `EMBEDDING_REVISION` and rebuild the index whenever that label changes. Do not present that label as a provider commit hash.

## Colab

Upload the delivered ZIP to Colab and open `notebooks/01_colab_retrieval.ipynb`. The notebook installs this same package and calls the same evaluator. Core logic is not duplicated in notebook cells.

Colab secrets should be read interactively or through Colab Secrets; never save an API key in the notebook.

## Docker

Create the experiment environment file and insert your Groq key:

```bash
cp .env.docker.example .env
docker compose up --build
```

The selected Sentence Transformers embedding dependencies are installed by default. The pinned model is downloaded on first startup and retained in the `huggingface-cache` Docker volume. The generated 18-document index is retained separately in `rag-index`.

The frontend should call the backend—not Groq or Together directly. In the
combined Vercel package, the browser calls the same-origin Next.js proxy and
that proxy adds `Authorization: Bearer ...` server-side. Set
`API_SHARED_SECRET` on this service and set the identical value as
`RAG_API_TOKEN` on Vercel. Add the exact frontend origin to `ALLOWED_ORIGINS`.
Never use `*` for the final experiment unless there is a documented reason.

## Before the pilot

- Select and record the actual embedding provider, model, and revision.
- Evaluate candidate fixed `TOP_K` values against the included gold set.
- Inspect the per-query results, especially the broad Creative query and exact SWTS prompts.
- Select and freeze the Groq or Together chat model.
- Review and freeze `SYSTEM_PROMPT_VERSION` and prompt contents.
- Turn off debug retrieval.
- Confirm the web app logs original messages, timestamps, task/session IDs, returned source IDs, model identity, prompt version, and final responses.
- Run an end-to-end pilot through the actual participant interface.
