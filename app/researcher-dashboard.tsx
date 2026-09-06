"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { SUPABASE_KEY, SUPABASE_URL } from "./runtime-config";
import ResearcherModelLab from "./researcher-model-lab";

type Language = "en" | "fa";
type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: { id: string; email?: string };
};
type Summary = {
  total_sessions: number;
  active_sessions: number;
  completed_tests: number;
  unused_invitations: number;
};
type Participant = {
  session_id: string;
  participant_id: string;
  current_phase: string;
  created_at: string;
  last_seen_at: string;
  completed_at: string | null;
  invitation_status: string;
  invitation_expires_at: string | null;
  invitation_code: string | null;
  archived_at: string | null;
  archived_by: string | null;
  test_status: string;
  items_completed: number;
  saved_test_answers: number;
  analytic_median_ms: number | null;
  wholistic_median_ms: number | null;
  wholistic_analytic_ratio: number | null;
  correct_analytic_count: number;
  correct_wholistic_count: number;
  consented: boolean;
  age_range: string | null;
  education: string | null;
};
type Trial = {
  participant_id?: string;
  test_version?: string;
  trial_id: string;
  trial_index: number;
  trial_kind: string;
  subtest: string | null;
  response_value: string;
  correct_answer: string | null;
  is_correct: boolean | null;
  reaction_time_ms: number;
  page_hidden: boolean;
  focus_lost_count: number;
  input_method: string | null;
  client_created_at: string;
  server_received_at: string;
};
type SwtsTaskRecord = {
  id: string;
  task_id: string;
  task_position: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  final_response: string | null;
  effort: number | null;
  confidence: number | null;
};
type SwtsAttempt = {
  id: string;
  task_session_id: string;
  task_id: string;
  sequence_number: number;
  participant_message: string;
  participant_visible_answer: string | null;
  original_backend_answer: string | null;
  status: string;
  latency_ms: number | null;
  sources: unknown[];
  retrieval: Record<string, unknown>;
  prompt_version: string | null;
  error_category: string | null;
  manual_retry: boolean;
  client_sent_at: string;
  response_received_at: string | null;
};
type SwtsDetails = {
  run: { status: string; current_position: number; task_order: string[] } | null;
  tasks: SwtsTaskRecord[];
  attempts: SwtsAttempt[];
};
type StudyFormRecord = { form_name: string; form_version: string; task_id: string; task_position: number | null; responses: Record<string, unknown>; submitted_at: string };
type InvitationCode = { id: string; code: string; status: string; created_at: string; expires_at: string | null };
type DashboardData = { summary: Summary; participants: Participant[]; invitations: InvitationCode[] };

const AUTH_STORAGE_KEY = "study-researcher-auth";

