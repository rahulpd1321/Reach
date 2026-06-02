import { getServerBackendUrl } from "@/lib/backend-url";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: { sessionId: string } }
) {
  const backend = getServerBackendUrl();
  const res = await fetch(`${backend}/api/session/${params.sessionId}`, {
    cache: "no-store",
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
