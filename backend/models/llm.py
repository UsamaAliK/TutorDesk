from dotenv import load_dotenv
from backend.schemas.lesson import LessonPlan
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import settings




model=ChatGoogleGenerativeAI(
    model=settings.model,
    temperature=0.4
)

lessonmodel=model.with_structured_output(LessonPlan)
