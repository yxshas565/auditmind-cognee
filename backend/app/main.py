# import os
# import uuid
# import traceback
# from datetime import datetime, timezone

# os.environ["LLM_PROVIDER"] = "openai"
# os.environ["LLM_MODEL"] = "openai/gpt-4o-mini"
# os.environ["LLM_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
# os.environ["EMBEDDING_PROVIDER"] = "openai"
# os.environ["EMBEDDING_MODEL"] = "openai/text-embedding-3-small"
# os.environ["EMBEDDING_DIMENSIONS"] = "1536"
# os.environ["VECTOR_DB_SUBPROCESS_ENABLED"] = "false"
# os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "false"

# import cognee
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel

# app = FastAPI(title="AuditMind")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# _LAST_TRACES: dict[str, dict] = {}
# _MEMORY_LOG: dict[str, dict] = {}

# GENERIC_NAMES = {"person"}


# class ChatRequest(BaseModel):
#     message: str
#     session_id: str | None = None


# class MemoryRequest(BaseModel):
#     text: str


# class ForgetRequest(BaseModel):
#     memory_id: str


# @app.get("/health")
# async def health():
#     return {"status": "ok"}


# @app.post("/memory")
# async def add_memory(req: MemoryRequest):
#     print(f"[/memory] {req.text!r}", flush=True)
#     try:
#         await cognee.remember(req.text)
#     except Exception as e:
#         print("[/memory] ERROR:", repr(e), flush=True)
#         traceback.print_exc()
#         return {"status": "error", "detail": str(e)}

#     memory_id = str(uuid.uuid4())
#     _MEMORY_LOG[memory_id] = {
#         "text": req.text,
#         "created_at": datetime.now(timezone.utc).isoformat(),
#         "forgotten": False,
#     }
#     return {"status": "stored", "memory_id": memory_id}


# @app.get("/memories")
# async def list_memories():
#     return {
#         "memories": [
#             {"memory_id": mid, **entry}
#             for mid, entry in _MEMORY_LOG.items()
#         ]
#     }


# @app.post("/forget")
# async def forget_memory(req: ForgetRequest):
#     entry = _MEMORY_LOG.get(req.memory_id)
#     if not entry:
#         return {"status": "error", "detail": "unknown memory_id"}
#     if entry["forgotten"]:
#         return {"status": "already_forgotten"}

#     # find the matching dataset entries and delete them
#     try:
#         # prune just the specific text from the graph by re-searching and deleting
#         # cognee v1.2.x forget() takes a dataset name — we remove the whole
#         # item by pruning data that matches this specific memory text
#         datasets = await cognee.get_datasets()
#         for ds in (datasets or []):
#             try:
#                 await cognee.forget(dataset=ds)
#                 break
#             except Exception:
#                 pass
#         # mark forgotten regardless — UI reflects it, trace won't re-surface it
#         # since the graph nodes get pruned on next cognify run
#         entry["forgotten"] = True
#     except Exception as e:
#         print("[/forget] ERROR:", repr(e), flush=True)
#         traceback.print_exc()
#         # still mark as forgotten in our log even if cognee call is uncertain
#         entry["forgotten"] = True

#     return {"status": "forgotten", "memory_id": req.memory_id}


# @app.post("/chat")
# async def chat(req: ChatRequest):
#     print(f"[/chat] {req.message!r}", flush=True)
#     try:
#         results = await cognee.recall(query_text=req.message)
#     except Exception as e:
#         print("[/chat] RECALL ERROR:", repr(e), flush=True)
#         traceback.print_exc()
#         return {"response_id": None, "answer": f"Recall failed: {e}"}

#     answer_text = results[0].text if results else "I don't have enough memory to answer that yet."
#     response_id = str(uuid.uuid4())
#     _LAST_TRACES[response_id] = {
#         "query": req.message,
#         "answer": answer_text,
#     }
#     return {"response_id": response_id, "answer": answer_text}


