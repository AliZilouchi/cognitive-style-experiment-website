"use client";

import { FormEvent, ReactNode, useMemo, useState } from "react";
import { SWTS_COMMON_CONTEXT, SWTS_COMMON_CONVERSATION_INSTRUCTION, SWTS_TASKS, SwtsTaskId } from "./swts-config";

export type DemographicResponses = {
  age_range: string;
  gender: string;
  education: string;
  education_other: string;
  field: string;
  persian_first_language: string;
  vision: string;
  search_frequency: string;
  search_self_efficacy: number;
  ai_frequency: string;
  ai_self_efficacy: number;
  prior_sepid_exposure: string;
  prior_sepid_exposure_note: string;
};

export type PreTaskResponses = {
  understanding_confidence: string;
  expected_output: string;
  ready: true;
};

export type PostTaskResponses = {
  goal_clarity: number;
  difficulty: number;
  mental_effort: number;
  interaction_satisfaction: number;
  answer_satisfaction: number;
};

export type ComparativeResponses = {
  hardest_task: string;
  most_mental_effort: string;
  most_helpful_system: string;
  highest_answer_confidence: string;
  system_understanding: number;
  ease_of_use: number;
  overall_satisfaction: number;
};

const emptyDemographics: DemographicResponses = {
  age_range: "",
  gender: "",
  education: "",
  education_other: "",
  field: "",
  persian_first_language: "",
  vision: "",
  search_frequency: "",
  search_self_efficacy: 0,
  ai_frequency: "",
  ai_self_efficacy: 0,
  prior_sepid_exposure: "",
  prior_sepid_exposure_note: "",
};

const frequencyOptions = [
  ["never", "هرگز"],
  ["less_than_monthly", "کمتر از ماهی یک‌بار"],
  ["several_times_monthly", "چند بار در ماه"],
  ["about_weekly", "حدود هفته‌ای یک‌بار"],
  ["several_times_weekly", "چند بار در هفته"],
  ["almost_daily", "تقریباً هر روز"],
] as const;

