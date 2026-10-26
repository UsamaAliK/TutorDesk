from backend.llm.model import llm
from backend.graph.state import TutorState

GRADE_PROMPT = """\
You are a document relevance grader for an AI teaching assistant.

The user asked:
{query}

Below is the retrieved material that is available to answer this question:

{material}

Decide: is this material SUFFICIENT to generate a complete, accurate
educational answer to the user's question?

Rules:
- "Sufficient" means the material covers the core concepts needed.
  It does not need to be perfect or exhaustive.
- If the material is empty, blank, or clearly off-topic, it is NOT sufficient.
- If the material partially covers the topic but is missing key parts,
  it is NOT sufficient.

Reply with exactly one word: YES or NO
"""


def _format_material(rag_docs: list[dict], web_docs: list[dict]) -> str:
    """Combine RAG and web documents into a single text block for grading."""

    parts = []

    if rag_docs:
        parts.append("=== Uploaded Documents ===")
        for i, doc in enumerate(rag_docs, 1):
            content = doc.get("content", "")
            parts.append(f"[Chunk {i}] {content[:500]}")

    if web_docs:
        parts.append("=== Web Research ===")
        for i, doc in enumerate(web_docs, 1):
            content = doc.get("content", "")
            parts.append(f"[Source {i}] {content[:500]}")

    return "\n\n".join(parts) if parts else "(no material retrieved)"


def grade_documents(state: TutorState) -> dict:
    """Grade whether RAG-retrieved documents are sufficient."""

    material = _format_material(
        state.get("rag_documents", []),
        [],
    )

    message = llm.invoke(GRADE_PROMPT.format(
        query=state["query"],
        material=material,
    ))
    verdict = message.content.strip().upper()

    return {"documents_sufficient": verdict.startswith("YES")}


def grade_combined(state: TutorState) -> dict:
    """Grade whether RAG + web documents together are sufficient."""

    material = _format_material(
        state.get("rag_documents", []),
        state.get("web_documents", []),
    )

    message = llm.invoke(GRADE_PROMPT.format(
        query=state["query"],
        material=material,
    ))
    verdict = message.content.strip().upper()

    return {"documents_sufficient": verdict.startswith("YES")}

