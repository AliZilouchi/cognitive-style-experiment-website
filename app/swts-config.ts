export type SwtsTaskId = "task_1" | "task_2" | "task_3";

export const SWTS_VERSION = "sepid-island-fa-swts-v3-neutral-reflection";
export const SWTS_TIME_LIMIT_SECONDS = 12 * 60;

const NEUTRAL_REFLECTION_PROMPT =
  "مهم‌ترین چیزی که از این گفت‌وگو برای شما روشن شد چه بود؟";
const NEUTRAL_REFLECTION_PLACEHOLDER = "پاسخ کوتاه خود را بنویسید…";
const NEUTRAL_REFLECTION_WORD_LIMIT = 50;

// Borlund source-of-need and environment: intentionally identical for all tasks.
export const SWTS_COMMON_CONTEXT = `شما و پنج نفر از دوستان و اعضای خانواده قصد دارید سفری پنج‌روزه به جزیره سپید داشته باشید. کارهای آماده‌سازی سفر بین اعضای گروه تقسیم شده و از شما خواسته شده است در چند بخش به گروه کمک کنید.

جزیره سپید کاملاً خیالی است، هیچ‌کدام قبلاً به آنجا نرفته‌اید و فقط اطلاعات موجود در این سامانه معتبر است.`;

export const SWTS_COMMON_CONVERSATION_INSTRUCTION =
  "در این بخش، مسیر گفت‌وگو و نحوه بررسی موضوع اهمیت دارد و لازم نیست گزارش یا متن رسمی آماده کنید. تا زمانی که احساس می‌کنید موضوع را به اندازه کافی شناخته‌اید، پرسش‌های خود را مطرح کنید، درباره پاسخ‌ها توضیح بخواهید و در صورت نیاز اطلاعات را مقایسه کنید. در پایان، برداشت کوتاه خود را از گفت‌وگو ثبت خواهید کرد.";

export type SwtsTask = {
  id: SwtsTaskId;
  title: string;
  problem: string;
  objective: string;
  closingPrompt: string;
  closingPlaceholder: string;
  maxReflectionWords: number;
};

// Research-level labels are deliberately absent from participant-facing text.
export const SWTS_TASKS: Record<SwtsTaskId, SwtsTask> = {
  task_1: {
    id: "task_1",
    title: "شناخت گزینه‌های اقامت",
    problem:
      "گروه هنوز نمی‌داند در جزیره سپید چه گزینه‌هایی برای اقامت وجود دارد و این گزینه‌ها از نظر موقعیت، ظرفیت، هزینه، امکانات و مقررات چه تفاوت‌هایی دارند.",
    objective:
      "با دستیار گفت‌وگو کنید تا اطلاعات لازم درباره گزینه‌های اقامت را پیدا کنید. هدف این است که در پایان بدانید هر گزینه چه ویژگی‌هایی دارد و کدام گزینه‌ها با نیازهای گروه شما سازگارند.",
    closingPrompt: NEUTRAL_REFLECTION_PROMPT,
    closingPlaceholder: NEUTRAL_REFLECTION_PLACEHOLDER,
    maxReflectionWords: NEUTRAL_REFLECTION_WORD_LIMIT,
  },
  task_2: {
    id: "task_2",
    title: "مقایسه زمان‌های سفر",
    problem:
      "گروه هنوز درباره زمان سفر تصمیم نگرفته است. اعضای گروه به تجربه‌هایی مانند طبیعت‌گردی، فعالیت‌های ساحلی، بازدید از جاذبه‌ها و رویدادهای محلی علاقه دارند، اما شرایط آب‌وهوا، هزینه‌ها و امکان استفاده از مکان‌ها و فعالیت‌ها در طول سال یکسان نیست.",
    objective:
      "با دستیار گفت‌وگو کنید تا زمان‌های مختلف سفر را از جنبه‌های مرتبط بررسی و مقایسه کنید. هدف این است که در پایان به ترجیحی برسید که بتوانید دلایل آن و مصالحه‌های احتمالی را توضیح دهید.",
    closingPrompt: NEUTRAL_REFLECTION_PROMPT,
    closingPlaceholder: NEUTRAL_REFLECTION_PLACEHOLDER,
    maxReflectionWords: NEUTRAL_REFLECTION_WORD_LIMIT,
  },
  task_3: {
    id: "task_3",
    title: "درک زندگی و تعامل محترمانه",
    problem:
      "در این سفر فقط بازدید از مکان‌ها برای گروه مهم نیست؛ احتمال دارد با ساکنان جزیره تعامل داشته باشید، از محله‌ها و فضاهای عمومی دیدن کنید و در بعضی آیین‌ها یا فعالیت‌های محلی حاضر شوید. با باورها، رسوم، نشانه‌ها، روایت‌ها و حساسیت‌های مردم جزیره آشنا نیستید و نمی‌خواهید ناخواسته رفتار نامناسبی داشته باشید.",
    objective:
      "با دستیار گفت‌وگو کنید تا جنبه‌های مختلف زندگی و فرهنگ جزیره را کشف کنید. هدف این است که در پایان، برداشت منسجمی از چگونگی تعامل محترمانه با مردم در موقعیت‌های گوناگون شکل دهید.",
    closingPrompt: NEUTRAL_REFLECTION_PROMPT,
    closingPlaceholder: NEUTRAL_REFLECTION_PLACEHOLDER,
    maxReflectionWords: NEUTRAL_REFLECTION_WORD_LIMIT,
  },
};

export const SWTS_TASK_IDS = Object.keys(SWTS_TASKS) as SwtsTaskId[];