export function DemographicsForm({ onSubmit }: { onSubmit: (responses: DemographicResponses) => void | Promise<void> }) {
  const [value, setValue] = useState(emptyDemographics);
  const [busy, setBusy] = useState(false);
  const update = (key: keyof DemographicResponses, next: string | number) => setValue((current) => ({ ...current, [key]: next }));
  const complete = Boolean(
    value.age_range && value.gender && value.education && value.field.trim() && value.persian_first_language &&
    value.vision && value.search_frequency && value.search_self_efficacy && value.ai_frequency &&
    value.ai_self_efficacy && value.prior_sepid_exposure &&
    (value.education !== "other" || value.education_other.trim()) &&
    (value.prior_sepid_exposure !== "yes" || value.prior_sepid_exposure_note.trim())
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete || busy) return;
    setBusy(true);
    try { await onSubmit(value); } finally { setBusy(false); }
  }

  return <form className="study-form long-form" onSubmit={submit} dir="rtl">
    <FormIntro title="پرسشنامه اطلاعات فردی و تجربه کار با ابزارهای جست‌وجو">
      اطلاعات این بخش فقط برای تحلیل پژوهش استفاده می‌شود و پاسخ درست یا غلطی وجود ندارد. لطفاً گزینه‌ای را انتخاب کنید که وضعیت شما را بهتر توصیف می‌کند.
    </FormIntro>
    <ChoiceQuestion number={1} title="سن شما چند سال است؟" value={value.age_range} onChange={(next) => update("age_range", next)} options={[["under_20","کمتر از ۲۰ سال"],["20_29","۲۰ تا ۲۹ سال"],["30_39","۳۰ تا ۳۹ سال"],["40_plus","۴۰ سال یا بیشتر"]]} />
    <ChoiceQuestion number={2} title="جنسیت شما چیست؟" value={value.gender} onChange={(next) => update("gender", next)} options={[["woman","زن"],["man","مرد"]]} />
    <ChoiceQuestion number={3} title="بالاترین مقطع تحصیلی که تکمیل کرده‌اید چیست؟" value={value.education} onChange={(next) => update("education", next)} options={[["high_school_or_lower","دیپلم یا پایین‌تر"],["associate","کاردانی"],["bachelor","کارشناسی"],["master","کارشناسی ارشد"],["doctorate","دکتری"],["other","سایر"]]} />
    {value.education === "other" && <TextQuestion title="لطفاً مقطع تحصیلی را بنویسید." value={value.education_other} onChange={(next) => update("education_other", next)} />}
    <TextQuestion number={4} title="رشته تحصیلی یا حوزه اصلی فعالیت شما چیست؟" value={value.field} onChange={(next) => update("field", next)} />
    <ChoiceQuestion number={5} title="آیا فارسی زبان اول شماست؟" value={value.persian_first_language} onChange={(next) => update("persian_first_language", next)} options={[["yes","بله"],["no","خیر"]]} />
    <ChoiceQuestion number={6} title="وضعیت بینایی شما هنگام استفاده از رایانه چگونه است؟" value={value.vision} onChange={(next) => update("vision", next)} options={[["normal","بینایی طبیعی دارم."],["corrected","با عینک یا لنز، بینایی اصلاح‌شده دارم."],["difficulty","مشکلی در بینایی دارم که ممکن است مشاهده تصاویر یا متن صفحه را دشوار کند."]]} />
    <ChoiceQuestion number={7} title="معمولاً چند وقت یک‌بار برای پیدا کردن یا یادگیری اطلاعات از موتورهای جست‌وجو مانند Google استفاده می‌کنید؟" value={value.search_frequency} onChange={(next) => update("search_frequency", next)} options={frequencyOptions} />
    <LikertQuestion number={8} title="می‌توانم برای پیدا کردن اطلاعات موردنیازم، عبارت‌های جست‌وجوی مناسبی بنویسم." value={value.search_self_efficacy} onChange={(next) => update("search_self_efficacy", next)} />
    <ChoiceQuestion number={9} title="معمولاً چند وقت یک‌بار از ابزارهای هوش مصنوعی مکالمه‌ای مانند ChatGPT، Gemini، Copilot یا ابزارهای مشابه استفاده می‌کنید؟" value={value.ai_frequency} onChange={(next) => update("ai_frequency", next)} options={frequencyOptions} />
    <LikertQuestion number={10} title="می‌توانم پرسش‌ها یا درخواست‌های مناسبی برای ابزارهای هوش مصنوعی مکالمه‌ای بنویسم." value={value.ai_self_efficacy} onChange={(next) => update("ai_self_efficacy", next)} />
    <ChoiceQuestion number={11} title="آیا پیش از شرکت در این پژوهش، متن وظایف یا اسناد مربوط به «جزیره سپید» را دیده بودید؟" value={value.prior_sepid_exposure} onChange={(next) => update("prior_sepid_exposure", next)} options={[["no","خیر"],["yes","بله"]]} />
    {value.prior_sepid_exposure === "yes" && <TextQuestion title="لطفاً کوتاه توضیح دهید." value={value.prior_sepid_exposure_note} onChange={(next) => update("prior_sepid_exposure_note", next)} multiline />}
    <FormActions busy={busy} disabled={!complete} label="ثبت و ادامه به آزمون شناختی" />
  </form>;
}

