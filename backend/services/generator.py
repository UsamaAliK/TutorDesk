import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.model import llm
from backend.db.models import Material, Upload
from backend.graph.graph import generation_graph
from backend.graph.state import GenerationState
from backend.schemas.material import (
    LessonGenerateRequest,
    QuizGenerateRequest,
    AssignmentGenerateRequest,
    RegenerateItemRequest,
    EducationalLevel,
    SourceMode,
)


def _extract_json(text: str) -> Dict[str, Any]:
    """Robustly extracts JSON object from LLM response text."""
    clean = text.strip()
    # Remove markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
    if fence_match:
        clean = fence_match.group(1).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try extracting first {...} block
        brace_match = re.search(r"\{[\s\S]*\}", clean)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail="Failed to generate structured educational content. Please try again with adjusted instructions."
        )


async def _resolve_selected_upload(
    user_id: int,
    source_mode: SourceMode,
    selected_document_id: Optional[int],
    db: AsyncSession,
) -> Optional[Upload]:
    """Validates user's document selection for grounded generation."""
    if source_mode in (SourceMode.MATERIAL_ONLY, SourceMode.COMBINED) and not selected_document_id:
        raise HTTPException(
            status_code=400,
            detail="Choose a PDF for this material or select web research only.",
        )
    if selected_document_id:
        result = await db.execute(
            select(Upload).where(Upload.id == selected_document_id, Upload.user_id == user_id)
        )
        upload = result.scalar_one_or_none()
        if not upload:
            raise HTTPException(
                status_code=400,
                detail="The selected PDF is no longer available in your uploaded materials."
            )
        return upload
    return None


# ─────────────────────────────────────────────────────────────────────
# 1. Lesson Generator (Iterative LangGraph Workflow)
# ─────────────────────────────────────────────────────────────────────

