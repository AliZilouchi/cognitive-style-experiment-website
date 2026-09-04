# راهنمای استقرار روی Vercel با AvalAI

این repository به‌صورت دو پروژهٔ Vercel deploy می‌شود:

```text
Browser → Next.js frontend/proxy → FastAPI backend → AvalAI
                    ↓
                 Supabase
```

کلید AvalAI فقط در پروژهٔ بک‌اند قرار می‌گیرد و هرگز نباید متغیر `NEXT_PUBLIC_*` باشد.

## ۱. secret داخلی

در Windows Command Prompt اجرا کنید:

```cmd
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

خروجی را نگه دارید. این مقدار باید در بک‌اند `API_SHARED_SECRET` و در فرانت‌اند `RAG_API_TOKEN` باشد.

## ۲. پروژهٔ بک‌اند

همان GitHub repository را در Vercel import کنید و Root Directory را `backend` قرار دهید. Build و Install Command را override نکنید. متغیرهای Production:

| Variable | Value |
|---|---|
| `APP_ENV` | `experiment` |
| `EMBEDDING_PROVIDER` | `avalai` |
| `EMBEDDING_MODEL` | `text-embedding-3-large` |
| `EMBEDDING_REVISION` | `avalai-2026-09-04` |
| `EMBEDDING_DIMENSION` | `1024` |
| `QUERY_PREFIX` | خالی |
| `DOCUMENT_PREFIX` | خالی |
| `TOP_K` | `3` |
| `RETRIEVAL_SCORE_MARGIN` | `0.12` |
| `MAX_CHUNKS_PER_SOURCE` | `2` |
| `MMR_LAMBDA` | `0.75` |
| `LLM_PROVIDER` | `avalai` |
| `LLM_MODEL` | `gpt-4.1-mini-2025-04-14` |
| `LLM_MAX_TOKENS` | `700` |
| `AVALAI_BASE_URL` | `https://api.avalai.ir/v1` |
| `AVALAI_API_KEY` | کلید AvalAI |
| `API_SHARED_SECRET` | secret مرحلهٔ ۱ |
| `INDEX_DIR` | `/tmp/sepid-index` |
| `ENABLE_DEBUG_RETRIEVAL` | `false` |
| `ALLOWED_ORIGINS` | URL دقیق frontend |

برای مدل OpenAI جدید prefix لازم نیست. متغیرهای OpenRouter، Groq و Together لازم نیستند.

Deploy کنید و سپس `https://YOUR-BACKEND.vercel.app/health` را باز کنید. خروجی باید `environment: "experiment"`، `source_count: 29`، `chunk_count: 90`، `top_k: 3`، `llm_provider: "avalai"` و embedding identity با ابتدای `avalai:` نشان دهد.

## ۳. پروژهٔ frontend

repository را بار دیگر import کنید، Root Directory را `.` نگه دارید و این متغیرها را وارد کنید:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL پروژهٔ Supabase |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | publishable key پروژه |
| `RAG_API_URL` | URL بک‌اند، بدون `/health` یا `/chat` |
| `RAG_API_TOKEN` | دقیقاً همان `API_SHARED_SECRET` |

Deploy کنید. سپس URL نهایی frontend را در `ALLOWED_ORIGINS` پروژهٔ بک‌اند وارد و backend را Redeploy کنید.

## ۴. ارزیابی مدل embedding جدید

تغییر به `text-embedding-3-large` یک تغییر واقعی مدل است. پیش از جمع‌آوری دادهٔ شرکت‌کنندگان، گزارش جدید بسازید:

```cmd
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.evaluation.example .env
notepad .env
.venv\Scripts\python.exe scripts\evaluate_retrieval.py --output reports\avalai_embedding_large_k3.json
```

در `.env` کلید واقعی AvalAI را جایگزین کنید. گزارش embedding قبلی قابل استفاده برای این مدل نیست.

## ۵. تست نهایی

1. `https://YOUR-FRONTEND/api/rag/health` را بررسی کنید.
2. `/free-chat` را تست کنید؛ refresh نباید مکالمه را برگرداند.
3. preview بدون ذخیرهٔ پژوهشگر را اجرا کنید.
4. با دعوت‌نامهٔ تازه سه وظیفهٔ SWTS را کامل کنید.
5. در Supabase ثبت پیام‌ها و پاسخ‌ها را در `swts_chat_attempts` بررسی کنید.
6. retry باید فقط دستی باشد و draft پس از خطا حفظ شود.

اگر دامنهٔ شخصی اضافه می‌کنید، آن را نیز به `ALLOWED_ORIGINS` اضافه کنید. چند origin با comma جدا می‌شوند؛ در مطالعه از `*` استفاده نکنید.
