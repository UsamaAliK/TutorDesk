from backend.llm.model import llm
from backend.graph.state import TutorState

REFINE_PROMPT = """\
You are a search query optimizer for an AI teaching assistant.

The user asked:
{query}

A web search was performed but the results were not sufficient to answer
the question properly. Here is a summary of what was already found:

{existing_material}

Rewrite the search query to find DIFFERENT, more specific, or more
relevant information that fills the gaps. Return ONLY the new search
query — nothing else.
"""


def refine_query(state: TutorState) -> dict:
    """Rewrite the search query for a better web research retry."""

    existing_snippets = []
    for doc in state.get("web_documents", []):
        content = doc.get("content", "")
        existing_snippets.append(content[:300])

    existing_material = (
        "\n---\n".join(existing_snippets) if existing_snippets
        else "(nothing useful was found)"
    )

    message = llm.invoke(REFINE_PROMPT.format(
        query=state["query"],
        existing_material=existing_material,
    ))

    return {
        "refined_query": message.content.strip(),
        "retry_count": state.get("retry_count", 0) + 1,
    }