# @app.post("/improve")
# async def run_improve():
#     try:
#         before_nodes, _ = await cognee.get_memory_provenance_graph(include_memory=True)
#         await cognee.improve()
#         after_nodes, _ = await cognee.get_memory_provenance_graph(include_memory=True)
#     except Exception as e:
#         print("[/improve] ERROR:", repr(e), flush=True)
#         traceback.print_exc()
#         return {"status": "error", "detail": str(e)}

#     return {
#         "status": "improved",
#         "node_count_before": len(before_nodes),
#         "node_count_after": len(after_nodes),
#     }


# @app.get("/trace/{response_id}")
# async def get_trace(response_id: str):
#     context = _LAST_TRACES.get(response_id)
#     if not context:
#         return {"error": "unknown response_id"}

#     nodes, edges = await cognee.get_memory_provenance_graph(include_memory=True)
#     answer_lower = context["answer"].lower()

#     relevant_entity_ids = set()
#     for n in nodes:
#         name = (n.properties.get("name") or "").lower()
#         node_type = n.properties.get("type")
#         if node_type not in ("Entity", "EntityType") or not name:
#             continue
#         if name in GENERIC_NAMES:
#             continue
#         if name in answer_lower:
#             relevant_entity_ids.add(n.id)

#     source_ids = set()
#     for e in edges:
#         if e.relation == "mentions" and e.target in relevant_entity_ids:
#             source_ids.add(e.source)

#     keep_ids = relevant_entity_ids | source_ids
#     filtered_edges = [
#         e for e in edges
#         if e.source in keep_ids and e.target in keep_ids
#         and (e.target in relevant_entity_ids or e.source in relevant_entity_ids)
#     ]
#     filtered_nodes = [n for n in nodes if n.id in keep_ids]

#     return {
#         "query": context["query"],
#         "answer": context["answer"],
#         "nodes": [{"id": n.id, **n.properties} for n in filtered_nodes],
#         "edges": [{"source": e.source, "target": e.target, "relation": e.relation} for e in filtered_edges],
#         "full_graph_node_count": len(nodes),
#         "filtered_node_count": len(filtered_nodes),
#     }


















































"""
AuditMind backend — with Temporal Memory Arbitration (TMA)

Three layers on top of cognee:
  L1 — Contradiction detector: before storing, check if new fact contradicts
       an existing memory about the same entity+attribute. If yes, mark old
       one deprecated so it loses priority in recall.
  L2 — Temporal metadata index: every memory tagged with stored_at + an
       entity_attribute key so we can rank by recency when conflicts exist.
  L3 — Pre-return arbitration: after cognee.recall() returns candidates,
       group by entity+attribute, keep only the most recent non-deprecated
       entry per group before sending the answer.
"""

import os
import re
import uuid
import traceback
from datetime import datetime, timezone
from difflib import SequenceMatcher

os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_MODEL"] = "openai/gpt-4o-mini"
os.environ["LLM_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
os.environ["EMBEDDING_PROVIDER"] = "openai"
os.environ["EMBEDDING_MODEL"] = "openai/text-embedding-3-small"
os.environ["EMBEDDING_DIMENSIONS"] = "1536"
os.environ["VECTOR_DB_SUBPROCESS_ENABLED"] = "false"
os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "false"
os.environ["COGNEE_DATA_PATH"] = os.path.join(os.getcwd(), ".cognee_data")

import cognee
from openai import AsyncOpenAI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AuditMind")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_openai = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ── TMA index ──────────────────────────────────────────────────────────────
# memory_id -> {
#   text, stored_at, entity_attr_key, deprecated, deprecated_by, forgotten
# }
_MEMORY_LOG: dict[str, dict] = {}
_LAST_TRACES: dict[str, dict] = {}

GENERIC_NAMES = {"person"}


# ── helpers ────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def _extract_entity_attr(text: str) -> str:
    """
    L2: Ask GPT to extract a canonical entity+attribute key from a fact.
    e.g. "Alex is a 2nd year CS student" -> "alex::year"
         "Alex interned at Horizon Robotics" -> "alex::internship"
         "AtlasMind pivoted to decision provenance" -> "atlasmind::focus"
    Returns a short lowercase key or 'unknown::unknown' if it can't parse.
    """
    try:
        r = await _openai.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=30,
            temperature=0,
            messages=[{
                "role": "user",
                "content": (
                    "Extract a canonical entity::attribute key from this fact. "
                    "Format: lowercase_entity::lowercase_attribute. "
                    "Examples: 'Alex is 2nd year' -> 'alex::year', "
                    "'AtlasMind pivoted to provenance' -> 'atlasmind::focus'. "
                    "Reply with ONLY the key, nothing else.\n\n"
                    f"Fact: {text}"
                )
            }]
        )
        key = r.choices[0].message.content.strip().lower()
        # validate format
        if "::" in key and len(key) < 80:
            return key
        return "unknown::unknown"
    except Exception as e:
        print(f"[TMA-L2] entity_attr extraction failed: {e}", flush=True)
        return "unknown::unknown"


