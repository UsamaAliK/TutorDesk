import trafilatura
from langchain_core.documents import Document


def fetch_page(url:str):
    html=trafilatura.fetch_url(url)
    text=trafilatura.extract(html)
    if not text:
        return []
    return [Document(page_content=text, metadata={"source": url})]
