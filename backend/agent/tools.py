from langchain_core.tools import tool
from backend.rag.vector_store import retrieve_chunks
from backend.websearch.research import research_topic

@tool
def rag_tool(query:str):

    """Return relevant text chunks from material uploaded to the workspace.
    Returns documents and the source files they came from. Does NOT generate content."""

    return retrieve_chunks(query)

@tool
def search_tool(query:str):

    """Research information from the web and return the research text
    together with the source URLs. Does NOT generate content."""

    return research_topic(query)