async def _detect_contradiction(new_text: str, existing_memories: list[dict]) -> list[str]:
    """
    L1: Given new_text and existing active memories, return list of memory_ids
    that contradict the new fact. Uses GPT to check semantic contradiction.
    Only checks memories that share the same entity_attr_key.
    """
    if not existing_memories:
        return []

    # build a numbered list for GPT
    candidates = "\n".join(
        f"{i+1}. [{m['memory_id'][:8]}] {m['text']}"
        for i, m in enumerate(existing_memories)
    )

    try:
        r = await _openai.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=120,
            temperature=0,
            messages=[{
                "role": "user",
                "content": (
                    "New fact: " + new_text + "\n\n"
                    "Existing facts:\n" + candidates + "\n\n"
                    "Which existing facts DIRECTLY CONTRADICT the new fact? "
                    "A contradiction means they cannot both be true at the same time. "
                    "Reply with ONLY the bracketed IDs of contradicting facts, "
                    "comma-separated, e.g. [abc12345],[def67890]. "
                    "If none contradict, reply NONE."
                )
            }]
        )
        content = r.choices[0].message.content.strip()
        print(f"[TMA-L1] contradiction check: {content}", flush=True)
        if content == "NONE":
            return []
        # extract 8-char ids from brackets
        found = re.findall(r'\[([a-f0-9]{8})\]', content)
        # map short ids back to full memory_ids
        result = []
        for m in existing_memories:
            if m['memory_id'][:8] in found:
                result.append(m['memory_id'])
        return result
    except Exception as e:
        print(f"[TMA-L1] contradiction detection failed: {e}", flush=True)
        return []


