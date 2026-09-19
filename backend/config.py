from dotenv import load_dotenv
import os

load_dotenv()


class Settings():
   GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
   TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
   DATABASE_URL = os.getenv("DATABASE_URL")
   model='gemini-2.5-flash'
   embedding_model='gemini-embedding-001'


settings=Settings()