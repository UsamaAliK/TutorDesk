import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_postgres import PGVector
from backend.config import settings
from backend.rag.chunking import chunk_docs
from backend.rag.embedding import embeddings
from backend.rag.loader import load_pdf

COLLECTION = settings.VECTOR_COLLECTION

SYNC_URL = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg")
ASYNC_URL = settings.DATABASE_URL

EMBED_BATCH_SIZE = settings.EMBED_BATCH_SIZE
MAX_EMBED_IN_FLIGHT = settings.MAX_EMBED_IN_FLIGHT
EMBEDDING_DIMENSIONS = settings.EMBEDDING_DIMENSIONS


def get_vector_store():
    return PGVector(
        embeddings=embeddings,
        connection=SYNC_URL,
        collection_name=COLLECTION,
        use_jsonb=True,
        embedding_length=EMBEDDING_DIMENSIONS,
        create_extension=False,
        async_mode=False,
    )


def get_async_vector_store():
    return PGVector(
        embeddings=embeddings,
        connection=ASYNC_URL,
        collection_name=COLLECTION,
        use_jsonb=True,
        embedding_length=EMBEDDING_DIMENSIONS,
        create_extension=False,
        async_mode=True,
    )


async def _embed_batch(texts: list[str], sem: asyncio.Semaphore):
    async with sem:
        return await embeddings.aembed_documents(texts)


async def ingest_pdf(pdf_path: str, user_id: int, original_filename: str = None):
    chunks = chunk_docs(load_pdf(pdf_path))
    if not chunks:
        return None

    filename = original_filename or os.path.basename(pdf_path)
    texts = [c.page_content for c in chunks]
    metadatas = [
        {
            **c.metadata,
            "source": filename,
            "filename": filename,
            "user_id": str(user_id),
        }
        for c in chunks
    ]

    batches = [texts[i:i + EMBED_BATCH_SIZE]
               for i in range(0, len(texts), EMBED_BATCH_SIZE)]
    sem = asyncio.Semaphore(MAX_EMBED_IN_FLIGHT)
    results = await asyncio.gather(*(_embed_batch(b, sem) for b in batches))
    vectors = [v for r in results for v in r]

    store = get_async_vector_store()
    await store.aadd_embeddings(texts, vectors, metadatas=metadatas)
    return store


async def delete_pdf_embeddings(user_id: int, filename: str, db: AsyncSession):
    """Delete all embeddings associated with this file for the user."""
    await db.execute(
        text(
            """
            DELETE FROM langchain_pg_embedding
            WHERE cmetadata->>'user_id' = :user_id
              AND (
                  cmetadata->>'source' = :filename
                  OR cmetadata->>'filename' = :filename
                  OR cmetadata->>'source' LIKE :pattern
              )
            """
        ),
        {"user_id": str(user_id), "filename": filename, "pattern": f"%{filename}"},
    )
    await db.commit()


def retrieve(query: str, k: int = None, user_id: int = None):
    return get_vector_store().similarity_search(
        query, k=k or settings.RETRIEVE_K, filter={"user_id": str(user_id)}
    )


def retrieve_chunks(query: str, k: int = None, user_id: int = None):
    docs = retrieve(query, k=k, user_id=user_id)

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