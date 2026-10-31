from langgraph.graph import StateGraph, END
from backend.graph.state import GenerationState
from backend.graph.nodes.retrieve import retrieve_material
from backend.graph.nodes.grader import grade_rag_material, grade_combined_material
from backend.graph.nodes.research import web_research
from backend.graph.nodes.refine import refine_query
from backend.graph.nodes.generate import generate_material


# ── Routing Functions ────────────────────────────────────────────────

def route_entry(state: GenerationState) -> str:
    """Entry point router based on source_mode and material presence."""
    source_mode = state.get("source_mode", "web_search")

    # If material only or combined, retrieve uploaded material first
    if source_mode in ("material_only", "combined"):
        return "retrieve_material"

    # Default to web research
    return "web_research"


def route_after_rag_grade(state: GenerationState) -> str:
    """Decides next step after grading uploaded material."""
    source_mode = state.get("source_mode", "web_search")
    is_sufficient = state.get("documents_sufficient", False)

    # In material-only mode, we strictly respect user's constraint
    if source_mode == "material_only":
        return "generate_material"

    # In combined mode, or if RAG was insufficient, augment with web research
    return "web_research"


def route_after_web_grade(state: GenerationState) -> str:
    """Decides if web research is sufficient or if query should be refined."""
    is_sufficient = state.get("documents_sufficient", False)
    retries = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if is_sufficient or retries >= max_retries:
        return "generate_material"

    return "refine_query"


# ── Graph Builder ────────────────────────────────────────────────────

def build_generation_graph():
    builder = StateGraph(GenerationState)

    # 1. Add processing nodes
    builder.add_node("retrieve_material", retrieve_material)
    builder.add_node("grade_rag_material", grade_rag_material)
    builder.add_node("web_research", web_research)
    builder.add_node("grade_combined_material", grade_combined_material)
    builder.add_node("refine_query", refine_query)
    builder.add_node("generate_material", generate_material)

    # 2. Add entry conditional edge
    builder.set_conditional_entry_point(
        route_entry,
        {
            "retrieve_material": "retrieve_material",
            "web_research": "web_research",
        }
    )

    # 3. retrieve_material -> grade_rag_material
    builder.add_edge("retrieve_material", "grade_rag_material")

    # 4. grade_rag_material -> (generate_material | web_research)
    builder.add_conditional_edges(
        "grade_rag_material",
        route_after_rag_grade,
        {
            "generate_material": "generate_material",
            "web_research": "web_research",
        }
    )

    # 5. web_research -> grade_combined_material
    builder.add_edge("web_research", "grade_combined_material")

    # 6. grade_combined_material -> (generate_material | refine_query)
    builder.add_conditional_edges(
        "grade_combined_material",
        route_after_web_grade,
        {
            "generate_material": "generate_material",
            "refine_query": "refine_query",
        }
    )

    # 7. refine_query -> web_research (Iterative loop back)
    builder.add_edge("refine_query", "web_research")

    # 8. generate_material -> END
    builder.add_edge("generate_material", END)

    return builder.compile()


# Compiled LangGraph Workflow Instance
generation_graph = build_generation_graph()

