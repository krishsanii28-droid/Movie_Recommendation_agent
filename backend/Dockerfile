# Backend-only image (Render, Railway, Fly.io, or behind a separate frontend on Vercel/Netlify).
# Build:  docker build -t moodreel-api backend
# Full AI stack: docker build --build-arg INSTALL_ML=1 -t moodreel-api backend
FROM python:3.11-slim

ARG INSTALL_ML=0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    HF_HOME=/app/data/hf-cache

WORKDIR /app
COPY requirements.txt requirements-ml.txt ./
RUN pip install -r requirements.txt \
 && if [ "$INSTALL_ML" = "1" ]; then pip install -r requirements-ml.txt; fi

COPY moodreel ./moodreel
COPY eval ./eval
COPY pyproject.toml ./

# Bake the curated catalogue + index into the image so cold starts are instant.
# Catalogue baked into the image (survives restarts on ephemeral hosts like Render's free plan).
# With TMDB_API_KEY available at build time (Render passes service env vars as build args),
# the curated seed list is replaced by live TMDB data; if TMDB fails, the seed list is kept.
ARG TMDB_API_KEY=""
ARG TMDB_READ_TOKEN=""
ARG TMDB_PAGES=8
RUN useradd -m -u 1000 app && mkdir -p /app/data \
 && python -m moodreel.data.pipeline seed --no-index \
 && if [ -n "$TMDB_API_KEY$TMDB_READ_TOKEN" ]; then \
      python -m moodreel.data.pipeline ingest --pages "$TMDB_PAGES" --replace-seed --no-index \
      || echo "TMDB ingest failed - keeping the curated seed catalogue"; \
    else echo "No TMDB key at build time - using the curated seed catalogue"; fi \
 && python -m moodreel.data.pipeline stats \
 && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health')"
CMD ["sh", "-c", "uvicorn moodreel.api.main:app --host 0.0.0.0 --port ${PORT}"]
