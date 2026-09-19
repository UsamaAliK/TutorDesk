from langchain_core.tools import tool
from backend.rag.rag_chain import ask_rag
from backend.websearch.lecture import ask_with_search

@tool
def rag_tool(query:str):

    """Answer questions using material uploaded to the workspace."""

    return ask_rag(query)

@tool
def search_tool(query:str):

    """research the web, scrape relevant websites, clean the content, and generate research."""

    return ask_with_search(query)