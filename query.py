"""
Milestone 5 — Grounded generation.

Pipeline (from planning.md):
    question -> retrieve top-k chunks (ChromaDB) -> grounded LLM answer (Groq) -> {answer, sources}

Grounding is enforced two ways:
  1. The system prompt instructs the model to answer ONLY from the provided
     context and to decline when the context is insufficient.
  2. Source attribution is built programmatically from the retrieved chunks'
     metadata -- it never depends on the LLM remembering to cite.
"""

import os

from dotenv import load_dotenv
from groq import Groq

from retrieval import retrieve, TOP_K

load_dotenv()

MODEL = "llama-3.3-70b-versatile"   # planning.md generation model
DECLINE = "I don't have enough information on that."

# If the best match is farther than this (cosine distance), treat the corpus
# as not covering the question and decline rather than force an answer.
MAX_DISTANCE = 0.75

_client = None


def get_client():
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY not set in .env")
        _client = Groq(api_key=key)
    return _client


SYSTEM_PROMPT = (
    "You are a factual assistant that answers questions about colleges using "
    "ONLY the student reviews and rating summaries provided in the context. "
    "Follow these rules strictly:\n"
    "1. Use only information found in the context below. Do NOT use any outside "
    "or prior knowledge about these colleges.\n"
    f"2. If the context does not contain enough information to answer, reply "
    f"with exactly: \"{DECLINE}\"\n"
    "3. Refer to schools by name (the context labels each excerpt with its "
    "source school).\n"
    "4. Do not invent ratings, numbers, or quotes that are not in the context."
)


def build_context(chunks):
    """Format retrieved chunks into a numbered, source-labeled context block."""
    blocks = []
    for i, c in enumerate(chunks, 1):
        tag = "RATING SUMMARY" if c["type"] == "summary" else "REVIEW"
        meta = c["source"]
        if c["type"] == "review" and c.get("rating", -1) and c["rating"] >= 0:
            meta += f", rated {c['rating']}"
        if c.get("date"):
            meta += f", {c['date']}"
        blocks.append(f"[{i}] ({tag} — {meta})\n{c['text']}")
    return "\n\n".join(blocks)


def format_sources(chunks):
    """Programmatically derive the source list from retrieved metadata.

    One entry per distinct school, with how many chunks it contributed.
    This is what guarantees attribution regardless of the LLM's output.
    """
    counts = {}
    urls = {}
    for c in chunks:
        counts[c["source"]] = counts.get(c["source"], 0) + 1
        urls[c["source"]] = c.get("url", "")
    sources = []
    for school, n in counts.items():
        label = f"{school} ({n} excerpt{'s' if n > 1 else ''})"
        if urls[school]:
            label += f" — {urls[school]}"
        sources.append(label)
    return sources


def ask(question, k=TOP_K):
    """End-to-end: retrieve, generate a grounded answer, attach sources.

    Returns {"answer": str, "sources": [str], "chunks": [...]}.
    """
    chunks = retrieve(question, k=k)

    # No chunk is even loosely relevant -> decline before calling the LLM.
    if not chunks or chunks[0]["distance"] > MAX_DISTANCE:
        return {"answer": DECLINE, "sources": [], "chunks": chunks}

    context = build_context(chunks)
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above."
    )

    resp = get_client().chat.completions.create(
        model=MODEL,
        temperature=0.1,   # low -> stays close to the evidence
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    answer = resp.choices[0].message.content.strip()

    # Don't attach sources to a refusal.
    sources = [] if answer.strip().rstrip(".") == DECLINE.rstrip(".") else format_sources(chunks)

    return {"answer": answer, "sources": sources, "chunks": chunks}


if __name__ == "__main__":
    # Grounded-generation smoke test: 2 in-domain queries + 1 out-of-domain.
    tests = [
        "What opinions do students have about food and dining options?",
        "What do students review the most postive from the colleges?",
        "What is the football team's win-loss record this season?",  # not in corpus
    ]
    for q in tests:
        print("\n" + "=" * 70)
        print("Q:", q)
        out = ask(q)
        print("-" * 70)
        print("A:", out["answer"])
        print("\nSources:")
        for s in out["sources"]:
            print("  •", s)
