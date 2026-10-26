from typing import TypedDict


class TutorState(TypedDict, total=False):
    # ── Input ──
    query: str
    user_id: int

    # ── Classification ──
    query_type: str                    # "rag" | "web" | "greeting"

    # ── Retrieved material ──
    rag_documents: list[dict]          # chunks from the vector store
    web_documents: list[dict]          # fetched web page contents
    rag_sources: list[str]             # PDF / file names
    web_sources: list[str]             # URLs

    # ── Grading / iteration ──
    documents_sufficient: bool         # grader verdict
    refined_query: str                 # rewritten search query for retry
    retry_count: int                   # web research attempts so far
    max_retries: int                   # cap (from settings)

    # ── Output ──
    answer: str                        # final generated text
    all_sources: list[str]             # merged sources for the response

