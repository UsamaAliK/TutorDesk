from langchain_core.tools import tool
from backend.rag.rag_chain import ask_rag
from backend.websearch.lecture import ask_with_search

@tool
def rag_tool(query:str):

    """Answer questions using material uploaded to the workspace."""

    return ask_rag(query)

@tool
def lesson_plan_tool(query:str):

    """Research a topic on the web and create a complete, classroom-ready lesson plan.
    Returns the lesson plan along with the source URLs used."""

    return ask_with_search(query)