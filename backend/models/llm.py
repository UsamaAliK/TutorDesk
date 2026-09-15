from dotenv import load_dotenv
from backend.schemas.lesson import LessonPlan
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()


model=ChatGoogleGenerativeAI(
    model='gemini-2.5-flash',
    temperature=0.4
)

lessonmodel=model.with_structured_output(LessonPlan)
