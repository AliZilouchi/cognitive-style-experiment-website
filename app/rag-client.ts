import type { SwtsTaskId } from "./swts-config";

const RAG_API_BASE = "/api/rag";

export type RagRole = "user" | "assistant";
export type RagTaskId = SwtsTaskId | "free_chat";

export type RagHistoryItem = {
  role: RagRole;
  content: string;
};

export type RagSource = {
  source_id: string;
  chunk_id?: string;
  topic?: string;
  relative_path: string;
  rank: number;
  score: number;
};

export type RagChatRequest = {
  session_id: string;
  task_id: RagTaskId;
  message: string;
  history: RagHistoryItem[];
};

export type RagChatResponse = {
  request_id: string;
  session_id: string;
  task_id: RagTaskId;
  answer: string;
  sources: RagSource[];
  retrieval: {
    requested_top_k: number;
    returned_chunks: number;
    task_id: RagTaskId;
    embedding_model: string;
    query: string;
  };
  prompt_version: string;
  knowledge_scope?: {
    version: string;
    classification: "supported" | "outside_world" | "unknown_topic" | "unknown";
    task_relevance?: "core" | "adjacent" | "outside_task" | "free_chat" | "unknown";
  };
  verification?: {
    enabled: boolean;
    status:
      | "verified_unchanged"
      | "verified_revised"
      | "fallback_to_draft"
      | "disabled"
      | "not_needed"
      | "not_available"
      | "unknown";
    prompt_version: string;
  };
};

export type RagHealthResponse = {
  status: string;
  environment: string;
  source_count: number;
  chunk_count?: number;
  top_k: number;
  embedding_model: string;
  llm_provider: string;
  response_verifier?: boolean;
  knowledge_scope_version?: string;
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
    .replace(/\s*\[(?:S\d{2}|E\d{2})\]/g, "")
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
  // semantic-chunk in-memory index before it can answer its first request.
  const response = await fetchWithTimeout(`${RAG_API_BASE}/health`, { method: "GET" }, 60_000);
  if (!response.ok) throw new RagRequestError("not_ready", response.status);
  const result = (await response.json()) as RagHealthResponse;
  if (
    result.status !== "ok" ||
    result.environment !== "experiment" ||
    !Number.isInteger(result.source_count) ||
    result.source_count < 1 ||
    !Number.isInteger(result.top_k) ||
    result.top_k < 1 ||
    result.top_k > 10
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
