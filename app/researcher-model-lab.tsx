"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  DEFAULT_MODEL_EVALUATION_SCENARIOS,
  type ModelEvaluationScenario,
} from "./model-evaluation-scenarios";
import {
  sendRagMessage,
  type RagChatResponse,
  type RagHistoryItem,
  type RagTaskId,
} from "./rag-client";

type EvaluationTurn = {
  question: string;
  response?: RagChatResponse;
  error?: string;
  elapsedMs: number;
};

const cloneDefaults = () =>
  DEFAULT_MODEL_EVALUATION_SCENARIOS.map((scenario) => ({
    ...scenario,
    questions: [...scenario.questions],
  }));

export default function ResearcherModelLab({ language }: { language: "fa" | "en" }) {
  const fa = language === "fa";
  const [scenarios, setScenarios] = useState<ModelEvaluationScenario[]>(cloneDefaults);
  const [selectedId, setSelectedId] = useState(DEFAULT_MODEL_EVALUATION_SCENARIOS[0]?.id || "");
  const [results, setResults] = useState<EvaluationTurn[]>([]);
  const [running, setRunning] = useState(false);
  const selected = useMemo(
    () => scenarios.find((scenario) => scenario.id === selectedId) || scenarios[0],
    [scenarios, selectedId],
  );

  function updateSelected(change: Partial<ModelEvaluationScenario>) {
    if (!selected) return;
    setScenarios((current) =>
      current.map((scenario) => scenario.id === selected.id ? { ...scenario, ...change } : scenario),
    );
  }

  function addScenario() {
    const id = `scenario-${crypto.randomUUID()}`;
    setScenarios((current) => [...current, {
      id,
      title: fa ? "سناریوی تازه" : "New scenario",
      taskId: "free_chat",
      questions: [""],
    }]);
    setSelectedId(id);
    setResults([]);
  }

  function deleteScenario() {
    if (!selected) return;
    const remaining = scenarios.filter((scenario) => scenario.id !== selected.id);
    setScenarios(remaining);
    setSelectedId(remaining[0]?.id || "");
    setResults([]);
  }

  async function runScenario() {
    if (!selected || running) return;
    const questions = selected.questions.map((item) => item.trim()).filter(Boolean);
    if (!questions.length) return;
    setRunning(true);
    setResults([]);
    const history: RagHistoryItem[] = [];
    const sessionId = `researcher-eval-${crypto.randomUUID()}`;
    const collected: EvaluationTurn[] = [];
    for (const question of questions) {
      const started = performance.now();
      try {
        const response = await sendRagMessage({
          session_id: sessionId,
          task_id: selected.taskId,
          message: question,
          history,
        });
        const turn = { question, response, elapsedMs: performance.now() - started };
        collected.push(turn);
        history.push({ role: "user", content: question }, { role: "assistant", content: response.answer });
      } catch (error) {
        collected.push({
          question,
          error: error instanceof Error ? error.message : "request_failed",
          elapsedMs: performance.now() - started,
        });
      }
      setResults([...collected]);
    }
    setRunning(false);
  }

  return <section className="card model-lab">
    <div className="model-lab-heading">
      <div>
        <p className="card-kicker">{fa ? "آزمایشگاه مدل" : "Model scenario lab"}</p>
        <p className="muted">{fa
          ? "یک گفت‌وگوی چندمرحله‌ای واقعی را اجرا کنید. سناریوها، پرسش‌ها و نتایج با خروج از صفحه پاک می‌شوند."
          : "Run a real multi-turn conversation. Scenarios, questions, and results are cleared when you leave this page."}</p>
      </div>
      <div className="model-lab-actions">
        <button type="button" className="secondary compact-button" onClick={addScenario}>{fa ? "سناریوی جدید" : "New scenario"}</button>
        <button type="button" className="admin-text-button danger" onClick={deleteScenario} disabled={!selected}>{fa ? "حذف" : "Delete"}</button>
      </div>
    </div>

    {!selected ? <button type="button" className="primary" onClick={addScenario}>{fa ? "ساخت نخستین سناریو" : "Create first scenario"}</button> : <>
      <div className="model-lab-config">
        <label>{fa ? "سناریو" : "Scenario"}<select value={selected.id} onChange={(event) => { setSelectedId(event.target.value); setResults([]); }}>{scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.title}</option>)}</select></label>
        <label>{fa ? "عنوان" : "Title"}<input value={selected.title} onChange={(event) => updateSelected({ title: event.target.value })} /></label>
        <label>{fa ? "حالت مدل" : "Model context"}<select value={selected.taskId} onChange={(event) => updateSelected({ taskId: event.target.value as RagTaskId })}><option value="free_chat">free_chat</option><option value="task_1">task_1</option><option value="task_2">task_2</option><option value="task_3">task_3</option></select></label>
      </div>
      <div className="model-lab-questions">
        {selected.questions.map((question, index) => <div key={`${selected.id}-${index}`}>
          <span>{index + 1}</span>
          <textarea value={question} onChange={(event) => updateSelected({ questions: selected.questions.map((item, itemIndex) => itemIndex === index ? event.target.value : item) })} />
          <div>
            <button type="button" aria-label={fa ? "بالا" : "Move up"} disabled={index === 0} onClick={() => { const next = [...selected.questions]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; updateSelected({ questions: next }); }}>↑</button>
            <button type="button" aria-label={fa ? "پایین" : "Move down"} disabled={index === selected.questions.length - 1} onClick={() => { const next = [...selected.questions]; [next[index], next[index + 1]] = [next[index + 1], next[index]]; updateSelected({ questions: next }); }}>↓</button>
            <button type="button" aria-label={fa ? "حذف پرسش" : "Delete question"} onClick={() => updateSelected({ questions: selected.questions.filter((_, itemIndex) => itemIndex !== index) })}>×</button>
          </div>
        </div>)}
        <button type="button" className="model-lab-add-question" onClick={() => updateSelected({ questions: [...selected.questions, ""] })}>+ {fa ? "افزودن پرسش" : "Add question"}</button>
      </div>
      <div className="model-lab-runbar">
        <span>{fa ? `${selected.questions.filter((item) => item.trim()).length} پیام، با حفظ تاریخچه` : `${selected.questions.filter((item) => item.trim()).length} messages with history`}</span>
        <button type="button" className="primary compact-button" onClick={() => void runScenario()} disabled={running || !selected.questions.some((item) => item.trim())}>{running ? (fa ? "در حال اجرا…" : "Running…") : (fa ? "اجرای سناریو" : "Run scenario")}</button>
        <button type="button" className="secondary compact-button" onClick={() => setResults([])} disabled={!results.length || running}>{fa ? "پاک‌کردن نتایج" : "Clear results"}</button>
      </div>
    </>}

    {!!results.length && <div className="model-lab-results">{results.map((turn, index) => <article key={`${index}-${turn.question}`}>
      <div className="model-lab-question"><span>{index + 1}</span><p>{turn.question}</p></div>
      {turn.response ? <div className="model-lab-answer">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.response.answer}</ReactMarkdown>
        <footer><span>{turn.elapsedMs.toFixed(0)} ms</span><span>{turn.response.prompt_version}</span><span>{turn.response.knowledge_scope?.classification || "unknown"}</span><span>{turn.response.knowledge_scope?.judge_status || "unknown"}</span><span>{turn.response.verification?.status || "unknown"}</span></footer>
        {turn.response.knowledge_scope?.coverage && <p className="model-lab-coverage">{turn.response.knowledge_scope.coverage}</p>}
        <details><summary>{fa ? `شواهد بازیابی‌شده (${turn.response.sources.length})` : `Retrieved evidence (${turn.response.sources.length})`}</summary><ul>{turn.response.sources.map((source) => <li key={`${source.source_id}-${source.chunk_id}`}>{source.chunk_id || source.source_id} · {source.topic || "—"} · {source.score.toFixed(3)}</li>)}</ul></details>
      </div> : <p className="model-lab-error">{fa ? "خطا: " : "Error: "}{turn.error}</p>}
    </article>)}</div>}
  </section>;
}
