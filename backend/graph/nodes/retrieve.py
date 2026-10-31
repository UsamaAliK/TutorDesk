from backend.graph.state import GenerationState
from backend.rag.vector_store import retrieve_chunks


def retrieve_material(state: GenerationState) -> dict:
    """Retrieves relevant document chunks from user's indexed materials."""
    user_id = state.get("user_id")
    query = state.get("query") or f"{state.get('subject')}: {state.get('topic')}"
    selected_doc_id = state.get("selected_document_id")
    selected_filename = state.get("selected_filename")

    chunks = []
    # If a specific upload is selected, filter by upload_id and/or filename
    if selected_doc_id:
        chunks = retrieve_chunks(query, user_id=user_id, k=6, upload_id=selected_doc_id)
        if not chunks and selected_filename:
            chunks = retrieve_chunks(query, user_id=user_id, k=6, filename=selected_filename)
    else:
        chunks = retrieve_chunks(query, user_id=user_id, k=6)

    # Fallback to broader query if specific query returned empty
    if not chunks and ":" in query:
        broader_query = query.split(":")[0].strip()
        if selected_doc_id:
            chunks = retrieve_chunks(broader_query, user_id=user_id, k=6, upload_id=selected_doc_id)
        else:
            chunks = retrieve_chunks(broader_query, user_id=user_id, k=6)

    formatted_docs = []
    sources = []
    for doc in chunks:
        content = doc.get("content", "").strip()
        if not content:
            continue
        src = doc.get("source") or selected_filename or "Uploaded Document"
        formatted_docs.append({"content": content, "source": src})
        if src not in sources:
            sources.append(src)

    return {
        "rag_documents": formatted_docs,
        "rag_sources": sources,
        "has_uploaded_material": len(formatted_docs) > 0,
    }

