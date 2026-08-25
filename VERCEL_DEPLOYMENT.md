# راهنمای دقیق استقرار کامل روی Vercel

در این نسخه، هیچ embedding روی رایانهٔ شخصی اجرا نمی‌شود:

```text
Browser → Next.js/Vercel proxy → FastAPI/Vercel
                                 ├─ Together Embeddings
                                 └─ Groq Chat
                 └──────────────→ Supabase
```

دو پروژهٔ Vercel از یک GitHub repository ساخته می‌شوند: یکی با Root Directory
برابر `backend` و دیگری با Root Directory برابر `.`.

## ۱. ساخت کلیدها

1. در Together یک API key بسازید.
2. کلید Groq فعلی را نگه دارید.
3. در Windows Command Prompt یک secret مشترک بسازید:

```cmd
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

خروجی را نگه دارید. این مقدار در بک‌اند `API_SHARED_SECRET` و در فرانت‌اند
`RAG_API_TOKEN` خواهد بود. هیچ کلیدی را در GitHub commit نکنید.

## ۲. ارزیابی embedding میزبانی‌شده پیش از مطالعه

این مرحله embedding را از Together می‌گیرد و مدل محلی دانلود نمی‌کند:

```cmd
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.evaluation.example .env
notepad .env
```

در `.env` فقط `REPLACE_WITH_YOUR_TOGETHER_API_KEY` را با کلید واقعی عوض کنید،
فایل را ذخیره کنید و سپس اجرا کنید:

```cmd
.venv\Scripts\python.exe scripts\evaluate_retrieval.py --output reports\together_hosted_k5.json
```

گزارش محلی مرجع در `reports/e5_local_k5.json` است. برای شروع داده‌گیری واقعی،
`hit_at_k` باید `1.0` بماند و تفاوت رتبه‌ها/Recall باید بازبینی و ثبت شود. چون
Together commit hash مدل میزبانی‌شده را منتشر نمی‌کند، عبارت
`together-serverless-catalog-2026-08-25` یک برچسب freeze مطالعه است، نه hash
رسمی provider.

## ۳. قرار دادن پروژه در GitHub

از ریشهٔ پروژه:

```cmd
git init
git add .
git commit -m "Prepare Persian SWTS study for Vercel"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

اگر repository از قبل remote دارد، فقط commit و push کنید. فایل‌های `.env` و
`.env.local` توسط `.gitignore` خارج می‌مانند؛ پیش از push نیز با `git status`
بررسی کنید.

## ۴. ساخت پروژهٔ بک‌اند در Vercel

1. **Add New → Project** و همان repository را import کنید.
2. نامی مانند `sepid-rag-api` بدهید.
3. **Root Directory** را `backend` قرار دهید.
4. Build/Install Command را override نکنید. `app.py` و `requirements.txt`
   باعث تشخیص خودکار FastAPI/Python 3.12 می‌شوند.
5. متغیرهای زیر را برای Production وارد کنید:

| Variable | Value |
|---|---|
| `APP_ENV` | `experiment` |
| `EMBEDDING_PROVIDER` | `together` |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large-instruct` |
| `EMBEDDING_REVISION` | `together-serverless-catalog-2026-08-25` |
| `EMBEDDING_DIMENSION` | `1024` |
| `QUERY_PREFIX` | `Instruct: Given a Persian search query, retrieve relevant Persian passages that answer the query\nQuery: ` |
| `TOP_K` | `5` |
| `LLM_PROVIDER` | `groq` |
| `LLM_MODEL` | `qwen/qwen3.6-27b` |
| `LLM_MAX_TOKENS` | `700` |
| `TOGETHER_API_KEY` | کلید Together |
| `GROQ_API_KEY` | کلید Groq |
| `API_SHARED_SECRET` | secret ساخته‌شده در مرحلهٔ ۱ |
| `INDEX_DIR` | `/tmp/sepid-index` |
| `ENABLE_DEBUG_RETRIEVAL` | `false` |
| `ALLOWED_ORIGINS` | فعلاً `http://localhost:3000` |

`DOCUMENT_PREFIX` و `CORPUS_ROOT` را تعریف نکنید؛ مقدار درست آن‌ها به‌ترتیب
خالی و مسیر corpus داخل deployment است.

6. Deploy کنید. اولین cold start ممکن است چند ثانیه بیشتر طول بکشد، چون embedding
   هجده سند از Together گرفته و در `/tmp` همان instance cache می‌شود.
7. این آدرس را باز کنید:

```text
https://YOUR-BACKEND.vercel.app/health
```

باید `environment: "experiment"`، `source_count: 18`، `top_k: 5`،
`llm_provider: "groq"` و embedding identity شامل `together:` برگرداند.

## ۵. ساخت پروژهٔ وب‌سایت در Vercel

1. دوباره **Add New → Project** و همان repository را import کنید.
2. نامی مانند `cognitive-style-study` بدهید.
3. Root Directory را روی `.` نگه دارید.
4. Framework باید Next.js باشد؛ Build Command و Install Command را override
   نکنید.
5. متغیرهای Production را وارد کنید:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL فعلی پروژهٔ Supabase |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | publishable key فعلی Supabase |
| `RAG_API_URL` | `https://YOUR-BACKEND.vercel.app` بدون `/health` یا `/chat` |
| `RAG_API_TOKEN` | دقیقاً همان `API_SHARED_SECRET` |

6. Deploy کنید و URL نهایی frontend را کپی کنید.

## ۶. بستن CORS و اتصال دامنه

1. در پروژهٔ بک‌اند Vercel، مقدار `ALLOWED_ORIGINS` را به URL دقیق frontend
   تغییر دهید؛ مثال: `https://cognitive-style-study.vercel.app`.
2. بک‌اند را Redeploy کنید.
3. برای دامنهٔ شخصی، در پروژهٔ frontend به **Settings → Domains** بروید، دامنه
   را اضافه کنید و DNS پیشنهادی Vercel را در registrar اعمال کنید.
4. پس از فعال‌شدن دامنه، آن را نیز به `ALLOWED_ORIGINS` اضافه کنید و بک‌اند را
   دوباره Redeploy کنید. چند origin با comma جدا می‌شوند؛ از `*` استفاده نکنید.

## ۷. تست نهایی

1. `https://YOUR-FRONTEND/api/rag/health` را باز کنید؛ مقادیر ۱۸/۵/experiment را
   بررسی کنید.
2. `/free-chat` را امتحان کنید؛ refresh نباید گفت‌وگو را برگرداند.
3. Researcher view را باز کنید و preview بدون ذخیره را اجرا کنید.
4. با دعوت‌نامهٔ تازه، مسیر کامل سه SWTS را اجرا کنید.
5. در Supabase جدول `swts_chat_attempts` را بررسی کنید: هر پیام/پاسخ، latency،
   request ID، منابع پنهان، query، embedding identity و prompt version باید ثبت
   شده باشد.
6. خطا retry خودکار ندارد؛ draft باید حفظ شود و retry فقط دستی باشد.

> مدل `qwen/qwen3.6-27b` در Groq فعلاً Preview است. قبل از جمع‌آوری اصلی، همین
> مدل را برای کل نمونه ثابت نگه دارید یا یک مدل Production را جداگانه پایلوت و
> سپس یک‌باره جایگزین کنید؛ وسط مطالعه مدل را تغییر ندهید.
