# سامانه پژوهش سبک شناختی + Sepid RAG

این مخزن نسخهٔ یکپارچه و آمادهٔ استقرار پژوهش است:

- وب‌سایت فارسی Next.js برای Vercel
- Supabase برای دعوت‌نامه، فرم‌ها، E-CSA-WA، تاریخچهٔ کامل SWTS و داشبورد پژوهشگر
- بک‌اند FastAPI/LangGraph در پوشهٔ `backend`، آمادهٔ Vercel
- پیکرهٔ هیبریدی ۹۰ واحدی: ۶۱ واحد دستی + ۲۹ سند کامل، با embedding میزبانی‌شدهٔ AvalAI، `top_k=3` و تولید فارسی با GPT-4.1 Mini
- گفت‌وگوی آزاد و پیش‌نمایش پژوهشگر بدون ذخیره در Supabase

## معماری استقرار

مرورگر هرگز مستقیماً به AvalAI یا بک‌اند RAG وصل نمی‌شود:

```text
Browser → Next.js/Vercel proxy → FastAPI/Vercel → AvalAI
                    ↓
                 Supabase
```

وب‌سایت و پراکسی امن در یک پروژهٔ Vercel و FastAPI در پروژهٔ دوم Vercel اجرا
می‌شوند. مدل embedding دقیق `text-embedding-3-large` با خروجی ۱۰۲۴بعدی از AvalAI
فراخوانی می‌شود؛ بنابراین رایانهٔ پژوهشگر، Docker، GPU و دانلود مدل لازم نیست.

راهنمای دقیق استقرار: [`VERCEL_DEPLOYMENT.md`](./VERCEL_DEPLOYMENT.md)

## اجرای محلی در Windows Command Prompt

ابتدا یک secret مشترک بسازید:

```cmd
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

کلید AvalAI را فقط در `backend\.env` وارد کنید. مقدار secret خروجی
را در دو محل یکسان وارد کنید:

- `RAG_API_TOKEN` در `.env.local`
- `API_SHARED_SECRET` در `backend\.env`

برای اجرای محلی با embedding میزبانی‌شده:

```cmd
copy .env.example .env.local
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.experiment.example .env
notepad .env
.venv\Scripts\python.exe -m uvicorn app:app --port 8000
```

در یک Command Prompt دوم، از ریشهٔ پروژه:

```cmd
npm ci
npm run dev
```

سایت در `http://localhost:3000` اجرا می‌شود. وضعیت RAG را می‌توانید از
`http://localhost:3000/api/rag/health` بررسی کنید.

## جریان پژوهش

1. دعوت‌نامه و رضایت آگاهانه
2. اطلاعات فردی کامل
3. E-CSA-WA: چهار تمرین + ۸۰ سؤال اصلی
4. راهنمای بیان افکار
5. سه چرخهٔ پیش‌فرم ← چت و پاسخ نهایی ← پس‌فرم
6. مقایسهٔ نهایی و پایان

تعریف زمینهٔ مشترک و بخش اختصاصی هر وظیفه فقط در
`app/swts-config.ts` قرار دارد. با تغییر وظیفه، تاریخچهٔ RAG خالی می‌شود و هیچ
prompt وظیفه‌ای به‌طور خودکار به‌عنوان پیام شرکت‌کننده ارسال نمی‌شود.

## رفتار ثبت داده

- حالت آزمایش: تمام تلاش‌های موفق و ناموفق، متن اصلی، پاسخ اصلی/نمایشی، latency،
  request ID، رتبه و امتیاز منابع، query بازیابی، مدل embedding و prompt version
  در Supabase ثبت می‌شوند.
- خطاها retry خودکار ندارند؛ متن حفظ می‌شود و کاربر retry دستی انجام می‌دهد.
- `/free-chat`: مکالمه در Supabase یا حافظهٔ دائمی مرورگر ذخیره نمی‌شود.
- پیش‌نمایش پژوهشگر: دعوت‌نامه مصرف نمی‌کند و هیچ دادهٔ پژوهشی ذخیره نمی‌کند.

## مهاجرت‌های Supabase

فایل‌های `supabase/001_...sql` تا `supabase/008_...sql` را به ترتیب اجرا کنید.
اگر پروژه قبلاً تا `006` آماده شده، فقط `007_swts_chat.sql` و
`008_persian_study_flow.sql` لازم‌اند.

## بررسی پیش از پایلوت

```cmd
npm ci
npm test
cd backend
python -m pytest
```

سپس یک اجرای واقعی با دعوت‌نامهٔ آزمایشی و یک اجرای پیش‌نمایش بدون ذخیره انجام
دهید و خروجی CSV داشبورد را بررسی کنید.
