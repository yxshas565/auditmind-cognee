# """
# AuditMind backend entrypoint.
# Wires together Cognee (memory) + Claude (reasoning) behind a FastAPI app.
# """

# import os
# import uuid

# os.environ["LLM_PROVIDER"] = "openai"
# os.environ["LLM_MODEL"] = "openai/gpt-4o-mini"
# os.environ["LLM_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
# os.environ["EMBEDDING_PROVIDER"] = "openai"
# os.environ["EMBEDDING_MODEL"] = "openai/text-embedding-3-small"
# os.environ["EMBEDDING_DIMENSIONS"] = "1536"
# os.environ["VECTOR_DB_SUBPROCESS_ENABLED"] = "false"

# import cognee
# from fastapi import FastAPI
# from pydantic import BaseModel

# app = FastAPI(title="AuditMind")

# from fastapi.middleware.cors import CORSMiddleware

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# _LAST_TRACES: dict[str, dict] = {}


# class ChatRequest(BaseModel):
#     message: str


# class MemoryRequest(BaseModel):
#     text: str


# @app.get("/health")
# async def health():
#     return {"status": "ok"}


# @app.post("/memory")
# async def add_memory(req: MemoryRequest):
#     await cognee.remember(req.text)
#     return {"status": "stored"}


# @app.post("/chat")
# async def chat(req: ChatRequest):
#     results = await cognee.recall(query_text=req.message)
#     answer_text = results[0].text if results else "I don't have enough memory to answer that yet."

#     # pull out anything in the raw result that looks like graph context
#     # (triplets/edges/entities actually used to build this answer)
#     used_entity_names = set()
#     for r in results:
#         raw = r.raw if hasattr(r, "raw") else {}
#         if isinstance(raw, dict):
#             text_blob = str(raw.get("value", "")) + " " + req.message
#         else:
#             text_blob = str(raw) + " " + req.message
#         used_entity_names.add(text_blob.lower())

#     response_id = str(uuid.uuid4())
#     _LAST_TRACES[response_id] = {
#         "query": req.message,
#         "answer": answer_text,
#         "context_blob": " ".join(used_entity_names),
#     }

#     return {"response_id": response_id, "answer": answer_text}


# @app.get("/trace/{response_id}")
# async def get_trace(response_id: str):
#     context = _LAST_TRACES.get(response_id)
#     if not context:
#         return {"error": "unknown response_id"}

#     nodes, edges = await cognee.get_memory_provenance_graph(include_memory=True)
#     answer_and_query = (context["answer"] + " " + context["query"]).lower()

#     # step 1: find entities actually named in the answer/query
#     relevant_entity_ids = set()
#     for n in nodes:
#         name = (n.properties.get("name") or "").lower()
#         node_type = n.properties.get("type")
#         if node_type in ("Entity", "EntityType") and name and name in answer_and_query:
#             relevant_entity_ids.add(n.id)

#     # step 2: find only the direct source files/chunks that mention those
#     # specific entities (not all entities mentioned by that file)
#     source_ids = set()
#     for e in edges:
#         if e.relation == "mentions" and e.target in relevant_entity_ids:
#             source_ids.add(e.source)

#     keep_ids = relevant_entity_ids | source_ids

