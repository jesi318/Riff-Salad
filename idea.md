# RiffVault — Local AI Guitar Idea Vault

## 1. Project Overview

Build **RiffVault**, a local-first AI application for guitarists that solves one specific problem:

> **“I record dozens of guitar ideas, then later I can’t find the riff I remember.”**

RiffVault should let a guitarist import or record short guitar ideas, automatically analyze them, attach searchable musical metadata, and later retrieve them using natural-language queries or by finding musically similar riffs.

The application is intended as a **Hacktoberfest weekend challenge project** demonstrating how open-source/open-weight AI can solve a real personal problem.

The application must prioritize:

1. Local-first execution
2. Open-source/open-weight AI
3. Privacy
4. Simple, polished UX
5. A genuinely working MVP over a large feature set
6. Easy model replacement
7. Clear demonstration of why the open approach matters

Do NOT build a generic AI chatbot.

Do NOT over-engineer the application.

The finished MVP should feel like a small, polished product that one guitarist could actually use.

---

# 2. Core User Story

A guitarist has 50+ recordings of riffs and ideas scattered across their computer.

They remember:

> “I recorded a heavy Drop C riff around 145 BPM. I think I called it a chorus idea.”

But they cannot remember the filename.

With RiffVault they should be able to type:

> “Find my heavy Drop C riffs around 140–150 BPM that I marked as possible chorus ideas.”

and get the correct recordings.

They should also be able to select a riff and ask:

> “Find riffs similar to this.”

RiffVault should return musically similar recordings.

---

# 3. Product Principles

## Local First

User recordings and metadata should remain on the user's machine.

Avoid mandatory cloud services.

AI inference should preferably run locally.

The system should continue to function without an internet connection after dependencies/models have been installed.

## Open AI Components

Use open-source/open-weight tools wherever practical.

Recommended components:

* Whisper / faster-whisper for speech transcription
* Spotify Basic Pitch for audio-to-MIDI/note extraction
* librosa and/or Essentia for audio analysis
* Ollama for local LLM inference
* Qwen, Gemma, or Llama-family open-weight model as the default LLM
* SQLite for metadata
* a local vector index for similarity search

Do not hard-code the application around one model provider.

All AI components should be abstracted behind replaceable services/interfaces.

---

# 4. MVP Scope

The MVP must support:

1. Import a riff
2. Analyze the riff locally
3. Store metadata
4. Browse riffs
5. Search using natural language
6. Search semantically
7. Find similar riffs
8. Play the original recording
9. Inspect the analysis
10. Run without cloud AI APIs

The core product loop is:

> **Store → Understand → Search → Discover**

---

# 5. Milestone Strategy

## IMPORTANT

This project must be developed as **4 independent milestones**.

Each milestone must leave the repository in a working state.

The purpose is to allow the project to be resumed later in a completely fresh Antigravity session without depending on previous conversation context.

Each milestone must:

* have a clear scope
* produce working code
* update documentation
* update `MILESTONES.md`
* update `HANDOFF.md`
* record what is complete
* record what remains
* record known issues
* record exact commands needed to continue
* avoid leaving the application in a knowingly broken state

Do NOT move to the next milestone until the current milestone is runnable.

At the end of each milestone, produce a concise completion report.

The agent may be instructed to continue to the next milestone in the same session, but each milestone must also be independently resumable.

---

# 6. Required Project Documentation for Continuity

Create these files at the repository root:

```text
MILESTONES.md
HANDOFF.md
ARCHITECTURE.md
README.md
```

## MILESTONES.md

Track:

```text
Milestone 1 — Foundation
Status: Complete / In Progress / Blocked

Milestone 2 — Audio Intelligence
Status: ...

Milestone 3 — AI Search
Status: ...

Milestone 4 — Polish + Demo
Status: ...
```

For each milestone include:

* objectives
* completed work
* files changed
* tests
* known limitations
* next steps

## HANDOFF.md

This is extremely important.

It must always contain enough information for a **new AI coding session** to continue the project.

It should contain:

### Current state

```text
Current milestone:
Current branch/state:
Application status:
Backend status:
Frontend status:
Database status:
AI services status:
```

### What works

List concrete working features.

### What does not work

List actual problems.

### Important architectural decisions

Document decisions so a new model does not unnecessarily rewrite existing architecture.

### Commands

Show exact commands for:

* backend
* frontend
* tests
* database setup
* Ollama
* demo data

### Next task

Give the next recommended implementation task in concrete terms.

### Do not redo

Explicitly list work that is already complete.

