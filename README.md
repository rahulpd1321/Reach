# Website URL - (https://reach-five-rho.vercel.app/)
# Reach — Social Video RAG Analyst

> Full-stack RAG chatbot that compares **YouTube (Video A)** vs **Instagram Reels (Video B)** using live transcripts, engagement metrics, vector search, and streaming AI answers with citations and conversation memory.

---

## Table of Contents

1. [What This Project Does](#1-what-this-project-does)
2. [Project Overview](#2-project-overview)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [File Structure](#5-file-structure)
6. [Core Concepts & Knowledge](#6-core-concepts--knowledge)
7. [How It Works — End-to-End Workflow](#7-how-it-works--end-to-end-workflow)
8. [RAG Pipeline (Detailed)](#8-rag-pipeline-detailed)
9. [API Reference](#9-api-reference)
10. [Environment Variables](#10-environment-variables)
11. [Building & Running Locally](#11-building--running-locally)
12. [Expected Output](#12-expected-output)
13. [Example Questions](#13-example-questions)
14. [Deployment](#14-deployment)
15. [Troubleshooting](#15-troubleshooting)
16. [Scalability & Cost](#16-scalability--cost)
17. [FAQ](#17-faq)
18. [License](#18-license)

---

## 1. What This Project Does

**Reach** helps social media creators and analysts **compare two videos side by side**:


| Input                  | Role                                |
| ---------------------- | ----------------------------------- |
| **YouTube URL**        | Video **A** — first video ingested  |
| **Instagram Reel URL** | Video **B** — second video ingested |


For each video, Reach **automatically**:

- Fetches **metadata** (views, likes, comments, creator, followers, hashtags, upload date, duration, thumbnail)
- Extracts **transcripts** (captions via API or yt-dlp subtitles)
- Computes **engagement rate**: `(likes + comments) / views × 100`
- **Chunks** transcript text and **embeds** it into **ChromaDB** (tagged `video_id`: A or B)
- Powers a **RAG chat** where you ask natural-language questions and get **streaming answers** with **source citations** (`[Video A, chunk 3]`) and **multi-turn memory**

Nothing is hard-coded about video content — only demo URL placeholders in the UI can be preset; all metrics and answers are **dynamic** from the URLs you provide.

---

## 2. Project Overview


| Aspect            | Description                                                                  |
| ----------------- | ---------------------------------------------------------------------------- |
| **Type**          | Full-stack web application (monorepo)                                        |
| **Frontend**      | Next.js 14 (React) — video cards + streaming chat UI                         |
| **Backend**       | FastAPI (Python) — ingest, indexing, RAG, SSE streaming                      |
| **AI**            | LangGraph (retrieval) + LangChain (generation) + Google Gemini (default LLM) |
| **Vector DB**     | ChromaDB (persistent collections per session)                                |
| **Embeddings**    | FastEmbed BGE-small-en (local, no API cost by default)                       |
| **Transcripts**   | yt-dlp + youtube-transcript-api                                              |
| **Deploy target** | Railway (backend) + Vercel (frontend)                                        |


**Primary users:** Creators, growth marketers, and engineers evaluating cross-platform video performance.

---

## 3. Architecture

### High-level diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                                   │
│                    https://your-app.vercel.app                           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
   /health (or            /api/ingest            /api/chat (SSE)
   Railway direct)        (2–5 min)              (stream tokens)
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Railway / :8000)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌─────────────────┐ │
│  │ video_      │  │ vector_store │  │ rag_graph  │  │ rag_service     │ │
│  │ ingestion   │→ │ ChromaDB     │← │ (LangGraph)│→ │ (LangChain +    │ │
│  │ yt-dlp      │  │ + FastEmbed  │  │ retrieve   │  │  Gemini stream) │ │
│  └─────────────┘  └──────────────┘  └────────────┘  └─────────────────┘ │
│         │                │                  │                  │          │
│         └────────────────┴──────────────────┴──────────────────┘          │
│                              session_store (in-memory)                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Request paths (production)


| Action         | Browser calls                        | Backend endpoint             |
| -------------- | ------------------------------------ | ---------------------------- |
| Health check   | `NEXT_PUBLIC_BACKEND_URL/health`     | `GET /health`                |
| Ingest         | `NEXT_PUBLIC_BACKEND_URL/api/ingest` | `POST /api/ingest`           |
| Chat           | `NEXT_PUBLIC_BACKEND_URL/api/chat`   | `POST /api/chat` (SSE)       |
| Fallback proxy | Vercel `/api/chat`, `/api/ingest`    | Same (if public URL not set) |


### Component responsibilities


| Component           | Responsibility                                             |
| ------------------- | ---------------------------------------------------------- |
| **Next.js UI**      | URL inputs, video cards, chat panel, SSE client            |
| **video_ingestion** | yt-dlp metadata + transcript for YT & IG                   |
| **vector_store**    | Chunk transcripts, embed, store in Chroma per `session_id` |
| **rag_graph**       | LangGraph node: similarity search → context + sources      |
| **rag_service**     | LangChain prompt + Gemini stream + session memory          |
| **session_store**   | Per-session videos, messages, chunk count (RAM)            |
| **llm_provider**    | Gemini (default) or OpenAI with model fallbacks on quota   |


---

## 4. Tech Stack


| Layer             | Technology                                      | Purpose                        |
| ----------------- | ----------------------------------------------- | ------------------------------ |
| **UI**            | Next.js 14, React 18, Tailwind CSS              | App Router, streaming UX       |
| **API**           | FastAPI, Uvicorn, Pydantic                      | REST + SSE                     |
| **Orchestration** | LangGraph, LangChain                            | Retrieval graph + chat chain   |
| **LLM**           | Google Gemini (`gemini-2.5-flash-lite` default) | Answers; OpenAI optional       |
| **Embeddings**    | FastEmbed (`BAAI/bge-small-en-v1.5`)            | Local vectors; OpenAI optional |
| **Vector DB**     | ChromaDB                                        | Persistent chunk storage       |
| **Video**         | yt-dlp, youtube-transcript-api                  | Metadata + captions            |
| **Streaming**     | SSE (sse-starlette + fetch reader)              | Token-by-token chat            |
| **Deploy**        | Railway, Vercel, Docker                         | Production hosting             |


---

## 5. File Structure

```
Reach/
├── README.md                 # This file               
├── docker-compose.yml        # Local Docker (dev)
├── docker-compose.prod.yml   # Production Docker (VPS)
├── render.yaml               # Render.com blueprint (optional)
│
├── backend/                  # FastAPI API (deploy root on Railway)
│   ├── Dockerfile
│   ├── railway.toml
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py           # Routes: /health, /api/ingest, /api/chat, /api/session
│       ├── config.py         # Settings from environment
│       ├── models/
│       │   └── schemas.py    # Pydantic request/response models
│       └── services/
│           ├── video_ingestion.py   # yt-dlp + transcripts
│           ├── vector_store.py      # Chunk, embed, Chroma index/retrieve
│           ├── embeddings_provider.py  # FastEmbed / OpenAI embeddings
│           ├── rag_graph.py           # LangGraph retrieval node
│           ├── rag_service.py         # LangChain stream + memory
│           ├── llm_provider.py        # Gemini / OpenAI + fallbacks
│           ├── context_format.py      # Metadata + citation formatting
│           └── session_store.py       # In-memory sessions
│
├── frontend/                 # Next.js UI (deploy root on Vercel)
│   ├── package.json
│   ├── next.config.mjs       # Rewrites to backend (fallback)
│   ├── vercel.json           # Vercel build + function timeouts
│   ├── .env.example
│   ├── app/
│   │   ├── page.tsx          # Main page: ingest + layout
│   │   ├── layout.tsx          # Fonts, global shell
│   │   ├── globals.css
│   │   ├── api/
│   │   │   ├── chat/route.ts       # SSE proxy to Railway
│   │   │   ├── ingest/route.ts     # Long-running ingest proxy
│   │   │   └── session/[sessionId]/route.ts
│   │   └── backend-health/route.ts # Health proxy
│   ├── components/
│   │   ├── VideoCard.tsx     # Side-by-side metrics UI
│   │   └── ChatPanel.tsx     # RAG chat + suggested prompts
│   └── lib/
│       ├── api.ts            # fetch helpers, SSE parser
│       └── backend-url.ts    # BACKEND_URL resolution
│
├── scripts/
│   ├── start-backend.ps1
│   └── start-frontend.ps1
│
└── .github/workflows/
    └── deploy-check.yml      # CI: import backend + build frontend
```

---

## 6. Core Concepts & Knowledge

### 6.1 RAG (Retrieval-Augmented Generation)

Instead of asking the LLM to guess, Reach:

1. **Retrieves** the most relevant transcript chunks from Chroma (semantic search).
2. **Augments** the prompt with those chunks + structured metadata (views, engagement, etc.).
3. **Generates** an answer grounded in that context, with inline citations.

### 6.2 Video A vs Video B


| ID    | Platform  | Source field                           |
| ----- | --------- | -------------------------------------- |
| **A** | YouTube   | First URL in ingest (`youtube_url`)    |
| **B** | Instagram | Second URL in ingest (`instagram_url`) |


Every chunk in Chroma carries `metadata.video_id` = `"A"` or `"B"`.

### 6.3 Engagement rate

```
engagement_rate = (likes + comments) / views × 100
```

Computed at **ingest** from live yt-dlp metadata (not re-calculated by the LLM).

### 6.4 Chunking & embeddings

- Transcripts split with `RecursiveCharacterTextSplitter` (default **500** chars, **80** overlap).
- Each chunk stored with `chunk_index`, `video_id`, `session_id`, title, creator.
- Embeddings: **BGE-small-en** via FastEmbed (normalized vectors).

### 6.5 LangGraph vs LangChain


| Tool          | Role in Reach                                                                     |
| ------------- | --------------------------------------------------------------------------------- |
| **LangGraph** | Single-node graph: `retrieve` → returns `context`, `sources`, `video_metadata`    |
| **LangChain** | `ChatPromptTemplate` + `ChatGoogleGenerativeAI` + `StrOutputParser` for streaming |


### 6.6 Session & memory

- Each ingest creates a `session_id` (UUID).
- **Videos** and **chat messages** stored in `session_store` (Python dict in RAM).
- Last **10** turns passed as `chat_history` to the LLM.
- **Chroma** persists vectors on disk; **sessions** are lost if the backend restarts (unless you add Redis later).

### 6.7 Streaming & citations

- Backend emits **SSE** events: `status`, `sources`, `token`, `done`, `error`.
- Frontend parses SSE and updates the chat bubble live.
- **Sources** list shows `Video A/B`, `chunk_index`, and a text snippet for each retrieved chunk.

### 6.8 Dynamic vs hard-coded


| Dynamic (from URLs)                 | Can be hard-coded (UI defaults only) |
| ----------------------------------- | ------------------------------------ |
| Transcripts, views, likes, comments | Demo YouTube URL in `.env`           |
| Engagement rate, hashtags, creator  | Empty Instagram placeholder          |
| RAG answers, citations              | Suggested prompt button labels       |


---

## 7. How It Works — End-to-End Workflow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ 1. User  │────►│ 2. Ingest│────►│ 3. Index │────►│ 4. Chat  │────►│ 5. UI    │
│ enters   │     │ metadata │     │ Chroma   │     │ RAG+SSE  │     │ cards +  │
│ 2 URLs   │     │ + transcript     │ + embed  │     │ stream   │     │ chat     │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
```

### Step 1 — User input

User opens the app, enters:

- YouTube URL → **Video A**
- Instagram Reel URL → **Video B**

Clicks **Ingest & Index Transcripts**.

### Step 2 — Ingest (`POST /api/ingest`)

For each URL:

1. **yt-dlp** fetches JSON metadata (title, views, likes, comments, uploader, tags, duration, thumbnail).
2. **Transcript** from `youtube-transcript-api` (YouTube) or yt-dlp subtitles / description fallback.
3. **Engagement rate** calculated.
4. Response returns `session_id`, `videos[]`, `chunks_indexed` (transcript body not sent to client).

### Step 3 — Index (same request, backend)

1. Split transcripts into chunks.
2. Embed with FastEmbed.
3. `Chroma.from_documents()` → collection `reach_{session_id}`.
4. Save session in `session_store`.

### Step 4 — Chat (`POST /api/chat`)

1. User asks a question (or clicks a suggested prompt).
2. **LangGraph** retrieves top-k similar chunks for the question.
3. **LangChain** builds prompt: system rules + metadata + chunks + chat history + question.
4. **Gemini** streams tokens; backend forwards as SSE.
5. Assistant message + sources saved to session.

### Step 5 — UI output

- **Video cards**: thumbnails, stats, engagement %, hashtags, transcript preview.
- **Chat**: streaming answer + source citations; follow-up questions use memory.

---

## 8. RAG Pipeline (Detailed)

```
User question
      │
      ▼
┌─────────────────┐
│ LangGraph       │
│  retrieve node  │──► Chroma similarity search (k=6)
└────────┬────────┘
         │ context string + sources[{video_id, chunk_index, snippet}]
         ▼
┌─────────────────┐
│ Build prompt    │──► SYSTEM + metadata + chunks + chat_history + question
└────────┬────────┘
         ▼
┌─────────────────┐
│ Gemini stream   │──► async tokens (fallback: ainvoke if stream empty)
│ (+ model retry  │     on 429: try gemini-2.5-flash-lite → 1.5-flash → …
│  on quota)      │
└────────┬────────┘
         ▼
   SSE → Browser
```

**Prompt rules** (enforced in system message):

- Use only provided context/metadata.
- Cite `[Video A, chunk N]` / `[Video B, chunk N]`.
- Use precomputed engagement rates for metric questions.
- Focus on opening transcript lines for “first 5 seconds” / hook questions.

---

## 9. API Reference


| Method | Path                        | Description                                               |
| ------ | --------------------------- | --------------------------------------------------------- |
| `GET`  | `/health`                   | API status, `llm_provider`, `llm_model`, `llm_ready`      |
| `POST` | `/api/ingest`               | Body: `{ youtube_url, instagram_url }` → session + videos |
| `POST` | `/api/chat`                 | Body: `{ session_id, message }` → SSE stream              |
| `GET`  | `/api/session/{session_id}` | Chat history + video metadata                             |
| `GET`  | `/api/demo-urls`            | Demo URL hints                                            |


### SSE event types (`/api/chat`)


| Event     | Payload                                        | Meaning                                |
| --------- | ---------------------------------------------- | -------------------------------------- |
| `status`  | `retrieving` / `generating`                    | Progress                               |
| `sources` | `[{ video_id, chunk_index, content_snippet }]` | Citations                              |
| `token`   | string                                         | Streamed answer text                   |
| `done`    | full answer string                             | Complete                               |
| `error`   | error message                                  | Failure (quota, session missing, etc.) |


---

## 10. Environment Variables

### Backend (`backend/.env`)


| Variable                 | Required     | Default                 | Description                                            |
| ------------------------ | ------------ | ----------------------- | ------------------------------------------------------ |
| `GOOGLE_API_KEY`         | Yes (Gemini) | —                       | [Google AI Studio](https://aistudio.google.com/apikey) |
| `LLM_PROVIDER`           | No           | `gemini`                | `gemini` or `openai`                                   |
| `GEMINI_MODEL`           | No           | `gemini-2.5-flash-lite` | Primary Gemini model                                   |
| `GEMINI_MODEL_FALLBACKS` | No           | `gemini-1.5-flash,...`  | Comma-separated fallback models                        |
| `AUTO_FALLBACK_OPENAI`   | No           | `true`                  | Use OpenAI if Gemini quota exhausted                   |
| `OPENAI_API_KEY`         | If OpenAI    | —                       | Optional fallback LLM                                  |
| `CHROMA_PERSIST_DIR`     | No           | `./data/chroma`         | Use `/app/data/chroma` on Railway                      |
| `FRONTEND_ORIGIN`        | Prod         | `http://localhost:3000` | Vercel URL for CORS                                    |
| `FRONTEND_ORIGINS`       | No           | —                       | Extra CORS origins (comma-separated)                   |
| `YTDLP_COOKIES_BROWSER`  | No           | —                       | `chrome` for IG locally only (not Railway)             |


### Frontend (`frontend/.env.local`)


| Variable                     | Required   | Description                     |
| ---------------------------- | ---------- | ------------------------------- |
| `BACKEND_URL`                | Local/prod | Server-side proxy target        |
| `NEXT_PUBLIC_BACKEND_URL`    | Prod       | Browser direct calls to Railway |
| `NEXT_PUBLIC_DEMO_YOUTUBE`   | No         | Default YouTube URL in form     |
| `NEXT_PUBLIC_DEMO_INSTAGRAM` | No         | Default Instagram URL in form   |


---

## 11. Building & Running Locally

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Gemini API key** (`GOOGLE_API_KEY`)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env — set GOOGLE_API_KEY

uvicorn app.main:app --reload --port 8000
```

Verify: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → must include `"llm_provider": "gemini"`.

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

### Production build (verify before deploy)

```powershell
cd frontend
npm run build
npm start
```

### Docker (optional)

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)  
- Backend: [http://localhost:8000](http://localhost:8000)

---

## 12. Expected Output

### Health endpoint

```json
{
  "status": "ok",
  "llm_provider": "gemini",
  "llm_model": "gemini-2.5-flash-lite",
  "llm_ready": true
}
```

### After ingest (UI)

- Two **video cards** (A = YouTube, B = Instagram)
- **Views, likes, comments**, engagement rate %, creator, hashtags, date, duration
- Message: `Indexed N transcript chunks into ChromaDB`
- **API connected** (green) when backend is reachable

### After chat (UI)

- User message bubble (right)
- Assistant message (left) with **streaming text**
- **Sources** section: `Video A, chunk 2` — snippet preview
- Follow-up questions remember prior turns (same `session_id`)

### Terminal (backend logs)

```
INFO: Reach backend started (llm=gemini, model=gemini-2.5-flash-lite)
INFO: Using FastEmbed local embeddings (bge-small-en-v1.5)
INFO: Chat succeeded with Gemini model: gemini-2.5-flash-lite
```

---

## 13. Example Questions

These work with the RAG + metadata pipeline:


| Question                                                      | What Reach uses               |
| ------------------------------------------------------------- | ----------------------------- |
| Why did Video A get more engagement than Video B?             | Metadata + retrieved chunks   |
| What's the engagement rate of each?                           | Precomputed `engagement_rate` |
| Compare the hooks in the first 5 seconds.                     | Opening transcript chunks     |
| Who's the creator of Video B and what's their follower count? | Metadata fields               |
| Suggest improvements for B based on what worked in A.         | Retrieval + LLM reasoning     |


Suggested prompts are built into the chat panel UI.

---

## 14. Deployment

**Recommended:** [Railway](https://railway.app) (backend) + [Vercel](https://vercel.com) (frontend).


| Service | Root directory | Public URL                               |
| ------- | -------------- | ---------------------------------------- |
| Railway | `backend`      | `https://xxx.up.railway.app`             |
| Vercel  | `frontend`     | `https://xxx.vercel.app` ← **open this** |


Full step-by-step: **[DEPLOY.md](./DEPLOY.md)**

**Critical production env (Vercel):**

```
BACKEND_URL=https://YOUR-RAILWAY-URL
NEXT_PUBLIC_BACKEND_URL=https://YOUR-RAILWAY-URL
```

**Critical production env (Railway):**

```
FRONTEND_ORIGIN=https://YOUR-VERCEL-URL
CHROMA_PERSIST_DIR=/app/data/chroma
+ mount volume at /app/data/chroma
```

---

## 15. Troubleshooting


| Symptom                              | Cause                                | Fix                                                           |
| ------------------------------------ | ------------------------------------ | ------------------------------------------------------------- |
| "Backend is not running" / port 8000 | Wrong API URL or local port conflict | Set `NEXT_PUBLIC_BACKEND_URL`; free port 8000 locally         |
| Health OK but no `llm_provider`      | Wrong app on port 8000               | Start Reach backend; check Railway root = `backend`           |
| YouTube "Sign in to confirm you're not a bot" | YouTube bot check | `YTDLP_COOKIES_BROWSER=chrome` in `backend/.env`, restart backend |
| Ingest fails Instagram               | Private reel / login required        | Use public URL; `YTDLP_COOKIES_BROWSER=chrome` **local only** |
| Gemini quota error                   | Model limit exhausted                | Use `gemini-2.5-flash-lite`; wait; or add `OPENAI_API_KEY`    |
| Chat stuck on "Retrieving chunks"    | LLM/stream/CORS issue                | Set `NEXT_PUBLIC_BACKEND_URL`; check Railway logs             |
| Session not found after redeploy     | In-memory sessions cleared           | Re-ingest videos                                              |
| Vercel build fails                   | TypeScript/env                       | Run `npm run build` locally; fix errors                       |
| CORS error                           | `FRONTEND_ORIGIN` mismatch           | Set exact Vercel URL on Railway                               |


---

## 16. Scalability & Cost

**Bottlenecks (in order):** video fetch → embedding → vector storage → LLM tokens.


| Scale target      | Recommendation                                                        |
| ----------------- | --------------------------------------------------------------------- |
| Demo / MVP        | Current stack (Railway + Vercel + Chroma + FastEmbed + Gemini Flash)  |
| 1000 creators/day | Ingest queue, S3 cache, Qdrant/Pinecone, Redis sessions, Gemini Flash |
| Lower LLM cost    | Groq + Llama 8B                                                       |
| Higher quality    | AssemblyAI transcripts + GPT-4o for paid tier                         |


**Rough cost @ 1000 creators/day, 2 videos, ~5 chats:** ~$30–85/day (compute + Gemini + vector DB).

---

## 17. FAQ

**Q: Do I open Railway or Vercel in the browser?**  
A: **Vercel** — that's the website. Railway is API-only.

**Q: Can I use only YouTube or only Instagram?**  
A: The product requires **both** URLs per spec (A = YouTube, B = Instagram).

**Q: Is data stored permanently?**  
A: Chroma vectors persist on disk (with volume). Chat sessions are in-memory until restart.

**Q: Does it work without OpenAI?**  
A: Yes. Default uses Gemini + local FastEmbed embeddings.

**Q: Why LangGraph if there's only one node?**  
A: Satisfies orchestration requirement; retrieval is isolated and extensible (e.g. add rerank, router nodes later).

**Q: What validates Reach vs a random app on :8000?**  
A: `/health` must return `llm_provider` (e.g. `"gemini"`).

---

## 18. License

MIT

---

**Reach** — Compare. Ingest. Ask. Cite.
