import json
import re
from typing import Any, Dict, List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.model import llm
from backend.db.models import Material
from backend.schemas.material import (
    LessonGenerateRequest,
    QuizGenerateRequest,
    AssignmentGenerateRequest,
    RegenerateItemRequest,
    EducationalLevel,
)
from backend.services.source_resolver import resolve_content_sources


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


# ─────────────────────────────────────────────────────────────────────
# 1. Lesson Generator
# ─────────────────────────────────────────────────────────────────────

LESSON_SYSTEM_PROMPT = """\
You are TutorDesk, an expert curriculum designer and pedagogy specialist.
Your mission is to generate a comprehensive, highly structured lesson for educators.

CRITICAL INSTRUCTIONS:
1. Grounding: Rely strictly on the PROVIDED SOURCES below. Never fabricate statistics, quotes, or claims not supported by the sources.
2. Educational Level: Adapt vocabulary, depth, conceptual sophistication, and examples to: {educational_level}.
   {phd_instruction}
3. Duration Proportion: The lesson is designed for EXACTLY {duration_minutes} MINUTES.
   - Allocate minutes across sections accurately so their sum equals {duration_minutes}.
   - A short 10-20 min lesson should be focused and concise.
   - A 60-120 min lecture must be deep, thoroughly elaborated with detailed subtopics and discussions.
4. Output Format: Return a VALID RAW JSON OBJECT only. Do not wrap in markdown quotes if possible, or use standard ```json.

REQUIRED JSON STRUCTURE:
{{
  "title": "Clear and Engaging Lesson Title",
  "overview": "2-3 sentence overview of what students will master",
  "subject": "{subject}",
  "topic": "{topic}",
  "educational_level": "{educational_level}",
  "duration_minutes": {duration_minutes},
  "learning_objectives": ["Objective 1 with measurable verb", "Objective 2"],
  "prerequisite_knowledge": ["Concept A", "Concept B"],
  "sections": [
    {{
      "id": "sec_1",
      "title": "Section Title (e.g. Introduction & Conceptual Hook)",
      "time_minutes": 10,
      "concepts": "In-depth theoretical explanation and core principles...",
      "examples": ["Concrete real-world example or demonstration"],
      "activities": "Interactive student activity or check for understanding"
    }}
  ],
  "practice_questions": [
    {{
      "id": "pq_1",
      "question": "Practice question prompt",
      "guidance": "Brief teacher answer or scoring guide"
    }}
  ],
  "summary": "Key takeaways synthesized in 3-4 bullet points",
  "assessment_followup": "Homework, project idea, or exit ticket suggestion",
  "sources": []
}}
"""

async def generate_lesson(request: LessonGenerateRequest, user_id: int, db: AsyncSession) -> Material:
    query = f"{request.subject}: {request.topic}"
    context, sources = await resolve_content_sources(
        user_id=user_id,
        source_mode=request.source_mode,
        query=query,
        educational_level=request.educational_level,
        selected_document_id=request.selected_document_id,
        db=db,
    )

    phd_instruction = ""
    if request.educational_level == EducationalLevel.PHD_RESEARCH:
        phd_instruction = (
            "RESEARCH / PHD MODE ACTIVATED: Focus on critical analysis of theoretical frameworks, "
            "methodological considerations, current empirical debates, literature synthesis, and cite available sources rigorously."
        )

    user_prompt = f"""
Subject: {request.subject}
Topic: {request.topic}
Educational Level: {request.educational_level.value}
Duration: {request.duration_minutes} minutes
Language: {request.language}
Preferred Teaching Style: {request.teaching_style or 'Engaging, clear, pedagogical'}
Learning Objectives Requested: {request.learning_objectives or 'Standard curriculum outcomes'}
Curriculum/Syllabus: {request.curriculum or 'Standard'}
Additional Teacher Instructions: {request.additional_instructions or 'None'}

PROVIDED SOURCES FOR GROUNDING:
{context}
"""

    formatted_system = LESSON_SYSTEM_PROMPT.format(
        subject=request.subject,
        topic=request.topic,
        educational_level=request.educational_level.value,
        duration_minutes=request.duration_minutes,
        phd_instruction=phd_instruction,
    )

    response = await llm.ainvoke([
        ("system", formatted_system),
        ("user", user_prompt)
    ])

    data = _extract_json(response.content)
    data["sources"] = sources
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
# 2. Quiz Generator
# ─────────────────────────────────────────────────────────────────────

