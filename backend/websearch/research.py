from backend.websearch.search import web_search
from backend.websearch.fetcher import fetch_page
from backend.websearch.processed import process_results,is_valid_doc,clean_text


def search_topic(query: str):

    search_results = web_search(query)

    processed_results = process_results(search_results)

    documents = []

    for result in processed_results[:3]:

        url = result["url"]

        if "youtube.com" in url or "youtu.be" in url:
            continue

        document = fetch_page(url)

        if not document:
            continue

        content = clean_text(document.page_content)

        if not is_valid_doc(content):
            continue

        documents.append({
            "content": content,
            "source": document.metadata.get("source")
        })

    return documents