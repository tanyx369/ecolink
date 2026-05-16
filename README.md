# EcoLink AI

**AI-powered ecosystem relationship management** — MyHack 2026 hackathon prototype.

Treats every mentor–company linkage as a first-class, programmable entity stored in Firestore, surfaced through a knowledge graph, and matched using a dual-AI pipeline (Gemini + Claude).

---

## Architecture

```
Browser (Next.js 14)
     │  Google Sign-In (Firebase Auth)
     │  Google Maps (ecosystem map)
     ▼
FastAPI (Cloud Run, asia-southeast1)
     │
     ├── Firestore          ← nodes + edges persistence
     ├── Vertex AI          ← text-embedding-004, 768-dim actor profile embeddings
     ├── Gemini 1.5 Pro     ← subgraph structural analysis (structural_score + insight)
     └── Claude Sonnet      ← explainable match narrative, streamed live to UI
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud project with billing enabled (see [GOOGLE_SETUP.md](GOOGLE_SETUP.md))
- Anthropic API key (get one at console.anthropic.com)

---

## First-time setup

```bash
# 1. Clone / enter the directory
cd ecolink-ai

# 2. Backend environment
cp backend/.env.example backend/.env
# Edit backend/.env — fill in ANTHROPIC_API_KEY, GOOGLE_CLOUD_PROJECT, etc.
# Place your service-account.json in backend/

# 3. Frontend environment
cp frontend/.env.local.example frontend/.env.local
# Edit frontend/.env.local — fill in Firebase config, Maps key, API URL

# 4. Seed Firestore (run once — generates Vertex AI embeddings for all actors)
cd backend
pip install -r requirements.txt
python seed.py
cd ..

# 5. Start both servers
chmod +x start.sh && ./start.sh
```

Open http://localhost:3000 — sign in with Google.

---

## Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard — metrics + recent linkages |
| `/login` | Google Sign-In |
| `/graph` | Force-directed knowledge graph (NetworkX data, react-force-graph-2d) |
| `/map` | Geographic map of all ecosystem actors (Google Maps) |
| `/match` | AI mentor matching — Gemini structural analysis + Claude narrative (SSE streaming) |
| `/linkages` | Table of all mentoring linkages — update outcomes, clone to new programme |
| `/onboard` | Add new mentors/companies — auto-generates Vertex AI embeddings |

---

## Match pipeline

1. **GraphRAG** — k-hop traversal of Firestore graph with NetworkX, tag overlap + Vertex AI cosine similarity ranking
2. **Gemini 1.5 Pro** — receives serialised subgraph, returns `structural_score`, `pattern_insight`, `risk_flag`
3. **Claude claude-sonnet-4-20250514** — combines graph context + Gemini scores, streams the final human-readable recommendation

Each match card shows both AI contributions with attribution.

---

## Cloud Run deployment

```bash
# Build and push image
gcloud builds submit backend/ --tag gcr.io/YOUR_PROJECT_ID/ecolink-backend

# Deploy to Cloud Run (Singapore region — low latency for MY)
gcloud run deploy ecolink-backend \
  --image gcr.io/YOUR_PROJECT_ID/ecolink-backend \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY=sk-ant-...,GOOGLE_CLOUD_PROJECT=your-project-id,GOOGLE_CLOUD_LOCATION=us-central1

# Update frontend to point at Cloud Run URL
# In frontend/.env.local:
# NEXT_PUBLIC_API_URL=https://ecolink-backend-xxxx-as.a.run.app
```

For the service account on Cloud Run, use `--service-account` pointing at your backend service account, or set `GOOGLE_APPLICATION_CREDENTIALS` pointing at a mounted secret.

---

## Demo flow (for judges)

1. **Login** with Google → lands on Dashboard showing 8 mentors, 10 companies, 3 programmes
2. **Map** → see ecosystem spread across KL, Penang, JB, Cyberjaya — click a mentor marker
3. **Graph** → same mentor highlighted — side panel shows linkage history
4. **Match** → select AgroVision + CBIP 2026 → Generate
   - Watch Gemini structural scores appear per candidate
   - Watch Claude stream its reasoning live
5. **Approve** top match → new edge written to Firestore
6. **Linkages** → clone a completed linkage to CBIP 2026 with one click
7. **Onboard** → add a new mentor → explain Vertex AI embeds it in real time

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Database | Firebase Firestore (native mode) |
| Auth | Firebase Authentication (Google Sign-In) |
| Embeddings | Vertex AI `text-embedding-004` (768-dim) |
| Graph AI | Gemini 1.5 Pro via `google-generativeai` |
| Match AI | Claude `claude-sonnet-4-20250514` via `anthropic` |
| Graph engine | NetworkX (in-memory, rebuilt from Firestore) |
| Map | Google Maps JavaScript API + `@react-google-maps/api` |
| Deployment | Google Cloud Run (backend), Vercel / Firebase Hosting (frontend) |
