import trafilatura
from langchain_core.documents import Document

def fetch_page(url: str):

    html = trafilatura.fetch_url(url)

    if not html:
        return None

    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_links=False,
    )

    if not text:
        return None

    return Document(
        page_content=text,
        metadata={"source": url}
    )