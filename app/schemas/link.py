from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class ActionableLink(BaseModel):
    id: Optional[str] = None
    title: str
    url: str
    category: str
    description: str
    walkthrough: List[str] = [] # List of steps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class CreateLinkRequest(BaseModel):
    title: str
    url: str
    category: str
    description: str
    walkthrough: List[str] = []
