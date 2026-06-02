# Deploy Reach

Recommended stack: **Railway** (FastAPI + Chroma disk) + **Vercel** (Next.js).

| Service | Platform | Why |
|---------|----------|-----|
| Backend | [Railway](https://railway.app) | Long requests for ingest (~2–5 min), persistent volume for Chroma |
| Frontend | [Vercel](https://vercel.com) | Native Next.js, SSE chat proxy via `/api/chat` |

---

## 1. Deploy backend (Railway)

### Option A — GitHub (easiest)

1. Push this repo to GitHub.
2. [Railway](https://railway.app) → **New Project** → **Deploy from GitHub** → select repo.
3. Add a service → set **Root Directory** to `backend`.
4. Railway detects `backend/Dockerfile` automatically.
5. **Variables** (Settings → Variables):

| Variable | Value |
|----------|--------|
| `GOOGLE_API_KEY` | Your Gemini key |
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` |
| `GEMINI_MODEL_FALLBACKS` | `gemini-1.5-flash,gemini-2.5-flash` |
| `CHROMA_PERSIST_DIR` | `/app/data/chroma` |
| `FRONTEND_ORIGIN` | `https://YOUR-APP.vercel.app` (set after step 2) |
| `FRONTEND_ORIGINS` | Same URL (optional duplicate) |
| `OPENAI_API_KEY` | Optional fallback |
| `AUTO_FALLBACK_OPENAI` | `true` |

6. **Volume**: Settings → Volumes → mount path `/app/data/chroma` (1 GB).
7. **Networking** → **Generate Domain** → copy URL, e.g. `https://reach-api-production.up.railway.app`
8. Deploy → open `https://YOUR-URL/health` → should show `"llm_provider": "gemini"`.

### Option B — Render

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint** → connect repo.
2. Uses root `render.yaml` (Starter plan + disk for Chroma).
3. Set secret env vars in dashboard (`GOOGLE_API_KEY`, `FRONTEND_ORIGIN`).
4. **Free tier warning:** 30s HTTP limit may timeout on ingest; use Railway or paid Render for production.

### Option C — VPS (Docker)

```bash
# On server with Docker
git clone <your-repo> && cd Reach
cp backend/.env.example backend/.env   # fill in keys
export FRONTEND_ORIGIN=https://your-domain.com
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 2. Deploy frontend (Vercel)

1. [Vercel](https://vercel.com) → **Add New Project** → import GitHub repo.
2. Set **Root Directory** to `frontend`.
3. **Environment variables**:

| Name | Value |
|------|--------|
| `BACKEND_URL` | `https://reach-api-production.up.railway.app` (no trailing slash) |
| `NEXT_PUBLIC_BACKEND_URL` | **Same Railway URL** (required for health check + ingest) |

4. **Redeploy** after saving env vars (Vercel bakes rewrites at build time; these vars fix that).

5. Deploy.
5. Copy your Vercel URL, e.g. `https://reach-xyz.vercel.app`.

---

## 3. Link frontend ↔ backend

1. **Railway** → backend service → Variables:
   - `FRONTEND_ORIGIN` = `https://reach-xyz.vercel.app`
   - `FRONTEND_ORIGINS` = same (comma-separated if multiple)
2. Redeploy backend (CORS uses these + `*.vercel.app` regex).
3. **Vercel** → Redeploy if you changed `BACKEND_URL`.

---

## 4. Smoke test

1. Open Vercel URL.
2. Banner: **API connected** (green).
3. Paste YouTube + Instagram URLs → **Ingest** (wait 1–3 min).
4. Ask a question in RAG Analyst → streaming reply + sources.

---

## Environment checklist

```env
# backend
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
CHROMA_PERSIST_DIR=/app/data/chroma
FRONTEND_ORIGIN=https://your-frontend.vercel.app

# frontend (Vercel) — both required
BACKEND_URL=https://your-backend.up.railway.app
NEXT_PUBLIC_BACKEND_URL=https://your-backend.up.railway.app
```

---

## Costs (rough)

| Tier | Cost |
|------|------|
| Vercel Hobby | $0 |
| Railway (usage) | ~$5–20/mo with volume |
| Gemini API | Free tier / pay per use |
| Render Starter + disk | ~$7+/mo |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Failed to fetch | Wrong `BACKEND_URL` or backend down |
| CORS error | Set `FRONTEND_ORIGIN` on backend to exact Vercel URL |
| Ingest timeout on Vercel | Ingest goes through rewrite; use Railway backend (long timeout) |
| Chat works, ingest fails | Instagram needs `YTDLP_COOKIES_BROWSER=chrome` on backend |
| Empty Chroma after redeploy | Attach Railway/Render volume at `/app/data/chroma` |
| Gemini quota | Use `gemini-2.5-flash-lite`, not `gemini-2.0-flash` |

---

## Optional: GitHub Actions

See `.github/workflows/deploy-check.yml` for a CI smoke test on push (health + build only).
