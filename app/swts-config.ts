export type SwtsTaskId = "task_1" | "task_2" | "task_3";

export const SWTS_VERSION = "sepid-island-fa-swts-v1";
export const SWTS_TIME_LIMIT_SECONDS = 60 * 60;

// This block is intentionally defined once and shown unchanged for every task.
export const SWTS_COMMON_CONTEXT = `شما و پنج نفر از دوستان و اعضای خانواده قصد دارید سفری پنج‌روزه به جزیره‌ی سپید داشته باشید. کارهای آماده‌سازی سفر بین اعضای گروه تقسیم شده و از شما خواسته شده است در چند بخش به گروه کمک کنید.

جزیره‌ی سپید کاملاً خیالی است، هیچ‌کدام قبلاً به آنجا نرفته‌اید و فقط اطلاعات موجود در این سامانه معتبر است.`;

export type SwtsTask = {
  id: SwtsTaskId;
  title: string;
  prompt: string;
  requiredResponse: string;
  maxWords?: number;
};

// Only the task-specific block changes between tasks. Research-level labels
// (receptive, critical, creative) are deliberately absent from participant UI.
export const SWTS_TASKS: Record<SwtsTaskId, SwtsTask> = {
  task_1: {
    id: "task_1",
    title: "اقامت",
    prompt:
      "گروه هنوز نمی‌داند در جزیره‌ی سپید چه گزینه‌هایی برای اقامت وجود دارد. گزینه‌های اقامت را پیدا کنید و برای هرکدام، هزینه‌ی هر شب، ظرفیت و مقررات یا مجوز لازم را به‌طور خلاصه توضیح دهید. در این تسک لازم نیست بهترین گزینه را انتخاب کنید.",
    requiredResponse:
      "معرفی کوتاه گزینه‌های اقامت و اطلاعات اصلی هرکدام.",
  },
  task_2: {
    id: "task_2",
    title: "زمان سفر",
    prompt:
      "گروه باید زمان سفر را انتخاب کند. سه بازه‌ی مختلف سال از نظر هزینه و شرایط سفر تفاوت دارند و ممکن است تجربه‌ی یکسانی از جزیره فراهم نکنند. با استفاده از اطلاعات سامانه، این سه بازه را مقایسه کنید، مناسب‌ترین بازه را برای گروه انتخاب کنید و دلیل انتخاب خود و مناسب‌نبودن دو بازه‌ی دیگر را توضیح دهید.",
    requiredResponse:
      "بازه‌ی انتخاب‌شده و دلیل کوتاه انتخاب یا رد هر بازه.",
  },
  task_3: {
    id: "task_3",
    title: "راهنمای تعامل با ساکنان جزیره",
    prompt:
      "گروه می‌خواهد پیش از سفر راهنمایی برای تعامل محترمانه و مسئولانه با ساکنان جزیره داشته باشد. با استفاده از اطلاعات سامانه، یک راهنمای کوتاه و کاربردی تهیه کنید تا اعضای گروه بدانند در موقعیت‌های روزمره چگونه رفتار کنند. اطلاعات مهم را انتخاب و به‌شکلی منسجم سازمان‌دهی کنید و در صورت نیاز برای روشن‌شدن توصیه‌ها توضیح یا مثال بیاورید.\n\nمی‌توانید راهنما را به‌شکل متن پیوسته، بخش‌بندی‌شده، فهرست یا ترکیبی از این قالب‌ها ارائه کنید.",
    requiredResponse:
      "یک راهنمای کوتاه تا متوسط و قابل‌استفاده، حداکثر در ۳۰۰ واژه. تعداد توصیه‌ها از پیش تعیین نشده است.",
    maxWords: 300,
  },
};

export const SWTS_TASK_IDS = Object.keys(SWTS_TASKS) as SwtsTaskId[];

