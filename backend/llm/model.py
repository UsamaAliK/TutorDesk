from dotenv import load_dotenv
from backend.schemas.lesson import LessonPlan
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import settings


llm = ChatGoogleGenerativeAI(
    model=settings.model,
    temperature=0.4
)

lessonmodel = llm.with_structured_output(LessonPlan)