"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SUPABASE_KEY, SUPABASE_URL } from "./runtime-config";
import { checkRagHealth, RagHistoryItem, RagRequestError, sendRagMessage, toParticipantAnswer } from "./rag-client";
import { SWTS_COMMON_CONTEXT, SWTS_TASK_IDS, SWTS_TASKS, SWTS_TIME_LIMIT_SECONDS, SwtsTaskId } from "./swts-config";

export type ParticipantSession = { session_id: string; participant_id: string; recovery_token: string };
export type SwtsTaskMeta = { taskId: SwtsTaskId; position: number; order: SwtsTaskId[] };

type StoredExchange = {
  attempt_id: string;
  sequence_number: number;
  participant_message: string;
  participant_visible_answer: string | null;
  success: boolean | null;
  error_category: string | null;
  manual_retry: boolean;
  client_sent_at: string;
  response_received_at: string | null;
};

export type SwtsState = {
  accepted: boolean;
  status: "in_progress" | "completed";
  run_id: string;
  current_position: number;
  total_tasks: number;
  task_order: SwtsTaskId[];
  task_id: SwtsTaskId | null;
  rag_session_id: string | null;
  task_started_at: string | null;
  exchanges: StoredExchange[];
  next_sequence: number;
};

type VisibleMessage = { key: string; role: "user" | "assistant"; content: string };
type PendingFinish = { body: Record<string, unknown>; successExchange?: StoredExchange };

const preparingMessage = "سامانه گفتگو در حال آماده‌سازی است. لطفاً چند لحظه دیگر دوباره تلاش کنید.";
const requestFailedMessage = "پاسخ دریافت نشد. متن شما حفظ شده است؛ برای تلاش دوباره دکمه ارسال را بزنید.";
const logFailedMessage = "ثبت پژوهشی این پیام کامل نشده است. برای ادامه، ثبت را دوباره انجام دهید.";

