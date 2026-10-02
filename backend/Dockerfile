# ── Stage 1: base ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System deps for librosa/numpy/scipy (libsndfile, ffmpeg, gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libsndfile1 \
    ffmpeg \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Stage 2: dependencies ────────────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 3: runtime ─────────────────────────────────────────────────────────
FROM deps AS runtime

COPY app/ ./app/

# Data dirs are mounted as volumes; create stubs so the app can boot
RUN mkdir -p /data/audio /data/midi /data/embeddings /data/voice_notes

ENV DATA_DIRECTORY=/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