def _arbitrate(results: list, query: str) -> list:
    """
    L3: Pre-return arbitration.
    Given cognee recall results, cross-reference with our TMA index.
    For each result text, find matching memory entries, group by entity_attr_key,
    and within each group keep only the most recent non-deprecated one.
    If a result has no TMA entry (e.g. old cognee data), pass it through but
    flag it as unverified.
    """
    if not results:
        return results

    # build a lookup: text snippet -> best matching TMA entry
    active = {
        mid: m for mid, m in _MEMORY_LOG.items()
        if not m.get("forgotten") and not m.get("deprecated")
    }
    deprecated = {
        mid: m for mid, m in _MEMORY_LOG.items()
        if m.get("deprecated") and not m.get("forgotten")
    }

    arbitrated = []
    seen_entity_attrs = {}  # entity_attr_key -> best result already picked

    for r in results:
        r_text = getattr(r, 'text', str(r))

        # find the TMA entry that best matches this result's text
        best_mid = None
        best_score = 0.0
        for mid, m in {**active, **deprecated}.items():
            score = _similarity(r_text, m['text'])
            if score > best_score:
                best_score = score
                best_mid = mid

        # if no TMA entry matches well, it's old/untracked data — pass through
        if best_mid is None or best_score < 0.35:
            arbitrated.append(r)
            continue

        entry = _MEMORY_LOG[best_mid]

        # if this result matches a deprecated entry, skip it
        if entry.get("deprecated"):
            print(f"[TMA-L3] suppressed deprecated result: {r_text[:60]}", flush=True)
            continue

        # entity_attr deduplication: keep only the most recent per key
        ea_key = entry.get("entity_attr_key", "unknown::unknown")
        if ea_key != "unknown::unknown":
            if ea_key in seen_entity_attrs:
                # compare stored_at, keep newer
                existing_mid = seen_entity_attrs[ea_key]
                existing_ts = _MEMORY_LOG[existing_mid]["stored_at"]
                if entry["stored_at"] > existing_ts:
                    # replace: remove the one we already added
                    arbitrated = [
                        x for x in arbitrated
                        if getattr(x, 'text', str(x)) != getattr(
                            results[0], 'text', ''
                        )
                    ]
                    seen_entity_attrs[ea_key] = best_mid
                    arbitrated.append(r)
                    print(f"[TMA-L3] replaced older {ea_key} entry with newer one", flush=True)
                else:
                    print(f"[TMA-L3] kept existing newer {ea_key} entry, skipped older", flush=True)
                continue
            else:
                seen_entity_attrs[ea_key] = best_mid

        arbitrated.append(r)

    print(f"[TMA-L3] {len(results)} -> {len(arbitrated)} after arbitration", flush=True)
    return arbitrated if arbitrated else results  # fallback: never return empty


# ── models ─────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class MemoryRequest(BaseModel):
    text: str

class ForgetRequest(BaseModel):
    memory_id: str


# ── routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/memory")
async def add_memory(req: MemoryRequest):
    print(f"[/memory] received: {req.text!r}", flush=True)

    # ── L2: extract entity+attribute key ──
    ea_key = await _extract_entity_attr(req.text)
    print(f"[TMA-L2] entity_attr_key: {ea_key}", flush=True)

    # ── L1: contradiction detection ──
    # find all active memories with the same entity_attr_key
    same_attr_memories = [
        {"memory_id": mid, "text": m["text"]}
        for mid, m in _MEMORY_LOG.items()
        if m.get("entity_attr_key") == ea_key
        and not m.get("deprecated")
        and not m.get("forgotten")
        and ea_key != "unknown::unknown"
    ]

    contradicted_ids = await _detect_contradiction(req.text, same_attr_memories)
    if contradicted_ids:
        print(f"[TMA-L1] deprecating {len(contradicted_ids)} contradicted memories", flush=True)
        for mid in contradicted_ids:
            memory_id_new = str(uuid.uuid4())  # placeholder, will be set below
            _MEMORY_LOG[mid]["deprecated"] = True
            _MEMORY_LOG[mid]["deprecated_reason"] = f"contradicted by new fact: {req.text[:80]}"
            _MEMORY_LOG[mid]["deprecated_at"] = _now()

    # ── store in cognee ──
    try:
        await cognee.remember(req.text)
        await cognee.cognify()
        print("[/memory] cognee remember+cognify done", flush=True)
    except Exception as e:
        print("[/memory] ERROR:", repr(e), flush=True)
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}

    # ── register in TMA index ──
    memory_id = str(uuid.uuid4())
    _MEMORY_LOG[memory_id] = {
        "text": req.text,
        "stored_at": _now(),
        "entity_attr_key": ea_key,
        "deprecated": False,
        "forgotten": False,
        "contradicted_ids": contradicted_ids,
    }

    print(f"[/memory] stored memory_id={memory_id[:8]} ea_key={ea_key} deprecated_count={len(contradicted_ids)}", flush=True)
    return {
        "status": "stored",
        "memory_id": memory_id,
        "entity_attr_key": ea_key,
        "contradictions_resolved": len(contradicted_ids),
    }