QUIZ_SYSTEM_PROMPT = """\
You are TutorDesk, an expert assessment specialist.
Generate a high-quality, strictly calibrated quiz for teachers with TWO DISTINCT SECTIONS:
- SECTION A: MULTIPLE CHOICE QUESTIONS (MCQs)
- SECTION B: SHORT & LONG ANSWER QUESTIONS

STRICT CONFIGURATION CONSTRAINTS:
- Educational Level: {educational_level}
- Difficulty: {difficulty}
- SECTION A (MCQs): Exactly {num_mcqs} questions.
  * Each MCQ MUST have EXACTLY {mcq_options_count} options (e.g. A, B, C, D).
  * EXACTLY ONE option is correct.
  * Options must be plausible; avoid lazy distractors like 'None of the above'.
- SECTION B (WRITTEN QUESTIONS): Exactly {num_short_answer} Short-Answer and {num_long_answer} Long-Answer questions.
- ANSWER KEY & EXPLANATIONS:
  * Provide an unambiguous correct answer and an explanatory rationale for every question.

REQUIRED JSON STRUCTURE:
{{
  "title": "Quiz: {topic}",
  "subject": "{subject}",
  "topic": "{topic}",
  "educational_level": "{educational_level}",
  "difficulty": "{difficulty}",
  "time_limit_minutes": {time_limit_str},
  "total_marks": {total_marks_str},
  "instructions_for_students": "Read each section carefully. Section A contains multiple-choice questions; Section B contains written questions.",
  "mcq_section": {{
    "title": "Section A: Multiple Choice Questions",
    "instructions": "Select the single best answer for each question.",
    "mcqs": [
      {{
        "id": "mcq_1",
        "type": "mcq",
        "prompt": "Which of the following describes...",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct_answer": "A) ...",
        "explanation": "Option A is correct because...",
        "marks": 1
      }}
    ]
  }},
  "questions_section": {{
    "title": "Section B: Short & Long Answer Questions",
    "instructions": "Write detailed, well-reasoned answers to the questions below.",
    "questions": [
      {{
        "id": "q_1",
        "type": "short_answer",
        "prompt": "Define ... and state two examples.",
        "correct_answer": "Model short answer criteria...",
        "explanation": "Expected key concepts include...",
        "marks": 3
      }},
      {{
        "id": "q_2",
        "type": "long_answer",
        "prompt": "Explain in detail how ... impacts ...",
        "correct_answer": "Comprehensive model response with evaluation points...",
        "explanation": "Grading guidance: award points for thesis, evidence, and conclusion.",
        "marks": 5
      }}
    ]
  }},
  "sources": []
}}
"""