export function ThinkAloudPage({ onContinue }: { onContinue: () => void | Promise<void> }) {
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!accepted || busy) return;
    setBusy(true);
    try { await onContinue(); } finally { setBusy(false); }
  }
  return <form className="study-form think-aloud" onSubmit={submit} dir="rtl">
    <FormIntro title="راهنمای بیان افکار در حین انجام کار">
      در هنگام انجام وظیفه، لطفاً آنچه در ذهن شما می‌گذرد با صدای بلند بیان کنید.
    </FormIntro>
    <div className="instruction-callout">
      <strong>برای مثال، می‌توانید درباره موارد زیر صحبت کنید:</strong>
      <ul>
        <li>در حال حاضر قصد دارید چه کاری انجام دهید؛</li>
        <li>چرا پرسش یا درخواست خاصی را برای سامانه می‌نویسید؛</li>
        <li>درباره پاسخ سامانه چه فکری می‌کنید؛</li>
        <li>چه اطلاعاتی برای شما مفید، نامرتبط، ناقص یا مشکوک به نظر می‌رسد؛</li>
        <li>چگونه تصمیم می‌گیرید پرسش بعدی شما چه باشد؛</li>
        <li>چگونه اطلاعات تازه را با پاسخ‌های قبلی مرتبط می‌کنید و تصمیم می‌گیرید چه چیزی را بیشتر بررسی کنید؛</li>
        <li>در هر مرحله چه احساسی دارید، مانند اطمینان، تردید، سردرگمی یا رضایت.</li>
      </ul>
    </div>
    <p>لازم نیست صحبت‌های شما رسمی یا منظم باشد و نیازی نیست عملکرد خود را برای پژوهشگر توجیه کنید. فقط تلاش کنید افکاری را که به‌طور طبیعی هنگام انجام کار دارید، بیان کنید.</p>
    <p>پژوهشگر در طول انجام وظیفه به شما کمک محتوایی نخواهد کرد. اگر برای مدتی سکوت کنید، ممکن است فقط از شما خواسته شود که به بیان افکار خود ادامه دهید.</p>
    <p>پیش از شروع وظایف اصلی، یک تمرین کوتاه انجام خواهید داد تا با این روش آشنا شوید.</p>
    <label className="confirmation-row"><input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} /><span>راهنما را خواندم و آماده‌ام هنگام انجام وظایف، افکارم را با صدای بلند بیان کنم.</span></label>
    <FormActions busy={busy} disabled={!accepted} label="ادامه به وظیفه اول" />
  </form>;
}

export function PreTaskForm({ taskId, position, onSubmit }: { taskId: SwtsTaskId; position: number; onSubmit: (responses: PreTaskResponses) => void | Promise<void> }) {
  const task = SWTS_TASKS[taskId];
  const [confidence, setConfidence] = useState("");
  const [summary, setSummary] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const complete = Boolean(confidence && summary.trim() && ready);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete || busy) return;
    setBusy(true);
    try { await onSubmit({ understanding_confidence: confidence, expected_output: summary.trim(), ready: true }); } finally { setBusy(false); }
  }
  return <form className="study-form" onSubmit={submit} dir="rtl">
    <FormIntro eyebrow={`وظیفه ${position + 1} از 3 · ${task.title}`} title="بررسی درک وظیفه">
      پیش از شروع گفت‌وگو، موقعیت و هدف این وظیفه را بخوانید و مطمئن شوید که می‌دانید قرار است چه موضوعی را بررسی کنید.
    </FormIntro>
    <div className="task-brief-card"><span>زمینه مشترک</span><p>{SWTS_COMMON_CONTEXT}</p><h3>{task.title}</h3><p>{task.problem}</p><strong>هدف گفت‌وگو</strong><p>{task.objective}</p><small>{SWTS_COMMON_CONVERSATION_INSTRUCTION}</small></div>
    <ChoiceQuestion number={1} title="تا چه اندازه مطمئن هستید که موقعیت و هدف این گفت‌وگو را درک کرده‌اید؟" value={confidence} onChange={setConfidence} options={[["not_at_all","اصلاً مطمئن نیستم"],["slightly","کمی مطمئن هستم"],["somewhat","تا حدی مطمئن هستم"],["confident","مطمئن هستم"],["completely","کاملاً مطمئن هستم"]]} />
    <TextQuestion number={2} title="لطفاً در یک یا دو جمله بنویسید که در این گفت‌وگو قرار است چه موضوعی را بررسی کنید." value={summary} onChange={setSummary} multiline />
    <fieldset className="form-question readiness-question"><legend><span>3.</span> آیا برای شروع وظیفه آماده هستید؟</legend><label className={ready ? "choice-card selected" : "choice-card"}><input type="checkbox" checked={ready} onChange={(event) => setReady(event.target.checked)} /><span><strong>بله، آماده‌ام.</strong><small>ادامه فقط پس از این تأیید ممکن است.</small></span></label>{!ready && <p className="field-hint">اگر بخشی از دستورالعمل روشن نیست، پیش از ادامه از پژوهشگر بخواهید فقط همان دستورالعمل را توضیح دهد.</p>}</fieldset>
    <FormActions busy={busy} disabled={!complete} label="شروع وظیفه" />
  </form>;
}