async def generate_lesson(request: LessonGenerateRequest, user_id: int, db: AsyncSession) -> Material:
    upload = await _resolve_selected_upload(
        user_id=user_id,
        source_mode=request.source_mode,
        selected_document_id=request.selected_document_id,
        db=db,
    )

    state: GenerationState = {
        "subject": request.subject,
        "topic": request.topic,
        "material_type": "lesson",
        "educational_level": request.educational_level.value,
        "source_mode": request.source_mode.value,
        "user_id": user_id,
        "selected_document_id": upload.id if upload else None,
        "selected_filename": upload.filename if upload else None,
        "query": f"{request.subject}: {request.topic}",
        "retry_count": 0,
        "max_retries": 2,
        "generation_spec": {
            "duration_minutes": request.duration_minutes,
            "teaching_style": request.teaching_style,
            "learning_objectives": request.learning_objectives,
            "curriculum": request.curriculum,
            "additional_instructions": request.additional_instructions,
            "language": request.language,
        },
    }

    final_state = await asyncio.to_thread(generation_graph.invoke, state)
    data = final_state.get("content_json")
    if not data:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate lesson content via LangGraph. Please adjust instructions and try again."
        )

    title = data.get("title") or f"Lesson: {request.topic}"
    material = Material(
        user_id=user_id,
        type="lesson",
        title=title,
        subject=request.subject,
        topic=request.topic,
        educational_level=request.educational_level.value,
        difficulty="Standard",
        source_mode=request.source_mode.value,
        content_json=data,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


# ─────────────────────────────────────────────────────────────────────
# 2. Quiz Generator (Section A: MCQs, Section B: Written Questions)
# ─────────────────────────────────────────────────────────────────────

async def generate_quiz(request: QuizGenerateRequest, user_id: int, db: AsyncSession) -> Material:
    upload = await _resolve_selected_upload(
        user_id=user_id,
        source_mode=request.source_mode,
        selected_document_id=request.selected_document_id,
        db=db,
    )

    state: GenerationState = {
        "subject": request.subject,
        "topic": request.topic,
        "material_type": "quiz",
        "educational_level": request.educational_level.value,
        "difficulty": request.difficulty.value,
        "source_mode": request.source_mode.value,
        "user_id": user_id,
        "selected_document_id": upload.id if upload else None,
        "selected_filename": upload.filename if upload else None,
        "query": f"{request.subject}: {request.topic}",
        "retry_count": 0,
        "max_retries": 2,
        "generation_spec": {
            "num_mcqs": request.num_mcqs,
            "num_short_answer": request.num_short_answer,
            "num_long_answer": request.num_long_answer,
            "mcq_options_count": request.mcq_options_count,
            "time_limit_minutes": request.time_limit_minutes,
            "total_marks": request.total_marks,
            "additional_instructions": request.additional_instructions,
            "learning_objectives": request.learning_objectives,
        },
    }

    final_state = await asyncio.to_thread(generation_graph.invoke, state)
    data = final_state.get("content_json")
    if not data:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate quiz content via LangGraph. Please adjust instructions and try again."
        )

    # Harmonize sections and backward-compatible flat list
    mcq_sec = data.get("mcq_section") or {}
    mcqs = mcq_sec.get("mcqs", [])
    q_sec = data.get("questions_section") or {}
    written_questions = q_sec.get("questions", [])

    if not mcqs and not written_questions and "questions" in data:
        flat = data.get("questions", [])
        mcqs = [q for q in flat if q.get("type") == "mcq" or q.get("options")]
        written_questions = [q for q in flat if q not in mcqs]
        data["mcq_section"] = {
            "title": "Section A: Multiple Choice Questions (MCQs)",
            "instructions": "Select the single best answer for each question.",
            "total_mcqs": len(mcqs),
            "mcqs": mcqs,
        }
        data["questions_section"] = {
            "title": "Section B: Short & Long Answer Questions",
            "instructions": "Write detailed, well-reasoned answers to the questions below.",
            "total_questions": len(written_questions),
            "questions": written_questions,
        }

    # Ensure flat questions array exists for backward compatibility
    data["questions"] = mcqs + written_questions

    # Enforce marks consistency if specified
    all_items = mcqs + written_questions
    if request.total_marks:
        computed_marks = sum(q.get("marks", 1) for q in all_items)
        data["total_marks"] = computed_marks or request.total_marks

    title = data.get("title") or f"Quiz: {request.topic}"
    material = Material(
        user_id=user_id,
        type="quiz",
        title=title,
        subject=request.subject,
        topic=request.topic,
        educational_level=request.educational_level.value,
        difficulty=request.difficulty.value,
        source_mode=request.source_mode.value,
        content_json=data,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


# ─────────────────────────────────────────────────────────────────────
# 3. Assignment Generator (LangGraph Iterative Workflow)
# ─────────────────────────────────────────────────────────────────────

async def generate_assignment(request: AssignmentGenerateRequest, user_id: int, db: AsyncSession) -> Material:
    upload = await _resolve_selected_upload(
        user_id=user_id,
        source_mode=request.source_mode,
        selected_document_id=request.selected_document_id,
        db=db,
    )

    state: GenerationState = {
        "subject": request.subject,
        "topic": request.topic,
        "material_type": "assignment",
        "educational_level": request.educational_level.value,
        "difficulty": request.difficulty.value,
        "source_mode": request.source_mode.value,
        "user_id": user_id,
        "selected_document_id": upload.id if upload else None,
        "selected_filename": upload.filename if upload else None,
        "query": f"{request.subject}: {request.topic}",
        "retry_count": 0,
        "max_retries": 2,
        "generation_spec": {
            "num_mcqs": request.num_mcqs,
            "total_tasks": request.total_tasks,
            "task_types": request.task_types,
            "total_marks": request.total_marks,
            "deadline_days": request.deadline_days,
            "instructions_for_students": request.instructions_for_students,
            "include_rubric": request.include_rubric,
            "include_model_answers": request.include_model_answers,
            "additional_instructions": request.additional_instructions,
        },
    }

    final_state = await asyncio.to_thread(generation_graph.invoke, state)
    data = final_state.get("content_json")
    if not data:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate assignment content via LangGraph. Please adjust instructions and try again."
        )

    title = data.get("title") or f"Assignment: {request.topic}"
    material = Material(
        user_id=user_id,
        type="assignment",
        title=title,
        subject=request.subject,
        topic=request.topic,
        educational_level=request.educational_level.value,
        difficulty=request.difficulty.value,
        source_mode=request.source_mode.value,
        content_json=data,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


# ─────────────────────────────────────────────────────────────────────
# 4. Granular Item Regeneration
# ─────────────────────────────────────────────────────────────────────

async def regenerate_single_item(
    material: Material,
    request: RegenerateItemRequest,
    db: AsyncSession,
) -> Material:
    """Regenerates a single question, section, or task within a saved material without rebuilding the whole document."""
    content = dict(material.content_json)
    item_type = request.item_type.lower()
    item_id = str(request.item_id)
    guidance = request.teacher_guidance or "Provide a refreshed, high quality alternative."

    if material.type == "quiz":
        # Search in mcq_section, questions_section, or questions
        mcqs = content.get("mcq_section", {}).get("mcqs", [])
        written = content.get("questions_section", {}).get("questions", [])
        flat = content.get("questions", [])

        target_container = None
        target_idx = None
        current_item = None

        if item_type == "mcq" or "mcq" in item_id:
            for i, q in enumerate(mcqs):
                if str(q.get("id")) == item_id or str(i + 1) == item_id:
                    target_container = mcqs
                    target_idx = i
                    current_item = q
                    break

        if current_item is None:
            for i, q in enumerate(written):
                if str(q.get("id")) == item_id or str(i + 1) == item_id:
                    target_container = written
                    target_idx = i
                    current_item = q
                    break

        if current_item is None:
            for i, q in enumerate(flat):
                if str(q.get("id")) == item_id or str(i + 1) == item_id:
                    target_container = flat
                    target_idx = i
                    current_item = q
                    break

        if current_item is None:
            raise HTTPException(status_code=404, detail=f"Question/MCQ '{item_id}' not found in quiz.")

        is_mcq_target = current_item.get("type") == "mcq" or bool(current_item.get("options"))

        prompt = f"""
Regenerate this specific quiz {'multiple choice question (MCQ)' if is_mcq_target else 'written question'}.
Topic: {material.topic}
Level: {material.educational_level}
Difficulty: {material.difficulty}
Current Item to Replace:
{json.dumps(current_item, indent=2)}

Teacher Guidance: {guidance}

Return a single JSON object matching keys (id, type, prompt, options, correct_answer, explanation, marks).
"""
        resp = await llm.ainvoke([("user", prompt)])
        new_q = _extract_json(resp.content)
        new_q["id"] = current_item["id"]
        target_container[target_idx] = new_q

        # Synchronize flat list if present
        for i, q in enumerate(flat):
            if str(q.get("id")) == str(current_item["id"]):
                flat[i] = new_q
                break

    elif material.type == "lesson" and "sections" in content:
        target_idx = None
        current_item = None
        for i, s in enumerate(content["sections"]):
            if str(s.get("id")) == item_id or str(i + 1) == item_id:
                target_idx = i
                current_item = s
                break

        if target_idx is None:
            raise HTTPException(status_code=404, detail=f"Section '{item_id}' not found in lesson.")

        prompt = f"""
Regenerate this specific lesson section.
Topic: {material.topic}
Level: {material.educational_level}
Current Section to Replace:
{json.dumps(current_item, indent=2)}

Teacher Guidance: {guidance}

Return a single JSON object for this section matching keys (id, title, time_minutes, concepts, examples, activities).
"""
        resp = await llm.ainvoke([("user", prompt)])
        new_sec = _extract_json(resp.content)
        new_sec["id"] = current_item["id"]
        content["sections"][target_idx] = new_sec

    elif material.type == "assignment" and "tasks" in content:
        if item_type == "mcq" or "mcq" in item_id.lower():
            mcqs = content.get("mcq_section", {}).get("mcqs", [])
            target_idx = next(
                (i for i, q in enumerate(mcqs) if str(q.get("id")) == item_id or str(i + 1) == item_id),
                None,
            )
            if target_idx is None:
                raise HTTPException(status_code=404, detail=f"MCQ '{item_id}' not found in assignment.")
            current_item = mcqs[target_idx]
            prompt = f"""
Regenerate this specific assignment multiple-choice question.
Topic: {material.topic}
Level: {material.educational_level}
Current MCQ to Replace:
{json.dumps(current_item, indent=2)}

Teacher Guidance: {guidance}

Return one JSON object with keys (id, type, prompt, options, correct_answer, explanation, marks).
"""
            resp = await llm.ainvoke([("user", prompt)])
            new_mcq = _extract_json(resp.content)
            new_mcq["id"] = current_item["id"]
            new_mcq["type"] = "mcq"
            mcqs[target_idx] = new_mcq
        else:
            target_idx = None
            current_item = None
            for i, t in enumerate(content["tasks"]):
                if str(t.get("id")) == item_id or str(i + 1) == item_id:
                    target_idx = i
                    current_item = t
                    break

            if target_idx is None:
                raise HTTPException(status_code=404, detail=f"Task '{item_id}' not found in assignment.")

            prompt = f"""
Regenerate this specific assignment task.
Topic: {material.topic}
Level: {material.educational_level}
Current Task to Replace:
{json.dumps(current_item, indent=2)}

Teacher Guidance: {guidance}

Return a single JSON object for this task matching keys (id, type, title, prompt, marks, model_answer, rubric_criteria).
"""
            resp = await llm.ainvoke([("user", prompt)])
            new_task = _extract_json(resp.content)
            new_task["id"] = current_item["id"]
            content["tasks"][target_idx] = new_task
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported item regeneration for material type {material.type}.")

    material.content_json = content
    await db.commit()
    await db.refresh(material)
    return material

