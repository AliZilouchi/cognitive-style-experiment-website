"use client";

import { FormEvent, SyntheticEvent, useEffect, useLayoutEffect, useMemo, useState } from "react";
import NextImage from "next/image";
import ResearcherDashboard from "./researcher-dashboard";
import { ExperimentSwtsChat, loadParticipantSwtsState, SwtsTaskMeta } from "./swts-chat";
import { ComparativeForm, DemographicsForm, PostTaskForm, PreTaskForm, ThinkAloudPage } from "./study-forms";
import { SWTS_TASK_IDS, SwtsTaskId } from "./swts-config";
import { SUPABASE_KEY, SUPABASE_URL } from "./runtime-config";
import {
  ECSA_SCORING_VERSION,
  ECSA_TRIALS,
  ECSA_VERSION,
  EcsaAnswer,
  EcsaTrial,
  validateEcsaMaterials,
} from "./ecsa-materials";

type Language = "en" | "fa";
type Stage = "entry" | "introduction" | "demographics" | "test" | "think_aloud" | "pre_task" | "swts" | "post_task" | "comparative" | "complete";
type ParticipantSession = { session_id: string; participant_id: string; recovery_token: string; phase: Stage };
type PendingEvent = { id: string; sequence: number; type: string; payload: Record<string, unknown>; createdAt: string };
type TimingState = "intro" | "ready" | "responding" | "result";
type EcsaScreen = "overview" | "instructions" | "ready" | "trial" | "feedback" | "complete";
type StimulusStatus = "buffering" | "ready" | "visible" | "error";
type EcsaResponse = { trialId: string; subtest: "wholistic" | "analytic"; practice: boolean; answer?: EcsaAnswer; correct: boolean; reactionTimeMs: number };
type EcsaRunState = { currentIndex: number; responses: EcsaResponse[] };

const stimulusCache = new Map<string, Promise<void>>();

