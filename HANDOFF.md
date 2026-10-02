# Handoff Document

## Current state
Current milestone: Milestone 2 Complete, Starting Milestone 3
Current branch/state: Main branch
Application status: Audio Intelligence layer functioning
Backend status: FastAPI with SQLite, async audio processing using librosa and basic-pitch.
Frontend status: React app displaying basic audio metadata, status, and waveform.
Database status: SQLite DB updated with audio intelligence fields.
AI services status: Basic Pitch configured for note extraction. Local Whisper and Ollama pending.

## What works
- Import WAV, MP3, M4A files.
- Waveform generation via wavesurfer.js.
- Background task extracting BPM, duration, energy, and MIDI (via Basic Pitch).
- Refresh button polls for updated processing status.

## What does not work
- N/A

## Important architectural decisions
- **Backend:** Python + FastAPI using SQLAlchemy and SQLite.
- **Audio Intelligence:** `librosa` and `basic-pitch` running asynchronously via `BackgroundTasks`.
- **Frontend:** React + TypeScript (Vite) + Tailwind CSS v4.
- **Storage:** Local filesystem (`./data/audio` and `./data/midi`).

## Commands
TBD (will be updated once scaffolded).

## Next task
- Scaffold the project structure (frontend and backend).
- Setup Python FastAPI backend.
- Setup React frontend.

## Do not redo
- DO NOT rewrite the documentation files unnecessarily.
