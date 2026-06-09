"""
Milestone 4 — Embedding + Vector Store + Retrieval.

Architecture (from planning.md):
    chunks.json  ->  all-MiniLM-L6-v2 embeddings  ->  ChromaDB  ->  top-k retrieval

Run directly to (re)build the index and test retrieval on the eval queries:
    python retrieval.py
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# =====================================================
# CONFIG
# =====================================================

CHUNKS_PATH = Path("data/chunks.json")
DB_DIR = Path("data/chroma")          # persistent on-disk vector store
COLLECTION_NAME = "college_reviews"
EMBED_MODEL = "all-MiniLM-L6-v2"      # planning.md retrieval approach
TOP_K = 5                             # planning.md top-k

# Loaded lazily so importing this module is cheap.
_model = None


def get_model():
    global _model
    if _model is None:
        print(f"Loading embedding model: {EMBED_MODEL}")
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def get_collection():
    """Return the persistent Chroma collection (created if missing)."""
    client = chromadb.PersistentClient(path=str(DB_DIR))
    # cosine distance suits sentence-transformer embeddings better than the
    # default L2; smaller distance = more similar.
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

# =====================================================
# BUILD INDEX
# =====================================================

def build_index():
    """Embed every chunk and (re)load it into ChromaDB with source metadata."""
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    model = get_model()

    client = chromadb.PersistentClient(path=str(DB_DIR))
    # Rebuild from scratch so re-running never duplicates documents.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    documents, metadatas, ids = [], [], []
    position_by_school = {}  # chunk position within each source document

    for c in chunks:
        school = c["school"]
        pos = position_by_school.get(school, 0)
        position_by_school[school] = pos + 1

        documents.append(c["text"])
        metadatas.append({
            "source": school,                 # source document name (for attribution)
            "position": pos,                  # chunk position within that source
            "url": c.get("source", ""),
            "type": c.get("type", "review"),
            # Chroma metadata must be scalar & non-null -> coerce.
            "rating": c["rating"] if c.get("rating") is not None else -1.0,
            "date": c.get("date") or "",
        })
        ids.append(f"{school.replace(' ', '_')}-{pos}")

    print(f"Embedding {len(documents)} chunks ...")
    embeddings = model.encode(
        documents, batch_size=64, show_progress_bar=True
    ).tolist()

    collection.add(
        ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
    )
    print(f"Stored {collection.count()} chunks in ChromaDB at {DB_DIR}")
    return collection

# =====================================================
# RETRIEVAL
# =====================================================

def retrieve(query, k=TOP_K):
    """Return the top-k most relevant chunks for a query string.

    Each result: {text, source, position, type, rating, date, distance}.
    Lower distance = more similar (cosine).
    """
    collection = get_collection()
    query_emb = get_model().encode([query]).tolist()

    res = collection.query(
        query_embeddings=query_emb,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    results = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        results.append({
            "text": doc,
            "source": meta["source"],
            "position": meta["position"],
            "type": meta["type"],
            "rating": meta["rating"],
            "date": meta["date"],
            "distance": dist,
        })
    return results

# =====================================================
# EVAL / TEST
# =====================================================

# 3 of the 5 evaluation-plan queries from planning.md.
TEST_QUERIES = [
    "What opinions do students have about food and dining options?",
    "What do students say about how crowded the colleges are?",
    "What do students say about the professors of the colleges?",
]


def test_retrieval():
    for q in TEST_QUERIES:
        print("\n" + "=" * 70)
        print(f"QUERY: {q}")
        print("=" * 70)
        for i, r in enumerate(retrieve(q), 1):
            print(f"\n[{i}] distance={r['distance']:.3f}  "
                  f"source={r['source']}  type={r['type']}  rating={r['rating']}")
            print("    " + r["text"][:].replace("\n", " "))


if __name__ == "__main__":
    build_index()
    test_retrieval()
