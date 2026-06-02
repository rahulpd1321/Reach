import { getServerBackendUrl } from "@/lib/backend-url";

export const dynamic = "force-dynamic";

export async function GET() {
  const backend = getServerBackendUrl();
  try {
    const res = await fetch(`${backend}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return Response.json(
      {
        status: "error",
        detail: e instanceof Error ? e.message : "Backend unreachable",
        backend,
      },
      { status: 502 }
    );
  }
}
