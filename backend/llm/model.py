from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import settings


llm = ChatGoogleGenerativeAI(
    model=settings.model,
    temperature=0.4
)