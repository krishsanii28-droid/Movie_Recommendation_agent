# Deploying MoodReel

MoodReel is two parts: a **FastAPI backend** (agent, data, memory) and a **Vue SPA**.
Pick one of these layouts:

| Layout | Where | Cost | Good for |
|---|---|---|---|
| **A. Single container on Render** | Render web service (root `Dockerfile`) | Free tier | Simplest free option; one URL, no CORS |
| **B. Single container on Hugging Face Spaces** | HF Space (Docker SDK) | Needs HF PRO | One URL, inside the HF ecosystem |
| **C. Split** | Render (API) + Vercel/Netlify (UI) | Free tiers | Fast global CDN for the UI |

All of them work with zero API keys (seed catalogue and the built-in fallbacks). Add `TMDB_API_KEY` for
live data and `HF_TOKEN` + `LLM_BACKEND=hf_inference` for the LLM planner.

---

## A. Render, single container (free)

The root [`Dockerfile`](../Dockerfile) builds the UI and the API into one image. Render sets `$PORT` and the
container listens on it, so nothing needs changing. Everything is done in the browser.

1. Sign up at [render.com](https://render.com) with GitHub and give it access to this repository.
2. **New → Web Service** → pick the repository.
3. Settings:
   - **Branch:** `main`
   - **Language:** `Docker`. Leave the root directory empty and the Dockerfile path as `./Dockerfile`.
   - **Instance type:** Free
   - **Health check path** (under Advanced): `/api/health`
   - **Environment variables** (optional): `TMDB_API_KEY`
4. **Create Web Service**. The first build takes about 5–10 minutes; then open the `onrender.com` URL.

Free-plan caveats:
- The service sleeps when idle, so the first request after a break takes 30–60 seconds.
- The disk is ephemeral: feedback, watchlists and mood history reset on every deploy or restart. For
  lasting data, set `DATABASE_URL` to a managed PostgreSQL database (see Render setup in layout C).

---

## B. Hugging Face Spaces (single container)

> **Hugging Face now requires a PRO subscription to host Docker Spaces.** On a free account, creating the
> Space fails with `402 Payment Required`. Use layout A for a free deploy.

The root [`Dockerfile`](../Dockerfile) builds the frontend, installs the backend, seeds the catalogue and
serves everything on port **7860**.

**One command:** [`scripts/deploy_hf_space.py`](../scripts/deploy_hf_space.py) creates the Space, uploads the
repo with the required Space README, and copies `TMDB_API_KEY` into the Space as a secret:

```bash
pip install huggingface_hub
export HF_TOKEN=hf_...                 # a write token
export TMDB_API_KEY=...                # optional: live movie data
python scripts/deploy_hf_space.py --space <your-username>/moodreel          # add --llm for the LLM planner
```

**Or by hand:**

1. Create a new Space → **SDK: Docker** → blank template.
2. Push this repository to the Space (or connect it with a GitHub Action). The Space's `README.md` must start
   with this front matter. Keep the GitHub README as it is and add the block only in the Space repo:

   ```yaml
   ---
   title: MoodReel
   emoji: 🎬
   colorFrom: yellow
   colorTo: red
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```

3. In **Settings → Variables and secrets**, add as needed:
   - `TMDB_API_KEY` (secret): live TMDB data. See [Refreshing data](#refreshing-data).
   - `HF_TOKEN` (secret) and `LLM_BACKEND=hf_inference`: the LLM planner via HF Inference Providers.
   - `LLM_MODEL`: defaults to `Qwen/Qwen2.5-1.5B-Instruct`. Any chat model with tool calling that your
     token can reach works, for example a larger Qwen or Llama instruct model.
4. For the full Hugging Face stack (emotion classifier, multilingual sentence embeddings, ChromaDB), build
   with `INSTALL_ML=1`. On Spaces, change `ARG INSTALL_ML=0` to `1` in the Dockerfile. The image grows
   by about 1.5 GB (CPU torch), and startup downloads the model weights into `data/hf-cache`.

> **Persistence:** a Space's disk resets on restart unless you enable persistent storage. If you do, mount it
> and set `DATABASE_URL=sqlite:////data/moodreel.db` and `CHROMA_DIR=/data/chroma`. You can also point
> `DATABASE_URL` at a managed PostgreSQL database.

Local equivalent:

```bash
docker compose up --build          # http://localhost:7860
```

---

## C. Render (API) + Vercel/Netlify (UI)

### Backend on Render

[`render.yaml`](../render.yaml) is a Blueprint that deploys `backend/Dockerfile` as a web service.

1. Render dashboard → **New → Blueprint** → select the repo.
2. Fill the `sync: false` secrets (`TMDB_API_KEY`, `HF_TOKEN`).
3. Set `CORS_ORIGINS` to your frontend URL as a JSON list, e.g. `["https://moodreel.vercel.app"]`.
   `CORS_ORIGIN_REGEX` already allows `*.vercel.app` / `*.netlify.app` preview URLs. Tighten it for production.
4. Check `https://<service>.onrender.com/api/health`.

The free plan sleeps when idle (the first request after a sleep takes about 30 s) and its disk is
ephemeral. For lasting feedback, watchlists and mood history, use PostgreSQL:

```bash
pip install "psycopg[binary]"   # add to backend/requirements.txt
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/moodreel
```

### Frontend on Vercel

1. **New Project** → import the repo → **Root directory: `frontend`** (framework: Vite).
2. Environment variable: `VITE_API_BASE_URL=https://<service>.onrender.com`
3. Deploy. [`frontend/vercel.json`](../frontend/vercel.json) rewrites client routes (`/watchlist`, `/moods`) to the SPA.

### Frontend on Netlify

**Base directory:** `frontend`. [`frontend/netlify.toml`](../frontend/netlify.toml) sets the build and the SPA
redirect. Add `VITE_API_BASE_URL` under **Site settings → Environment variables**.

---

## Refreshing data

The seed catalogue (119 films) is for demos. With a TMDB key:

```bash
cd backend
python -m moodreel.data.pipeline ingest --pages 5 --replace-seed   # first load: up to ~500 films (5 languages x 5 pages x 20)
python -m moodreel.data.pipeline refresh --days 45                  # new releases + provider changes
```

Run `refresh` on a schedule (weekly is plenty; streaming deals change monthly). Options:

- Render **Cron Job** with the same Docker image and command
  `python -m moodreel.data.pipeline refresh`. It needs the same `DATABASE_URL`, so use PostgreSQL.
- A scheduled GitHub Action that runs the command against your production database.

The pipeline respects TMDB rate limits (token bucket, `TMDB_REQUESTS_PER_SECOND`, default 20/s) and
retries 429 and 5xx responses with backoff. It rebuilds the vector index when it finishes. A running API
loads the catalogue at startup, so restart it after a refresh.

---

## Checklist

- [ ] `/api/health` reports the movie count and engines you expect (`embedder`, `emotion`, `llm`)
- [ ] `CORS_ORIGINS` contains the frontend's exact origin (layout B)
- [ ] TMDB and JustWatch attribution are visible in the footer (required by their terms)
- [ ] Secrets are set in the platform, never committed (`.env` is git-ignored)
