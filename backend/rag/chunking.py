from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings


def chunk_docs(docs):
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    return splitter.split_documents(docs)


