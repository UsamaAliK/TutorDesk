from langgraph.graph import StateGraph, END

from backend.graph.state import TutorState
from backend.graph.nodes.classify import classify_query
from backend.graph.nodes.acknowledge import acknowledge
from backend.graph.nodes.retrieve import rag_retrieve
from backend.graph.nodes.grader import grade_documents, grade_combined
from backend.graph.nodes.research import web_research
from backend.graph.nodes.refine import refine_query
from backend.graph.nodes.generate import generate, generate_partial


# ── Routing functions for conditional edges ──────────────────────────

def route_after_classify(state: TutorState) -> str:
    """START → classify → ?"""
    query_type = state.get("query_type", "web")
    if query_type == "greeting":
        return "acknowledge"
    if query_type == "rag":
        return "rag_retrieve"
    return "web_research"


def route_after_grade_rag(state: TutorState) -> str:
    """rag_retrieve → grade_documents → ?"""
    if state.get("documents_sufficient"):
        return "generate"
    return "web_research"


def route_after_grade_combined(state: TutorState) -> str:
    """web_research → grade_combined → ?"""
    if state.get("documents_sufficient"):
        return "generate"
    if state.get("retry_count", 0) < state.get("max_retries", 2):
        return "refine_query"
    return "generate_partial"


# ── Build the graph ──────────────────────────────────────────────────

def build_graph():
    g = StateGraph(TutorState)

    # Add nodes
    g.add_node("classify", classify_query)
    g.add_node("acknowledge", acknowledge)
    g.add_node("rag_retrieve", rag_retrieve)
    g.add_node("grade_documents", grade_documents)
    g.add_node("web_research", web_research)
    g.add_node("grade_combined", grade_combined)
    g.add_node("refine_query", refine_query)
    g.add_node("generate", generate)
    g.add_node("generate_partial", generate_partial)

    # Entry point
    g.set_entry_point("classify")

    # classify → (greeting | rag_retrieve | web_research)
    g.add_conditional_edges("classify", route_after_classify, {
        "acknowledge": "acknowledge",
        "rag_retrieve": "rag_retrieve",
        "web_research": "web_research",
    })

    # acknowledge → END
    g.add_edge("acknowledge", END)

    # rag_retrieve → grade_documents
    g.add_edge("rag_retrieve", "grade_documents")

    # grade_documents → (generate | web_research)
    g.add_conditional_edges("grade_documents", route_after_grade_rag, {
        "generate": "generate",
        "web_research": "web_research",
    })

    # web_research → grade_combined
    g.add_edge("web_research", "grade_combined")

    # grade_combined → (generate | refine_query | generate_partial)
    g.add_conditional_edges("grade_combined", route_after_grade_combined, {
        "generate": "generate",
        "refine_query": "refine_query",
        "generate_partial": "generate_partial",
    })

    # refine_query → web_research  (the retry loop)
    g.add_edge("refine_query", "web_research")

    # generate → END
    g.add_edge("generate", END)

    # generate_partial → END
    g.add_edge("generate_partial", END)

    return g.compile()


# Compiled graph instance, ready to .invoke()
graph = build_graph()

