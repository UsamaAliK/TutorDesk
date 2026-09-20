from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str


class AskRequest(ChatRequest):
    conversation_id: Optional[int] = None


class ConversationCreate(BaseModel):
    title: str = "New chat"