Example:

```text
DO NOT rebuild the database layer.
DO NOT replace the audio analysis service.
DO NOT restructure the frontend unless required.
```

This prevents a new coding session from wasting tokens re-understanding the project.

---

# 7. Milestone 1 — Foundation

## Goal

Build the application skeleton and basic riff library.

At the end of Milestone 1:

> A user can import audio, save it locally, see it in the application, and play it.

### Implement

* project structure
* React + TypeScript frontend
* Python + FastAPI backend
* SQLite database
* Riff model
* repository/data-access layer
* REST API
* audio import
* local storage
* waveform generation/display
* audio playback
* riff library
* riff detail page
* basic dark music-oriented UI

### Do NOT implement yet

* Whisper
* Basic Pitch
* LLM tagging
* embeddings
* semantic search
* similarity search

Keep the foundation stable before introducing AI.

### Acceptance criteria

* [ ] User can import WAV
* [ ] User can import MP3
* [ ] User can import M4A
* [ ] Audio is stored locally
* [ ] Riff is persisted in SQLite
* [ ] Library displays riffs
* [ ] User can play audio
* [ ] Waveform is displayed
* [ ] Riff detail page works
* [ ] Restarting the application preserves data

### Milestone 1 documentation

Update:

```text
MILESTONES.md
HANDOFF.md
ARCHITECTURE.md
README.md
```

Then verify the app from a clean start.

---

# 8. Milestone 2 — Audio Intelligence

## Goal

Make RiffVault understand the audio.

At the end of Milestone 2:

> An imported riff automatically receives useful musical metadata.

### Implement

## Audio analysis

Use:

* librosa
* optionally Essentia where useful

Extract:

* duration
* BPM estimate
* BPM confidence if available
* energy
* onset density
* spectral features
* chroma
* other lightweight features useful for similarity

## Basic Pitch

Attempt:

* note extraction
* MIDI generation

Store MIDI locally.

If extraction fails:

```text
MIDI: unavailable
```

Do not fabricate results.

## Tolerant processing

The import pipeline must not fail completely because one analyzer fails.

Example:

```text
✓ Audio imported
✓ BPM detected
✓ Audio features analyzed
⚠ MIDI extraction unavailable
```

### Processing architecture

Make analysis asynchronous.

Suggested flow:

```text
Import
  ↓
Save audio
  ↓
Create database record
  ↓
Queue/process analysis
  ↓
Update metadata
  ↓
UI shows progress
```

### Acceptance criteria

* [ ] BPM analysis works
* [ ] Audio features are stored
* [ ] Basic Pitch integration works where possible
* [ ] MIDI output is stored
* [ ] Processing status is visible
* [ ] Failed analysis steps do not destroy the riff
* [ ] Analysis can be rerun
* [ ] Existing riffs survive application restart

At the end of this milestone, update all documentation and `HANDOFF.md`.

---

# 9. Milestone 3 — Local AI + Search

## Goal

Turn RiffVault from an audio library into an intelligent searchable archive.

At the end of Milestone 3:

> A guitarist can describe the riff they remember and RiffVault can retrieve it.

## Whisper

Use faster-whisper locally.

Support optional spoken notes such as:

> “Possible chorus idea. Try this at 155 BPM.”

Store:

```text
voice_note_transcript
```

Allow manual editing.

## Local LLM

Use Ollama.

The LLM must be configurable.