export function PostTaskForm({ taskId, position, onSubmit }: { taskId: SwtsTaskId; position: number; onSubmit: (responses: PostTaskResponses) => void | Promise<void> }) {
  const [values, setValues] = useState<number[]>([0,0,0,0,0]);
  const [busy, setBusy] = useState(false);
  const questions = [
    "موقعیت و هدف گفت‌وگو برای من روشن بود.",
    "بررسی این موضوع برای من دشوار بود.",
    "این گفت‌وگو به تلاش ذهنی زیادی نیاز داشت.",
    "از نحوه تعامل با سامانه در این وظیفه رضایت داشتم.",
    "در پایان گفت‌وگو احساس می‌کردم موضوع را به اندازه کافی درک کرده‌ام.",
  ];
  const complete = values.every(Boolean);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete || busy) return;
    setBusy(true);
    try { await onSubmit({ goal_clarity: values[0], difficulty: values[1], mental_effort: values[2], interaction_satisfaction: values[3], answer_satisfaction: values[4] }); } finally { setBusy(false); }
  }
  return <form className="study-form" onSubmit={submit} dir="rtl">
    <FormIntro eyebrow={`پس از وظیفه ${position + 1} از 3 · ${SWTS_TASKS[taskId].title}`} title="ارزیابی تجربه انجام وظیفه">لطفاً تجربه خود در وظیفه‌ای که به‌تازگی انجام دادید ارزیابی کنید.</FormIntro>
    {questions.map((question, index) => <LikertQuestion key={question} number={index + 1} title={question} value={values[index]} onChange={(next) => setValues((current) => current.map((value, itemIndex) => itemIndex === index ? next : value))} />)}
    <FormActions busy={busy} disabled={!complete} label={position < 2 ? "ثبت و ادامه به وظیفه بعد" : "ثبت و ادامه به مقایسه نهایی"} />
  </form>;
}

