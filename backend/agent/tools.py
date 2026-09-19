from langchain_core.tools import tool
from backend.rag.rag_chain import ask_rag
from backend.websearch.lecture import ask_with_search
from backend.models.llm import lessonmodel
from backend.prompts.lesson import lessonprompt

@tool
def rag_tool(query:str):
    
    """Answer questions using material uploaded to the workspace."""

    return ask_rag(query)

@tool
def search_tool(query:str):

    """Search the web, scrape relevant websites, clean the content, and generate research."""

    return ask_with_search(query)

@tool
def lesson_plan_tool(query):

    """Create a lesson plan for a teaching topic."""

    chain=lessonprompt|lessonmodel
    response = chain.invoke({"request": query})
    return response.model_dump()