Example:

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3
```

Do not hard-code a model name inside application logic.

### LLM responsibilities

The LLM should generate:

* tags
* short descriptions
* structured search intent

Example:

Input:

```text
BPM: 146
Key: C
High onset density
Low-register pitch concentration
Strong repeating rhythm
```

Output:

```text
Tags:
- djent
- chug
- syncopated
- heavy
- palm-muted
```

The system must clearly distinguish:

* extracted facts
* estimates
* AI-generated descriptions

Never present an AI-generated guess as measured fact.

---

# 10. Natural Language Search

Create a prominent search field:

> Search your riffs...

Support queries such as:

* “heavy Drop C riffs”
* “riffs around 150 BPM”
* “ideas I recorded last month”
* “chuggy riffs with a melody”
* “possible chorus ideas”
* “aggressive riffs similar to this one”

The LLM should convert natural language into structured filters when useful.

Example:

```json
{
  "tuning": "Drop C",
  "bpm_min": 140,
  "bpm_max": 150,
  "tags": ["heavy"]
}
```

Then the backend should perform deterministic retrieval.

Do NOT ask the LLM to invent database results.

The LLM interprets intent.

The database/search layer retrieves records.

---

# 11. Semantic Search

Create embeddings locally.

Search should consider:

* description
* tags
* voice-note transcript
* manually entered notes

Example:

> “dark rhythmic riff with open-string chugs”

should be able to find relevant riffs even when those exact words were never used.

Keep embedding generation abstract behind:

```text
EmbeddingService
```

Store the embedding model/version.

---

# 12. Similar Riff Search

Add:

**Find Similar**

For the selected riff:

1. Use stored audio/features/embedding
2. Search the local similarity index
3. Return related riffs
4. Display an approximate similarity score

Example:

```text
Riff 021 — 91%
Riff 044 — 87%
Riff 012 — 81%
```

Use “similarity” terminology.

Do not claim that a score means objective musical equivalence.

---

# 13. Milestone 3 Acceptance Criteria

* [ ] Whisper transcription works locally
* [ ] Voice notes are searchable
* [ ] Local LLM generates tags
* [ ] Local LLM generates descriptions
* [ ] Natural-language search works
* [ ] Metadata filtering works
* [ ] Semantic search works
* [ ] Similar-riff search works
* [ ] No cloud AI API is required
* [ ] AI failures are gracefully handled

Update:

```text
MILESTONES.md
HANDOFF.md
ARCHITECTURE.md
README.md
```

---

# 14. Milestone 4 — Polish + Hackathon Demo

## Goal

Turn the working prototype into a polished, convincing demo.

### UI polish

Improve:

* typography
* spacing
* cards
* waveform presentation
* loading states
* empty states
* errors
* search experience
* transitions
* responsiveness

The interface should feel like a modern music application.

Avoid making it look like an enterprise CRUD dashboard.

---

# 15. Demo Dataset

Create a safe demo dataset.

Include 5–10 example recordings or generated/demo audio files that can be distributed with the project.

Add:

```bash
python scripts/seed_demo_data.py
```

The demo must work without copyrighted commercial music.

---

# 16. Demo Scenario

The demo should tell a simple story.

### Step 1

Show a messy folder of recordings:

```text
IMG_3021.m4a
recording_17.wav
riff_new.wav
idea_final2.wav
voice_2026-09-28.m4a
...
```

### Step 2

Import them into RiffVault.

### Step 3

Let local analysis complete.

### Step 4

Search:

> “Find my heavy Drop C riffs around 140–150 BPM.”

### Step 5

Open one result.

### Step 6

Play the riff.

### Step 7

Show the voice-note transcript:

> “Maybe this can be the chorus.”

### Step 8

Click:

> Find Similar Riffs

### Step 9

Show older related ideas.

The key emotional moment should be:

> “I had completely forgotten about this riff.”

---

# 17. Final Hackathon Story

The application should clearly communicate:

## Problem

Musicians lose creative ideas because recordings become unsearchable collections of files.

## Solution

RiffVault turns guitar recordings into a searchable personal creative archive.

## Why Open Innovation Matters

The important data is personal creative work.

Using local/open models means:

* guitar recordings stay on the user's machine
* voice notes stay private
* no mandatory cloud AI subscription
* models can be swapped
* the pipeline can be modified
* inference can run locally
* the project is not locked to a single AI vendor

This should be explained in the README and final demo.

---

# 18. Technical Architecture

Use clear service boundaries.

Suggested interfaces:

```python
class AudioAnalysisService:
    ...

class TranscriptionService:
    ...

class MidiExtractionService:
    ...

class EmbeddingService:
    ...

class LLMService:
    ...

class RiffSearchService:
    ...

class SimilarityService:
    ...
```

Implement local versions:

```text
LocalWhisperService
LocalBasicPitchService
LocalEmbeddingService
LocalOllamaService
```

AI providers/models must be replaceable.

---

# 19. Recommended Stack

## Frontend

React + TypeScript

## Backend

Python + FastAPI

## Database

SQLite

## Local AI runtime

Ollama

## Audio

* librosa
* numpy
* scipy
* optionally Essentia

## Transcription

faster-whisper

## Note extraction

Spotify Basic Pitch

## Embeddings

A lightweight local embedding model.

Prefer simplicity and reliability.

Do not introduce cloud infrastructure.

---

# 20. Suggested Project Structure

```text
riffvault/
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       ├── services/
│       └── types/
│
├── backend/
│   └── app/
│       ├── api/
│       ├── domain/
│       ├── services/
│       ├── models/
│       ├── repositories/
│       ├── ai/
│       ├── audio/
│       └── database/
│
├── data/
│   ├── audio/
│   ├── midi/
│   ├── embeddings/
│   └── database/
│
├── scripts/
├── tests/
│
├── README.md
├── MILESTONES.md
├── HANDOFF.md
├── ARCHITECTURE.md
└── .env.example
```

---

# 21. Error Handling

The original audio is always the source of truth.

If an AI or analysis component fails:

* keep the audio
* preserve the database record
* record the failure
* allow retry
* allow other analysis steps to continue

Example:

```text
✓ Audio imported
✓ BPM detected
✓ Features analyzed
⚠ MIDI extraction unavailable
✓ Description generated
```

---

# 22. Configuration

Use environment-based configuration.

Example:

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3
WHISPER_MODEL=small
EMBEDDING_MODEL=...
DATA_DIRECTORY=./data
```