async function participantRpc(name: string, body: Record<string, unknown>) {
  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
    method: "POST",
    headers: { apikey: SUPABASE_KEY, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("database_request_failed");
  const result = await response.json();
  if (!result?.accepted) throw new Error(result?.reason || "database_request_rejected");
  return result;
}

export async function loadParticipantSwtsState(session: ParticipantSession) {
  return participantRpc("start_or_restore_swts", {
    p_session_id: session.session_id,
    p_recovery_token: session.recovery_token,
  }) as Promise<SwtsState>;
}

function successfulMessages(exchanges: StoredExchange[]): VisibleMessage[] {
  return exchanges.flatMap((exchange) => !exchange.success || !exchange.participant_visible_answer ? [] : [
    { key: `${exchange.attempt_id}-u`, role: "user" as const, content: exchange.participant_message },
    { key: `${exchange.attempt_id}-a`, role: "assistant" as const, content: exchange.participant_visible_answer },
  ]);
}

function historyFromMessages(messages: VisibleMessage[]): RagHistoryItem[] {
  return messages.slice(-20).map(({ role, content }) => ({ role, content }));
}

function wordCount(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed.split(/\s+/u).length : 0;
}

function formatRemaining(seconds: number) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  const rest = Math.max(0, seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${rest}`;
}

export function MarkdownMessage({ children }: { children: string }) {
  return <div className="markdown-body" dir="rtl"><ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown></div>;
}

export function ExperimentSwtsChat({
  session,
  mode = "experiment",
  previewTaskId = "task_1",
  previewPosition = 0,
  previewOrder = SWTS_TASK_IDS,
  simulateRagFailure = false,
  onTaskLoaded,
  onTaskComplete,
}: {
  session: ParticipantSession;
  mode?: "experiment" | "preview";
  previewTaskId?: SwtsTaskId;
  previewPosition?: number;
  previewOrder?: SwtsTaskId[];
  simulateRagFailure?: boolean;
  onTaskLoaded?: (meta: SwtsTaskMeta) => void;
  onTaskComplete?: (meta: SwtsTaskMeta & { finalResponse: string; completed: boolean }) => void | Promise<void>;
}) {
  const [state, setState] = useState<SwtsState | null>(null);
  const [loading, setLoading] = useState(true);
  const [healthReady, setHealthReady] = useState(false);
  const [healthBusy, setHealthBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [pendingMessage, setPendingMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [lastFailedAttemptId, setLastFailedAttemptId] = useState<string | null>(null);
  const [pendingFinish, setPendingFinish] = useState<PendingFinish | null>(null);
  const [finalResponse, setFinalResponse] = useState("");
  const [submittingFinal, setSubmittingFinal] = useState(false);
  const [remaining, setRemaining] = useState(SWTS_TIME_LIMIT_SECONDS);
  const messagesEnd = useRef<HTMLDivElement | null>(null);
  const onTaskLoadedRef = useRef(onTaskLoaded);

  const messages = useMemo(() => successfulMessages(state?.exchanges || []), [state]);
  const currentTask = state?.task_id ? SWTS_TASKS[state.task_id] : null;
  const currentWords = wordCount(finalResponse);
  const finalTooLong = Boolean(currentTask?.maxWords && currentWords > currentTask.maxWords);

  useEffect(() => { onTaskLoadedRef.current = onTaskLoaded; }, [onTaskLoaded]);

  // In the real experiment, restore once per participant session. Parent task
  // metadata updates must not restart this component. Preview mode deliberately
  // restores when its selected task or order changes.
  const restoreContextKey = mode === "preview"
    ? `preview:${previewTaskId}:${previewPosition}:${previewOrder.join(",")}`
    : `experiment:${session.session_id}`;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void restore(); }, [restoreContextKey]);
  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages.length, pendingMessage]);
  useEffect(() => {
    if (!state?.task_started_at || state.status === "completed" || mode === "preview") return;
    const update = () => setRemaining(Math.max(0, SWTS_TIME_LIMIT_SECONDS - Math.floor((Date.now() - new Date(state.task_started_at!).getTime()) / 1000)));
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [state?.task_started_at, state?.status, mode]);

  async function restore() {
    setLoading(true);
    setError("");
    try {
      const result = mode === "preview" ? {
        accepted: true,
        status: "in_progress" as const,
        run_id: "preview-run",
        current_position: previewPosition,
        total_tasks: 3,
        task_order: previewOrder,
        task_id: previewTaskId,
        rag_session_id: `preview-${previewTaskId}-${crypto.randomUUID()}`,
        task_started_at: new Date().toISOString(),
        exchanges: [],
        next_sequence: 1,
      } : await loadParticipantSwtsState(session);
      setState(result);
      setFinalResponse("");
      setRemaining(SWTS_TIME_LIMIT_SECONDS);
      if (result.task_id) onTaskLoadedRef.current?.({ taskId: result.task_id, position: result.current_position, order: result.task_order });
      setLoading(false);
      void verifyHealth();
    } catch {
      setError("بازیابی مرحله گفت‌وگو انجام نشد. اتصال را بررسی و دوباره تلاش کنید.");
      setLoading(false);
    }
  }

  async function verifyHealth() {
    setHealthBusy(true);
    setHealthReady(false);
    try {
      if (simulateRagFailure) throw new Error("simulated_failure");
      await checkRagHealth();
      setHealthReady(true);
      setError("");
    } catch { setError(preparingMessage); }
    finally { setHealthBusy(false); }
  }

  async function finishAttempt(pending: PendingFinish) {
    if (mode === "experiment") await participantRpc("finish_swts_attempt", { p_session_id: session.session_id, p_recovery_token: session.recovery_token, ...pending.body });
    setState((value) => value ? { ...value, exchanges: pending.successExchange ? [...value.exchanges, pending.successExchange] : value.exchanges, next_sequence: value.next_sequence + 1 } : value);
    setPendingFinish(null);
  }

  async function retryPendingLog() {
    if (!pendingFinish) return;
    setIsSending(true);
    setError("");
    try { await finishAttempt(pendingFinish); } catch { setError(logFailedMessage); } finally { setIsSending(false); }
  }

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const message = draft;
    if (!message.trim() || !state?.task_id || !state.rag_session_id || isSending || pendingFinish || remaining <= 0) return;
    const attemptId = crypto.randomUUID();
    const clientSentAt = new Date().toISOString();
    const manualRetry = Boolean(lastFailedAttemptId);
    setIsSending(true);
    setPendingMessage(message);
    setError("");
    try {
      if (mode === "experiment") await participantRpc("begin_swts_attempt", {
        p_session_id: session.session_id,
        p_recovery_token: session.recovery_token,
        p_attempt_id: attemptId,
        p_task_id: state.task_id,
        p_sequence_number: state.next_sequence,
        p_participant_message: message,
        p_client_sent_at: clientSentAt,
        p_manual_retry: manualRetry,
        p_retry_of: lastFailedAttemptId,
      });
      const started = performance.now();
      try {
        if (simulateRagFailure) throw new RagRequestError("simulated_failure");
        const result = await sendRagMessage({ session_id: state.rag_session_id, task_id: state.task_id, message, history: historyFromMessages(messages) });
        const responseReceivedAt = new Date().toISOString();
        const latencyMs = Math.round((performance.now() - started) * 100) / 100;
        const visibleAnswer = toParticipantAnswer(result.answer);
        const exchange: StoredExchange = { attempt_id: attemptId, sequence_number: state.next_sequence, participant_message: message, participant_visible_answer: visibleAnswer, success: true, error_category: null, manual_retry: manualRetry, client_sent_at: clientSentAt, response_received_at: responseReceivedAt };
        const pending: PendingFinish = { successExchange: exchange, body: { p_attempt_id: attemptId, p_success: true, p_response_received_at: responseReceivedAt, p_latency_ms: latencyMs, p_request_id: result.request_id, p_original_backend_answer: result.answer, p_participant_visible_answer: visibleAnswer, p_sources: result.sources, p_retrieval: result.retrieval, p_prompt_version: result.prompt_version, p_error_category: null } };
        setDraft("");
        setLastFailedAttemptId(null);
        try { await finishAttempt(pending); } catch { setPendingFinish(pending); setError(logFailedMessage); }
      } catch (ragError) {
        const category = ragError instanceof RagRequestError ? ragError.category : "unknown";
        const failedFinish: PendingFinish = { body: { p_attempt_id: attemptId, p_success: false, p_response_received_at: new Date().toISOString(), p_latency_ms: Math.round((performance.now() - started) * 100) / 100, p_request_id: ragError instanceof RagRequestError ? ragError.requestId || null : null, p_original_backend_answer: null, p_participant_visible_answer: null, p_sources: [], p_retrieval: {}, p_prompt_version: null, p_error_category: category } };
        setLastFailedAttemptId(attemptId);
        try { await finishAttempt(failedFinish); setError(requestFailedMessage); } catch { setPendingFinish(failedFinish); setError(logFailedMessage); }
      }
    } catch { setError("پیام ارسال نشد، چون ثبت اولیه پژوهش انجام نشد. متن شما حفظ شده است."); }
    finally { setPendingMessage(""); setIsSending(false); }
  }

  function composerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); }
  }

  async function submitFinal(event: FormEvent) {
    event.preventDefault();
    if (!state?.task_id || !finalResponse.trim() || finalTooLong || pendingFinish) return;
    setSubmittingFinal(true);
    setError("");
    const meta = { taskId: state.task_id, position: state.current_position, order: state.task_order, finalResponse: finalResponse.trim(), completed: state.current_position >= 2 };
    try {
      if (mode === "experiment") await participantRpc("submit_swts_task_v2", {
        p_session_id: session.session_id,
        p_recovery_token: session.recovery_token,
        p_task_id: state.task_id,
        p_final_response: finalResponse.trim(),
        p_client_submitted_at: new Date().toISOString(),
      });
      await onTaskComplete?.(meta);
    } catch { setError("پاسخ نهایی ثبت نشد. متن شما حفظ شده است؛ دوباره تلاش کنید."); }
    finally { setSubmittingFinal(false); }
  }

  if (loading) return <div className="swts-loading"><span className="pulse-dot" /><p>در حال آماده‌سازی فضای وظیفه…</p></div>;
  if (!state) return <div className="swts-error"><p>{error}</p><button className="secondary" onClick={() => void restore()}>تلاش دوباره</button></div>;
  if (state.status === "completed") return <div className="swts-complete"><span>✓</span><h2>هر سه وظیفه کامل شده‌اند</h2><p>اکنون ارزیابی نهایی را تکمیل کنید.</p></div>;
  if (!currentTask) return null;

  return <div className="swts-workspace" dir="rtl">
    <aside className="swts-task-panel">
      <div className="swts-task-topline"><span>وظیفه {state.current_position + 1} از {state.total_tasks}</span><strong dir="ltr">{mode === "preview" ? "PREVIEW" : formatRemaining(remaining)}</strong></div>
      <section><small>زمینه مشترک</small><p>{SWTS_COMMON_CONTEXT}</p></section>
      <section><small>وظیفه فعلی</small><h2>{currentTask.title}</h2><p>{currentTask.prompt}</p></section>
      <section className="required-response"><small>خروجی موردنیاز</small><p>{currentTask.requiredResponse}</p></section>
    </aside>

    <section className="swts-chat-panel" aria-label="گفت‌وگو با سامانه">
      <header className="swts-chat-header"><div className="assistant-avatar" aria-hidden="true">س</div><div><strong>دستیار جزیره سپید</strong><span><i className={healthReady ? "ready" : "pending"} />{healthReady ? "آماده پاسخ‌گویی" : "در حال اتصال"}</span></div></header>
      <div className="swts-messages" aria-live="polite">
        {!messages.length && <div className="swts-empty"><span>✦</span><strong>از کجا شروع کنیم؟</strong><p>برای یافتن اطلاعات موردنیاز، سؤال خود را درباره همین وظیفه بنویسید.</p></div>}
        {messages.map((message) => <article key={message.key} className={`swts-message ${message.role}`}><span>{message.role === "user" ? "شما" : "دستیار"}</span>{message.role === "assistant" ? <MarkdownMessage>{message.content}</MarkdownMessage> : <p>{message.content}</p>}</article>)}
        {pendingMessage && <article className="swts-message user pending"><span>شما</span><p>{pendingMessage}</p></article>}
        {isSending && !pendingFinish && <div className="swts-typing" role="status"><i /><i /><i /><span>در حال آماده‌کردن پاسخ…</span></div>}
        <div ref={messagesEnd} />
      </div>
      {error && <div className="swts-alert" role="alert"><p>{error}</p>{pendingFinish ? <button onClick={() => void retryPendingLog()} disabled={isSending}>ثبت دوباره</button> : !healthReady ? <button onClick={() => void verifyHealth()} disabled={healthBusy}>بررسی دوباره</button> : null}</div>}
      {remaining <= 0 && <p className="swts-timeup">زمان جست‌وجو به پایان رسیده است. اکنون پاسخ نهایی خود را ثبت کنید.</p>}
      <form className="swts-composer" onSubmit={(event) => void send(event)}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={composerKeyDown} maxLength={8000} placeholder="پیام خود را بنویسید…" disabled={!healthReady || isSending || Boolean(pendingFinish) || remaining <= 0} /><div><small>Enter برای ارسال · Shift+Enter برای خط جدید</small><button className="chat-send" aria-label="ارسال پیام" disabled={!draft.trim() || !healthReady || isSending || Boolean(pendingFinish) || remaining <= 0}>↑</button></div></form>
    </section>

    <aside className="swts-answer-panel">
      <div><span className="answer-icon">✓</span><div><strong>پاسخ نهایی من</strong><small>می‌توانید هم‌زمان با گفت‌وگو پاسخ را کامل کنید.</small></div></div>
      <form onSubmit={submitFinal}><label htmlFor="swts-final-answer">پاسخ موردنظر برای تحویل</label><textarea id="swts-final-answer" value={finalResponse} onChange={(event) => setFinalResponse(event.target.value)} rows={14} placeholder="یادداشت‌ها و پاسخ نهایی خود را اینجا بنویسید…" required />{currentTask.maxWords && <small className={finalTooLong ? "word-limit over" : "word-limit"}>{currentWords.toLocaleString("fa-IR")} / {currentTask.maxWords.toLocaleString("fa-IR")} واژه</small>}<button className="primary" disabled={!finalResponse.trim() || finalTooLong || submittingFinal || Boolean(pendingFinish)}>{submittingFinal ? "در حال ثبت…" : "ثبت پاسخ و ادامه"}</button></form>
      <p className="answer-save-note">{mode === "preview" ? "حالت پیش‌نمایش: این پاسخ ذخیره نمی‌شود." : "پیام‌ها و پاسخ نهایی این بخش برای پژوهش ثبت می‌شوند."}</p>
    </aside>
  </div>;
}

export function FreeRagChat() {
  const [taskId, setTaskId] = useState<SwtsTaskId>("task_1");
  const [sessionId, setSessionId] = useState(() => `free-${crypto.randomUUID()}-task_1`);
  const [messages, setMessages] = useState<VisibleMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesEnd = useRef<HTMLDivElement | null>(null);
  useEffect(() => { void verify(); }, []);
  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length]);
  async function verify() { setBusy(true); try { await checkRagHealth(); setReady(true); setError(""); } catch { setReady(false); setError(preparingMessage); } finally { setBusy(false); } }
  async function send(event?: FormEvent) {
    event?.preventDefault();
    const message = draft;
    if (!message.trim() || !ready || busy || !sessionId) return;
    setBusy(true); setError("");
    try {
      const result = await sendRagMessage({ session_id: sessionId, task_id: taskId, message, history: historyFromMessages(messages) });
      setMessages((current) => [...current, { key: crypto.randomUUID(), role: "user", content: message }, { key: crypto.randomUUID(), role: "assistant", content: toParticipantAnswer(result.answer) }]);
      setDraft("");
    } catch { setError(requestFailedMessage); } finally { setBusy(false); }
  }
  return <main className="free-chat-page" dir="rtl"><header className="free-chat-header"><div><p className="eyebrow">جزیره سپید</p><h1>گفت‌وگوی آزاد با سامانه</h1><p>این صفحه خارج از آزمایش است و هیچ پیام یا پاسخی را در پایگاه داده پژوهش ذخیره نمی‌کند.</p></div><Link className="secondary compact-button" href="/">بازگشت به مطالعه</Link></header><section className="free-chat-shell"><div className="free-chat-toolbar"><label>زمینه گفتگو<select value={taskId} onChange={(event) => { const next = event.target.value as SwtsTaskId; setTaskId(next); setSessionId(`free-${crypto.randomUUID()}-${next}`); setMessages([]); setDraft(""); }}>{SWTS_TASK_IDS.map((id) => <option key={id} value={id}>{SWTS_TASKS[id].title}</option>)}</select></label><span><i className={ready ? "ready" : "pending"} />{ready ? "سامانه آماده است" : "در حال اتصال"}</span></div><div className="swts-messages free-messages" aria-live="polite">{!messages.length && <div className="swts-empty"><span>✦</span><strong>گفت‌وگوی تازه</strong><p>می‌توانید آزادانه درباره اطلاعات جزیره سپید سؤال کنید.</p></div>}{messages.map((message) => <article key={message.key} className={`swts-message ${message.role}`}><span>{message.role === "user" ? "شما" : "دستیار"}</span>{message.role === "assistant" ? <MarkdownMessage>{message.content}</MarkdownMessage> : <p>{message.content}</p>}</article>)}{busy && <div className="swts-typing"><i /><i /><i /><span>در حال آماده‌کردن پاسخ…</span></div>}<div ref={messagesEnd} /></div>{error && <div className="swts-alert"><p>{error}</p>{!ready && <button onClick={() => void verify()} disabled={busy}>بررسی دوباره</button>}</div>}<form className="swts-composer" onSubmit={(event) => void send(event)}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} maxLength={8000} placeholder="پیام خود را بنویسید…" disabled={!ready || busy} /><div><small>این گفتگو فقط تا زمانی که این صفحه باز است نگه داشته می‌شود.</small><button className="chat-send" disabled={!draft.trim() || !ready || busy}>↑</button></div></form></section></main>;
}
