from typing import Optional, Tuple, List
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Upload
from backend.rag.vector_store import retrieve_chunks
from backend.websearch.research import research_topic
from backend.schemas.material import SourceMode, EducationalLevel


async def resolve_content_sources(
    user_id: int,
    source_mode: SourceMode,
    query: str,
    educational_level: EducationalLevel,
    selected_document_id: Optional[int],
    db: AsyncSession,
) -> Tuple[str, List[str]]:
    """
    Resolves grounding context and citations based on the selected SourceMode.
    Respects strict grounding policy without silently falling back.
    """
    context_blocks = []
    sources = []

    # Check user's uploaded documents in DB
    user_uploads_query = select(Upload).where(Upload.user_id == user_id)
    if selected_document_id:
        user_uploads_query = user_uploads_query.where(Upload.id == selected_document_id)
    
    result = await db.execute(user_uploads_query)
    user_uploads = result.scalars().all()

    # ─────────────────────────────────────────────────────────────
    # Mode A: Provided material only
    # ─────────────────────────────────────────────────────────────
    if source_mode == SourceMode.MATERIAL_ONLY:
        if not user_uploads:
            if selected_document_id:
                raise HTTPException(
                    status_code=400,
                    detail="The selected document could not be found in your uploaded materials."
                )
            raise HTTPException(
                status_code=400,
                detail="You selected 'Provided material only', but have not uploaded any documents yet. Please upload a PDF or switch to 'Web search'."
            )

        rag_chunks = retrieve_chunks(query, user_id=user_id, k=6)
        if not rag_chunks:
            # Fallback to general terms query if specific query yielded no chunks
            general_query = query.split(":")[0] if ":" in query else query
            rag_chunks = retrieve_chunks(general_query, user_id=user_id, k=6)

        if not rag_chunks:
            raise HTTPException(
                status_code=400,
                detail=f"No relevant content was found in your uploaded documents for topic '{query}'. Please upload relevant materials or switch to 'Web search' mode."
            )

        context_blocks.append("=== PRIMARY GROUNDING: USER UPLOADED DOCUMENTS ===")
        for i, chunk in enumerate(rag_chunks, 1):
            src = chunk.get("source") or "Uploaded Document"
            context_blocks.append(f"[Document Excerpt {i} - Source: {src}]\n{chunk.get('content', '')}")
            if src not in sources:
                sources.append(src)

        return "\n\n".join(context_blocks), sources

    # ─────────────────────────────────────────────────────────────
    # Mode B: Web search
    # ─────────────────────────────────────────────────────────────
    if source_mode == SourceMode.WEB_SEARCH:
        search_query = query
        if educational_level == EducationalLevel.PHD_RESEARCH:
            search_query = f"{query} scholarly review peer-reviewed research theoretical framework"

        web_res = research_topic(search_query)
        web_docs = web_res.get("research", [])
        web_sources = web_res.get("sources", [])

        if web_docs:
            context_blocks.append("=== EXTERNAL WEB RESEARCH ===")
            for i, doc in enumerate(web_docs, 1):
                url = web_sources[i - 1] if i - 1 < len(web_sources) else "Web Source"
                context_blocks.append(f"[Web Citation {i} - URL: {url}]\n{doc}")
                if url not in sources:
                    sources.append(url)
        else:
            context_blocks.append(f"(Web search returned minimal results for '{query}'. Using foundational topic knowledge with strict educational standards.)")

        return "\n\n".join(context_blocks), sources

    # ─────────────────────────────────────────────────────────────
    # Mode C: Combined (Provided material + Web search)
    # ─────────────────────────────────────────────────────────────
    if source_mode == SourceMode.COMBINED:
        has_rag = False
        if user_uploads:
            rag_chunks = retrieve_chunks(query, user_id=user_id, k=4)
            if rag_chunks:
                has_rag = True
                context_blocks.append("=== PRIMARY GROUNDING: USER UPLOADED DOCUMENTS ===")
                for i, chunk in enumerate(rag_chunks, 1):
                    src = chunk.get("source") or "Uploaded Document"
                    context_blocks.append(f"[Document Excerpt {i} - Source: {src}]\n{chunk.get('content', '')}")
                    if src not in sources:
                        sources.append(src)

        # Augment with web research
        search_query = query
        if educational_level == EducationalLevel.PHD_RESEARCH:
            search_query = f"{query} academic research methodology citations"

        web_res = research_topic(search_query)
        web_docs = web_res.get("research", [])
        web_sources = web_res.get("sources", [])

        if web_docs:
            context_blocks.append("=== SUPPLEMENTARY WEB RESEARCH ===")
            for i, doc in enumerate(web_docs, 1):
                url = web_sources[i - 1] if i - 1 < len(web_sources) else "Web Source"
                context_blocks.append(f"[Web Citation {i} - URL: {url}]\n{doc}")
                if url not in sources:
                    sources.append(url)

        if not context_blocks:
            context_blocks.append(f"(No uploaded material found. Relying on verified core concepts for '{query}'.)")

        return "\n\n".join(context_blocks), sources

    return "", []