async def generate_quiz(request: QuizGenerateRequest, user_id: int, db: AsyncSession) -> Material:
    query = f"{request.subject}: {request.topic}"
    context, sources = await resolve_content_sources(
        user_id=user_id,
        source_mode=request.source_mode,
        query=query,
        educational_level=request.educational_level,
        selected_document_id=request.selected_document_id,
        db=db,
    )

    system_prompt = QUIZ_SYSTEM_PROMPT.format(
        subject=request.subject,
        topic=request.topic,
        educational_level=request.educational_level.value,
        difficulty=request.difficulty.value,
        num_mcqs=request.num_mcqs,
        num_short_answer=request.num_short_answer,
        num_long_answer=request.num_long_answer,
        mcq_options_count=request.mcq_options_count,
        time_limit_str=str(request.time_limit_minutes) if request.time_limit_minutes else "null",
        total_marks_str=str(request.total_marks) if request.total_marks else "null",
    )

    user_prompt = f"""
Subject: {request.subject}
Topic: {request.topic}
Educational Level: {request.educational_level.value}
Difficulty: {request.difficulty.value}
Section A - MCQs Count: {request.num_mcqs} (each with {request.mcq_options_count} options)
Section B - Short Answer Count: {request.num_short_answer}
Section B - Long Answer Count: {request.num_long_answer}
Learning Objectives: {request.learning_objectives or 'Comprehensive mastery'}
Additional Instructions: {request.additional_instructions or 'None'}

GROUNDING MATERIAL:
{context}
"""

    response = await llm.ainvoke([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    data = _extract_json(response.content)
    data["sources"] = sources

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
            "title": "Section A: Multiple Choice Questions",
            "instructions": "Select the single best answer for each question.",
            "mcqs": mcqs
        }
        data["questions_section"] = {
            "title": "Section B: Short & Long Answer Questions",
            "instructions": "Write detailed, well-reasoned answers to the questions below.",
            "questions": written_questions
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
# 3. Assignment Generator
# ─────────────────────────────────────────────────────────────────────

ASSIGNMENT_SYSTEM_PROMPT = """\
You are TutorDesk, a distinguished educator creating a structured assignment.

REQUIREMENTS:
- Educational Level: {educational_level}
- Difficulty: {difficulty}
- SECTION A: Exactly {num_mcqs} multiple-choice questions (MCQs). This count is separate and must NOT be included in the task count.
- If {num_mcqs} is 0, return an empty MCQ array.
- SECTION B: Exactly {total_tasks} tasks/problems. This count excludes MCQs.
- Allowed Task Types: {task_types}
- Output must feature both student-facing problem descriptions AND a complete teacher grading rubric + model answer for every task.
- Ensure tasks stimulate critical thinking, application of theory, and analytical depth appropriate for {educational_level}.

REQUIRED JSON STRUCTURE:
{{
  "title": "Assignment: {topic}",
  "subject": "{subject}",
  "topic": "{topic}",
  "educational_level": "{educational_level}",
  "difficulty": "{difficulty}",
  "total_marks": {total_marks_str},
  "deadline_days": {deadline_days_str},
  "instructions_for_students": "Detailed guidelines on submission format, academic integrity, and expectations...",
  "mcq_section": {{
    "title": "Section A: Multiple Choice Questions",
    "mcqs": [
      {{"id": "mcq_1", "type": "mcq", "prompt": "Question...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct_answer": "A) ...", "explanation": "...", "marks": 1}}
    ]
  }},
  "tasks": [
    {{
      "id": "t1",
      "type": "problem_solving",
      "title": "Task 1 Title",
      "prompt": "Comprehensive scenario or task description...",
      "marks": 10,
      "model_answer": "Exemplary solution demonstrating full points...",
      "rubric_criteria": [
        {{"criterion": "Conceptual Accuracy", "points": 5, "description": "Accurately applies principles..."}},
        {{"criterion": "Analytical Rigor", "points": 5, "description": "Provides step-by-step logic and justification."}}
      ]
    }}
  ],
  "marking_rubric_summary": "General criteria for overall submission...",
  "sources": []
}}
"""

async def generate_assignment(request: AssignmentGenerateRequest, user_id: int, db: AsyncSession) -> Material:
    query = f"{request.subject}: {request.topic}"
    context, sources = await resolve_content_sources(
        user_id=user_id,
        source_mode=request.source_mode,
        query=query,
        educational_level=request.educational_level,
        selected_document_id=request.selected_document_id,
        db=db,
    )

    system_prompt = ASSIGNMENT_SYSTEM_PROMPT.format(
        subject=request.subject,
        topic=request.topic,
        educational_level=request.educational_level.value,
        difficulty=request.difficulty.value,
        total_tasks=request.total_tasks,
        num_mcqs=request.num_mcqs,
        task_types=", ".join(request.task_types),
        total_marks_str=str(request.total_marks) if request.total_marks else "50",
        deadline_days_str=str(request.deadline_days) if request.deadline_days else "7",
    )

    user_prompt = f"""
Subject: {request.subject}
Topic: {request.topic}
Educational Level: {request.educational_level.value}
Difficulty: {request.difficulty.value}
Section A MCQs: {request.num_mcqs} (separate count; do not include in task count)
Section B Tasks / Problems: {request.total_tasks}
Selected Task Types: {request.task_types}
Student Instructions Customization: {request.instructions_for_students or 'Standard format'}
Include Rubric: {request.include_rubric}
Include Model Answers: {request.include_model_answers}
Additional Teacher Instructions: {request.additional_instructions or 'None'}

GROUNDING CONTEXT:
{context}
"""

    response = await llm.ainvoke([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    data = _extract_json(response.content)
    data["sources"] = sources
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

