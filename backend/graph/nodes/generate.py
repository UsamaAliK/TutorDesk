from backend.llm.model import llm
from backend.graph.state import TutorState

GENERATE_PROMPT = """\
You are TutorDesk, an AI teaching assistant.

Your job is to help teachers create educational content such as:
- Lesson plans
- MCQs
- Quizzes
- Explanations
- Assignments
- Summaries
- Study material

GROUNDING POLICY — CRITICAL:
  You must NEVER answer from your own knowledge, memory, or training data.
  Base ALL generated content strictly on the material provided below.
  Do not add facts, examples, or numbers that are not in the material.
  Always include the relevant source file names or URLs at the end of
  your response.

Content generation rules:
- Generate exactly the type of content the user asks for.
- If the user requests a specific number of questions or items, generate
  exactly that number.
- If the user specifies a difficulty level, follow it.
- If the user specifies a grade level, adapt vocabulary, difficulty,
  examples, activities, and explanations to that level.
- If the user does NOT specify a grade or level, default to a BEGINNER
  level appropriate for a general high-school student with no prior
  knowledge of the topic.
- Start from foundational definitions and plain-language explanations.

{partial_notice}

User's question:
{query}

Available material:
{material}

Sources:
{sources}
"""

PARTIAL_NOTICE = """\
NOTE: The available material does not fully cover the user's question.
Generate the best answer you can from what IS available, and explicitly
state at the end which parts of the question could not be answered due
to insufficient source material. Do NOT make up information to fill gaps.
"""


def _build_material(state: TutorState) -> tuple[str, list[str]]:
    """Merge RAG and web documents into a single material block and source list."""

    parts = []
    all_sources = []

    rag_docs = state.get("rag_documents", [])
    if rag_docs:
        parts.append("=== From Uploaded Documents ===")
        for i, doc in enumerate(rag_docs, 1):
            parts.append(f"[Chunk {i}] {doc.get('content', '')}")

    rag_sources = state.get("rag_sources", [])
    for s in rag_sources:
        if s not in all_sources:
            all_sources.append(s)

    web_docs = state.get("web_documents", [])
    if web_docs:
        parts.append("=== From Web Research ===")
        for i, doc in enumerate(web_docs, 1):
            parts.append(f"[Source {i}] {doc.get('content', '')}")

    web_sources = state.get("web_sources", [])
    for s in web_sources:
        if s not in all_sources:
            all_sources.append(s)

    material = "\n\n".join(parts) if parts else "(no material available)"
    return material, all_sources


def generate(state: TutorState) -> dict:
    """Generate the final educational content from sufficient material."""

    material, all_sources = _build_material(state)

    message = llm.invoke(GENERATE_PROMPT.format(
        query=state["query"],
        material=material,
        sources="\n".join(all_sources) if all_sources else "(none)",
        partial_notice="",
    ))

    return {
        "answer": message.content.strip(),
        "all_sources": all_sources,
    }


def generate_partial(state: TutorState) -> dict:
    """Generate the best answer possible when material is insufficient."""

    material, all_sources = _build_material(state)

    message = llm.invoke(GENERATE_PROMPT.format(
        query=state["query"],
        material=material,
        sources="\n".join(all_sources) if all_sources else "(none)",
        partial_notice=PARTIAL_NOTICE,
    ))

    return {
        "answer": message.content.strip(),
        "all_sources": all_sources,
    }

