from fastapi import FastAPI,UploadFile,File,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.llm.model import llm,lessonmodel
from backend.schemas.chat import ChatRequest
from backend.schemas.auth import SignupRequest,LoginRequest,TokenResponse
from backend.prompts.tutor import tutorprompt
from backend.prompts.lesson import lessonprompt
from backend.rag.rag_chain import ask_rag
from backend.rag.vector_store import create_vector_store
from backend.websearch.research import research_topic
from backend.agent.agent import agent
from backend.db.database import get_db
from backend.db.models import User
from backend.security import hash_password,verify_password,create_access_token
from backend.auth import get_current_user





app=FastAPI(title="TutorDesk")


@app.get('/')
def health():
    return  {"message": "TutorDesk API is running"}

@app.post("/signup", status_code=201)
async def signup(body:SignupRequest, db:AsyncSession=Depends(get_db)):
    existing=await db.execute(select(User).where(User.email==body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user=User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id":user.id, "email":user.email}


@app.post("/login", response_model=TokenResponse)
async def login(body:LoginRequest, db:AsyncSession=Depends(get_db)):
    result=await db.execute(select(User).where(User.email==body.email))
    user=result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/me")
async def me(user:User=Depends(get_current_user)):
    return {"id":user.id, "email":user.email}

@app.post("/ask")
def ask(request:ChatRequest):
    response=agent.invoke({
        "messages":[
            ("user", request.query)
        ]
    })
    return response


@app.post("/chat")
def chat(request:ChatRequest):
    chain=tutorprompt|llm
    response=chain.invoke(
        {
            "message":request.query
        }
    )
    
    return {"response":response.content
            }

@app.post("/rag/chat")
def rag_chat(request:ChatRequest):
    response=ask_rag(request.query)
    return {
        "response":response
    }

@app.post("/lesson-plan")
def create_lesson_plan(requesst:ChatRequest):
    chain=lessonprompt|lessonmodel
    response=chain.invoke(
        {
           "request":requesst.query
        }
        )
    return response.model_dump()

@app.post("/search")
def search(request:ChatRequest):
    response=research_topic(request.query)
    return response

@app.post("/upload")
async def upload_pdf(file:UploadFile=File(...)):
    file_path=f"backend/data/uploads/{file.filename}"
    with open(file_path,"wb") as buffer:
        buffer.write(await file.read())
    create_vector_store(file_path)
    return{
        "Filename":file.filename,
        "Message":"PDF UPLOADED AND INDEXED SUCCSESSFYLLY"
    }