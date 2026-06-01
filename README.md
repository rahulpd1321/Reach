# Reach — Social Video RAG Analyst

Full-stack RAG chatbot comparing **YouTube (Video A)** vs **Instagram Reels (Video B)**. Dynamically ingests transcripts + metadata, indexes into **ChromaDB**, and answers creator questions via **LangGraph retrieval + LangChain streaming chat** with citations and session memory.

## Architecture

```
┌─────────────┐     ingest      ┌──────────────────────────────────────┐
│  Next.js UI │ ──────────────► │ FastAPI                               │
│  (stream)   │ ◄── SSE chat ── │  yt-dlp + youtube-transcript-api      │
└─────────────┘                 │  → chunk/embed → ChromaDB (video_id)   │
                                │  → LangGraph retrieve → GPT-4o stream   │
                                └──────────────────────────────────────┘
```

## Deploy

See **[DEPLOY.md](./DEPLOY.md)** for production setup (Railway backend + Vercel frontend).

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) on PATH (`pip install yt-dlp` or standalone binary)
- `GOOGLE_API_KEY` (required for chat via **Gemini**; embeddings default to local **FastEmbed BGE-small** — no API cost)

### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env — set GOOGLE_API_KEY (Gemini)

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000 — paste a **public YouTube URL** and **public Instagram Reel URL**, click **Ingest**, then chat.

**Troubleshooting "Failed to fetch"**

1. Start the **Reach** backend on port **8000** (another app on that port breaks ingest).
2. Restart `npm run dev` after changing `next.config.mjs` — the UI proxies `/api/*` to the backend.
3. Use a **real public Instagram Reel URL** (not a placeholder).
4. If Instagram blocks yt-dlp, add to `backend/.env`: `YTDLP_COOKIES_BROWSER=chrome` (logged into Instagram in that browser).

## Example questions

- Why did Video A get more engagement than Video B?
- What's the engagement rate of each?
- Compare the hooks in the first 5 seconds.
- Who's the creator of Video B and what's their follower count?
- Suggest improvements for B based on what worked in A.

## Engagement rate

`(likes + comments) / views × 100` — computed at ingest from live metadata.

## Tech choices

| Layer | Choice | Why |
|-------|--------|-----|
| Ingest | **yt-dlp** + **youtube-transcript-api** | Free, no vendor lock-in; works for YT + IG public URLs |
| Embeddings (default) | **FastEmbed BGE-small-en** (local) | Zero embedding API cost; fast install vs full PyTorch stack |
| Embeddings (optional) | `text-embedding-3-small` | Set `USE_OPENAI_EMBEDDINGS=true` for slightly better retrieval |
| Vector DB | **ChromaDB** (persistent) | Zero ops for demo; swap to **Qdrant/Pinecone** for multi-tenant prod |
| Orchestration | **LangGraph** (retrieve) + **LangChain** (stream) | Meets requirement; clear separation of retrieval vs generation |
| LLM | **Gemini 2.0 Flash** (default; set `LLM_PROVIDER=openai` for GPT) | Strong reasoning, generous free tier, fast streaming |

## Scalability & cost (1000 creators/day)

**Bottleneck order:** video fetch → embedding → storage → LLM tokens.

### Recommended production path

1. **Ingest queue** (SQS/Redis + Celery): rate-limit yt-dlp; cache by `platform:video_id` in S3 (metadata JSON + transcript text, TTL 24h).
2. **Embeddings:** batch on GPU workers with **BGE** or **Cohere embed v3** (~$0.02/1M tokens vs OpenAI). Re-embed only when transcript changes.
3. **Vector DB:** **Qdrant** or **Pinecone** with namespace per `creator_id`, metadata filter `video_id`. Chroma is fine for &lt;100k chunks single-node.
4. **LLM:** **Gemini Flash** for chat (low cost / free tier); route simple metric questions to **deterministic handlers** (engagement rate, creator name) — no LLM call — saves ~30% tokens.
5. **Session memory:** Redis with 20-turn window; not full transcript in prompt.
6. **Instagram:** yt-dlp breaks when Meta changes; fallback **Apify/ScraperAPI** only for IG (~$0.001/Reel) if needed.

### Cost sketch (1000 creators/day, 2 videos each, ~5 chat turns)

| Item | Estimate/day |
|------|----------------|
| yt-dlp / compute | ~$5–15 (spot workers) |
| Embeddings (BGE self-hosted) | ~$2–5 GPU amortized |
| LLM (4o-mini, ~2k tokens/session) | ~$15–40 |
| Vector DB (Qdrant cloud starter) | ~$5–25 |
| **Total** | **~$30–85/day** |

**Higher quality alternative:** AssemblyAI for transcripts when captions missing (+$0.15/min) + **gpt-4o** for final answers (+3× LLM cost) — use only for paying tiers.

**Lower cost alternative:** Llama 3.1 8B on Groq for chat + BGE embeddings — ~60% cheaper LLM, slightly weaker comparison reasoning.

This repo defaults to **lowest cost that still meets quality**: local BGE + Gemini Flash + free transcripts.

## API

- `POST /api/ingest` — `{ youtube_url, instagram_url }`
- `POST /api/chat` — SSE stream `{ session_id, message }`
- `GET /api/session/{session_id}` — history + videos
- `GET /health`

## Loom demo checklist

1. Show ingest with real YouTube + Instagram URLs.
2. Show side-by-side cards (engagement %, stats).
3. Ask 2–3 suggested prompts; show **streaming** + **source citations**.
4. Follow-up question to prove **memory**.
5. Explain scale/cost section above.

## License

MIT
