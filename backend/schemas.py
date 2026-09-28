from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RumbleRequest(BaseModel):
    url: str = ""
    pattern: str
    model: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    email: str


class RegisterResponse(BaseModel):
    token: str
    username: str
    email: str


class UserResponse(BaseModel):
    username: str
    email: str


class JobStatusResponse(BaseModel):
    id: str
    source: str
    url: Optional[str] = None
    pattern: str
    status: str
    transcript: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata_json: Optional[dict] = None
    username: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class HistoryFilter(BaseModel):
    source: Optional[str] = None
    pattern: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class PatternInfo(BaseModel):
    name: str
    description: str = ""