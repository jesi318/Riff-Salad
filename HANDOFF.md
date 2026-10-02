# Handoff Document

## Current state
Current milestone: Milestone 4 Complete
Current branch/state: Main branch
Application status: Fully polished — all core UX improvements implemented.
Backend status: FastAPI with SQLite, async audio processing; new PATCH /title and PATCH /meta endpoints for inline editing.
Frontend status: React + Vite + Tailwind CSS v4. Full polish pass complete (sticky player, drag-and-drop, debounced search, toasts, skeleton loaders, inline editing, playing-bar animations).

## What works
- Import WAV, MP3, M4A files via button or **drag-and-drop anywhere on the page**.
- Waveform generation via wavesurfer.js (detail view + sticky bottom player).
- **Sticky persistent player** anchored to bottom — audio keeps playing while scrolling/searching.
- **Spacebar** toggles play/pause globally (as long as a track is loaded).
- Background task extracting BPM, duration, energy, and MIDI (via Basic Pitch).
- **Debounced search** — results update 500ms after typing stops.
- **Loading skeletons** while initial load or search is running.
- **Toast notifications** for upload, delete, transcription, and errors.
- **Drag-and-drop** file import anywhere on the page.
- **Inline title editing** — click the title to rename.
- **Inline BPM/Key override** — click the BPM or Key badge to manually correct.
- **Playing-bar animation** on the active riff card.
- **Empty states** for search no-results and empty vault.
- **Processing stage labels** — "Analyzing BPM & Key…", "Running AI tagging…", etc.
- Semantic search, similar-riff search, voice notes, LLM tagging, embeddings.

## What does not work
- N/A

## Important architectural decisions
- **Backend:** Python + FastAPI using SQLAlchemy and SQLite.
- **Audio Intelligence:** `librosa` and `basic-pitch` running asynchronously via `BackgroundTasks`.
- **Frontend:** React + TypeScript (Vite) + Tailwind CSS v4 + Inter font.
- **Storage:** Local filesystem (`./data/audio` and `./data/midi`).
- **Inline editing:** Title via `PATCH /api/riffs/{id}/title`; BPM/Key via `PATCH /api/riffs/{id}/meta`.
- **Re-tagging:** "Re-analyze" button triggers full analysis + LLM tagging (no separate retag button).

## Commands
- Backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`

## Do not redo
- DO NOT rewrite the documentation files unnecessarily.
