from backend.graph.state import GenerationState
from backend.websearch.research import research_topic


def web_research(state: GenerationState) -> dict:
    """Performs live web research to gather factual grounding."""
    subject = state.get("subject", "")
    topic = state.get("topic", "")
    level = state.get("educational_level", "")
    query = state.get("refined_query") or state.get("query") or f"{subject} {topic}"

    # For PhD level, enrich query with academic phrasing
    if "PhD" in level or "Research" in level:
        search_query = f"{query} scholarly peer-reviewed framework literature methodology"
    else:
        search_query = query

    try:
        search_res = research_topic(search_query)
        docs = [{"content": c} for c in search_res.get("research", []) if c.strip()]
        sources = [s for s in search_res.get("sources", []) if s.strip()]
    except Exception:
        docs = []
        sources = []

    # Merge with any existing web docs from prior retries
    existing_docs = state.get("web_documents", [])
    existing_sources = state.get("web_sources", [])

    merged_sources = list(existing_sources)
    for s in sources:
        if s not in merged_sources:
            merged_sources.append(s)

    return {
        "web_documents": existing_docs + docs,
        "web_sources": merged_sources,
    }

