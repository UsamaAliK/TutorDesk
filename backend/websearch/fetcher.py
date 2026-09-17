from langchain_community.document_loaders import WebBaseLoader


def fetch_page(url:str):
    loader=WebBaseLoader(url)
    document=loader.load()
    return document