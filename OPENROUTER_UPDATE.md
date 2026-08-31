# OpenRouter update

This release sends both chat and embeddings from the FastAPI backend to OpenRouter. The browser never receives the OpenRouter API key.

## Backend Vercel variables

Set these on the Vercel project whose Root Directory is `backend`:

```text
APP_ENV=experiment
EMBEDDING_PROVIDER=openrouter
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_REVISION=openrouter-catalog-2026-08-25
EMBEDDING_DIMENSION=1024
QUERY_PREFIX=query:
DOCUMENT_PREFIX=passage:
TOP_K=3
RETRIEVAL_SCORE_MARGIN=0.12
MAX_CHUNKS_PER_SOURCE=2
MMR_LAMBDA=0.75
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4o-mini
LLM_MAX_TOKENS=700
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=YOUR_NEW_OPENROUTER_KEY
OPENROUTER_HTTP_REFERER=https://YOUR-FRONTEND.vercel.app
OPENROUTER_APP_TITLE=Cognitive Style Experiment
API_SHARED_SECRET=YOUR_RANDOM_INTERNAL_SECRET_AT_LEAST_32_CHARACTERS
INDEX_DIR=/tmp/sepid-index
ENABLE_DEBUG_RETRIEVAL=false
ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app
```

`QUERY_PREFIX` and `DOCUMENT_PREFIX` intentionally omit the final space because some dashboards trim it; the backend restores the required E5 separator.

Do not set `RAG_API_TOKEN` to the OpenRouter key. On the frontend Vercel project, `RAG_API_TOKEN` must equal `API_SHARED_SECRET`, and `RAG_API_URL` must be the backend deployment URL.

After changing the embedding model, run a new retrieval evaluation before collecting participant data:

```cmd
cd backend
copy .env.evaluation.example .env
notepad .env
.venv\Scripts\python.exe scripts\evaluate_retrieval.py --output reports\openrouter_e5_large_k5.json
```

Do not reuse a report created for `multilingual-e5-large-instruct`.
