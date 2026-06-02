/** Resolve backend URL for server vs browser (production-safe). */

export function getServerBackendUrl(): string {
  return (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
}

/** When set on Vercel, browser calls Railway directly (avoids rewrite build-time issues). */
export function getPublicBackendUrl(): string | null {
  const url = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  return url ? url.replace(/\/$/, "") : null;
}

export function isProductionDeploy(): boolean {
  return process.env.NODE_ENV === "production";
}
