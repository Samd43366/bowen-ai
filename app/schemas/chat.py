from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Message(BaseModel):
    role: str # 'user' or 'ai'
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class SourceChunk(BaseModel):
    filename: str
    chunk_index: int
    text: str

class AskResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]