import asyncio
import os
import time
from fastapi import FastAPI,UploadFile,File,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.schemas.chat import AskRequest, ConversationCreate
from backend.schemas.auth import SignupRequest,LoginRequest,TokenResponse
from backend.rag.vector_store import ingest_pdf
from backend.agent.agent import agent
from backend.agent.response import final_text, collect_sources
from backend.db.database import get_db
from backend.db.models import User, Conversation, Message
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
async def ask(request:AskRequest, user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    conversation_id = await _ensure_conversation(db, user.id, request)

    db.add(Message(conversation_id=conversation_id, role="user", content=request.query))
    await db.commit()

    state = await asyncio.to_thread(
        agent.invoke,
        {"messages": [("user", request.query)]},
        config={"configurable": {"user_id": user.id}},
    )

    messages = state["messages"]
    answer = final_text(messages[-1].content)
    db.add(Message(conversation_id=conversation_id, role="assistant", content=answer))
    await db.commit()

    return {
        "conversation_id": conversation_id,
        "response": answer,
        "sources": collect_sources(messages),
    }


@app.post("/conversations", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = Conversation(user_id=user.id, title=body.title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return {"id": conversation.id, "title": conversation.title}


@app.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
    )
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at}
        for c in result.scalars().all()
    ]


@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_conversation(db, conversation_id, user.id)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content}
        for m in result.scalars().all()
    ]


async def _get_owned_conversation(db: AsyncSession, conversation_id: int, user_id: int) -> Conversation:
    conversation = (
        await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def _ensure_conversation(db: AsyncSession, user_id: int, request: AskRequest) -> int:
    if request.conversation_id is not None:
        conversation = await _get_owned_conversation(db, request.conversation_id, user_id)
        return conversation.id

    conversation = Conversation(user_id=user_id, title=request.query[:60])
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation.id


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
        await ingest_pdf(tmp_path, user.id)
    finally:
        os.remove(tmp_path)

    return {
        "Filename":file.filename,
        "storage_path":storage_path,
        "Message":"PDF uploaded and indexed successfully"
    }