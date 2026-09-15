from pydantic import BaseModel



class LessonPlan(BaseModel):
    title: str
    prerequisites: list[str]
    objectives: list[str]
    explanation: str
    activities: list[str]
    assessments: list[str]