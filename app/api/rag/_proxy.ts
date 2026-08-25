import { NextResponse } from "next/server";

const DEFAULT_LOCAL_RAG_URL = "http://127.0.0.1:8000";

function ragBaseUrl(): string | null {
  const configured = process.env.RAG_API_URL?.trim();
  if (configured) return configured.replace(/\/+$/, "");
  return process.env.NODE_ENV === "development" ? DEFAULT_LOCAL_RAG_URL : null;
}

function upstreamHeaders(contentType = false): HeadersInit {
  const headers: Record<string, string> = {};
  if (contentType) headers["Content-Type"] = "application/json";
  const token = process.env.RAG_API_TOKEN?.trim();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function unavailable() {
  return NextResponse.json(
    { detail: "rag_backend_unavailable" },
    { status: 503, headers: { "Cache-Control": "no-store" } },
  );
}

async function forward(path: "/health" | "/chat", init: RequestInit) {
  const baseUrl = ragBaseUrl();
  if (!baseUrl) return unavailable();

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      cache: "no-store",
      signal: AbortSignal.timeout(path === "/chat" ? 70_000 : 55_000),
    });
    const body = await response.text();
    return new NextResponse(body || null, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return unavailable();
  }
}

export function proxyRagHealth() {
  return forward("/health", { method: "GET", headers: upstreamHeaders() });
}

export async function proxyRagChat(request: Request) {
  const rawBody = await request.text();
  if (!rawBody || rawBody.length > 180_000) {
    return NextResponse.json({ detail: "invalid_request" }, { status: 400 });
  }
  return forward("/chat", {
    method: "POST",
    headers: upstreamHeaders(true),
    body: rawBody,
  });
}
