from langchain_core.tools import tool
from backend.rag.rag_chain import ask_rag
from backend.websearch.lecture import ask_with_source

@tool
def rag_tool(query:str):

    """Answer questions using material uploaded to the workspace."""

    return ask_rag(query)

@tool
def lesson_plan_tool(query:str, source: str = "auto"):

    """Research a topic and create a complete, classroom-ready lesson plan.
    Returns the lesson plan along with the source URLs used.
    source options: "web" for web research only, "rag" for uploaded material only,
    "both" to combine both, "auto" to decide automatically."""

    return ask_with_source(query, source)