const copy = {
  en: {
    eyebrow: "Protected researcher area",
    title: "Researcher dashboard",
    subtitle: "Monitor sessions, create invitations, inspect test records, and export research data.",
    back: "Back to participant study",
    email: "Researcher email",
    password: "Password",
    signIn: "Sign in",
    signingIn: "Signing in…",
    loginHelp: "Use the Supabase researcher account authorized for this study.",
    invalidLogin: "The email or password is incorrect.",
    denied: "This account is not authorized as a researcher.",
    migrationMissing: "The researcher database setup is not active yet.",
    signedInAs: "Signed in as",
    signOut: "Sign out",
    refresh: "Refresh data",
    refreshing: "Refreshing…",
    total: "Participant sessions",
    active: "Active sessions",
    completed: "Completed tests",
    unused: "Unused invitations",
    invitationTitle: "Create a participant invitation",
    invitationHelp: "The plain code is shown only here. Give it to one participant; it can be redeemed once.",
    code: "Invitation code",
    generate: "Generate",
    expiry: "Expires",
    sevenDays: "In 7 days",
    thirtyDays: "In 30 days",
    noExpiry: "No expiry",
    create: "Create invitation",
    creating: "Creating…",
    created: "Invitation created",
    copy: "Copy code",
    copied: "Copied",
    duplicateCode: "That invitation code already exists. Generate a new one.",
    availableCodes: "Available invitation codes",
    noAvailableCodes: "No retrievable unused codes. Create a new invitation above.",
    createdAt: "Created",
    expired: "Expired",
    participants: "Participant monitoring",
    search: "Search participant ID",
    allPhases: "All phases",
    noParticipants: "No matching participants.",
    activeView: "Active",
    trashView: "Trash",
    archive: "Move to trash",
    restore: "Restore",
    archiveConfirm: "Move this participant session to trash? No research data will be deleted.",
    sessionActionFailed: "The session could not be updated.",
    unavailableCode: "Unavailable",
    participant: "Participant",
    phase: "Phase",
    test: "Test",
    items: "Saved items",
    ratio: "W/A ratio",
    lastSeen: "Last seen",
    inspect: "Inspect",
    exports: "Exports",
    exportSummary: "Participant summary CSV",
    exportTrials: "All trial responses CSV",
    exportSwts: "All SWTS conversations CSV",
    exportForms: "All study forms CSV",
    exporting: "Preparing export…",
    detail: "Participant record",
    close: "Close",
    consent: "Consent",
    age: "Age range",
    education: "Education",
    analyticMedian: "Analytic median",
    wholisticMedian: "Wholistic median",
    correctCounts: "Correct A / W",
    loadTrials: "Load trial responses",
    swtsData: "SWTS conversations and closing reflections",
    noSwtsData: "No SWTS record is available for this participant.",
    formData: "Study forms and questionnaires",
    noFormData: "No new-form record is available for this participant.",
    message: "Participant message",
    answer: "Visible answer",
    latency: "Latency",
    finalResponse: "Closing reflection",
    effort: "Effort",
    confidence: "Confidence",
    loadingTrials: "Loading responses…",
    trial: "Trial",
    subtest: "Subtest",
    response: "Response",
    correct: "Correct",
    reaction: "Reaction time",
    interruption: "Interruption",
    yes: "Yes",
    no: "No",
    none: "—",
    preview: "Open no-save study preview",
  },
  fa: {
    eyebrow: "بخش محافظت‌شده پژوهشگر",
    title: "داشبورد پژوهشگر",
    subtitle: "پایش جلسات، ساخت دعوت‌نامه، بررسی نتایج آزمون و خروجی‌گرفتن از داده‌های پژوهش.",
    back: "بازگشت به مطالعه شرکت‌کننده",
    email: "ایمیل پژوهشگر",
    password: "رمز عبور",
    signIn: "ورود",
    signingIn: "در حال ورود…",
    loginHelp: "از حساب پژوهشگری استفاده کنید که در Supabase برای این مطالعه مجاز شده است.",
    invalidLogin: "ایمیل یا رمز عبور نادرست است.",
    denied: "این حساب به‌عنوان پژوهشگر مجاز نشده است.",
    migrationMissing: "تنظیمات پایگاه داده پژوهشگر هنوز فعال نشده است.",
    signedInAs: "واردشده با",
    signOut: "خروج",
    refresh: "به‌روزرسانی داده‌ها",
    refreshing: "در حال به‌روزرسانی…",
    total: "جلسات شرکت‌کنندگان",
    active: "جلسات فعال",
    completed: "آزمون‌های کامل",
    unused: "دعوت‌نامه‌های استفاده‌نشده",
    invitationTitle: "ساخت دعوت‌نامه شرکت‌کننده",
    invitationHelp: "کد اصلی فقط همین‌جا نمایش داده می‌شود. آن را به یک شرکت‌کننده بدهید؛ هر کد فقط یک‌بار قابل استفاده است.",
    code: "کد دعوت",
    generate: "ساخت کد",
    expiry: "انقضا",
    sevenDays: "۷ روز دیگر",
    thirtyDays: "۳۰ روز دیگر",
    noExpiry: "بدون انقضا",
    create: "ایجاد دعوت‌نامه",
    creating: "در حال ایجاد…",
    created: "دعوت‌نامه ایجاد شد",
    copy: "کپی کد",
    copied: "کپی شد",
    duplicateCode: "این کد قبلاً وجود دارد. یک کد جدید بسازید.",
    availableCodes: "کدهای دعوت موجود",
    noAvailableCodes: "هیچ کد استفاده‌نشدهٔ قابل‌بازیابی وجود ندارد. یک دعوت‌نامهٔ جدید بسازید.",
    createdAt: "ساخته‌شده",
    expired: "منقضی‌شده",
    participants: "پایش شرکت‌کنندگان",
    search: "جست‌وجوی شناسه شرکت‌کننده",
    allPhases: "همه مراحل",
    noParticipants: "شرکت‌کننده‌ای مطابق جست‌وجو نیست.",
    activeView: "فعال",
    trashView: "سطل زباله",
    archive: "انتقال به سطل زباله",
    restore: "بازیابی",
    archiveConfirm: "این جلسه به سطل زباله منتقل شود؟ هیچ دادهٔ پژوهشی حذف نخواهد شد.",
    sessionActionFailed: "وضعیت جلسه به‌روزرسانی نشد.",
    unavailableCode: "در دسترس نیست",
    participant: "شرکت‌کننده",
    phase: "مرحله",
    test: "آزمون",
    items: "موارد ذخیره‌شده",
    ratio: "نسبت W/A",
    lastSeen: "آخرین فعالیت",
    inspect: "بررسی",
    exports: "خروجی‌ها",
    exportSummary: "CSV خلاصه شرکت‌کنندگان",
    exportTrials: "CSV تمام پاسخ‌های آزمون",
    exportSwts: "CSV تمام گفت‌وگوهای SWTS",
    exportForms: "CSV تمام فرم‌های مطالعه",
    exporting: "در حال آماده‌سازی خروجی…",
    detail: "پرونده شرکت‌کننده",
    close: "بستن",
    consent: "رضایت",
    age: "بازه سنی",
    education: "تحصیلات",
    analyticMedian: "میانه تحلیلی",
    wholisticMedian: "میانه کل‌نگر",
    correctCounts: "صحیح A / W",
    loadTrials: "بارگیری پاسخ‌های آزمون",
    swtsData: "گفت‌وگوها و بازتاب‌های پایانی SWTS",
    noSwtsData: "برای این شرکت‌کننده هنوز رکورد SWTS وجود ندارد.",
    formData: "فرم‌ها و پرسشنامه‌های مطالعه",
    noFormData: "برای این شرکت‌کننده هنوز فرم جدیدی ثبت نشده است.",
    message: "پیام شرکت‌کننده",
    answer: "پاسخ نمایش‌داده‌شده",
    latency: "زمان پاسخ",
    finalResponse: "بازتاب پایانی",
    effort: "تلاش",
    confidence: "اطمینان",
    loadingTrials: "در حال بارگیری پاسخ‌ها…",
    trial: "سؤال",
    subtest: "زیرآزمون",
    response: "پاسخ",
    correct: "صحیح",
    reaction: "زمان واکنش",
    interruption: "وقفه",
    yes: "بله",
    no: "خیر",
    none: "—",
    preview: "باز کردن پیش‌نمایش بدون ذخیره",
  },
};

