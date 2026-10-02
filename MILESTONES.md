# RiffVault Milestones

## Milestone 1 — Foundation
**Status: Complete**

Build the application skeleton and basic riff library.
- [x] User can import WAV, MP3, M4A
- [x] Audio is stored locally
- [x] Riff is persisted in SQLite
- [x] Library displays riffs
- [x] User can play audio
- [x] Waveform is displayed
- [x] Riff detail page works
- [x] Restarting the application preserves data

## Milestone 2 — Audio Intelligence
**Status: Complete**

Make RiffVault understand the audio (BPM, metadata).
- [x] BPM analysis works
- [x] Audio features are stored
- [x] Basic Pitch integration works where possible
- [x] MIDI output is stored
- [x] Processing status is visible
- [x] Failed analysis steps do not destroy the riff
- [x] Existing riffs survive application restart

## Milestone 3 — AI Search
**Status: Complete**

Turn RiffVault into an intelligent searchable archive.
- [x] Whisper transcription works locally (faster-whisper)
- [x] Voice notes are searchable
- [x] Local LLM generates tags (Ollama, configurable model)
- [x] Local LLM generates descriptions
- [x] Natural-language search works (LLM → structured filters → DB)
- [x] Metadata filtering works (BPM range, key, tags)
- [x] Semantic search works (sentence-transformers embeddings)
- [x] Similar-riff search works (cosine similarity)
- [x] No cloud AI API is required
- [x] AI failures are gracefully handled

## Milestone 4 — Polish + Demo
**Status: In Progress**

Turn the prototype into a polished, convincing hackathon demo.
