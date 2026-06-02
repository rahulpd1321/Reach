"use client";

import { useEffect, useState } from "react";
import { VideoCard } from "@/components/VideoCard";
import { ChatPanel } from "@/components/ChatPanel";
import {
  checkBackendHealth,
  ingestVideos,
  isReachBackend,
  VideoMetadata,
} from "@/lib/api";
import { Loader2, Zap, Link2, AlertTriangle, CheckCircle2 } from "lucide-react";

const DEFAULT_YOUTUBE =
  process.env.NEXT_PUBLIC_DEMO_YOUTUBE ||
  "https://www.youtube.com/watch?v=jNQXAC9IVRw";
const DEFAULT_INSTAGRAM = process.env.NEXT_PUBLIC_DEMO_INSTAGRAM || "";

export default function Home() {
  const [youtubeUrl, setYoutubeUrl] = useState(DEFAULT_YOUTUBE);
  const [instagramUrl, setInstagramUrl] = useState(DEFAULT_INSTAGRAM);
  const [videos, setVideos] = useState<VideoMetadata[] | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chunks, setChunks] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<"checking" | "ok" | "offline" | "wrong">(
    "checking"
  );
  const [healthInfo, setHealthInfo] = useState<string | null>(null);

  const isLocal =
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1");

  useEffect(() => {
    checkBackendHealth()
      .then((h) => {
        setHealthInfo(JSON.stringify(h));
        setApiStatus(isReachBackend(h) ? "ok" : "wrong");
      })
      .catch((e) => {
        setHealthInfo(e instanceof Error ? e.message : "unknown error");
        setApiStatus("offline");
      });
  }, []);

  async function handleIngest() {
    if (!instagramUrl.trim()) {
      setError("Paste a public Instagram Reel URL (Video B).");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await ingestVideos(youtubeUrl.trim(), instagramUrl.trim());
      setVideos(res.videos);
      setSessionId(res.session_id);
      setChunks(res.chunks_indexed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingest failed");
      setVideos(null);
      setSessionId(null);
    } finally {
      setLoading(false);
    }
  }

  const videoA = videos?.find((v) => v.video_id === "A");
  const videoB = videos?.find((v) => v.video_id === "B");

  return (
    <main className="min-h-screen px-4 py-8 md:px-8 max-w-[1600px] mx-auto">
      <header className="mb-10 text-center md:text-left">
        <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
          <Zap className="w-8 h-8 text-violet-400" />
          <h1 className="font-display text-4xl md:text-5xl font-bold gradient-text">
            Reach
          </h1>
        </div>
        <p className="text-reach-muted max-w-xl mx-auto md:mx-0">
          Compare YouTube vs Instagram Reels with RAG — transcripts, engagement
          metrics, and AI insights with cited sources.
        </p>
      </header>

      {apiStatus !== "ok" && (
        <div
          className={`mb-6 rounded-xl px-4 py-3 text-sm flex gap-2 items-start border ${
            apiStatus === "checking"
              ? "border-reach-border text-reach-muted"
              : "border-amber-500/40 bg-amber-500/10 text-amber-200"
          }`}
        >
          {apiStatus === "checking" ? (
            <Loader2 className="w-4 h-4 animate-spin shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          )}
          <div className="whitespace-pre-wrap">
            {apiStatus === "checking" && "Checking API connection…"}
            {apiStatus === "offline" &&
              (isLocal
                ? "Reach backend is not running on port 8000.\n\n1. Stop whatever is using port 8000 (see README)\n2. cd backend\n3. .venv\\Scripts\\uvicorn app.main:app --reload --port 8000\n4. npm run dev"
                : "Cannot reach your Railway API.\n\nVercel → Settings → Environment Variables:\n• BACKEND_URL = https://YOUR-APP.up.railway.app\n• NEXT_PUBLIC_BACKEND_URL = same URL\n\nThen Redeploy Vercel. Test Railway: YOUR-URL/health must show llm_provider.")}
            {apiStatus === "wrong" &&
              (isLocal
                ? "Something on port 8000 is NOT the Reach API (health missing llm_provider).\n\nFix:\n1. PowerShell: Get-NetTCPConnection -LocalPort 8000 | Select OwningProcess\n2. Stop-Process -Id <PID> -Force\n3. Start Reach: cd backend → .venv\\Scripts\\uvicorn app.main:app --reload --port 8000"
                : "Vercel is pointing at the wrong backend URL (not Reach).\n\nSet BOTH env vars to your Railway URL (not localhost:8000):\n• BACKEND_URL\n• NEXT_PUBLIC_BACKEND_URL\n\nOpen Railway-URL/health — must include \"llm_provider\": \"gemini\". Then Redeploy Vercel.")}
            {healthInfo && apiStatus !== "ok" && apiStatus !== "checking" && (
              <p className="mt-2 text-[10px] text-amber-400/70 font-mono break-all">
                Debug: {healthInfo}
              </p>
            )}
          </div>
        </div>
      )}
      {apiStatus === "ok" && (
        <div className="mb-6 flex items-center gap-2 text-xs text-emerald-400/90">
          <CheckCircle2 className="w-4 h-4" />
          API connected
        </div>
      )}

      <section className="glass rounded-2xl p-5 mb-8 border border-reach-border">
        <div className="flex items-center gap-2 text-sm text-reach-muted mb-4">
          <Link2 className="w-4 h-4" />
          <span>Video URLs (YouTube = A, Instagram Reel = B)</span>
        </div>
        <div className="grid md:grid-cols-2 gap-3 mb-4">
          <input
            type="url"
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            placeholder="YouTube URL"
            className="bg-reach-bg/80 border border-reach-border rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-violet-500/50 outline-none"
          />
          <input
            type="url"
            value={instagramUrl}
            onChange={(e) => setInstagramUrl(e.target.value)}
            placeholder="Instagram Reel URL"
            className="bg-reach-bg/80 border border-reach-border rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-cyan-500/50 outline-none"
          />
        </div>
        <button
          type="button"
          onClick={handleIngest}
          disabled={loading}
          className="w-full md:w-auto px-8 py-3 rounded-xl font-semibold bg-gradient-to-r from-violet-600 to-cyan-600 hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2 transition"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Fetching metadata & indexing…
            </>
          ) : (
            "Ingest & Index Transcripts"
          )}
        </button>
        {error && (
          <p className="mt-3 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 whitespace-pre-wrap">
            {error}
          </p>
        )}
        {chunks > 0 && (
          <p className="mt-3 text-xs text-reach-muted">
            Indexed {chunks} transcript chunks into ChromaDB · session{" "}
            <code className="text-cyan-400">{sessionId?.slice(0, 8)}…</code>
          </p>
        )}
      </section>

      <div className="grid lg:grid-cols-[1fr_400px] xl:grid-cols-[1fr_440px] gap-6">
        <div className="grid md:grid-cols-2 gap-6">
          {videoA ? (
            <VideoCard video={videoA} label="Video A" accent="violet" />
          ) : (
            <PlaceholderCard label="Video A — YouTube" accent="violet" />
          )}
          {videoB ? (
            <VideoCard video={videoB} label="Video B" accent="cyan" />
          ) : (
            <PlaceholderCard label="Video B — Instagram" accent="cyan" />
          )}
        </div>

        <div className="lg:sticky lg:top-6 h-[calc(100vh-8rem)] max-h-[720px]">
          <ChatPanel sessionId={sessionId} disabled={!sessionId} />
        </div>
      </div>
    </main>
  );
}

function PlaceholderCard({
  label,
  accent,
}: {
  label: string;
  accent: "violet" | "cyan";
}) {
  return (
    <div
      className={`glass rounded-2xl border border-dashed ${
        accent === "violet" ? "border-violet-500/30" : "border-cyan-500/30"
      } aspect-[4/5] flex items-center justify-center text-reach-muted text-sm p-8 text-center`}
    >
      {label}
      <br />
      <span className="text-xs mt-2 block opacity-60">
        Ingest to load live metadata
      </span>
    </div>
  );
}
