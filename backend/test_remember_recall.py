"""
Quick test: remember() -> recall() round trip.
Run this locally with your ANTHROPIC_API_KEY set to see real output shape.
"""

import asyncio
import os

os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_MODEL"] = "openai/gpt-4o-mini"
os.environ["LLM_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")

# embeddings default to OpenAI if unset -- use fastembed (local, free, no key needed)
os.environ["EMBEDDING_PROVIDER"] = "fastembed"
# os.environ["EMBEDDING_MODEL"] = "fastembed/BAAI/bge-small-en-v1.5"
os.environ["EMBEDDING_MODEL"] = "BAAI/bge-small-en-v1.5"
os.environ["EMBEDDING_DIMENSIONS"] = "384"

import cognee


async def main():
    # 1. wipe any previous test state so this is repeatable
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    # 2. remember() -- ingest a few facts (new v1 API: remember = add + cognify + improve)
    await cognee.remember("Yashas prefers concise, direct feedback over diplomatic hedging.")
    await cognee.remember("Yashas is building AuditMind, a traceable memory assistant, for the Cognee hackathon.")
    await cognee.remember("Yashas is a national-level inline and ice hockey athlete.")

    # 3. recall() -- ask something that requires connecting facts
    results = await cognee.recall(
        query_text="What kind of communication style does Yashas want, and what is he building right now?",
    )

    print("=== RECALL RESULTS ===")
    print(results)

    # 4. THE KEY PART FOR US: get the provenance graph (nodes + edges)
    # this is the trace -- exactly what AuditMind's trace view needs to render
    nodes, edges = await cognee.get_memory_provenance_graph(include_memory=True)

    print("\n=== PROVENANCE NODES ===")
    for n in nodes:
        print(n)

    print("\n=== PROVENANCE EDGES ===")
    for e in edges:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())