const copy = {
  en: {
    brand: "Cognitive Style Research",
    platform: "Participant Study Platform",
    admin: "Researcher view",
    freeChat: "Free chat",
    welcome: "Welcome to a study about how people think.",
    description: "This research explores different ways of thinking and how they shape decisions in a simulated work situation.",
    invitation: "Enter your invitation code",
    invitationHelp: "Use the code provided by the study supervisor.",
    codePlaceholder: "e.g. 7KM4-PQ92",
    supervised: "This is a remotely supervised research study. Your responses are recorded under a coded participant ID.",
    duration: "Please keep this window open. The full session may take up to two hours.",
    continue: "Continue",
    required: "Please enter your invitation code.",
    steps: ["Introduction", "Demographics", "Cognitive test", "Think aloud", "SWTS tasks", "Final comparison", "Complete"],
    saved: "Progress saved",
    introTitle: "Before you begin",
    introBody: "Your supervisor will guide the session. Short connection interruptions will not erase responses already recorded on this device.",
    consent: "I have read the study information and agree to continue.",
    next: "Continue to demographics",
    demoTitle: "Demographics",
    demoBody: "The final demographic questions will be configured here. This backbone keeps the form versioned and adjustable.",
    age: "Age range",
    education: "Highest education level",
    prefer: "Prefer not to say",
    demoNext: "Continue to cognitive test",
    testTitle: "Cognitive-style test",
    testBody: "Before the research test is added, this short system check verifies response timing and durable trial recording on this device.",
    diagnosticNote: "System check only — this is not an E-CSA-WA item and does not affect eligibility.",
    timingPrompt: "When the symbol appears, choose whether it is round or angular as quickly as you can.",
    startCheck: "Start timing check",
    readyPrompt: "Get ready…",
    round: "Round",
    angular: "Angular",
    recorded: "Response recorded",
    reactionTime: "Reaction time",
    repeatCheck: "Repeat check",
    testNext: "Continue to simulated work situation",
    ecsaEyebrow: "E-CSA-WA · Research test",
    ecsaReadyTitle: "Test engine ready",
    ecsaReadyBody: "The runner supports four practice items with feedback and 80 scored trials without feedback, prescribed ordering, Yes/No keyboard responses, millisecond timing, interruption flags, and safe resumption.",
    materialPending: "Verified test materials still need to be imported",
    materialPendingBody: "The application will not generate or substitute figures. Attach the approved image package and answer key to activate the research test.",
    materialCounts: "Expected: 4 practice · 40 wholistic · 40 analytic",
    testInstructionsTitle: "How to respond",
    testInstructionsBody: "For wholistic items, decide whether the two complex figures are identical. For analytic items, decide whether the simple figure is contained in the complex figure. Work accurately at a comfortable pace.",
    keyboardHelp: "Press Y for Yes or N for No. You may also use the buttons.",
    startHelp: "When you are ready, use the button below. Y and N become active only after the figure appears.",
    beginEcsa: "Start first practice item",
    resumeEcsa: "Continue E-CSA-WA",
    readyTrial: "The next item is ready",
    showTrial: "Show item",
    yes: "Yes",
    no: "No",
    correct: "Correct",
    incorrect: "Incorrect",
    yourAnswer: "Your answer",
    correctAnswer: "Correct answer",
    preparingItem: "Preparing image…",
    imageLoadError: "The image could not be prepared. Check the connection and try again.",
    retryImage: "Retry image",
    nextItem: "Next item",
    practiceLabel: "Practice",
    trialLabel: "Research item",
    wholisticLabel: "Wholistic",
    analyticLabel: "Analytic",
    testComplete: "Test complete",
    testCompleteBody: "Your raw responses and timing data have been stored. The derived score is versioned separately and is not displayed to participants.",
    chatTitle: "Simulated work situation",
    chatBody: "Eligible participants will enter the versioned chatbot scenario here. The model, eligibility rule, and final-answer form remain configurable.",
    restart: "Return to entry",
    connection: "Online",
    recovering: "Restoring session…",
  },
  fa: {
    brand: "پژوهش سبک شناختی",
    platform: "سامانه اجرای مطالعه",
    admin: "نمای پژوهشگر",
    freeChat: "گفت‌وگوی آزاد",
    welcome: "به پژوهشی درباره شیوه‌های تفکر خوش آمدید.",
    description: "این پژوهش شیوه‌های متفاوت تفکر و اثر آن‌ها بر تصمیم‌گیری در یک موقعیت کاری شبیه‌سازی‌شده را بررسی می‌کند.",
    invitation: "کد دعوت خود را وارد کنید",
    invitationHelp: "از کدی استفاده کنید که ناظر مطالعه در اختیار شما گذاشته است.",
    codePlaceholder: "برای مثال 7KM4-PQ92",
    supervised: "این مطالعه به‌صورت آنلاین و تحت نظارت اجرا می‌شود. پاسخ‌های شما با یک شناسه کدگذاری‌شده ثبت می‌شوند.",
    duration: "لطفاً این پنجره را باز نگه دارید. کل جلسه ممکن است تا دو ساعت طول بکشد.",
    continue: "ادامه",
    required: "لطفاً کد دعوت خود را وارد کنید.",
    steps: ["مقدمه", "اطلاعات فردی", "آزمون شناختی", "بیان افکار", "وظایف SWTS", "مقایسه نهایی", "پایان"],
    saved: "پیشرفت ذخیره شد",
    introTitle: "پیش از شروع",
    introBody: "ناظر، شما را در طول جلسه راهنمایی می‌کند. قطعی‌های کوتاه اینترنت پاسخ‌هایی را که در این دستگاه ثبت شده‌اند از بین نمی‌برد.",
    consent: "اطلاعات مطالعه را خوانده‌ام و با ادامه آن موافقم.",
    next: "ادامه به اطلاعات جمعیت‌شناختی",
    demoTitle: "اطلاعات جمعیت‌شناختی",
    demoBody: "پرسش‌های نهایی جمعیت‌شناختی در این بخش تنظیم می‌شوند. ساختار سامانه امکان نسخه‌بندی و تغییر فرم را حفظ می‌کند.",
    age: "بازه سنی",
    education: "بالاترین مقطع تحصیلی",
    prefer: "ترجیح می‌دهم پاسخ ندهم",
    demoNext: "ادامه به آزمون شناختی",
    testTitle: "آزمون سبک شناختی",
    testBody: "پیش از افزودن آزمون پژوهشی، این بررسی کوتاه صحت زمان‌سنجی پاسخ و ثبت پایدار داده را روی این دستگاه آزمایش می‌کند.",
    diagnosticNote: "این فقط بررسی سامانه است؛ بخشی از E-CSA-WA نیست و بر واجد شرایط بودن اثر ندارد.",
    timingPrompt: "پس از نمایش نماد، در سریع‌ترین زمان مشخص کنید گرد است یا زاویه‌دار.",
    startCheck: "شروع بررسی زمان‌سنجی",
    readyPrompt: "آماده باشید…",
    round: "گرد",
    angular: "زاویه‌دار",
    recorded: "پاسخ ثبت شد",
    reactionTime: "زمان واکنش",
    repeatCheck: "تکرار بررسی",
    testNext: "ادامه به موقعیت کاری شبیه‌سازی‌شده",
    ecsaEyebrow: "E-CSA-WA · آزمون پژوهشی",
    ecsaReadyTitle: "موتور آزمون آماده است",
    ecsaReadyBody: "سامانه از چهار سؤال تمرینی همراه بازخورد و ۸۰ سؤال اصلی بدون بازخورد، ترتیب ازپیش‌تعیین‌شده، پاسخ بله/خیر با صفحه‌کلید، زمان‌سنجی میلی‌ثانیه‌ای، ثبت وقفه‌ها و ادامه امن آزمون پشتیبانی می‌کند.",
    materialPending: "محتوای تأییدشده آزمون هنوز باید وارد شود",
    materialPendingBody: "سامانه هیچ شکل جایگزین یا ساختگی تولید نمی‌کند. برای فعال‌سازی آزمون، بسته تصاویر و کلید پاسخ تأییدشده را پیوست کنید.",
    materialCounts: "مورد انتظار: ۴ تمرینی · ۴۰ کل‌نگر · ۴۰ تحلیلی",
    testInstructionsTitle: "روش پاسخ‌دادن",
    testInstructionsBody: "در سؤال‌های کل‌نگر مشخص کنید دو شکل پیچیده یکسان هستند یا خیر. در سؤال‌های تحلیلی مشخص کنید شکل ساده در شکل پیچیده وجود دارد یا خیر. با دقت و با سرعت راحت خود پاسخ دهید.",
    keyboardHelp: "برای بله کلید Y و برای خیر کلید N را بزنید. دکمه‌های صفحه نیز قابل استفاده‌اند.",
    startHelp: "وقتی آماده بودید دکمه زیر را بزنید. کلیدهای Y و N فقط پس از نمایش شکل فعال می‌شوند.",
    beginEcsa: "شروع اولین سؤال تمرینی",
    resumeEcsa: "ادامه آزمون E-CSA-WA",
    readyTrial: "سؤال بعدی آماده است",
    showTrial: "نمایش سؤال",
    yes: "بله",
    no: "خیر",
    correct: "درست",
    incorrect: "نادرست",
    yourAnswer: "پاسخ شما",
    correctAnswer: "پاسخ صحیح",
    preparingItem: "در حال آماده‌سازی تصویر…",
    imageLoadError: "تصویر آماده نشد. اتصال را بررسی و دوباره تلاش کنید.",
    retryImage: "تلاش دوباره",
    nextItem: "سؤال بعدی",
    practiceLabel: "تمرینی",
    trialLabel: "سؤال اصلی",
    wholisticLabel: "کل‌نگر",
    analyticLabel: "تحلیلی",
    testComplete: "آزمون کامل شد",
    testCompleteBody: "پاسخ‌های خام و داده‌های زمانی شما ذخیره شدند. امتیاز محاسبه‌شده به‌صورت جداگانه نسخه‌بندی می‌شود و به شرکت‌کننده نمایش داده نمی‌شود.",
    chatTitle: "موقعیت کاری شبیه‌سازی‌شده",
    chatBody: "شرکت‌کنندگان واجد شرایط در این بخش وارد سناریوی نسخه‌بندی‌شده گفت‌وگو می‌شوند. مدل، شرط ورود و فرم پاسخ نهایی قابل تنظیم باقی می‌مانند.",
    restart: "بازگشت به ورودی",
    connection: "متصل",
    recovering: "در حال بازیابی جلسه…",
  },
};

