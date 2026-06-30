"""
AuditMind backend entrypoint.
Wires together Cognee (memory) + Claude (reasoning) behind a FastAPI app.
"""

from fastapi import FastAPI

app = FastAPI(title="AuditMind")


@app.get("/health")
async def health():
    return {"status": "ok"}


# TODO:
# - POST /chat        -> takes user message, calls recall(), calls Claude, returns answer
# - GET  /trace/{id}   -> returns the memory graph path that produced a given response
# - POST /memory       -> ingest new memory via remember()
