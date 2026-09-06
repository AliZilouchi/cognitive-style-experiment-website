import type { RagTaskId } from "./rag-client";

export type ModelEvaluationScenario = {
  id: string;
  title: string;
  taskId: RagTaskId;
  questions: string[];
};

// This is the only file researchers need to edit to permanently add, remove,
// or reorder the default evaluation scenarios. The dashboard also permits
// temporary edits; those intentionally disappear when the page is closed.
export const DEFAULT_MODEL_EVALUATION_SCENARIOS: ModelEvaluationScenario[] = [
  {
    id: "travel-followups",
    title: "زمان سفر و پرسش‌های پیوسته",
    taskId: "task_2",
    questions: [
      "سلام",
      "آب‌وهوای جزیره به‌طور کلی چگونه است؟ جزیره گرمسیری است یا خیر؟",
      "امکانات آبی و تفریحات آن در تمام سال برقرار است؟",
      "از نظر جمعیتی چه فصلی شلوغ‌تر است؟",
      "آیا جشن یا رویداد خاصی وجود دارد و چه زمانی برگزار می‌شود؟",
      "با توجه به این موارد، تفاوت اصلی سه بازه سفر چیست؟",
    ],
  },
  {
    id: "culture-reference",
    title: "فرهنگ و ارجاع به پیام قبلی",
    taskId: "task_3",
    questions: [
      "مردم جزیره در بدو دیدار چگونه برخورد می‌کنند؟",
      "در سلام و احوالپرسی رسم مشخصی مثل دست‌دادن یا تعظیم دارند؟",
      "برای شناخت تعامل محترمانه چه موضوع‌هایی مهم‌اند؟",
      "حالا همان‌ها را کوتاه توضیح بده.",
      "دین مردم جزیره چیست؟",
    ],
  },
  {
    id: "accommodation-evidence",
    title: "اقامت و مرز شواهد",
    taskId: "task_1",
    questions: [
      "چه گزینه‌هایی برای اقامت وجود دارد؟",
      "از ارزان‌ترین تا گران‌ترین مرتبشان کن.",
      "در کدام اقامتگاه غذا سرو می‌شود؟",
      "کدام اقامتگاه به بازار نزدیک است؟",
      "کدام اقامتگاه محیط شادتر و رنگی‌تری دارد؟",
    ],
  },
];
