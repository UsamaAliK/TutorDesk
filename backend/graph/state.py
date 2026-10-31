from typing import Any, Dict, List, Optional, TypedDict


class GenerationState(TypedDict, total=False):
    # Core request context
    subject: str
    topic: str
    material_type: str                  # "lesson" | "quiz" | "assignment"
    educational_level: str
    difficulty: Optional[str]
    source_mode: str                    # "material_only" | "web_search" | "combined"
    user_id: int
    selected_document_id: Optional[int]
    selected_filename: Optional[str]
    query: str                          # topic + subject search target

    # Retrieved materials
    has_uploaded_material: bool
    rag_documents: List[Dict[str, Any]]
    rag_sources: List[str]
    web_documents: List[Dict[str, Any]]
    web_sources: List[str]
    all_sources: List[str]

    # Quality check & retry state
    documents_sufficient: bool
    grader_rationale: Optional[str]
    refined_query: Optional[str]
    retry_count: int
    max_retries: int

    # Generation configuration & structured payload
    generation_spec: Dict[str, Any]
    content_json: Dict[str, Any]
    error: Optional[str]