export default function ResearcherDashboard({
  language,
  rtl,
  online,
  onBack,
  onOpenPreview,
}: {
  language: Language;
  rtl: boolean;
  online: boolean;
  onBack: () => void;
  onOpenPreview: () => void;
}) {
  const t = copy[language];
  const [auth, setAuth] = useState<AuthSession | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [restoring, setRestoring] = useState(true);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");
  const [phase, setPhase] = useState("all");
  const [sessionView, setSessionView] = useState<"active" | "trash">("active");
  const [sessionActionBusy, setSessionActionBusy] = useState("");
  const [invitationCode, setInvitationCode] = useState("");
  const [expiry, setExpiry] = useState("7");
  const [invitationBusy, setInvitationBusy] = useState(false);
  const [invitationError, setInvitationError] = useState("");
  const [createdCode, setCreatedCode] = useState("");
  const [copied, setCopied] = useState(false);
  const [selected, setSelected] = useState<Participant | null>(null);
  const [trials, setTrials] = useState<Trial[] | null>(null);
  const [trialsBusy, setTrialsBusy] = useState(false);
  const [swtsDetails, setSwtsDetails] = useState<SwtsDetails | null>(null);
  const [formDetails, setFormDetails] = useState<StudyFormRecord[] | null>(null);
  const [exportBusy, setExportBusy] = useState(false);

  useEffect(() => {
    let active = true;
    const restore = async () => {
      try {
        const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
        if (!stored) return;
        let session = JSON.parse(stored) as AuthSession;
        if (session.expires_at <= Date.now() + 30_000) session = await refreshAuth(session.refresh_token);
        if (!active) return;
        setAuth(session);
        await loadDashboard(session, false);
      } catch {
        window.localStorage.removeItem(AUTH_STORAGE_KEY);
      } finally {
        if (active) setRestoring(false);
      }
    };
    void restore();
    return () => { active = false; };
    // Initial researcher-session restoration intentionally runs once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredParticipants = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (dashboard?.participants || []).filter((participant) => {
      const matchesView = sessionView === "trash" ? Boolean(participant.archived_at) : !participant.archived_at;
      const matchesSearch = !needle || participant.participant_id.toLowerCase().includes(needle) || participant.invitation_code?.toLowerCase().includes(needle);
      const matchesPhase = phase === "all" || participant.current_phase === phase;
      return matchesView && matchesSearch && matchesPhase;
    });
  }, [dashboard, search, phase, sessionView]);

  function saveAuth(session: AuthSession) {
    setAuth(session);
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
  }

  async function refreshAuth(refreshToken: string) {
    const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: "POST",
      headers: { apikey: SUPABASE_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) throw new Error("refresh_failed");
    const result = await response.json();
    const session: AuthSession = {
      access_token: result.access_token,
      refresh_token: result.refresh_token,
      expires_at: Date.now() + Number(result.expires_in || 3600) * 1000,
      user: result.user,
    };
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    return session;
  }

  async function researcherRpc(name: string, body: Record<string, unknown>, session = auth) {
    if (!session) throw new Error("not_authenticated");
    let activeSession = session;
    if (activeSession.expires_at <= Date.now() + 30_000) {
      activeSession = await refreshAuth(activeSession.refresh_token);
      saveAuth(activeSession);
    }
    return fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
      method: "POST",
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${activeSession.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
  }

  async function loadDashboard(session = auth, showBusy = true) {
    if (!session) return;
    if (showBusy) setRefreshing(true);
    setAuthError("");
    try {
      const [response, invitationResponse, participantResponse] = await Promise.all([
        researcherRpc("researcher_dashboard", {}, session),
        researcherRpc("researcher_list_invitation_codes", {}, session),
        researcherRpc("researcher_participant_sessions", {}, session),
      ]);
      if (!response.ok || !invitationResponse.ok || !participantResponse.ok) {
        const failedResponse = !response.ok ? response : !invitationResponse.ok ? invitationResponse : participantResponse;
        const message = await failedResponse.text();
        if (response.status === 404 || message.includes("researcher_dashboard")) throw new Error("migration_missing");
        if (failedResponse.status === 401 || failedResponse.status === 403) throw new Error("access_denied");
        throw new Error("dashboard_failed");
      }
      const result = await response.json() as Omit<DashboardData, "invitations">;
      const invitations = await invitationResponse.json() as InvitationCode[];
      const participants = await participantResponse.json() as Participant[];
      const visibleParticipants = participants.filter((item) => !item.archived_at);
      const nextDashboard: DashboardData = {
        ...result,
        invitations,
        participants,
        summary: {
          ...result.summary,
          total_sessions: visibleParticipants.length,
          active_sessions: visibleParticipants.filter((item) => !item.completed_at).length,
          completed_tests: visibleParticipants.filter((item) => item.test_status === "completed").length,
        },
      };
      setDashboard(nextDashboard);
      if (selected) {
        setSelected(participants.find((item) => item.session_id === selected.session_id) || null);
      }
    } catch (error) {
      const reason = error instanceof Error ? error.message : "dashboard_failed";
      if (reason === "access_denied") setAuthError(t.denied);
      else if (reason === "migration_missing") setAuthError(t.migrationMissing);
      else setAuthError(language === "fa" ? "داده‌های داشبورد بارگیری نشد." : "Dashboard data could not be loaded.");
    } finally {
      setRefreshing(false);
    }
  }

  async function signIn(event: FormEvent) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
        method: "POST",
        headers: { apikey: SUPABASE_KEY, "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      if (!response.ok) throw new Error("invalid_login");
      const result = await response.json();
      const session: AuthSession = {
        access_token: result.access_token,
        refresh_token: result.refresh_token,
        expires_at: Date.now() + Number(result.expires_in || 3600) * 1000,
        user: result.user,
      };
      saveAuth(session);
      await loadDashboard(session, false);
      setPassword("");
    } catch (error) {
      if (error instanceof Error && error.message === "invalid_login") setAuthError(t.invalidLogin);
      else setAuthError(language === "fa" ? "ورود انجام نشد." : "Sign-in failed.");
    } finally {
      setAuthBusy(false);
      setRestoring(false);
    }
  }

  function signOut() {
    if (auth) {
      void fetch(`${SUPABASE_URL}/auth/v1/logout`, {
        method: "POST",
        headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${auth.access_token}` },
      }).catch(() => undefined);
    }
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    setAuth(null);
    setDashboard(null);
    setSelected(null);
    setTrials(null);
    setSwtsDetails(null);
    setFormDetails(null);
    setAuthError("");
  }

  function generateCode() {
    const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    const bytes = crypto.getRandomValues(new Uint8Array(10));
    const value = Array.from(bytes, (byte) => alphabet[byte % alphabet.length]).join("");
    setInvitationCode(`CSA-${value.slice(0, 5)}-${value.slice(5)}`);
    setCreatedCode("");
    setInvitationError("");
  }

  async function createInvitation(event: FormEvent) {
    event.preventDefault();
    if (invitationCode.trim().length < 6) {
      setInvitationError(language === "fa" ? "کد باید حداقل ۶ نویسه باشد." : "The code must contain at least 6 characters.");
      return;
    }
    setInvitationBusy(true);
    setInvitationError("");
    setCreatedCode("");
    try {
      const days = Number(expiry);
      const expiresAt = days ? new Date(Date.now() + days * 86_400_000).toISOString() : null;
      const response = await researcherRpc("researcher_create_invitation", {
        p_code: invitationCode.trim().toUpperCase(),
        p_expires_at: expiresAt,
      });
      if (!response.ok) throw new Error("create_failed");
      const result = await response.json();
      if (!result?.accepted) {
        if (result?.reason === "code_already_exists") throw new Error("duplicate");
        throw new Error("create_failed");
      }
      setCreatedCode(invitationCode.trim().toUpperCase());
      setInvitationCode("");
      setCopied(false);
      await loadDashboard(auth, false);
    } catch (error) {
      setInvitationError(error instanceof Error && error.message === "duplicate" ? t.duplicateCode : (language === "fa" ? "دعوت‌نامه ایجاد نشد." : "The invitation could not be created."));
    } finally {
      setInvitationBusy(false);
    }
  }

  async function copyCreatedCode() {
    if (!createdCode) return;
    await navigator.clipboard.writeText(createdCode);
    setCopied(true);
  }

  async function loadTrials(participant: Participant) {
    setSelected(participant);
    setTrials(null);
    setSwtsDetails(null);
    setFormDetails(null);
    setTrialsBusy(true);
    try {
      const [trialResponse, swtsResponse, formResponse] = await Promise.all([
        researcherRpc("researcher_trial_details", { p_session_id: participant.session_id }),
        researcherRpc("researcher_swts_details", { p_session_id: participant.session_id }),
        researcherRpc("researcher_study_form_details", { p_session_id: participant.session_id }),
      ]);
      if (!trialResponse.ok) throw new Error();
      setTrials(await trialResponse.json() as Trial[]);
      setSwtsDetails(swtsResponse.ok ? await swtsResponse.json() as SwtsDetails : null);
      setFormDetails(formResponse.ok ? await formResponse.json() as StudyFormRecord[] : []);
    } catch {
      setTrials([]);
    } finally {
      setTrialsBusy(false);
    }
  }

  async function setSessionArchived(participant: Participant, archived: boolean) {
    if (archived && !window.confirm(t.archiveConfirm)) return;
    setSessionActionBusy(participant.session_id);
    setAuthError("");
    try {
      const response = await researcherRpc("researcher_set_session_archived", {
        p_session_id: participant.session_id,
        p_archived: archived,
      });
      if (!response.ok) throw new Error("session_action_failed");
      const result = await response.json();
      if (!result?.accepted) throw new Error("session_action_failed");
      if (selected?.session_id === participant.session_id) {
        setSelected(null);
        setTrials(null);
        setSwtsDetails(null);
        setFormDetails(null);
      }
      await loadDashboard(auth, false);
    } catch {
      setAuthError(t.sessionActionFailed);
    } finally {
      setSessionActionBusy("");
    }
  }

  function exportParticipantSummary() {
    if (!dashboard) return;
    const rows = dashboard.participants.filter((participant) => !participant.archived_at).map((participant) => ({
      invitation_code: participant.invitation_code,
      participant_id: participant.participant_id,
      current_phase: participant.current_phase,
      created_at: participant.created_at,
      last_seen_at: participant.last_seen_at,
      consented: participant.consented,
      age_range: participant.age_range,
      education: participant.education,
      test_status: participant.test_status,
      items_completed: participant.items_completed,
      saved_test_answers: participant.saved_test_answers,
      analytic_median_ms: participant.analytic_median_ms,
      wholistic_median_ms: participant.wholistic_median_ms,
      wholistic_analytic_ratio: participant.wholistic_analytic_ratio,
      correct_analytic_count: participant.correct_analytic_count,
      correct_wholistic_count: participant.correct_wholistic_count,
    }));
    downloadCsv("cognitive-style-participants.csv", rows);
  }

  async function exportAllTrials() {
    setExportBusy(true);
    try {
      const response = await researcherRpc("researcher_export_trials", {});
      if (!response.ok) throw new Error();
      const rows = await response.json() as Array<Record<string, unknown>>;
      downloadCsv("cognitive-style-trial-responses.csv", rows);
    } finally {
      setExportBusy(false);
    }
  }

  async function exportAllSwts() {
    setExportBusy(true);
    try {
      const response = await researcherRpc("researcher_export_swts", {});
      if (!response.ok) throw new Error();
      const rows = await response.json() as Array<Record<string, unknown>>;
      downloadCsv("cognitive-style-swts-conversations.csv", rows);
    } finally {
      setExportBusy(false);
    }
  }

  async function exportAllForms() {
    setExportBusy(true);
    try {
      const response = await researcherRpc("researcher_export_study_forms", {});
      if (!response.ok) throw new Error();
      const rows = await response.json() as Array<Record<string, unknown>>;
      downloadCsv("cognitive-style-study-forms.csv", rows);
    } finally { setExportBusy(false); }
  }

  if (restoring) {
    return <section className="researcher-page content" dir={rtl ? "rtl" : "ltr"}><div className="admin-loading"><span className="pulse-dot" /><p>{t.refreshing}</p></div></section>;
  }

  if (!auth || !dashboard) {
    return <section className="researcher-page content" dir={rtl ? "rtl" : "ltr"}>
      <div className="admin-titlebar"><div><p className="eyebrow">{t.eyebrow}</p><h1>{t.title}</h1><p>{t.subtitle}</p></div><button className="secondary compact-button" onClick={onBack}>{t.back}</button></div>
      <form className="card researcher-login" onSubmit={signIn}>
        <h2>{t.signIn}</h2><p className="muted">{t.loginHelp}</p>
        <label>{t.email}<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required /></label>
        <label>{t.password}<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
        {authError && <p className="error" role="alert">{authError}</p>}
        <button className="primary" disabled={authBusy || !online}>{authBusy ? t.signingIn : t.signIn}</button>
      </form>
    </section>;
  }

  return <section className="researcher-page content" dir={rtl ? "rtl" : "ltr"}>
    <div className="admin-titlebar">
      <div><p className="eyebrow">{t.eyebrow}</p><h1>{t.title}</h1><p>{t.subtitle}</p></div>
      <div className="admin-account"><span>{t.signedInAs}<strong>{auth.user.email}</strong></span><button className="preview-launch" onClick={onOpenPreview}>{t.preview}</button><button className="secondary compact-button" onClick={() => void loadDashboard()} disabled={refreshing}>{refreshing ? t.refreshing : t.refresh}</button><button className="admin-text-button" onClick={signOut}>{t.signOut}</button><button className="admin-text-button" onClick={onBack}>{t.back}</button></div>
    </div>
    {authError && <p className="admin-alert" role="alert">{authError}</p>}

    <div className="summary-grid">
      <SummaryCard label={t.total} value={dashboard.summary.total_sessions} />
      <SummaryCard label={t.active} value={dashboard.summary.active_sessions} />
      <SummaryCard label={t.completed} value={dashboard.summary.completed_tests} />
      <SummaryCard label={t.unused} value={dashboard.summary.unused_invitations} />
    </div>

    <div className="admin-tools-grid">
      <form className="card invitation-tool" onSubmit={createInvitation}>
        <p className="card-kicker">{t.invitationTitle}</p><p className="muted">{t.invitationHelp}</p>
        <div className="invitation-code-row"><label>{t.code}<input value={invitationCode} onChange={(event) => setInvitationCode(event.target.value.toUpperCase())} /></label><button type="button" className="secondary compact-button" onClick={generateCode}>{t.generate}</button></div>
        <label>{t.expiry}<select value={expiry} onChange={(event) => setExpiry(event.target.value)}><option value="7">{t.sevenDays}</option><option value="30">{t.thirtyDays}</option><option value="0">{t.noExpiry}</option></select></label>
        {invitationError && <p className="error" role="alert">{invitationError}</p>}
        {createdCode && <div className="created-code"><span>{t.created}</span><strong dir="ltr">{createdCode}</strong><button type="button" onClick={() => void copyCreatedCode()}>{copied ? t.copied : t.copy}</button></div>}
        <button className="primary" disabled={invitationBusy || !online}>{invitationBusy ? t.creating : t.create}</button>
        <div className="available-invitations">
          <strong>{t.availableCodes}</strong>
          {!dashboard.invitations.length ? <p className="muted">{t.noAvailableCodes}</p> : dashboard.invitations.map((invitation) => {
            const expired = Boolean(invitation.expires_at && new Date(invitation.expires_at).getTime() <= Date.now());
            return <div className="available-invitation" key={invitation.id}>
              <div><code dir="ltr">{invitation.code}</code><small>{t.createdAt}: {formatDate(invitation.created_at, language)}{invitation.expires_at ? ` · ${t.expiry}: ${formatDate(invitation.expires_at, language)}` : ""}</small></div>
              {expired ? <span className="status-pill">{t.expired}</span> : <button type="button" onClick={() => void navigator.clipboard.writeText(invitation.code)}>{t.copy}</button>}
            </div>;
          })}
        </div>
      </form>
      <div className="card export-tool"><p className="card-kicker">{t.exports}</p><p className="muted">{language === "fa" ? "خروجی خلاصه، داده‌های آزمون، فرم‌ها یا گفت‌وگوهای SWTS را دریافت کنید." : "Download participant, test, form, or SWTS conversation data."}</p><button className="secondary" onClick={exportParticipantSummary}>{t.exportSummary}</button><button className="secondary" onClick={() => void exportAllTrials()} disabled={exportBusy}>{exportBusy ? t.exporting : t.exportTrials}</button><button className="secondary" onClick={() => void exportAllSwts()} disabled={exportBusy}>{exportBusy ? t.exporting : t.exportSwts}</button><button className="secondary" onClick={() => void exportAllForms()} disabled={exportBusy}>{exportBusy ? t.exporting : t.exportForms}</button></div>
    </div>

    <ResearcherModelLab language={language} />

    <div className="card participant-monitor">
      <div className="monitor-heading"><div><p className="card-kicker">{t.participants}</p><strong>{filteredParticipants.length}</strong></div><div className="monitor-filters"><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t.search} /><select value={phase} onChange={(event) => setPhase(event.target.value)}><option value="all">{t.allPhases}</option><option value="introduction">Introduction</option><option value="demographics">Demographics</option><option value="test">E-CSA-WA</option><option value="think_aloud">Think aloud</option><option value="pre_task">Pre-task</option><option value="swts">SWTS</option><option value="post_task">Post-task</option><option value="comparative">Final comparison</option><option value="complete">Complete</option></select></div></div>
      <div className="session-view-tabs"><button className={sessionView === "active" ? "active" : ""} onClick={() => setSessionView("active")}>{t.activeView} ({dashboard.participants.filter((item) => !item.archived_at).length})</button><button className={sessionView === "trash" ? "active" : ""} onClick={() => setSessionView("trash")}>{t.trashView} ({dashboard.participants.filter((item) => item.archived_at).length})</button></div>
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{t.participant}</th><th>{t.code}</th><th>{t.phase}</th><th>{t.test}</th><th>{t.items}</th><th>{t.ratio}</th><th>{t.lastSeen}</th><th /></tr></thead><tbody>{filteredParticipants.map((participant) => <tr key={participant.session_id}><td><code>{shortId(participant.participant_id)}</code></td><td><code dir="ltr">{participant.invitation_code || t.unavailableCode}</code></td><td><StatusPill value={participant.current_phase} /></td><td>{participant.test_status}</td><td>{participant.saved_test_answers} / 80</td><td>{formatNumber(participant.wholistic_analytic_ratio)}</td><td>{formatDate(participant.last_seen_at, language)}</td><td className="session-actions"><button onClick={() => void loadTrials(participant)}>{t.inspect}</button><button className={participant.archived_at ? "restore-action" : "archive-action"} disabled={sessionActionBusy === participant.session_id} onClick={() => void setSessionArchived(participant, !participant.archived_at)}>{participant.archived_at ? t.restore : t.archive}</button></td></tr>)}</tbody></table>{!filteredParticipants.length && <p className="empty-state">{t.noParticipants}</p>}</div>
    </div>

    {selected && <div className="card participant-detail">
      <div className="detail-heading"><div><p className="card-kicker">{t.detail}</p><h2><code>{shortId(selected.participant_id)}</code></h2></div><button className="admin-text-button" onClick={() => { setSelected(null); setTrials(null); setSwtsDetails(null); setFormDetails(null); }}>{t.close}</button></div>
      <div className="detail-grid">
        <Detail label={t.code} value={selected.invitation_code || t.unavailableCode} />
        <Detail label={t.phase} value={selected.current_phase} />
        <Detail label={t.consent} value={selected.consented ? t.yes : t.no} />
        <Detail label={t.age} value={selected.age_range || t.none} />
        <Detail label={t.education} value={selected.education || t.none} />
        <Detail label={t.analyticMedian} value={formatMs(selected.analytic_median_ms)} />
        <Detail label={t.wholisticMedian} value={formatMs(selected.wholistic_median_ms)} />
        <Detail label={t.ratio} value={formatNumber(selected.wholistic_analytic_ratio)} />
        <Detail label={t.correctCounts} value={`${selected.correct_analytic_count} / ${selected.correct_wholistic_count}`} />
      </div>
      {trialsBusy ? <p className="empty-state">{t.loadingTrials}</p> : trials === null ? <button className="secondary" onClick={() => void loadTrials(selected)}>{t.loadTrials}</button> : <div className="admin-table-wrap trial-table"><table className="admin-table"><thead><tr><th>{t.trial}</th><th>{t.subtest}</th><th>{t.response}</th><th>{t.correct}</th><th>{t.reaction}</th><th>{t.interruption}</th></tr></thead><tbody>{trials.map((trial) => <tr key={`${trial.trial_id}-${trial.trial_index}`}><td>{trial.trial_index + 1}</td><td>{trial.subtest || trial.trial_kind}</td><td>{trial.response_value}</td><td>{trial.is_correct === null ? t.none : trial.is_correct ? t.yes : t.no}</td><td>{Number(trial.reaction_time_ms).toFixed(2)} ms</td><td>{trial.page_hidden || trial.focus_lost_count > 0 ? t.yes : t.no}</td></tr>)}</tbody></table>{!trials.length && <p className="empty-state">{t.noParticipants}</p>}</div>}
      <div className="study-form-admin-detail"><h3>{t.formData}</h3>{!formDetails?.length ? <p className="empty-state">{t.noFormData}</p> : formDetails.map((form) => <details key={`${form.form_name}-${form.task_id}`}><summary><strong>{form.form_name}</strong><span>{form.task_id || "عمومی"} · {formatDate(form.submitted_at, language)}</span></summary><pre>{JSON.stringify(form.responses, null, 2)}</pre></details>)}</div>
      <div className="swts-admin-detail">
        <h3>{t.swtsData}</h3>
        {!swtsDetails?.run ? <p className="empty-state">{t.noSwtsData}</p> : swtsDetails.tasks.map((task) => <section key={task.id} className="swts-admin-task">
          <div className="swts-admin-task-heading"><strong>{task.task_position + 1}. {task.task_id}</strong><StatusPill value={task.status} /></div>
          {swtsDetails.attempts.filter((attempt) => attempt.task_session_id === task.id).map((attempt) => <div className="swts-admin-exchange" key={attempt.id}>
            <div><span>{t.message}</span><p>{attempt.participant_message}</p></div>
            <div><span>{t.answer}</span><p>{attempt.participant_visible_answer || `${attempt.status}: ${attempt.error_category || t.none}`}</p></div>
            <small>{t.latency}: {attempt.latency_ms === null ? t.none : `${Number(attempt.latency_ms).toFixed(2)} ms`} · {attempt.prompt_version || t.none}{attempt.manual_retry ? " · retry" : ""}</small>
          </div>)}
          {task.final_response && <div className="swts-admin-final"><span>{t.finalResponse}</span><p>{task.final_response}</p><small>{t.effort}: {task.effort ?? t.none} · {t.confidence}: {task.confidence ?? t.none}</small></div>}
        </section>)}
      </div>
    </div>}
  </section>;
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return <div className="summary-card"><span>{label}</span><strong>{value}</strong></div>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="detail-item"><span>{label}</span><strong>{value}</strong></div>;
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill phase-${value}`}>{value}</span>;
}

function shortId(value: string) { return `${value.slice(0, 8)}…${value.slice(-4)}`; }
function formatNumber(value: number | null) { return value === null || value === undefined ? "—" : Number(value).toFixed(3); }
function formatMs(value: number | null) { return value === null || value === undefined ? "—" : `${Number(value).toFixed(2)} ms`; }
function formatDate(value: string, language: Language) {
  return new Intl.DateTimeFormat(language === "fa" ? "fa-IR" : "en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function downloadCsv(filename: string, rows: Array<Record<string, unknown>>) {
  if (!rows.length) return;
  const headers = Array.from(rows.reduce((keys, row) => {
    Object.keys(row).forEach((key) => keys.add(key));
    return keys;
  }, new Set<string>()));
  const escape = (value: unknown) => {
    if (value === null || value === undefined) return "";
    const text = typeof value === "object" ? JSON.stringify(value) : String(value);
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const csv = [headers.join(","), ...rows.map((row) => headers.map((header) => escape(row[header])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
