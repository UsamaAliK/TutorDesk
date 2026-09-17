from backend.websearch.search import web_search
from backend.websearch.fetcher import fetch_page
from backend.websearch.processed import process_results,clean_documents


def research_topic(query:str):

    search_results=web_search(query)

    processed_result=process_results(search_results)
    document=[]

    for result in processed_result[:3]:
        
        fetch_doc=fetch_page(result["url"])

        document.extend(fetch_doc)
    cleaned_documents = clean_documents(document)
    return cleaned_documents

