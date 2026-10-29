from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator


class EducationalLevel(str, Enum):
    GRADE_1_5 = "Grades 1-5"
    GRADE_6_8 = "Grades 6-8"
    GRADE_9_12 = "Grades 9-12"
    BACHELORS = "Bachelor's Degree"
    MASTERS = "Master's Degree"
    PHD_RESEARCH = "PhD / Research Mode"


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    MIXED = "Mixed"


class SourceMode(str, Enum):
    MATERIAL_ONLY = "material_only"
    WEB_SEARCH = "web_search"
    COMBINED = "combined"


class AssignmentTaskType(str, Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    PROBLEM_SOLVING = "problem_solving"
    CASE_STUDY = "case_study"
    PROJECT = "project"


# ── Lesson Generation Request ──────────────────────────────────────────

class LessonGenerateRequest(BaseModel):
    subject: str = Field(..., min_length=2, max_length=150)
    topic: str = Field(..., min_length=2, max_length=250)
    educational_level: EducationalLevel = EducationalLevel.GRADE_9_12
    duration_minutes: int = Field(45, ge=10, le=120)
    source_mode: SourceMode = SourceMode.WEB_SEARCH
    learning_objectives: Optional[str] = None
    teaching_style: Optional[str] = None
    language: str = "English"
    curriculum: Optional[str] = None
    additional_instructions: Optional[str] = None
    selected_document_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_duration(self) -> "LessonGenerateRequest":
        if self.duration_minutes % 10 != 0:
            # Round to nearest 10 or raise
            rounded = max(10, min(120, round(self.duration_minutes / 10.0) * 10))
            self.duration_minutes = rounded
        return self


# ── Quiz Generation Request ────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    subject: str = Field(..., min_length=2, max_length=150)
    topic: str = Field(..., min_length=2, max_length=250)
    educational_level: EducationalLevel = EducationalLevel.GRADE_9_12
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    num_mcqs: int = Field(5, ge=0, description="Number of MCQs in Section A")
    num_short_answer: int = Field(3, ge=0, description="Number of Short-Answer Questions in Section B")
    num_long_answer: int = Field(2, ge=0, description="Number of Long-Answer Questions in Section B")
    total_written_questions: Optional[int] = Field(None, ge=0, description="Total written questions in Section B")
    total_questions: Optional[int] = Field(None, ge=1, description="Total combined items across quiz")
    mcq_options_count: int = Field(4, ge=2, le=6)
    time_limit_minutes: Optional[int] = Field(None, ge=5, le=180)
    total_marks: Optional[int] = Field(None, ge=1)
    marks_per_question: Optional[float] = None
    learning_objectives: Optional[str] = None
    include_answer_key: bool = True
    include_explanations: bool = True
    source_mode: SourceMode = SourceMode.WEB_SEARCH
    additional_instructions: Optional[str] = None
    selected_document_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_distribution(self) -> "QuizGenerateRequest":
        written_sum = self.num_short_answer + self.num_long_answer
        if self.total_written_questions is not None and self.total_written_questions != written_sum:
            raise ValueError(
                f"Written questions distribution ({self.num_short_answer} Short Answer + {self.num_long_answer} Long Answer = {written_sum}) "
                f"must equal total written questions ({self.total_written_questions})."
            )

        if self.num_mcqs == 0 and written_sum == 0:
            raise ValueError("Quiz must contain at least one MCQ or one written question.")

        if self.total_written_questions is None:
            self.total_written_questions = written_sum

        if self.total_questions is None:
            self.total_questions = self.num_mcqs + written_sum

        return self


# ── Assignment Generation Request ──────────────────────────────────────

class AssignmentGenerateRequest(BaseModel):
    subject: str = Field(..., min_length=2, max_length=150)
    topic: str = Field(..., min_length=2, max_length=250)
    educational_level: EducationalLevel = EducationalLevel.GRADE_9_12
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    total_tasks: int = Field(5, ge=1, le=30)
    task_types: List[str] = Field(default_factory=lambda: ["short_answer", "problem_solving"])
    total_marks: Optional[int] = Field(50, ge=1)
    deadline_days: Optional[int] = Field(7, ge=1, le=60)
    learning_objectives: Optional[str] = None
    instructions_for_students: Optional[str] = None
    include_rubric: bool = True
    include_model_answers: bool = True
    source_mode: SourceMode = SourceMode.WEB_SEARCH
    additional_instructions: Optional[str] = None
    selected_document_id: Optional[int] = None


# ── Granular Item Regeneration ─────────────────────────────────────────

class RegenerateItemRequest(BaseModel):
    item_type: str = Field(..., description="'question' | 'section' | 'task'")
    item_id: str = Field(..., description="Unique ID or index of item in content_json")
    teacher_guidance: Optional[str] = Field(None, description="Specific instructions for this item")


# ── Update & Response Schemas ──────────────────────────────────────────

class MaterialUpdateRequest(BaseModel):
    title: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None


class MaterialResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    subject: str
    topic: str
    educational_level: str
    difficulty: Optional[str] = None
    source_mode: str
    content_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MaterialListItem(BaseModel):
    id: int
    type: str
    title: str
    subject: str
    topic: str
    educational_level: str
    difficulty: Optional[str] = None
    source_mode: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

