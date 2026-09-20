from langchain_tavily import TavilySearch

from backend.config import settings

search_tool=TavilySearch(
    max_results=settings.WEB_SEARCH_MAX_RESULTS
)

def web_search(query:str):
    return search_tool.invoke({
        "query":query
    })