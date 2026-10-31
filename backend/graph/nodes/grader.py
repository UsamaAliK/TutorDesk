from backend.graph.state import GenerationState
from backend.llm.model import llm

GRADE_PROMPT = """\
You are an educational curriculum evaluator for TutorDesk.
An educator has requested to generate a {material_type} on:
Subject: {subject}
Topic: {topic}
Target Educational Level: {educational_level}

Below is the retrieved source material:
{material_text}

Task: Evaluate if this retrieved material provides SUFFICIENT factual information,
core concepts, and context to generate a rigorous, grounded, high-quality {material_type}.

Evaluation Criteria:
- YES: The material covers the essential concepts and details needed for the topic at this grade level.
- NO: The material is empty, superficial, irrelevant, or lacks key core facts needed to construct the educational content.

Respond with ONLY ONE WORD: YES or NO.
"""


def _format_context(rag_docs: list, web_docs: list) -> str:
    parts = []
    if rag_docs:
        parts.append("=== Uploaded Document Excerpts ===")
        for i, d in enumerate(rag_docs[:5], 1):
            parts.append(f"[{i}] {d.get('content', '')[:600]}")
    if web_docs:
        parts.append("=== Web Research Excerpts ===")
        for i, d in enumerate(web_docs[:4], 1):
            parts.append(f"[{i}] {d.get('content', '')[:600]}")
    return "\n\n".join(parts) if parts else "(No substantive text found)"


def grade_rag_material(state: GenerationState) -> dict:
    """Grades whether retrieved uploaded documents are sufficient alone."""
    rag_docs = state.get("rag_documents", [])
    if not rag_docs:
        return {"documents_sufficient": False, "grader_rationale": "No uploaded document chunks found."}

    material_text = _format_context(rag_docs, [])
    prompt = GRADE_PROMPT.format(
        material_type=state.get("material_type", "educational content"),
        subject=state.get("subject", ""),
        topic=state.get("topic", ""),
        educational_level=state.get("educational_level", "General"),
        material_text=material_text,
    )

    try:
        response = llm.invoke(prompt)
        verdict = response.content.strip().upper()
        is_sufficient = verdict.startswith("YES")
    except Exception:
        # Fallback to len check if grader call fails
        is_sufficient = len(rag_docs) >= 2

    return {
        "documents_sufficient": is_sufficient,
        "grader_rationale": "RAG material graded as sufficient." if is_sufficient else "RAG material insufficient or incomplete."
    }


def grade_combined_material(state: GenerationState) -> dict:
    """Grades whether PDF + Web documents together are sufficient."""
    rag_docs = state.get("rag_documents", [])
    web_docs = state.get("web_documents", [])

    if not rag_docs and not web_docs:
        return {"documents_sufficient": False, "grader_rationale": "No research or document data available."}

    material_text = _format_context(rag_docs, web_docs)
    prompt = GRADE_PROMPT.format(
        material_type=state.get("material_type", "educational content"),
        subject=state.get("subject", ""),
        topic=state.get("topic", ""),
        educational_level=state.get("educational_level", "General"),
        material_text=material_text,
    )

    try:
        response = llm.invoke(prompt)
        verdict = response.content.strip().upper()
        is_sufficient = verdict.startswith("YES")
    except Exception:
        is_sufficient = len(rag_docs) + len(web_docs) >= 1

    return {
        "documents_sufficient": is_sufficient,
        "grader_rationale": "Combined material graded as sufficient." if is_sufficient else "Combined material still lacks depth."
    }

