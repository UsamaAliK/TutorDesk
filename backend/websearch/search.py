from langchain_tavily import TavilySearch

search_tool=TavilySearch(
    max_results=5
)

def web_search(query:str):
    return search_tool.invoke({
        "query":query
    })