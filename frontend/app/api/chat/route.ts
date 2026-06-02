/**
 * Stream chat SSE from FastAPI without Next.js rewrite buffering.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { getServerBackendUrl } from "@/lib/backend-url";

export async function POST(req: Request) {
  const backend = getServerBackendUrl();
  const body = await req.text();

  let upstream: Response;
  try {
    upstream = await fetch(`${backend}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body,
    });
  } catch {
    return new Response(
      JSON.stringify({
        type: "error",
        content: "Cannot reach Reach backend. Is uvicorn running on port 8000?",
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
