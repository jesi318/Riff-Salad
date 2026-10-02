<div align="center">

<style>
  /* 1. Import Fonts directly from your package source */
  @import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,opsz,wght@0,18..144,300..900;1,18..144,300..900&family=Playwrite+AR:wght@100..400&display=swap');

  /* 2. Style Wrapper for the Editor Canvas */
  .editor-canvas {/* Deep dark background */
    padding: 40px;

    flex-direction: column;
    gap: 24px;
  }

  /* 3. Lined Heading Configuration (Playwrite AR) */
  .playwrite-heading {
    font-family: "Playwrite AR", cursive;
    font-size: 96px;       /* Set precisely to your app UI selection */
    font-weight: 300;      /* Elegant thin structure */
    font-style: normal;       /* Pure white typography */
    margin: 0;
    padding: 8px 16px;
    display: inline-block;
    
    /* Perfect horizontal tracking lines styled for dark mode themes */
    background-image: 
      linear-gradient(to bottom, transparent 95%, #ffffff 95%), /* Top Boundary */
      linear-gradient(to top, transparent 95%, #ffffff 95%);   /* Bottom Boundary */
    background-position: top, bottom;
    background-size: 100% 1px;
    background-repeat: no-repeat;
  }

  /* 4. Alternative Standard Body Text Configuration (Merriweather) */
  .merriweather-body {
    font-family: "Merriweather", serif;
    font-optical-sizing: auto;
    font-weight: 400;
    font-style: normal;
    color: #b3b3b3;        /* Soft contrasted white body text */
    font-variation-settings: "wdth" 100;
  }
</style>

<!-- Live Document Preview Element -->
<div class="editor-canvas">
  <h1 class="playwrite-heading">Riff Salad</h1>
</div>



**Your guitar ideas, searchable.**

A local-first AI vault for guitarists. Record a riff, import the file — and find it later by describing it in plain English.

[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Ollama](https://img.shields.io/badge/Ollama-local_AI-000000?style=flat-square)](https://ollama.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## The Problem

Every guitarist knows this feeling: you recorded a cool riff a few months ago, but you can't find it because you saved it as `recording_027_final_v2.wav`. You remember it was a heavy, slow, drop-tuned thing around 80 BPM — but searching a folder of audio files for that is impossible.

**RiffSalad solves this.** Import your recordings and search them like you'd describe them to a bandmate.

```
"heavy drop C riffs around 140 BPM"
"that mellow fingerpicking thing in E minor"
"fast aggressive shredding, lots of notes"
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│  Import WAV / MP3 / M4A                                          │
│         │                                                        │
│         ▼                                                        │
│  librosa analyzes: BPM, Key, Energy, Note Density, Duration      │
│         │                                                        │
│         ├──► Ollama LLM → Tags + Description                     │
│         │                                                        │
│         └──► sentence-transformers → Semantic Embedding          │
│                                                                  │
│  Search: "heavy doom riff" ──► LLM parses intent ──► Filters     │
│                                ──► Embedding similarity ──► Results│
└──────────────────────────────────────────────────────────────────┘
```

All AI runs **locally** — no API keys, no data leaves your machine.

---

## Features

### 🔍 Intelligent Search
- **Natural language queries** — describe riffs like you'd talk to a bandmate
- **4-layer search pipeline**: LLM intent parsing → structured filters → semantic embeddings → text fallback
- **Music vocabulary built-in**: "doom", "shredding", "palm muted", "fingerpicking" all map to the right filters
- **Debounced real-time search** — results update as you type

### 🎵 Audio Analysis
- **BPM detection** — multi-strategy with harmonic/percussive separation
- **Key detection** — Krumhansl-Kessler tonal hierarchy profiles
- **Energy & note density** — distinguishes a wall of distortion from a clean fingerpicked melody
- **MIDI extraction** — via Basic Pitch for melodic content
- **Whisper voice notes** — record a description in your own voice; it's transcribed and indexed

### 🎧 Playback
- **Visual waveforms** — via Wavesurfer.js
- **Persistent sticky player** — audio keeps playing as you scroll or search
- **Spacebar to play/pause** — muscle memory from your DAW works here too

### ✏️ Metadata Management
- **Inline editing** — click a title to rename it, click BPM/Key to override AI values
- **User notes** — add freeform context that gets indexed for search
- **AI tags & descriptions** — generated automatically, regeneratable via Re-analyze
- **Similarity search** — find musically related riffs via embedding cosine similarity

### 🖥️ UX Polish
- Dark studio theme with Inter typography
- Drag-and-drop file import anywhere on the page
- Toast notifications for every action
- Skeleton loading states
- Processing stage labels ("Analyzing BPM & Key…", "Running AI tagging…")

---

## Quick Start — Docker (Recommended)

The fastest way to run everything in one shot. Docker Compose brings up Ollama, pulls the required models automatically, starts the backend, and serves the frontend.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)

```bash
git clone https://github.com/yourusername/riffsalad
cd riffsalad

# Copy environment config (defaults work out of the box)
cp .env.example .env

# Start everything — first run pulls ~2 GB of AI models
docker compose up
```

Open **http://localhost:3000** and start importing riffs.

> **First boot** downloads `qwen2.5:1.5b` (~1 GB) and `nomic-embed-text` (~274 MB). Subsequent starts are instant.

### NVIDIA GPU acceleration

```bash
docker compose --profile gpu up
```

### Changing models

Edit `.env` before starting:

```env
LLM_MODEL=llama3.2:3b        # better quality, slower
WHISPER_MODEL=base            # better transcription, larger
EMBEDDING_MODEL=nomic-embed-text
```

---

## Manual Setup (Development)

If you want to hack on the code, run each service directly.

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend |
| Node.js | 20+ | Frontend |
| [Ollama](https://ollama.com) | latest | Local LLM |
| ffmpeg | any | Audio decoding |

### 1 — Ollama

```bash
# Install from https://ollama.com, then:
ollama pull qwen2.5:1.5b       # LLM for tagging + search
ollama pull nomic-embed-text   # Semantic embeddings
```

### 2 — Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
# API available at http://localhost:8000
```

### 3 — Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

---

## Architecture

```
riffsalad/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── riffs.py        # CRUD, upload, audio streaming
│   │   │   └── search.py       # 4-layer search, similar-riff, voice notes
│   │   ├── ai/
│   │   │   ├── llm.py          # Ollama: tagging, search intent parsing
│   │   │   ├── embeddings.py   # Semantic embeddings (Ollama / sentence-transformers)
│   │   │   └── transcription.py # faster-whisper voice note transcription
│   │   ├── audio/
│   │   │   └── analysis.py     # librosa: BPM, key, energy, MIDI
│   │   ├── models/riff.py      # SQLAlchemy model
│   │   └── core/config.py      # Environment-driven config
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main application
│   │   └── components/
│   │       ├── StickyPlayer.tsx     # Persistent bottom audio player
│   │       ├── WaveformDisplay.tsx  # Visual waveform (Wavesurfer.js)
│   │       ├── VoiceRecorder.tsx    # Browser mic recording
│   │       └── SkeletonCard.tsx     # Loading placeholder
│   └── Dockerfile
├── docker-compose.yml
└── data/                       # Created at runtime
    ├── audio/
    ├── midi/
    ├── embeddings/
    └── voice_notes/
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + SQLAlchemy + SQLite |
| Audio Analysis | librosa, Basic Pitch |
| LLM | Ollama (qwen2.5, llama3.2, any model) |
| Transcription | faster-whisper (local) |
| Embeddings | Ollama nomic-embed-text |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS v4 + Inter |
| Waveforms | Wavesurfer.js |
| Containers | Docker Compose |

---

## Search Examples

| Query | What happens |
|-------|-------------|
| `"heavy doom riff around 80 BPM"` | Filters BPM ≤ 80, energy ≥ 0.08, semantic re-rank |
| `"fast shredding in E minor"` | BPM ≥ 120, note density ≥ 2.5, key = E Minor |
| `"that clean mellow fingerpicked thing"` | Energy ≤ 0.07, density low, semantic match |
| `"something like my last blues riff"` | Embedding similarity from the selected riff |

---

## Roadmap

- [ ] Batch import (drag a whole folder)
- [ ] Export playlist / session file
- [ ] MIDI playback preview
- [ ] Tag editor UI
- [ ] Multi-instrument support (bass, piano)
- [ ] Remote Ollama support (point to a LAN machine)

---

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

```bash
# Run linter
cd frontend && npm run lint
cd backend && python -m pytest
```

---

## License

[MIT](LICENSE) — do whatever you want with it.

---

<div align="center">

Built with 🎸 for guitarists who lose their riffs.

</div>
