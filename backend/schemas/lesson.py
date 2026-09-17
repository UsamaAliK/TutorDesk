from pydantic import BaseModel



class LessonPlan(BaseModel):
    title: str
    objectives: list[str]
    explanation: str
    examples: list[str]
    activities: list[str]
    assessments: list[str]