from backend.websearch.research import research_topic
from backend.graph.state import TutorState


def web_research(state: TutorState) -> dict:
    """Search the web using the original or refined query."""

    search_query = state.get("refined_query") or state["query"]

    result = research_topic(search_query)

    documents = []
    for content in result.get("research", []):
        documents.append({"content": content})

    # Append to any existing web docs from previous retries
    existing_docs = state.get("web_documents", [])
    existing_sources = state.get("web_sources", [])

    new_sources = [
        url for url in result.get("sources", [])
        if url not in existing_sources
    ]

    return {
        "web_documents": existing_docs + documents,
        "web_sources": existing_sources + new_sources,
    }