@app.get("/memories")
async def list_memories():
    return {
        "memories": [
            {"memory_id": mid, **{k: v for k, v in entry.items()}}
            for mid, entry in _MEMORY_LOG.items()
        ]
    }


@app.post("/forget")
async def forget_memory(req: ForgetRequest):
    entry = _MEMORY_LOG.get(req.memory_id)
    if not entry:
        return {"status": "error", "detail": "unknown memory_id"}
    if entry.get("forgotten"):
        return {"status": "already_forgotten"}
    entry["forgotten"] = True
    entry["forgotten_at"] = _now()
    return {"status": "forgotten", "memory_id": req.memory_id}


@app.post("/chat")
async def chat(req: ChatRequest):
    print(f"[/chat] received: {req.message!r}", flush=True)
    try:
        results = await cognee.recall(query_text=req.message)
        print(f"[/chat] cognee returned {len(results)} raw results", flush=True)
    except Exception as e:
        print("[/chat] RECALL ERROR:", repr(e), flush=True)
        traceback.print_exc()
        return {"response_id": None, "answer": f"Recall failed: {e}"}

    # ── L3: arbitrate before answering ──
    arbitrated = _arbitrate(results, req.message)

    answer_text = arbitrated[0].text if arbitrated else "I don't have enough memory to answer that yet."

    response_id = str(uuid.uuid4())
    _LAST_TRACES[response_id] = {
        "query": req.message,
        "answer": answer_text,
        "raw_result_count": len(results),
        "arbitrated_result_count": len(arbitrated),
    }
    return {"response_id": response_id, "answer": answer_text}


@app.post("/improve")
async def run_improve():
    try:
        before_nodes, _ = await cognee.get_memory_provenance_graph(include_memory=True)
        await cognee.improve()
        after_nodes, _ = await cognee.get_memory_provenance_graph(include_memory=True)
    except Exception as e:
        print("[/improve] ERROR:", repr(e), flush=True)
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}
    return {
        "status": "improved",
        "node_count_before": len(before_nodes),
        "node_count_after": len(after_nodes),
    }


@app.get("/trace/{response_id}")
async def get_trace(response_id: str):
    context = _LAST_TRACES.get(response_id)
    if not context:
        return {"error": "unknown response_id"}

    nodes, edges = await cognee.get_memory_provenance_graph(include_memory=True)
    answer_lower = context["answer"].lower()

    relevant_entity_ids = set()
    for n in nodes:
        name = (n.properties.get("name") or "").lower()
        node_type = n.properties.get("type")
        if node_type not in ("Entity", "EntityType") or not name:
            continue
        if name in GENERIC_NAMES:
            continue
        if name in answer_lower:
            relevant_entity_ids.add(n.id)

    source_ids = set()
    for e in edges:
        if e.relation == "mentions" and e.target in relevant_entity_ids:
            source_ids.add(e.source)

    keep_ids = relevant_entity_ids | source_ids
    filtered_edges = [
        e for e in edges
        if e.source in keep_ids and e.target in keep_ids
        and (e.target in relevant_entity_ids or e.source in relevant_entity_ids)
    ]
    filtered_nodes = [n for n in nodes if n.id in keep_ids]

    # annotate nodes with TMA status
    tma_status = {}
    for mid, m in _MEMORY_LOG.items():
        tma_status[m["text"][:40]] = {
            "deprecated": m.get("deprecated", False),
            "ea_key": m.get("entity_attr_key", "?"),
        }

    return {
        "query": context["query"],
        "answer": context["answer"],
        "raw_result_count": context.get("raw_result_count"),
        "arbitrated_result_count": context.get("arbitrated_result_count"),
        "nodes": [{"id": n.id, **n.properties} for n in filtered_nodes],
        "edges": [{"source": e.source, "target": e.target, "relation": e.relation} for e in filtered_edges],
        "full_graph_node_count": len(nodes),
        "filtered_node_count": len(filtered_nodes),
    }