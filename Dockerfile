# Single-container image: Vue frontend + FastAPI backend on one port.
# Used for Render (listens on $PORT) or Hugging Face Spaces (port 7860) - see docs/deploy.md.
#   docker build -t moodreel . && docker run -p 7860:7860 --env-file .env moodreel
# Full AI stack (HF emotion model, sentence-transformers, ChromaDB, local LLM deps):
#   docker build --build-arg INSTALL_ML=1 -t moodreel .

# ---- 1. build the frontend --------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same origin as the API, so no base URL needed.
ENV VITE_API_BASE_URL=""
RUN npm run build

# ---- 2. backend + static files ---------------------------------------------
FROM python:3.11-slim
ARG INSTALL_ML=0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    FRONTEND_DIST=/app/frontend/dist \
    HF_HOME=/app/backend/data/hf-cache

WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-ml.txt ./
RUN pip install -r requirements.txt \
 && if [ "$INSTALL_ML" = "1" ]; then pip install -r requirements-ml.txt; fi

COPY backend/moodreel ./moodreel
COPY backend/eval ./eval
COPY backend/pyproject.toml ./
COPY --from=web /web/dist /app/frontend/dist

# HF Spaces runs containers as uid 1000; the data dir must be writable.
# Catalogue baked into the image (survives restarts on ephemeral hosts like Render's free plan).
# With TMDB_API_KEY available at build time (Render passes service env vars as build args),
# the curated seed list is replaced by live TMDB data; if TMDB fails, the seed list is kept.
ARG TMDB_API_KEY=""
ARG TMDB_READ_TOKEN=""
ARG TMDB_PAGES=8
RUN useradd -m -u 1000 app && mkdir -p data \
 && python -m moodreel.data.pipeline seed --no-index \
 && if [ -n "$TMDB_API_KEY$TMDB_READ_TOKEN" ]; then \
      python -m moodreel.data.pipeline ingest --pages "$TMDB_PAGES" --replace-seed --no-index \
      || echo "TMDB ingest failed - keeping the curated seed catalogue"; \
    else echo "No TMDB key at build time - using the curated seed catalogue"; fi \
 && python -m moodreel.data.pipeline stats \
 && chown -R app:app /app
USER app

EXPOSE 7860
CMD ["sh", "-c", "uvicorn moodreel.api.main:app --host 0.0.0.0 --port ${PORT}"]
