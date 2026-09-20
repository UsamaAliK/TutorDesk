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
   LLM_TEMPERATURE=0.4
   MAX_UPLOAD_BYTES=20*1024*1024
   STORAGE_BUCKET="uploads"
   VECTOR_COLLECTION="uploads"
   EMBEDDING_DIMENSIONS=768
   EMBED_BATCH_SIZE=50
   MAX_EMBED_IN_FLIGHT=5
   CHUNK_SIZE=800
   CHUNK_OVERLAP=130
   RETRIEVE_K=4
   WEB_SEARCH_MAX_RESULTS=5
   TOP_SOURCES=3


settings=Settings()