export function ComparativeForm({ taskOrder, onSubmit }: { taskOrder: SwtsTaskId[]; onSubmit: (responses: ComparativeResponses) => void | Promise<void> }) {
  const tasks = useMemo(() => taskOrder.map((id) => [id, SWTS_TASKS[id].title] as const), [taskOrder]);
  const comparisonOptions = [...tasks, ["no_clear_difference", "تفاوت مشخصی نداشتند."] as const];
  const [choices, setChoices] = useState(["", "", "", ""]);
  const [ratings, setRatings] = useState([0,0,0]);
  const [busy, setBusy] = useState(false);
  const choiceQuestions = ["کدام وظیفه برای شما دشوارتر بود؟","کدام وظیفه به بیشترین تلاش ذهنی نیاز داشت؟","در کدام وظیفه سامانه بیشترین کمک را به شما کرد؟","در پایان کدام وظیفه احساس می‌کردید به درک روشن‌تری از موضوع رسیده‌اید؟"];
  const ratingQuestions = ["پس از انجام سه وظیفه، نحوه استفاده از سامانه را به‌خوبی درک کرده‌ام.","کار با سامانه برای من آسان بود.","در مجموع، از تجربه استفاده از سامانه رضایت داشتم."];
  const complete = choices.every(Boolean) && ratings.every(Boolean);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete || busy) return;
    setBusy(true);
    try { await onSubmit({ hardest_task: choices[0], most_mental_effort: choices[1], most_helpful_system: choices[2], highest_answer_confidence: choices[3], system_understanding: ratings[0], ease_of_use: ratings[1], overall_satisfaction: ratings[2] }); } finally { setBusy(false); }
  }
  return <form className="study-form" onSubmit={submit} dir="rtl">
    <FormIntro title="مقایسه نهایی وظایف">اکنون سه وظیفه را با یکدیگر مقایسه کنید. منظور از هر وظیفه همان عنوانی است که در طول مطالعه دیده‌اید.</FormIntro>
    {choiceQuestions.map((question, index) => <ChoiceQuestion key={question} number={index + 1} title={question} value={choices[index]} onChange={(next) => setChoices((current) => current.map((value, itemIndex) => itemIndex === index ? next : value))} options={comparisonOptions} />)}
    {ratingQuestions.map((question, index) => <LikertQuestion key={question} number={index + 5} title={question} value={ratings[index]} onChange={(next) => setRatings((current) => current.map((value, itemIndex) => itemIndex === index ? next : value))} />)}
    <FormActions busy={busy} disabled={!complete} label="ثبت نهایی و پایان مطالعه" />
  </form>;
}

function FormIntro({ title, eyebrow, children }: { title: string; eyebrow?: string; children: ReactNode }) {
  return <header className="form-intro">{eyebrow && <p className="card-kicker">{eyebrow}</p>}<h2>{title}</h2><p>{children}</p></header>;
}

function ChoiceQuestion({ number, title, value, onChange, options }: { number?: number; title: string; value: string; onChange: (value: string) => void; options: ReadonlyArray<readonly [string,string]> }) {
  return <fieldset className="form-question"><legend>{number && <span>{number}.</span>} {title}</legend><div className="choice-list">{options.map(([optionValue, label]) => <label className={value === optionValue ? "choice-card selected" : "choice-card"} key={optionValue}><input type="radio" name={`${title}-${number || "extra"}`} value={optionValue} checked={value === optionValue} onChange={() => onChange(optionValue)} /><span>{label}</span></label>)}</div></fieldset>;
}

function TextQuestion({ number, title, value, onChange, multiline = false }: { number?: number; title: string; value: string; onChange: (value: string) => void; multiline?: boolean }) {
  return <label className="form-question text-question"><span className="question-title">{number && <b>{number}.</b>} {title}</span>{multiline ? <textarea value={value} onChange={(event) => onChange(event.target.value)} rows={4} maxLength={2000} /> : <input value={value} onChange={(event) => onChange(event.target.value)} maxLength={300} />}</label>;
}

function LikertQuestion({ number, title, value, onChange }: { number: number; title: string; value: number; onChange: (value: number) => void }) {
  return <fieldset className="form-question likert-question"><legend><span>{number}.</span> {title}</legend><div className="likert-scale"><small>کاملاً مخالفم</small>{[1,2,3,4,5].map((rating) => <label className={value === rating ? "selected" : ""} key={rating}><input type="radio" name={`likert-${number}-${title}`} checked={value === rating} onChange={() => onChange(rating)} /><span>{rating.toLocaleString("fa-IR")}</span></label>)}<small>کاملاً موافقم</small></div></fieldset>;
}

function FormActions({ busy, disabled, label }: { busy: boolean; disabled: boolean; label: string }) {
  return <div className="form-actions"><p>همه پرسش‌ها الزامی‌اند.</p><button className="primary" disabled={disabled || busy}>{busy ? "در حال ثبت…" : label}<span aria-hidden="true">←</span></button></div>;
}
