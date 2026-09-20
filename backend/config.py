from dotenv import load_dotenv
import os

load_dotenv()


class Settings():
   GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
   TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
   DATABASE_URL = os.getenv("DATABASE_URL")
   SECRET_KEY=os.getenv("SECRET_KEY")
   SUPABASE_URL=os.getenv("SUPABASE_URL")
   SUPABASE_SERVICE_ROLE_KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=60*24
   model='gemini-2.5-flash'
   embedding_model='gemini-embedding-001'


settings=Settings()