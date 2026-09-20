import asyncio
from langchain_postgres import PGVector
from backend.config import settings
from backend.rag.chunking import chunk_docs
from backend.rag.embedding import embeddings
from backend.rag.loader import load_pdf

COLLECTION = "uploads"

SYNC_URL = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg")
ASYNC_URL = settings.DATABASE_URL

EMBED_BATCH_SIZE = 50
MAX_EMBED_IN_FLIGHT = 5


def get_vector_store():
    return PGVector(
        embeddings=embeddings,
        connection=SYNC_URL,
        collection_name=COLLECTION,
        use_jsonb=True,
        create_extension=False,
        async_mode=False,
    )


def get_async_vector_store():
    return PGVector(
        embeddings=embeddings,
        connection=ASYNC_URL,
        collection_name=COLLECTION,
        use_jsonb=True,
        create_extension=False,
        async_mode=True,
    )


async def _embed_batch(texts: list[str], sem: asyncio.Semaphore):
    async with sem:
        return await embeddings.aembed_documents(texts)


async def ingest_pdf(pdf_path: str):
    chunks = chunk_docs(load_pdf(pdf_path))
    if not chunks:
        return None

    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]

    batches = [texts[i:i + EMBED_BATCH_SIZE]
               for i in range(0, len(texts), EMBED_BATCH_SIZE)]
    sem = asyncio.Semaphore(MAX_EMBED_IN_FLIGHT)
    results = await asyncio.gather(*(_embed_batch(b, sem) for b in batches))
    vectors = [v for r in results for v in r]

    store = get_async_vector_store()
    await store.aadd_embeddings(texts, vectors, metadatas=metadatas)
    return store


def retrieve(query: str, k: int = 4):
    return get_vector_store().similarity_search(query, k=k)


def retrieve_chunks(query: str, k: int = 4):
    docs = retrieve(query, k=k)

    chunks = []

    for doc in docs:
        content = doc.page_content.strip()

        if not content:
            continue

        chunks.append({
            "content": content,
            "source": doc.metadata.get("source")
        })

    return chunks