#     # step 3: edges are only kept if BOTH ends are in keep_ids AND it's
#     # either a source->entity mention for a relevant entity, or directly
#     # connects two relevant entities to each other
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
AuditMind backend entrypoint.
Wires together Cognee (memory) + Claude (reasoning) behind a FastAPI app.
"""

import os
import uuid

os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_MODEL"] = "openai/gpt-4o-mini"
os.environ["LLM_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
os.environ["EMBEDDING_PROVIDER"] = "openai"
os.environ["EMBEDDING_MODEL"] = "openai/text-embedding-3-small"
os.environ["EMBEDDING_DIMENSIONS"] = "1536"
os.environ["VECTOR_DB_SUBPROCESS_ENABLED"] = "false"

import cognee
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

_LAST_TRACES: dict[str, dict] = {}


class ChatRequest(BaseModel):
    message: str


class MemoryRequest(BaseModel):
    text: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/memory")
async def add_memory(req: MemoryRequest):
    await cognee.remember(req.text)
    return {"status": "stored"}


# @app.post("/chat")
# async def chat(req: ChatRequest):
#     # main answer call
#     results = await cognee.recall(query_text=req.message)
#     answer_text = results[0].text if results else "I don't have enough memory to answer that yet."

#     # second call: get the raw retrieved graph CONTEXT (the actual triplets
#     # used), not just the synthesized answer text. This is the real signal
#     # for "what was actually used", instead of text-matching the answer.
#     context_results = await cognee.recall(
#         query_text=req.message,
#         only_context=True,
#     )

#     # context_results contains the actual retrieved nodes/edges/triplets
#     # pull out any node/entity ids or names mentioned in the raw context
#     context_text_blob = ""
#     for r in context_results:
#         raw = getattr(r, "raw", None) or {}
#         if isinstance(raw, dict):
#             context_text_blob += " " + str(raw.get("value", ""))
#         else:
#             context_text_blob += " " + str(raw)
#         # also grab structured field if present
#         structured = getattr(r, "structured", None)
#         if structured:
#             context_text_blob += " " + str(structured)

#     response_id = str(uuid.uuid4())
#     _LAST_TRACES[response_id] = {
#         "query": req.message,
#         "answer": answer_text,
#         "context_blob": context_text_blob.lower(),
#     }

#     return {"response_id": response_id, "answer": answer_text}



@app.post("/chat")
async def chat(req: ChatRequest):
    results = await cognee.recall(query_text=req.message)
    answer_text = results[0].text if results else "I don't have enough memory to answer that yet."

    response_id = str(uuid.uuid4())
    _LAST_TRACES[response_id] = {
        "query": req.message,
        "answer": answer_text,
    }
    return {"response_id": response_id, "answer": answer_text}





# @app.get("/trace/{response_id}")
# async def get_trace(response_id: str):
#     context = _LAST_TRACES.get(response_id)
#     if not context:
#         return {"error": "unknown response_id"}

#     nodes, edges = await cognee.get_memory_provenance_graph(include_memory=True)

#     # use the actual retrieved CONTEXT blob (real triplets used by recall),
#     # not the final answer text, to decide relevance. This avoids the
#     # "Yashas appears everywhere" false-positive problem.
#     context_blob = context["context_blob"]

#     # build adjacency: entity_id -> set of source document ids that mention it
#     entity_to_sources = {}
#     for e in edges:
#         if e.relation == "mentions":
#             entity_to_sources.setdefault(e.target, set()).add(e.source)

#     # only count an entity as relevant if its name appears in the actual
#     # retrieved context blob AND it's not an overly generic node like "yashas"
#     # appearing in every single document (high document-fanout = generic/noisy)
#     relevant_entity_ids = set()
#     for n in nodes:
#         name = (n.properties.get("name") or "").lower()
#         node_type = n.properties.get("type")
#         if node_type not in ("Entity", "EntityType") or not name:
#             continue
#         if name not in context_blob:
#             continue
#         # skip overly generic entities that appear in almost every document
#         # (e.g. "yashas" mentioned in 6+ separate facts -> not a useful signal)
#         source_count = len(entity_to_sources.get(n.id, set()))
#         total_docs = sum(1 for nn in nodes if nn.properties.get("type") == "TextDocument")
#         if total_docs > 0 and source_count / total_docs > 0.5:
#             continue
#         relevant_entity_ids.add(n.id)

#     # if filtering was too aggressive and removed everything (e.g. only
#     # generic entities existed), fall back to top entities mentioned in answer
#     if not relevant_entity_ids:
#         answer_lower = context["answer"].lower()
#         for n in nodes:
#             name = (n.properties.get("name") or "").lower()
#             node_type = n.properties.get("type")
#             if node_type in ("Entity", "EntityType") and name and name in answer_lower:
#                 relevant_entity_ids.add(n.id)

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



@app.get("/trace/{response_id}")
async def get_trace(response_id: str):
    context = _LAST_TRACES.get(response_id)
    if not context:
        return {"error": "unknown response_id"}

    nodes, edges = await cognee.get_memory_provenance_graph(include_memory=True)
    answer_lower = context["answer"].lower()

    GENERIC_NAMES = {"yashas", "person"}

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

    return {
        "query": context["query"],
        "answer": context["answer"],
        "nodes": [{"id": n.id, **n.properties} for n in filtered_nodes],
        "edges": [{"source": e.source, "target": e.target, "relation": e.relation} for e in filtered_edges],
        "full_graph_node_count": len(nodes),
        "filtered_node_count": len(filtered_nodes),
    }