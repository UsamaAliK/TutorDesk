from backend.graph.state import GenerationState
from backend.llm.model import llm

REFINE_PROMPT = """\
You are an expert educational research assistant.
The educator requested educational material on:
Subject: {subject}
Topic: {topic}
Level: {educational_level}

The previous search did not gather sufficient depth or concepts.
Here is a summary of snippets found so far:
{snippets}

Task: Write a NEW, highly targeted search query (3-6 words) that will find
the missing core definitions, foundational theory, or specific examples for this topic.
Return ONLY the search query text without quotation marks or explanation.
"""


def refine_query(state: GenerationState) -> dict:
    """Rewrites the web query for an iterative research retry."""
    web_docs = state.get("web_documents", [])
    rag_docs = state.get("rag_documents", [])
    all_docs = rag_docs + web_docs

    snippets = "\n---\n".join(d.get("content", "")[:250] for d in all_docs[:3]) if all_docs else "(None)"

    prompt = REFINE_PROMPT.format(
        subject=state.get("subject", ""),
        topic=state.get("topic", ""),
        educational_level=state.get("educational_level", "General"),
        snippets=snippets,
    )

    try:
        response = llm.invoke(prompt)
        refined = response.content.strip().replace('"', '')
    except Exception:
        refined = f"{state.get('subject')} {state.get('topic')} core concepts"

    return {
        "refined_query": refined,
        "retry_count": state.get("retry_count", 0) + 1,
    }

