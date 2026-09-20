import os
import time
from fastapi import FastAPI,UploadFile,File,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.schemas.chat import ChatRequest
from backend.schemas.auth import SignupRequest,LoginRequest,TokenResponse
from backend.rag.vector_store import ingest_pdf
from backend.agent.agent import agent
from backend.db.database import get_db
from backend.db.models import User
from backend.security import hash_password,verify_password,create_access_token
from backend.auth import get_current_user
from supabase import create_async_client
from backend.config import settings




MAX_UPLOAD_BYTES = 20 * 1024 * 1024

_storage_client = None


async def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = await create_async_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _storage_client


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
def ask(request:ChatRequest, user:User=Depends(get_current_user)):
    response=agent.invoke({
        "messages":[
            ("user", request.query)
        ]
    })
    return response


@app.post("/upload")
async def upload_pdf(file:UploadFile=File(...), user:User=Depends(get_current_user)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    storage_path = f"uploads/user_{user.id}/{int(time.time())}_{file.filename}"
    client = await get_storage_client()
    await client.storage.from_("uploads").upload(
        storage_path, data, {"content-type": "application/pdf", "upsert": "true"}
    )

    user_dir = f"backend/data/uploads/user_{user.id}"
    os.makedirs(user_dir, exist_ok=True)
    tmp_path = f"{user_dir}/{int(time.time())}_{file.filename}"
    with open(tmp_path, "wb") as buffer:
        buffer.write(data)

    try:
        await ingest_pdf(tmp_path)
    finally:
        os.remove(tmp_path)

    return {
        "Filename":file.filename,
        "storage_path":storage_path,
        "Message":"PDF uploaded and indexed successfully"
    }