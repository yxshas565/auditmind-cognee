# AuditMind — Traceable Personal Memory

Built for the WeMakeDevs × Cognee Hackathon ("The Hangover Part AI: Where's My Context?"), June 29 – July 5, 2026.

## The Idea

Most AI memory layers are black boxes: you ask a question, you get an answer, you have no idea *why*. AuditMind is a personal AI assistant that remembers you across sessions using [Cognee](https://github.com/topoteretes/cognee)'s hybrid graph-vector memory, and — critically — can show you exactly which memories and graph connections produced any given response.

Not just "what happened last night." **Why** the AI thinks what it thinks.

## How it works

- **Memory layer**: Cognee (self-hosted), using the full lifecycle — `remember()`, `recall()`, `improve()`/`memify`, `forget()`
- **Reasoning layer**: Claude API generates responses from recalled context
- **Trace layer**: every response is paired with a visual path through the memory graph showing exactly which nodes informed the answer

## Status

🚧 Early build — hackathon in progress.

## Stack

- Backend: FastAPI, Python
- Memory: Cognee (self-hosted)
- LLM: Claude API
- Frontend: TBD (chat UI + graph trace panel)
- Containerization: Docker

## Setup

See `backend/README.md` (coming soon) for local dev setup.
