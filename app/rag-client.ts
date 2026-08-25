import type { SwtsTaskId } from "./swts-config";

const RAG_API_BASE = "/api/rag";

export type RagRole = "user" | "assistant";

export type RagHistoryItem = {
  role: RagRole;
  content: string;
};

export type RagSource = {
  source_id: string;
  relative_path: string;
  rank: number;
  score: number;
};

export type RagChatRequest = {
  session_id: string;
  task_id: SwtsTaskId;
  message: string;
  history: RagHistoryItem[];
};

export type RagChatResponse = {
  request_id: string;
  session_id: string;
  task_id: SwtsTaskId;
  answer: string;
  sources: RagSource[];
  retrieval: {
    top_k: number;
    embedding_model: string;
    query: string;
  };
  prompt_version: string;
};

export type RagHealthResponse = {
  status: string;
  environment: string;
  source_count: number;
  top_k: number;
  embedding_model: string;
  llm_provider: string;
};

export class RagRequestError extends Error {
  constructor(
    public readonly category: string,
    public readonly status?: number,
    public readonly requestId?: string,
  ) {
    super(category);
  }
}

export function toParticipantAnswer(answer: string): string {
  return answer
    .replace(/\s*\[S(?:0[1-9]|1[0-8])\]/g, "")
    .replace(/[ \t]+([،؛,.!?؟])/g, "$1")
    .trim();
}

async function fetchWithTimeout(
  input: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new RagRequestError("timeout");
    }
    throw new RagRequestError(navigator.onLine ? "network" : "offline");
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function checkRagHealth(): Promise<RagHealthResponse> {
  // A new serverless backend instance may need one hosted call to rebuild the
  // tiny 18-document in-memory index before it can answer its first request.
  const response = await fetchWithTimeout(`${RAG_API_BASE}/health`, { method: "GET" }, 60_000);
  if (!response.ok) throw new RagRequestError("not_ready", response.status);
  const result = (await response.json()) as RagHealthResponse;
  if (
    result.status !== "ok" ||
    result.environment !== "experiment" ||
    result.source_count !== 18 ||
    result.top_k !== 5
  ) {
    throw new RagRequestError("invalid_health");
  }
  return result;
}

export async function sendRagMessage(payload: RagChatRequest): Promise<RagChatResponse> {
  const response = await fetchWithTimeout(
    `${RAG_API_BASE}/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, history: payload.history.slice(-20) }),
    },
    75_000,
  );

  if (!response.ok) {
    let requestId: string | undefined;
    try {
      const errorBody = (await response.json()) as {
        detail?: { request_id?: string };
        request_id?: string;
      };
      requestId = errorBody.detail?.request_id || errorBody.request_id;
    } catch {
      // The status code still provides the participant-safe error category.
    }
    const category =
      response.status === 429
        ? "rate_limited"
        : response.status === 400 || response.status === 422
          ? "invalid_request"
          : response.status === 500 || response.status === 503
            ? "backend_unavailable"
            : "http_error";
    throw new RagRequestError(category, response.status, requestId);
  }

  return (await response.json()) as RagChatResponse;
}
