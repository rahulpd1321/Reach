from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    youtube_url: str = Field(..., description="YouTube video URL (Video A)")
    instagram_url: str = Field(..., description="Instagram Reel URL (Video B)")


class VideoMetadata(BaseModel):
    video_id: str  # "A" or "B"
    platform: str
    url: str
    title: str
    creator: str
    follower_count: int | None = None
    views: int
    likes: int
    comments: int
    engagement_rate: float
    hashtags: list[str] = Field(default_factory=list)
    upload_date: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    transcript_preview: str = ""


class IngestResponse(BaseModel):
    session_id: str
    videos: list[VideoMetadata]
    chunks_indexed: int


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SourceCitation(BaseModel):
    video_id: str
    chunk_index: int
    content_snippet: str
    score: float | None = None


class ChatMessage(BaseModel):
    role: str
    content: str
    sources: list[SourceCitation] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    videos: list[VideoMetadata]
