import { getServerBackendUrl } from "@/lib/backend-url";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST(req: Request) {
  const backend = getServerBackendUrl();
  const body = await req.text();

  try {
    const res = await fetch(`${backend}/api/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: AbortSignal.timeout(600_000),
    });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return Response.json(
      {
        detail:
          e instanceof Error
            ? e.message
            : `Cannot reach backend at ${backend}`,
      },
      { status: 502 }
    );
  }
}
