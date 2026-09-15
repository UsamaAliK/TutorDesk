from langchain_chroma import Chroma
from backend.rag.embedding import embeddings
from backend.rag.loader import load_pdf
from backend.rag.chunking import chunk_docs

PERSIST_DIR = "backend/data/chroma_db"


def create_vector_store(pdf_path: str):
    docs = load_pdf(pdf_path)
    chunks = chunk_docs(docs)
    store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
    )
    return store


def get_vector_store():
    return Chroma(
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )


def retrieve(query: str, k: int = 4):
    return get_vector_store().similarity_search(query, k=k)