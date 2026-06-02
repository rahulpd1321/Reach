/**
 * API client: uses NEXT_PUBLIC_BACKEND_URL in production when set,
 * otherwise same-origin proxies (/backend-health, /api/*).
 */
import { getPublicBackendUrl } from "./backend-url";

function healthUrl(): string {
  const direct = getPublicBackendUrl();
  return direct ? `${direct}/health` : "/backend-health";
}

function ingestUrl(): string {
  const direct = getPublicBackendUrl();
  return direct ? `${direct}/api/ingest` : "/api/ingest";
}

function sessionUrl(sessionId: string): string {
  const direct = getPublicBackendUrl();
  return direct
    ? `${direct}/api/session/${sessionId}`
    : `/api/session/${sessionId}`;
}

function chatUrl(): string {
  const direct = getPublicBackendUrl();
  // Direct to Railway avoids Vercel serverless timeout on long SSE streams
  return direct ? `${direct}/api/chat` : "/api/chat";
}

export interface VideoMetadata {
  video_id: string;
  platform: string;
  url: string;
  title: string;
  creator: string;
  follower_count: number | null;
  views: number;
  likes: number;
  comments: number;
  engagement_rate: number;
  hashtags: string[];
  upload_date: string | null;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  transcript_preview: string;
}

export interface SourceCitation {
  video_id: string;
  chunk_index: number;
  content_snippet: string;
  score?: number;
}

export interface IngestResponse {
  session_id: string;
  videos: VideoMetadata[];
  chunks_indexed: number;
}

export interface ChatMessage {
  role: string;
  content: string;
  sources?: SourceCitation[];
}

export interface BackendHealth {
  status: string;
  llm_provider?: string;
  llm_model?: string;
  llm_ready?: boolean;
  detail?: string;
  backend?: string;
}

function isLocalDev(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
  );
}

function networkErrorMessage(): string {
  if (isLocalDev()) {
    return (
      "Cannot reach the Reach API locally. Start the backend:\n" +
      "cd backend\n" +
      ".venv\\Scripts\\uvicorn app.main:app --reload --port 8000\n" +
      "Then: npm run dev"
    );
  }
  return (
    "Cannot reach your deployed API.\n\n" +
    "On Vercel → Settings → Environment Variables, set:\n" +
    "• BACKEND_URL = your Railway URL (e.g. https://xxx.up.railway.app)\n" +
    "• NEXT_PUBLIC_BACKEND_URL = same Railway URL\n\n" +
    "On Railway → FRONTEND_ORIGIN = your Vercel URL\n\n" +
    "Then Redeploy Vercel (required after env changes)."
  );
}

function wrapFetchError(err: unknown): Error {
  if (err instanceof TypeError) {
    return new Error(networkErrorMessage());
  }
  if (err instanceof Error) return err;
  return new Error("Request failed");
}

export async function checkBackendHealth(): Promise<BackendHealth> {
  try {
    const res = await fetch(healthUrl(), { cache: "no-store" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Health check failed (${res.status})`);
    }
    return res.json();
  } catch (e) {
    throw wrapFetchError(e);
  }
}

export function isReachBackend(health: BackendHealth): boolean {
  return health.status === "ok" && Boolean(health.llm_provider);
}

export async function ingestVideos(
  youtubeUrl: string,
  instagramUrl: string
): Promise<IngestResponse> {
  try {
    const res = await fetch(ingestUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        youtube_url: youtubeUrl,
        instagram_url: instagramUrl,
      }),
      signal: AbortSignal.timeout(600_000),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg).join(", ")
        : detail || `Ingest failed (${res.status})`;
      throw new Error(msg);
    }
    return res.json();
  } catch (e) {
    throw wrapFetchError(e);
  }
}

export async function getSession(sessionId: string) {
  try {
    const res = await fetch(sessionUrl(sessionId));
    if (!res.ok) throw new Error("Session not found");
    return res.json();
  } catch (e) {
    throw wrapFetchError(e);
  }
}

export type StreamEvent =
  | { type: "status"; content: string }
  | { type: "token"; content: string }
  | { type: "sources"; content: SourceCitation[] }
  | { type: "done"; content: string }
  | { type: "error"; content: string };

function parseSseChunk(raw: string): StreamEvent | null {
  const lines = raw.split(/\r?\n/);
  let data = "";
  for (const line of lines) {
    if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  }
  if (!data) return null;
  try {
    return JSON.parse(data) as StreamEvent;
  } catch {
    return null;
  }
}

export async function streamChat(
  sessionId: string,
  message: string,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  try {
    const res = await fetch(chatUrl(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.content || err.detail || `Chat failed (${res.status})`);
    }

    if (!res.body) {
      throw new Error("Chat stream not available");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() || "";

      for (const part of parts) {
        const ev = parseSseChunk(part);
        if (ev) onEvent(ev);
      }
    }

    if (buffer.trim()) {
      const ev = parseSseChunk(buffer);
      if (ev) onEvent(ev);
    }
  } catch (e) {
    throw wrapFetchError(e);
  }
}

export const SUGGESTED_PROMPTS = [
  "Why did Video A get more engagement than Video B?",
  "What's the engagement rate of each?",
  "Compare the hooks in the first 5 seconds.",
  "Who's the creator of Video B and what's their follower count?",
  "Suggest improvements for B based on what worked in A.",
];
