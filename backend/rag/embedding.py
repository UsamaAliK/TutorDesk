from langchain_google_genai import GoogleGenerativeAIEmbeddings
from backend.config import settings




embeddings=GoogleGenerativeAIEmbeddings(
    model=settings.embedding_model
)
