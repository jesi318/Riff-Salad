# Architecture

## Core Tech Stack
- **Frontend:** React + TypeScript (Vite)
- **Backend:** Python + FastAPI
- **Database:** SQLite
- **Local Storage:** Filesystem (`./data`)

## Suggested Directory Structure
```text
riffvault/
│
├── frontend/ (React + TS)
│
├── backend/ (FastAPI)
│   └── app/
│       ├── api/
│       ├── models/
│       └── database.py
│
├── data/
│   ├── audio/
│   └── database/
```

## AI Architecture (Future Milestones)
- **Audio Analysis:** `librosa`
- **Transcription:** `faster-whisper`
- **Note Extraction:** Spotify Basic Pitch
- **LLM:** Ollama (qwen, gemma, or llama)
- **Embeddings:** Local embedding model + vector store

All AI components will be abstracted behind interface services to allow model swapping.
