from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from backend.rag.vector_store import retrieve_chunks
from backend.websearch.research import research_topic

@tool
def rag_tool(query:str, config: RunnableConfig):
    """
    Retrieve information ONLY from the user's uploaded documents.

    Use this tool when the user explicitly wants an answer based on
    their own notes, PDFs, slides, files, course material, chapters,
    or uploaded documents (e.g., "in my notes", "the PDF", "my material",
    "the file I uploaded").

    Do NOT use this tool for web research or current information.
    Do NOT use this tool when the question is not about the user's uploaded material.
    Do NOT use this tool for greetings ("hi", "thanks") -- acknowledge those briefly without a tool.
    """

    user_id = config.get("configurable", {}).get("user_id")
    return retrieve_chunks(query, user_id=user_id)

@tool
def search_tool(query:str):
    """
    Search the live web and retrieve information from external webpages.

    This is the default grounding tool. Every substantive request that is
    NOT about the user's uploaded documents must be grounded here before
    answering (including lesson plans, quizzes, MCQs, explanations, and
    summaries about general topics).

    Use this tool when the user asks for web research, online research,
    current/latest information, external sources, citations, or any topic
    that is not clearly answered by their uploaded documents.

    Do NOT use this tool when the user explicitly wants information
    from their uploaded documents (use rag_tool).
    Do NOT use this tool for greetings ("hi", "thanks") -- acknowledge those briefly without a tool.
    """

    return research_topic(query)