Never scatter model names throughout the application.

---

# 23. Privacy Requirements

Default behavior:

* no external AI APIs
* no cloud storage
* no automatic uploads
* all user recordings stored locally
* all AI inference performed locally where practical

Document exactly which operations are local.

---

# 24. Testing

Include tests for:

* riff creation
* metadata persistence
* audio import
* search filters
* natural-language query parsing
* failed analysis handling
* similar-riff retrieval
* important UI interactions

AI-heavy tests should use mocked services wherever appropriate.

Tests should not require downloading a huge model.

---

# 25. What NOT to Build

Do not build:

* user accounts
* cloud sync
* collaboration
* social features
* mobile app
* payments
* subscriptions
* automatic songwriting
* AI music generation
* DAW plugin
* advanced tab generation
* full music-theory engine
* cloud deployment requirement

These are future ideas only.

---

# 26. Future Features

Document but do not implement unless the MVP is already complete:

* browser microphone recording
* tuner
* automatic tuning detection
* chord detection
* project/song organization
* MIDI export
* tab generation
* riff variation generation
* DAW plugin
* mobile companion
* local network sync
* vocal/melody idea storage
* bass/drum idea linking

---

# 27. Development Rules

1. Inspect the existing repository before modifying it.
2. Do not rewrite functioning code unnecessarily.
3. Do not introduce complexity without a clear reason.
4. Keep business logic outside UI components.
5. Keep AI integrations modular.
6. Never fabricate musical metadata.
7. Treat estimated values as estimates.
8. Preserve audio even if analysis fails.
9. Prefer deterministic retrieval over LLM hallucination.
10. Keep the application locally runnable.
11. Update documentation after every milestone.
12. Maintain `HANDOFF.md` after every milestone.
13. Do not proceed to the next milestone with known broken core functionality.
14. Keep the demo path working throughout development.

---

# 28. Milestone Handoff Protocol

At the end of EACH milestone, do the following.

## 1. Verify

Run:

* backend tests
* frontend tests/build
* application startup
* one end-to-end smoke test

## 2. Update documentation

Update:

```text
MILESTONES.md
HANDOFF.md
README.md
ARCHITECTURE.md
```

## 3. Write a milestone summary

Include:

```text
Completed:
...

Files added/changed:
...

Tests:
...

Known issues:
...

Next milestone:
...

Next exact task:
...
```

## 4. Create a clean checkpoint

If git is available, create a commit with a clear message.

Example:

```text
feat: complete milestone 1 foundation
```

Then:

```text
feat: complete milestone 2 audio intelligence
```

etc.

The repository should always have a clean, understandable checkpoint after each milestone.

---

# 29. Starting Instructions for the Coding Agent

Before writing code:

1. Inspect the repository.
2. Check whether anything has already been implemented.
3. Read all existing project documentation.
4. Create or update `MILESTONES.md`.
5. Create or update `HANDOFF.md`.
6. Create `ARCHITECTURE.md`.
7. Decide the smallest architecture satisfying this specification.
8. Begin **Milestone 1 only**.

At the end of Milestone 1:

* verify everything
* update documentation
* create a checkpoint
* clearly state that Milestone 1 is complete
* provide the exact continuation instructions for Milestone 2

Do not silently jump ahead.

When starting a fresh session later, read:

```text
README.md
MILESTONES.md
HANDOFF.md
ARCHITECTURE.md
```

Then continue from the current milestone rather than re-planning the entire project.

---

# 30. Final Definition of Success

RiffVault is successful when a guitarist can say:

> “I recorded this months ago, I completely forgot about it, and RiffVault actually found it.”

Everything else is secondary.

The core product is:

> **Your guitar ideas, searchable.**
