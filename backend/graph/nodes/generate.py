import json
import re
from typing import Any, Dict
from fastapi import HTTPException

from backend.graph.state import GenerationState
from backend.llm.model import llm


def _extract_json(text: str) -> Dict[str, Any]:
    """Robustly extracts JSON from an LLM response."""
    clean = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
    if fence_match:
        clean = fence_match.group(1).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        brace_match = re.search(r"\{[\s\S]*\}", clean)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail="Failed to parse structured educational content from model. Please adjust instructions and try again."
        )


def _build_grounding_block(state: GenerationState) -> tuple[str, list[str]]:
    parts = []
    sources = []

    rag_docs = state.get("rag_documents", [])
    if rag_docs:
        parts.append("=== PRIMARY GROUNDING: USER UPLOADED DOCUMENTS ===")
        for i, doc in enumerate(rag_docs, 1):
            src = doc.get("source") or "Uploaded Material"
            parts.append(f"[Document Excerpt {i} | Source: {src}]\n{doc.get('content', '')}")
            if src not in sources:
                sources.append(src)

    web_docs = state.get("web_documents", [])
    if web_docs:
        parts.append("=== SUPPLEMENTARY RESEARCH: LIVE WEB ===")
        web_sources = state.get("web_sources", [])
        for i, doc in enumerate(web_docs, 1):
            url = web_sources[i - 1] if i - 1 < len(web_sources) else "Web Resource"
            parts.append(f"[Web Citation {i} | URL: {url}]\n{doc.get('content', '')}")
            if url not in sources:
                sources.append(url)

    text_block = "\n\n".join(parts) if parts else "(Verified foundational topic knowledge adhering strictly to curriculum)."
    return text_block, sources


# ─────────────────────────────────────────────────────────────────────
# 1. Lesson Generator
# ─────────────────────────────────────────────────────────────────────

LESSON_PROMPT = """\
You are TutorDesk, an expert curriculum and instructional design specialist.
Create a proportioned, engaging lesson plan for educators.

CONFIGURATION:
- Subject: {subject}
- Topic: {topic}
- Educational Level: {educational_level}
- Duration: Exactly {duration_minutes} Minutes
{phd_instruction}

GROUNDING MATERIAL:
{context}

TEACHER INSTRUCTIONS & CONSTRAINTS:
- Teaching Style: {teaching_style}
- Learning Objectives: {learning_objectives}
- Curriculum: {curriculum}
- Additional Guidance: {additional_instructions}

OUTPUT FORMAT: Return a single RAW JSON OBJECT matching this exact structure:
{{
  "title": "Engaging Lesson Title",
  "overview": "2-3 sentence overview of what students will achieve",
  "subject": "{subject}",
  "topic": "{topic}",
  "educational_level": "{educational_level}",
  "duration_minutes": {duration_minutes},
  "learning_objectives": ["Measurable objective 1", "Measurable objective 2"],
  "prerequisite_knowledge": ["Concept 1", "Concept 2"],
  "sections": [
    {{
      "id": "sec_1",
      "title": "Section Title (e.g. Introduction & Conceptual Hook)",
      "time_minutes": 10,
      "concepts": "Deep conceptual explanation...",
      "examples": ["Real-world application or analogy"],
      "activities": "Interactive check for understanding"
    }}
  ],
  "practice_questions": [
    {{
      "id": "pq_1",
      "question": "Practice question prompt",
      "guidance": "Teacher answer or scoring guide"
    }}
  ],
  "summary": "Key takeaways synthesized in 3-4 bullet points",
  "assessment_followup": "Homework or exit-ticket assessment",
  "sources": []
}}
"""


# ─────────────────────────────────────────────────────────────────────
# 2. Quiz Generator (MCQs as a SEPARATE SECTION)
# ─────────────────────────────────────────────────────────────────────