const stageIndex: Record<Stage, number> = { entry: 0, introduction: 0, demographics: 1, test: 2, think_aloud: 3, pre_task: 4, swts: 4, post_task: 4, comparative: 5, complete: 6 };

export default function Home() {
  const [adminMode, setAdminMode] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [previewEvents, setPreviewEvents] = useState<Array<{ type: string; payload: Record<string, unknown> }>>([]);
  const [previewRagFailure, setPreviewRagFailure] = useState(false);
  const [language, setLanguage] = useState<Language>("fa");
  const [stage, setStage] = useState<Stage>("entry");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [checkingCode, setCheckingCode] = useState(false);
  const [consent, setConsent] = useState(false);
  const [online, setOnline] = useState(true);
  const [session, setSession] = useState<ParticipantSession | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<SwtsTaskId>("task_1");
  const [currentTaskPosition, setCurrentTaskPosition] = useState(0);
  const [taskOrder, setTaskOrder] = useState<SwtsTaskId[]>(SWTS_TASK_IDS);
  const [completedTask, setCompletedTask] = useState<{ taskId: SwtsTaskId; position: number } | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [timingState, setTimingState] = useState<TimingState>("intro");
  const [trialStart, setTrialStart] = useState(0);
  const [reactionTime, setReactionTime] = useState<number | null>(null);
  const [pageHidden, setPageHidden] = useState(false);
  const [focusLostCount, setFocusLostCount] = useState(0);
  const [ecsaScreen, setEcsaScreen] = useState<EcsaScreen>("overview");
  const [ecsaIndex, setEcsaIndex] = useState(0);
  const [ecsaResponses, setEcsaResponses] = useState<EcsaResponse[]>([]);
  const [ecsaTrialStart, setEcsaTrialStart] = useState(0);
  const [ecsaFeedback, setEcsaFeedback] = useState<boolean | null>(null);
  const [ecsaSelectedAnswer, setEcsaSelectedAnswer] = useState<EcsaAnswer | null>(null);
  const [stimulusStatus, setStimulusStatus] = useState<StimulusStatus>("buffering");
  const t = copy[language];
  const rtl = language === "fa";
  const materialStatus = useMemo(() => validateEcsaMaterials(ECSA_TRIALS), []);
  const currentEcsaTrial = ECSA_TRIALS[ecsaIndex] as EcsaTrial | undefined;

  useEffect(() => {
    const stored = window.localStorage.getItem("study-language") as Language | null;
    // Restore browser-only preferences after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (stored === "fa" || stored === "en") setLanguage(stored);
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    const saved = window.localStorage.getItem("study-participant-session");
    const savedRun = window.localStorage.getItem("study-ecsa-run");
    const savedSwts = window.localStorage.getItem("study-swts-current");
    const savedCompletedTask = window.localStorage.getItem("study-swts-completed-task");
    if (savedSwts) {
      try {
        const parsed = JSON.parse(savedSwts) as SwtsTaskMeta;
        setCurrentTaskId(parsed.taskId);
        setCurrentTaskPosition(parsed.position);
        setTaskOrder(parsed.order);
      } catch { window.localStorage.removeItem("study-swts-current"); }
    }
    if (savedCompletedTask) {
      try { setCompletedTask(JSON.parse(savedCompletedTask)); }
      catch { window.localStorage.removeItem("study-swts-completed-task"); }
    }
    if (savedRun) {
      try {
        const parsed = JSON.parse(savedRun) as EcsaRunState;
        setEcsaIndex(parsed.currentIndex || 0);
        setEcsaResponses(parsed.responses || []);
        setEcsaScreen("instructions");
      } catch { window.localStorage.removeItem("study-ecsa-run"); }
    }
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as ParticipantSession;
        setSession(parsed);
        restoreSession(parsed).finally(() => setRestoring(false));
      } catch { setRestoring(false); }
    } else setRestoring(false);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  // Session restoration intentionally runs once at application start.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Retry the durable local queue when connectivity or the active session changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (online && session) void flushEvents(session); }, [online, session]);

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = rtl ? "rtl" : "ltr";
    window.localStorage.setItem("study-language", language);
  }, [language, rtl]);

  useEffect(() => {
    const markHidden = () => { if (document.hidden && timingState === "responding") setPageHidden(true); };
    const markEcsaHidden = () => {
      if (ecsaScreen === "trial" && (document.hidden || !document.hasFocus())) {
        setPageHidden(true);
        setFocusLostCount((value) => value + 1);
      }
    };
    document.addEventListener("visibilitychange", markHidden);
    document.addEventListener("visibilitychange", markEcsaHidden);
    window.addEventListener("blur", markEcsaHidden);
    return () => {
      document.removeEventListener("visibilitychange", markHidden);
      document.removeEventListener("visibilitychange", markEcsaHidden);
      window.removeEventListener("blur", markEcsaHidden);
    };
  }, [timingState, ecsaScreen]);

  useLayoutEffect(() => {
    if (ecsaScreen !== "trial" || stimulusStatus !== "visible" || ecsaTrialStart > 0) return;
    const frame = window.requestAnimationFrame(() => setEcsaTrialStart(performance.now()));
    return () => window.cancelAnimationFrame(frame);
  }, [ecsaScreen, stimulusStatus, ecsaTrialStart]);

  useEffect(() => {
    if (ecsaScreen !== "trial") return;
    const onKey = (event: KeyboardEvent) => {
      if (event.repeat) return;
      if (event.key.toLowerCase() === "y") void answerEcsa("yes", "keyboard");
      if (event.key.toLowerCase() === "n") void answerEcsa("no", "keyboard");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  // answerEcsa intentionally reads the current render's trial and timing state.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ecsaScreen, ecsaTrialStart, currentEcsaTrial]);

  const progress = useMemo(() => stageIndex[stage], [stage]);

  async function rpc(name: string, body: Record<string, unknown>) {
    return fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
      method: "POST",
      headers: { apikey: SUPABASE_KEY, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async function restoreSession(saved: ParticipantSession) {
    try {
      const response = await rpc("restore_participant_session", { p_session_id: saved.session_id, p_recovery_token: saved.recovery_token });
      const result = await response.json();
      if (response.ok && result?.accepted) {
        const restoredStage = (result.phase === "chat" ? "swts" : result.phase) as Stage;
        setStage(restoredStage);
        setSession({ ...saved, phase: restoredStage });
        await flushEvents(saved);
      } else throw new Error();
    } catch { setStage(saved.phase || "introduction"); }
  }

  function readQueue(): PendingEvent[] {
    try { return JSON.parse(window.localStorage.getItem("study-pending-events") || "[]"); }
    catch { return []; }
  }

  async function flushEvents(active: ParticipantSession) {
    const queue = readQueue();
    for (const item of queue) {
      try {
        const response = await rpc("save_participant_event", {
          p_session_id: active.session_id, p_recovery_token: active.recovery_token,
          p_event_id: item.id, p_sequence_number: item.sequence, p_event_type: item.type,
          p_event_payload: item.payload, p_client_created_at: item.createdAt,
        });
        if (!response.ok || !(await response.json())?.accepted) break;
        window.localStorage.setItem("study-pending-events", JSON.stringify(readQueue().filter((event) => event.id !== item.id)));
      } catch { break; }
    }
  }

  async function recordEvent(type: string, payload: Record<string, unknown>, nextStage: Stage) {
    if (!session) return;
    if (previewMode) {
      setPreviewEvents((events) => [...events, { type, payload: { ...payload, phase: nextStage } }]);
      setStage(nextStage);
      return;
    }
    const next: ParticipantSession = { ...session, phase: nextStage };
    const queue = readQueue();
    queue.push({ id: crypto.randomUUID(), sequence: (Date.now() * 1000) + Math.floor(Math.random() * 1000), type, payload: { ...payload, phase: nextStage }, createdAt: new Date().toISOString() });
    window.localStorage.setItem("study-pending-events", JSON.stringify(queue));
    window.localStorage.setItem("study-participant-session", JSON.stringify(next));
    setSession(next);
    setStage(nextStage);
    if (navigator.onLine) await flushEvents(next);
  }

  function applyTaskMeta(meta: SwtsTaskMeta) {
    setCurrentTaskId(meta.taskId);
    setCurrentTaskPosition(meta.position);
    setTaskOrder(meta.order);
    if (!previewMode) window.localStorage.setItem("study-swts-current", JSON.stringify(meta));
  }

  async function prepareFirstSwtsTask() {
    if (!session) return;
    if (previewMode) {
      applyTaskMeta({ taskId: currentTaskId, position: currentTaskPosition, order: taskOrder });
    } else {
      const state = await loadParticipantSwtsState(session);
      if (!state.task_id) throw new Error("swts_task_unavailable");
      applyTaskMeta({ taskId: state.task_id, position: state.current_position, order: state.task_order });
    }
    await recordEvent("think_aloud_acknowledged", { version: "think-aloud-fa-v1", acknowledged: true }, "pre_task");
  }

  async function handleTaskComplete(meta: SwtsTaskMeta & { finalResponse: string; completed: boolean }) {
    applyTaskMeta(meta);
    const completed = { taskId: meta.taskId, position: meta.position };
    setCompletedTask(completed);
    if (!previewMode) window.localStorage.setItem("study-swts-completed-task", JSON.stringify(completed));
    await recordEvent("swts_task_answer_submitted", { version: "swts-task-answer-v2", task_id: meta.taskId, task_position: meta.position, final_response: meta.finalResponse }, "post_task");
  }

  async function continueAfterPostTask(responses: unknown) {
    if (!completedTask) return;
    const isLast = completedTask.position >= 2;
    await recordEvent("swts_post_task_submitted", { version: "swts-post-task-fa-v1", task_id: completedTask.taskId, task_position: completedTask.position, responses }, isLast ? "comparative" : "pre_task");
    if (!isLast) {
      if (previewMode) {
        const nextPosition = completedTask.position + 1;
        applyTaskMeta({ taskId: taskOrder[nextPosition] || SWTS_TASK_IDS[nextPosition], position: nextPosition, order: taskOrder });
      } else if (session) {
        const state = await loadParticipantSwtsState(session);
        if (state.task_id) applyTaskMeta({ taskId: state.task_id, position: state.current_position, order: state.task_order });
      }
      setCompletedTask(null);
      if (!previewMode) window.localStorage.removeItem("study-swts-completed-task");
    }
  }

  function openPreview() {
    const fakeSession: ParticipantSession = { session_id: "00000000-0000-4000-8000-000000000001", participant_id: "00000000-0000-4000-8000-000000000002", recovery_token: "preview-only" , phase: "introduction" };
    setAdminMode(false);
    setPreviewMode(true);
    setPreviewEvents([]);
    setPreviewRagFailure(false);
    setSession(fakeSession);
    setStage("introduction");
    setCurrentTaskId("task_1");
    setCurrentTaskPosition(0);
    setTaskOrder(SWTS_TASK_IDS);
    setCompletedTask(null);
    setEcsaIndex(0);
    setEcsaResponses([]);
    setEcsaScreen("overview");
  }

  function leavePreview() {
    setPreviewMode(false);
    setSession(null);
    setStage("entry");
    setAdminMode(true);
  }

  function jumpPreview(nextStage: Stage) {
    setStage(nextStage);
    if (nextStage === "test") setEcsaScreen("overview");
    if (nextStage === "post_task") setCompletedTask({ taskId: currentTaskId, position: currentTaskPosition });
  }

  function startTimingCheck() {
    setReactionTime(null);
    setPageHidden(false);
    setTimingState("ready");
    window.setTimeout(() => {
      window.requestAnimationFrame(() => {
        setTrialStart(performance.now());
        setTimingState("responding");
      });
    }, 700);
  }

  async function answerTimingCheck(response: "round" | "angular", inputMethod: string) {
    if (timingState !== "responding") return;
    const measured = Math.round((performance.now() - trialStart) * 100) / 100;
    setReactionTime(measured);
    setTimingState("result");
    await recordEvent("timing_check_completed", {
      version: "engine-check-0.1", trial_id: `timing-check-${Date.now()}`, trial_index: 0,
      response, reaction_time_ms: measured, page_hidden: pageHidden, input_method: inputMethod,
    }, "test");
  }

  function persistEcsaRun(currentIndex: number, responses: EcsaResponse[]) {
    if (previewMode) return;
    window.localStorage.setItem("study-ecsa-run", JSON.stringify({ currentIndex, responses } satisfies EcsaRunState));
  }

  function preloadAsset(src: string) {
    const existing = stimulusCache.get(src);
    if (existing) return existing;
    const pending = new Promise<void>((resolve, reject) => {
      const image = new window.Image();
      image.onload = async () => {
        try { if (image.decode) await image.decode(); } catch { /* onload already confirms usable pixels */ }
        resolve();
      };
      image.onerror = () => reject(new Error(`Unable to load ${src}`));
      image.src = src;
    });
    stimulusCache.set(src, pending);
    pending.catch(() => stimulusCache.delete(src));
    return pending;
  }

  function bufferUpcomingTrials(startIndex: number) {
    ECSA_TRIALS.slice(startIndex, startIndex + 4).forEach((trial) => void preloadAsset(trial.asset).catch(() => undefined));
  }

  async function prepareCurrentTrial(index = ecsaIndex) {
    const trial = ECSA_TRIALS[index];
    if (!trial) return;
    setStimulusStatus("buffering");
    try {
      await preloadAsset(trial.asset);
      setStimulusStatus("ready");
      bufferUpcomingTrials(index + 1);
    } catch {
      setStimulusStatus("error");
    }
  }

  function beginEcsa() {
    if (!materialStatus.valid || !ECSA_TRIALS[ecsaIndex]) return;
    persistEcsaRun(ecsaIndex, ecsaResponses);
    setEcsaScreen("ready");

    // Starting the participant UI must never wait for the network. Preloading
    // and durable event synchronization are best-effort background work.
    void prepareCurrentTrial(ecsaIndex);
    if (ecsaResponses.length === 0) {
      void recordEvent("ecsa_test_started", {
        test_version: ECSA_VERSION,
        scoring_version: ECSA_SCORING_VERSION,
        trial_order: ECSA_TRIALS.map((trial) => trial.id),
      }, "test");
    }
  }

  function showEcsaTrial() {
    if (stimulusStatus !== "ready") return;
    setPageHidden(false);
    setFocusLostCount(0);
    setEcsaFeedback(null);
    setEcsaSelectedAnswer(null);
    setEcsaTrialStart(0);
    setStimulusStatus("buffering");
    setEcsaScreen("trial");
  }

  async function revealStimulus(event: SyntheticEvent<HTMLImageElement>) {
    try { if (event.currentTarget.decode) await event.currentTarget.decode(); } catch { /* loaded image remains displayable */ }
    setStimulusStatus("visible");
  }

  function answerEcsa(answer: EcsaAnswer, inputMethod: "keyboard" | "pointer") {
    if (ecsaScreen !== "trial" || !currentEcsaTrial || ecsaTrialStart <= 0) return;
    const reactionTimeMs = Math.round((performance.now() - ecsaTrialStart) * 100) / 100;
    const correct = answer === currentEcsaTrial.correctAnswer;
    const response: EcsaResponse = {
      trialId: currentEcsaTrial.id,
      subtest: currentEcsaTrial.subtest,
      practice: currentEcsaTrial.practice,
      answer,
      correct,
      reactionTimeMs,
    };
    const nextResponses = [...ecsaResponses, response];
    setEcsaResponses(nextResponses);
    setEcsaFeedback(correct);
    setEcsaSelectedAnswer(answer);
    persistEcsaRun(ecsaIndex, nextResponses);
    void recordEvent("ecsa_trial_completed", {
      test_version: ECSA_VERSION,
      scoring_version: ECSA_SCORING_VERSION,
      trial_id: currentEcsaTrial.id,
      trial_index: ecsaIndex,
      subtest: currentEcsaTrial.subtest,
      is_practice: currentEcsaTrial.practice,
      response: answer,
      correct_answer: currentEcsaTrial.correctAnswer,
      is_correct: correct,
      reaction_time_ms: reactionTimeMs,
      page_hidden: pageHidden,
      focus_lost_count: focusLostCount,
      timed_out: false,
      input_method: inputMethod,
      viewport: { width: window.innerWidth, height: window.innerHeight, pixel_ratio: window.devicePixelRatio },
    }, "test");
    if (currentEcsaTrial.practice) setEcsaScreen("feedback");
    else advanceEcsa(nextResponses);
  }

  function advanceEcsa(responses = ecsaResponses) {
    const nextIndex = ecsaIndex + 1;
    if (nextIndex < ECSA_TRIALS.length) {
      setEcsaIndex(nextIndex);
      persistEcsaRun(nextIndex, responses);
      setEcsaScreen("ready");
      void prepareCurrentTrial(nextIndex);
      return;
    }

    const analytic = responses.filter((item) => !item.practice && item.correct && item.subtest === "analytic").map((item) => item.reactionTimeMs);
    const wholistic = responses.filter((item) => !item.practice && item.correct && item.subtest === "wholistic").map((item) => item.reactionTimeMs);
    const analyticMedian = median(analytic);
    const wholisticMedian = median(wholistic);
    const ratio = analyticMedian > 0 ? wholisticMedian / analyticMedian : 0;
    if (!previewMode) window.localStorage.removeItem("study-ecsa-run");
    setEcsaScreen("complete");
    void recordEvent("ecsa_test_completed", {
      test_version: ECSA_VERSION,
      scoring_version: ECSA_SCORING_VERSION,
      analytic_median_ms: analyticMedian,
      wholistic_median_ms: wholisticMedian,
      wholistic_analytic_ratio: Math.round(ratio * 1_000_000) / 1_000_000,
      correct_analytic_count: analytic.length,
      correct_wholistic_count: wholistic.length,
    }, "think_aloud");
  }

  async function enterStudy(event: FormEvent) {
    event.preventDefault();
    if (!code.trim()) { setError(t.required); return; }
    setError("");
    setCheckingCode(true);
    try {
      const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/redeem_invitation`, {
        method: "POST",
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${SUPABASE_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ invitation_code: code.trim().toUpperCase() }),
      });
      if (!response.ok) throw new Error("invitation_rejected");
      const result = await response.json();
      if (!result?.accepted) throw new Error("invitation_rejected");
      const created = { ...result, phase: "introduction" } as ParticipantSession;
      window.localStorage.setItem("study-participant-session", JSON.stringify(created));
      setSession(created);
      setStage("introduction");
    } catch {
      setError(language === "fa" ? "کد دعوت معتبر نیست یا قبلاً استفاده شده است." : "This invitation code is invalid or has already been used.");
    } finally {
      setCheckingCode(false);
    }
  }

  return (
    <main className="site-shell" dir={rtl ? "rtl" : "ltr"}>
      <header className="topbar">
        <div className="wordmark">
          <span className="brand">{t.brand}</span>
          <span className="rule" aria-hidden="true" />
          <span className="platform">{t.platform}</span>
        </div>
        <div className="header-actions">
          <span className={`connection ${online ? "online" : "offline"}`}><i />{online ? t.connection : "Offline"}</span>
          <a className="admin-link" href="/free-chat">{t.freeChat}</a>
          <button className="admin-link" type="button" onClick={() => setAdminMode(true)}>{t.admin}</button>
          <div className="language-switch" aria-label="Language">
            <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button>
            <button className={language === "fa" ? "active" : ""} onClick={() => setLanguage("fa")}>فا</button>
          </div>
        </div>
      </header>

      {adminMode ? <ResearcherDashboard language={language} rtl={rtl} online={online} onBack={() => setAdminMode(false)} onOpenPreview={openPreview} /> : restoring ? <section className="content stage-content"><div className="stage-header"><h1>{t.recovering}</h1></div></section> : <section className={`content ${stage === "entry" ? "entry-grid" : "stage-content"}`}>
        {previewMode && <PreviewToolbar stage={stage} taskId={currentTaskId} taskPosition={currentTaskPosition} taskOrder={taskOrder} eventCount={previewEvents.length} ragFailure={previewRagFailure} onStage={jumpPreview} onTask={(taskId) => { setCurrentTaskId(taskId); setCurrentTaskPosition(taskOrder.indexOf(taskId)); }} onOrder={(order) => { setTaskOrder(order); setCurrentTaskId(order[0]); setCurrentTaskPosition(0); }} onRagFailure={setPreviewRagFailure} onReset={openPreview} onExit={leavePreview} />}
        {stage === "entry" ? <div className="intro-column">
          <p className="eyebrow">E-CSA-WA · SWTS</p>
          <h1>{t.welcome}</h1>
          <p className="lead">{t.description}</p>
          <Progress steps={t.steps} current={progress} rtl={rtl} />
          <div className="contours" aria-hidden="true"><span /><span /><span /></div>
        </div> : <div className="stage-header">
          <div className="stage-heading"><p className="eyebrow">E-CSA-WA · SWTS</p><h1>{t.steps[progress]}</h1><span>{t.saved}</span></div>
          <Progress steps={t.steps} current={progress} rtl={rtl} />
        </div>}

        {stage === "entry" ? (
          <form className="card invitation-card" onSubmit={enterStudy}>
            <p className="card-kicker">01 · {t.steps[0]}</p>
            <h2>{t.invitation}</h2>
            <p className="muted">{t.invitationHelp}</p>
            <label className="sr-only" htmlFor="invitation">{t.invitation}</label>
            <input id="invitation" value={code} onChange={(e) => setCode(e.target.value)} placeholder={t.codePlaceholder} autoComplete="off" />
            {error && <p className="error" role="alert">{error}</p>}
            <div className="notice"><LockIcon /><div><p>{t.supervised}</p><p>{t.duration}</p></div></div>
            <button className="primary" type="submit" disabled={checkingCode}>{checkingCode ? (language === "fa" ? "در حال بررسی…" : "Checking…") : t.continue}<Arrow rtl={rtl} /></button>
          </form>
        ) : (
          <section className={`card phase-card ${stage === "swts" ? "swts-phase-card" : ""} ${stage === "demographics" ? "form-phase-card" : ""}`}>
            {stage === "introduction" && <>
              <p className="card-kicker">01 · {t.steps[0]}</p><h2>{t.introTitle}</h2><p className="phase-copy">{t.introBody}</p>
              <label className="check-row"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span>{t.consent}</span></label>
              <button className="primary" disabled={!consent} onClick={() => recordEvent("consent_submitted", { version: "0.1", accepted: true }, "demographics")}>{t.next}<Arrow rtl={rtl} /></button>
            </>}
            {stage === "demographics" && <>
              <DemographicsForm onSubmit={(responses) => recordEvent("demographics_submitted", { version: "demographics-fa-v2", responses }, "test")} />
            </>}
            {stage === "test" && <>
              <p className="card-kicker">03 · {t.ecsaEyebrow}</p><h2>{t.testTitle}</h2>
              {ecsaScreen === "overview" && <>
                <div className="engine-status">
                  <div><span className={materialStatus.valid ? "status-dot ready" : "status-dot pending"} /><strong>{t.ecsaReadyTitle}</strong></div>
                  <p>{t.ecsaReadyBody}</p>
                  <ul>
                    <li>{t.materialCounts}</li>
                    <li>{language === "fa" ? `وضعیت فعلی: ${materialStatus.total} از ۸۴ مورد` : `Current package: ${materialStatus.total} of 84 items`}</li>
                    <li>{language === "fa" ? "امتیاز: میانه زمان کل‌نگر ÷ میانه زمان تحلیلی" : "Score: median wholistic RT ÷ median analytic RT"}</li>
                  </ul>
                </div>
                {!materialStatus.valid ? <div className="material-warning" role="status"><strong>{t.materialPending}</strong><p>{t.materialPendingBody}</p></div> :
                  <button className="primary" onClick={() => setEcsaScreen("instructions")}>{ecsaResponses.length ? t.resumeEcsa : t.beginEcsa}<Arrow rtl={rtl} /></button>}
                {!materialStatus.valid && <details className="system-check"><summary>{language === "fa" ? "باز کردن بررسی زمان‌سنجی سامانه" : "Open system timing check"}</summary>
                  {timingState === "intro" && <><p className="diagnostic-note">{t.diagnosticNote}</p><button className="secondary" onClick={startTimingCheck}>{t.startCheck}</button></>}
                  {timingState === "ready" && <div className="timing-stage" role="status"><span className="pulse-dot" /><h3>{t.readyPrompt}</h3></div>}
                  {timingState === "responding" && <div className="timing-stage"><p>{t.timingPrompt}</p><div className="trial-symbol" aria-label="round symbol">●</div><div className="response-grid"><button onPointerDown={() => answerTimingCheck("round", "pointer")}>{t.round}</button><button onPointerDown={() => answerTimingCheck("angular", "pointer")}>{t.angular}</button></div></div>}
                  {timingState === "result" && <div className="timing-result" aria-live="polite"><span>{t.recorded}</span><strong>{reactionTime?.toFixed(2)} ms</strong><p>{t.reactionTime}</p><button className="secondary compact" onClick={startTimingCheck}>{t.repeatCheck}</button></div>}
                </details>}
              </>}
              {ecsaScreen === "instructions" && <div className="ecsa-instructions">
                <h3>{t.testInstructionsTitle}</h3><p>{t.testInstructionsBody}</p>
                <div className="practice-banner"><strong>ابتدا ۴ سؤال تمرینی</strong><span>در سؤال‌های تمرینی پاسخ صحیح را همراه همان تصویر می‌بینید. پس از پایان تمرین، ۸۰ سؤال اصلی بدون بازخورد آغاز می‌شوند.</span></div>
                <button className="primary ecsa-start" autoFocus onClick={beginEcsa}>{ecsaResponses.length ? t.resumeEcsa : t.beginEcsa}<Arrow rtl={rtl} /></button>
                <div className="key-help"><kbd>Y</kbd><span>{t.yes}</span><kbd>N</kbd><span>{t.no}</span></div><small>{t.keyboardHelp}</small><small>{t.startHelp}</small>
              </div>}
              {ecsaScreen === "ready" && currentEcsaTrial && <div className="ecsa-ready"><span>{currentEcsaTrial.practice ? t.practiceLabel : t.trialLabel}</span><strong>{ecsaIndex + 1} / {ECSA_TRIALS.length}</strong><h3>{stimulusStatus === "error" ? t.imageLoadError : stimulusStatus === "buffering" ? t.preparingItem : t.readyTrial}</h3>{stimulusStatus === "error" ? <button className="secondary" onClick={() => void prepareCurrentTrial()}>{t.retryImage}</button> : <button className="primary" disabled={stimulusStatus !== "ready"} onClick={showEcsaTrial}>{t.showTrial}</button>}</div>}
              {ecsaScreen === "trial" && currentEcsaTrial && <div className="ecsa-trial" aria-live="polite">
                <div className="trial-meta"><span>{currentEcsaTrial.practice ? t.practiceLabel : t.trialLabel}</span><span>{currentEcsaTrial.subtest === "wholistic" ? t.wholisticLabel : t.analyticLabel}</span><span>{ecsaIndex + 1} / {ECSA_TRIALS.length}</span></div>
                <figure className={`stimulus-frame ${currentEcsaTrial.subtest} ${stimulusStatus === "visible" ? "is-visible" : "is-buffering"}`}><NextImage key={currentEcsaTrial.asset} src={currentEcsaTrial.asset} alt={currentEcsaTrial.subtest === "wholistic" ? "Wholistic comparison item" : "Analytic containment item"} width={900} height={450} unoptimized draggable={false} priority onLoad={revealStimulus} onError={() => setStimulusStatus("error")} />{stimulusStatus !== "visible" && <span className="stimulus-loader" role="status">{stimulusStatus === "error" ? t.imageLoadError : t.preparingItem}</span>}</figure>
                <div className="response-grid"><button disabled={ecsaTrialStart <= 0} onPointerDown={() => answerEcsa("yes", "pointer")}><kbd>Y</kbd>{t.yes}</button><button disabled={ecsaTrialStart <= 0} onPointerDown={() => answerEcsa("no", "pointer")}><kbd>N</kbd>{t.no}</button></div>
              </div>}
              {ecsaScreen === "feedback" && currentEcsaTrial?.practice && <div className={`ecsa-feedback ${ecsaFeedback ? "correct" : "incorrect"}`} aria-live="assertive">
                <figure className="stimulus-frame feedback-stimulus"><NextImage src={currentEcsaTrial.asset} alt={currentEcsaTrial.subtest === "wholistic" ? "Wholistic comparison item" : "Analytic containment item"} width={900} height={450} unoptimized draggable={false} /></figure>
                <div className="feedback-summary"><span className="feedback-mark">{ecsaFeedback ? "✓" : "×"}</span><div><h3>{ecsaFeedback ? t.correct : t.incorrect}</h3><p>{t.yourAnswer}: <strong>{ecsaSelectedAnswer === "yes" ? t.yes : t.no}</strong> · {t.correctAnswer}: <strong>{currentEcsaTrial.correctAnswer === "yes" ? t.yes : t.no}</strong></p></div></div>
                <button className="primary" onClick={() => advanceEcsa()}>{t.nextItem}<Arrow rtl={rtl} /></button>
              </div>}
              {ecsaScreen === "complete" && <div className="ecsa-feedback ecsa-complete"><span>✓</span><h3>{t.testComplete}</h3><p>{t.testCompleteBody}</p><button className="primary" onClick={() => recordEvent("ecsa_stage_confirmed", { version: ECSA_VERSION }, "think_aloud")}>ادامه به راهنمای بیان افکار<Arrow rtl={rtl} /></button></div>}
            </>}
            {stage === "think_aloud" && <ThinkAloudPage onContinue={prepareFirstSwtsTask} />}
            {stage === "pre_task" && <PreTaskForm key={`${currentTaskId}-${currentTaskPosition}`} taskId={currentTaskId} position={currentTaskPosition} onSubmit={(responses) => recordEvent("swts_pre_task_submitted", { version: "swts-pre-task-fa-v1", task_id: currentTaskId, task_position: currentTaskPosition, responses }, "swts")} />}
            {stage === "swts" && session && <ExperimentSwtsChat key={`${previewMode ? "preview" : "experiment"}-${currentTaskId}-${currentTaskPosition}`} session={session} mode={previewMode ? "preview" : "experiment"} previewTaskId={currentTaskId} previewPosition={currentTaskPosition} previewOrder={taskOrder} simulateRagFailure={previewRagFailure} onTaskLoaded={(meta) => { applyTaskMeta(meta); void recordEvent("swts_task_opened", { version: "swts-flow-v2", task_id: meta.taskId, task_position: meta.position }, "swts"); }} onTaskComplete={handleTaskComplete} />}
            {stage === "post_task" && completedTask && <PostTaskForm key={`${completedTask.taskId}-${completedTask.position}`} taskId={completedTask.taskId} position={completedTask.position} onSubmit={(responses) => continueAfterPostTask(responses)} />}
            {stage === "comparative" && <ComparativeForm taskOrder={taskOrder} onSubmit={(responses) => recordEvent("final_comparative_submitted", { version: "final-comparative-fa-v1", task_order: taskOrder, responses }, "complete")} />}
            {stage === "complete" && <div className="study-complete"><span>✓</span><p className="card-kicker">پایان مطالعه</p><h2>از همراهی شما سپاسگزاریم</h2><p>تمام بخش‌ها کامل شدند. لطفاً این صفحه را باز نگه دارید و به پژوهشگر اطلاع دهید.</p>{previewMode && <button className="primary" onClick={leavePreview}>بازگشت به داشبورد پژوهشگر</button>}</div>}
          </section>
        )}
      </section>}
      <footer><span>Research prototype · v0.1</span><span>English / فارسی</span></footer>
    </main>
  );
}

function PreviewToolbar({ stage, taskId, taskPosition, taskOrder, eventCount, ragFailure, onStage, onTask, onOrder, onRagFailure, onReset, onExit }: {
  stage: Stage;
  taskId: SwtsTaskId;
  taskPosition: number;
  taskOrder: SwtsTaskId[];
  eventCount: number;
  ragFailure: boolean;
  onStage: (stage: Stage) => void;
  onTask: (task: SwtsTaskId) => void;
  onOrder: (order: SwtsTaskId[]) => void;
  onRagFailure: (value: boolean) => void;
  onReset: () => void;
  onExit: () => void;
}) {
  const stages: Array<[Stage, string]> = [
    ["introduction", "مقدمه"], ["demographics", "فرم فردی"], ["test", "E-CSA-WA"],
    ["think_aloud", "بیان افکار"], ["pre_task", "پیش‌وظیفه"], ["swts", "گفت‌وگو"],
    ["post_task", "پس‌وظیفه"], ["comparative", "مقایسه"], ["complete", "پایان"],
  ];
  const orders: SwtsTaskId[][] = [
    ["task_1","task_2","task_3"], ["task_1","task_3","task_2"], ["task_2","task_1","task_3"],
    ["task_2","task_3","task_1"], ["task_3","task_1","task_2"], ["task_3","task_2","task_1"],
  ];
  return <aside className="preview-toolbar" aria-label="کنترل پیش‌نمایش پژوهشگر" dir="rtl">
    <div className="preview-identity"><strong>پیش‌نمایش بدون ذخیره</strong><span>{eventCount.toLocaleString("fa-IR")} رویداد فقط در حافظه · وظیفه {taskPosition + 1}</span></div>
    <label>رفتن به مرحله<select value={stage} onChange={(event) => onStage(event.target.value as Stage)}>{stages.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <label>ترتیب<select value={taskOrder.join(",")} onChange={(event) => onOrder(event.target.value.split(",") as SwtsTaskId[])}>{orders.map((order) => <option key={order.join("-")} value={order.join(",")}>{order.map((id) => id.slice(-1)).join(" ← ")}</option>)}</select></label>
    <label>وظیفه SWTS<select value={taskId} onChange={(event) => onTask(event.target.value as SwtsTaskId)}>{taskOrder.map((id, index) => <option key={id} value={id}>وظیفه {index + 1}</option>)}</select></label>
    <label className="preview-toggle"><input type="checkbox" checked={ragFailure} onChange={(event) => onRagFailure(event.target.checked)} /><span>شبیه‌سازی خطای API</span></label>
    <button className="preview-button" onClick={onReset}>شروع دوباره</button>
    <button className="preview-button exit" onClick={onExit}>بازگشت به داشبورد</button>
  </aside>;
}

function Progress({ steps, current, rtl }: { steps: string[]; current: number; rtl: boolean }) {
  return <ol className="progress" aria-label="Study progress">{steps.map((step, index) => <li key={step} className={index === current ? "current" : index < current ? "complete" : ""}><span>{index + 1}</span><b>{step}</b>{index < steps.length - 1 && <Arrow rtl={rtl} />}</li>)}</ol>;
}

function Arrow({ rtl }: { rtl: boolean }) { return <span className={`arrow ${rtl ? "rtl" : ""}`} aria-hidden="true">→</span>; }
function LockIcon() { return <span className="lock" aria-hidden="true">⌑</span>; }
function median(values: number[]) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}
