from backend.rag.vector_store import retrieve_chunks
from backend.graph.state import TutorState


def rag_retrieve(state: TutorState) -> dict:
    """Retrieve chunks from the user's uploaded documents."""

    docs = retrieve_chunks(state["query"], user_id=state["user_id"])

    chunks = []
    sources = []

    for doc in docs:
        chunks.append(doc)
        source = doc.get("source")
        if source and source not in sources:
            sources.append(source)

    return {
        "rag_documents": chunks,
        "rag_sources": sources,
    }