QUIZ_PROMPT = """\
You are TutorDesk, an assessment specialist.
Generate a strictly calibrated quiz with TWO DISTINCT SECTIONS:
- SECTION A: MULTIPLE CHOICE QUESTIONS (MCQs)
- SECTION B: SHORT & LONG ANSWER QUESTIONS

CRITICAL INSTRUCTIONS ON SECTIONS:
1. MCQs MUST NOT be mixed into general questions. They belong strictly in "mcq_section" (Section A).
2. Written questions belong strictly in "questions_section" (Section B).
3. Section A must contain EXACTLY {num_mcqs} MCQs. Each MCQ has {mcq_options_count} options, and exactly ONE correct answer.
4. Section B must contain EXACTLY {num_short_answer} Short Answer questions and {num_long_answer} Long Answer questions.
5. Provide complete, unambiguous answer keys and explanations for both sections.

CONFIGURATION:
- Subject: {subject}
- Topic: {topic}
- Educational Level: {educational_level}
- Difficulty: {difficulty}
- Section A (MCQs Count): {num_mcqs}
- Section B (Short Answer): {num_short_answer}
- Section B (Long Answer): {num_long_answer}
- Time Limit: {time_limit}
- Total Marks: {total_marks}
- Additional Guidance: {additional_instructions}

GROUNDING MATERIAL:
{context}

OUTPUT FORMAT: Return a single RAW JSON OBJECT matching this exact structure:
{{
  "title": "Quiz: {topic}",
  "subject": "{subject}",
  "topic": "{topic}",
  "educational_level": "{educational_level}",
  "difficulty": "{difficulty}",
  "time_limit_minutes": {time_limit_json},
  "total_marks": {total_marks_json},
  "instructions_for_students": "Read each section carefully. Section A contains Multiple Choice Questions. Section B contains Written Questions.",
  "mcq_section": {{
    "title": "Section A: Multiple Choice Questions (MCQs)",
    "instructions": "Select the single best answer for each question.",
    "total_mcqs": {num_mcqs},
    "mcqs": [
      {{
        "id": "mcq_1",
        "type": "mcq",
        "prompt": "MCQ prompt...",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct_answer": "A) ...",
        "explanation": "Rationale for option A...",
        "marks": 1
      }}
    ]
  }},
  "questions_section": {{
    "title": "Section B: Short & Long Answer Questions",
    "instructions": "Answer the following written questions in complete, well-reasoned sentences.",
    "total_questions": {num_written_total},
    "questions": [
      {{
        "id": "q_1",
        "type": "short_answer",
        "prompt": "Short answer question prompt...",
        "correct_answer": "Model answer points...",
        "explanation": "Expected key criteria...",
        "marks": 3
      }},
      {{
        "id": "q_2",
        "type": "long_answer",
        "prompt": "Long answer essay/analysis prompt...",
        "correct_answer": "Comprehensive model response with evaluation points...",
        "explanation": "Grading guidance...",
        "marks": 5
      }}
    ]
  }},
  "sources": []
}}
"""


# ─────────────────────────────────────────────────────────────────────
# 3. Assignment Generator
# ─────────────────────────────────────────────────────────────────────

ASSIGNMENT_PROMPT = """\
You are TutorDesk, an educator designing a structured student assignment.

CONFIGURATION:
- Subject: {subject}
- Topic: {topic}
- Educational Level: {educational_level}
- Difficulty: {difficulty}
- SECTION A: Exactly {num_mcqs} multiple-choice questions (MCQs). This count is separate and must NOT be included in the task count.
- If {num_mcqs} is 0, provide an empty mcqs list in mcq_section.
- SECTION B: Exactly {total_tasks} tasks/problems. This count excludes MCQs.
- Allowed Task Types: {task_types}
- Additional Guidance: {additional_instructions}

GROUNDING MATERIAL:
{context}

OUTPUT FORMAT: Return a single RAW JSON OBJECT matching this exact structure:
{{
  "title": "Assignment: {topic}",
  "subject": "{subject}",
  "topic": "{topic}",
  "educational_level": "{educational_level}",
  "difficulty": "{difficulty}",
  "total_marks": {total_marks},
  "deadline_days": {deadline_days},
  "instructions_for_students": "Submission guidelines and academic expectations...",
  "mcq_section": {{
    "title": "Section A: Multiple Choice Questions (MCQs)",
    "instructions": "Select the single best answer for each question.",
    "total_mcqs": {num_mcqs},
    "mcqs": [
      {{
        "id": "mcq_1",
        "type": "mcq",
        "prompt": "Question...",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct_answer": "A) ...",
        "explanation": "...",
        "marks": 1
      }}
    ]
  }},
  "tasks": [
    {{
      "id": "task_1",
      "type": "problem_solving",
      "title": "Task 1 Title",
      "prompt": "Comprehensive problem or scenario prompt...",
      "marks": 10,
      "model_answer": "Exemplary solution demonstrating full points...",
      "rubric_criteria": [
        {{"criterion": "Conceptual Accuracy", "points": 5, "description": "Accurately applies core concepts."}},
        {{"criterion": "Analytical Rigor", "points": 5, "description": "Provides step-by-step logic and justification."}}
      ]
    }}
  ],
  "marking_rubric_summary": "General criteria for overall evaluation.",
  "sources": []
}}
"""


