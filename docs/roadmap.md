# AuditMind — Roadmap

Built for the WeMakeDevs × Cognee Hackathon ("The Hangover Part AI: Where's My Context?"), June 29 – July 5, 2026.

This roadmap is sequenced for hackathon judging impact, not general "production readiness" — items are ordered by how directly they map to the stated judging criteria (Potential Impact, Creativity & Innovation, Technical Excellence, Best Use of Cognee, User Experience, Presentation Quality).

## Status legend
- [x] Done
- [ ] Not started
- [~] In progress

---

## Tier 1 — Core differentiators (do first)

- [x] `remember()` → `recall()` round trip working end to end
- [x] Provenance graph (`get_memory_provenance_graph`) wired to a `/trace/{response_id}` endpoint
- [x] Entity-based trace filtering (full graph → only nodes relevant to a specific answer)
- [x] D3 force-directed graph visualization with pan/zoom, animated node entry, legend
- [x] Chat UI with typing indicator, clickable trace history per message
- [ ] `forget()` demo — UI action to remove a memory, confirm it disappears from a later trace
- [ ] `improve()`/`memify` demo — visible before/after showing reinforcement or graph enrichment
- [ ] Session memory (`session_id` wired into `/chat`) — multi-turn conversational context, trace distinguishes session vs. permanent memory
- [ ] History sidebar — list of past questions this session, clickable to reload their trace
- [ ] Stress test: bulk-load 30–50 facts, confirm trace filtering stays clean (not full-graph dump)

## Tier 2 — Product polish (do if Tier 1 is done with time to spare)

- [ ] Bulk/file ingestion — paste a paragraph or upload a text file instead of one fact at a time (`remember()` already supports file input)
- [ ] Loading skeleton instead of typing dots while `/chat` resolves
- [ ] Smooth camera/graph transition between trace views instead of hard reset
- [ ] Plain-language explainer under each trace ("we filtered 144 memories down to these 12 because...")
- [ ] README polish + 90-second demo video (script: ask question → answer → click trace → forget() demo → node-count stat)

## Tier 3 — Real but out of scope before July 5

- [ ] Multi-user support / proper auth
- [ ] Persistent hosted deployment (currently localhost-only)
- [ ] Production error handling, rate limiting
- [ ] Postgres/Neo4j swap from default SQLite/LanceDB/Kuzu for scale

---

## Known issues

- Entity deduplication: Cognee occasionally creates duplicate entity nodes for the same real-world entity (e.g. two separate "auditmind" nodes) when ingested across different `remember()` calls. Not something we control directly — worth mentioning if asked, not worth fixing in our code.
- LanceDB on Windows required `VECTOR_DB_SUBPROCESS_ENABLED=false` to avoid a subprocess I/O crash — documented as a known Windows-specific issue, not an AuditMind bug.
- `/chat` response time can run 20–60s depending on dataset size and `top_k`; worth tuning `top_k` down for the demo dataset size before presenting live.

## Design questions still open

- Should memories be added atomically (one fact per `remember()` call) or as bulk context dumps? Atomic is easier to selectively `forget()` later; bulk is faster to ingest. Currently supports both — worth a line in the submission writeup either way.