def generate_material(state: GenerationState) -> dict:
    """Generates final educational content grounded in retrieved and verified sources."""
    mtype = state.get("material_type", "lesson").lower()
    subject = state.get("subject", "")
    topic = state.get("topic", "")
    level = state.get("educational_level", "Grades 9-12")
    spec = state.get("generation_spec", {})

    if state.get("source_mode") == "material_only" and not state.get("rag_documents"):
        raise HTTPException(
            status_code=400,
            detail=f"No relevant content was found in your uploaded document(s) for topic '{topic}'. Please upload relevant materials or select web research."
        )

    context, sources = _build_grounding_block(state)

    if mtype == "lesson":
        duration = spec.get("duration_minutes", 45)
        phd_instruction = ""
        if "PhD" in level or "Research" in level:
            phd_instruction = "RESEARCH / PHD MODE ACTIVATED: Synthesize theoretical frameworks, methodologies, and literature citations."

        prompt = LESSON_PROMPT.format(
            subject=subject,
            topic=topic,
            educational_level=level,
            duration_minutes=duration,
            phd_instruction=phd_instruction,
            context=context,
            teaching_style=spec.get("teaching_style") or "Pedagogical, clear, engaging",
            learning_objectives=spec.get("learning_objectives") or "Standard curriculum outcomes",
            curriculum=spec.get("curriculum") or "Standard",
            additional_instructions=spec.get("additional_instructions") or "None",
        )

    elif mtype == "quiz":
        num_mcqs = spec.get("num_mcqs", 5)
        num_short = spec.get("num_short_answer", 3)
        num_long = spec.get("num_long_answer", 2)
        options_count = spec.get("mcq_options_count", 4)
        time_limit = spec.get("time_limit_minutes")
        total_marks = spec.get("total_marks")

        prompt = QUIZ_PROMPT.format(
            subject=subject,
            topic=topic,
            educational_level=level,
            difficulty=state.get("difficulty") or "Medium",
            num_mcqs=num_mcqs,
            num_short_answer=num_short,
            num_long_answer=num_long,
            num_written_total=num_short + num_long,
            mcq_options_count=options_count,
            time_limit=f"{time_limit} minutes" if time_limit else "Not specified",
            time_limit_json=str(time_limit) if time_limit else "null",
            total_marks=str(total_marks) if total_marks else "Calculated based on items",
            total_marks_json=str(total_marks) if total_marks else "null",
            additional_instructions=spec.get("additional_instructions") or "None",
            context=context,
        )

    elif mtype == "assignment":
        num_mcqs = spec.get("num_mcqs", 0)
        total_tasks = spec.get("total_tasks", 5)
        task_types = ", ".join(spec.get("task_types") or ["short_answer", "problem_solving"])
        total_marks = spec.get("total_marks", 50)
        deadline = spec.get("deadline_days", 7)

        prompt = ASSIGNMENT_PROMPT.format(
            subject=subject,
            topic=topic,
            educational_level=level,
            difficulty=state.get("difficulty") or "Medium",
            num_mcqs=num_mcqs,
            total_tasks=total_tasks,
            task_types=task_types,
            total_marks=total_marks,
            deadline_days=deadline,
            additional_instructions=spec.get("additional_instructions") or "None",
            context=context,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported material type '{mtype}'")

    response = llm.invoke(prompt)
    data = _extract_json(response.content)
    data["sources"] = sources

    # Compatibility layer for quizzes: maintain flat list if needed by legacy callers
    if mtype == "quiz":
        mcqs = data.get("mcq_section", {}).get("mcqs", [])
        written = data.get("questions_section", {}).get("questions", [])
        data["questions"] = mcqs + written

    return {
        "content_json": data,
        "all_sources": sources,
    }
