"""Shared formatting for RAG context and citations."""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

from app.services.session_store import SessionState


def format_video_metadata(videos: list[dict[str, Any]]) -> str:
    lines = []
    for v in videos:
        label = "Video A (YouTube)" if v["video_id"] == "A" else "Video B (Instagram)"
        lines.append(
            f"""{label}:
  - Title: {v['title']}
  - Creator: {v['creator']}
  - Followers: {v.get('follower_count') or 'N/A'}
  - Views: {v['views']:,}
  - Likes: {v['likes']:,}
  - Comments: {v['comments']:,}
  - Engagement rate: {v['engagement_rate']}%
  - Hashtags: {', '.join('#' + h for h in v.get('hashtags', [])[:15]) or 'none'}
  - Upload date: {v.get('upload_date') or 'N/A'}
  - Duration: {v.get('duration_seconds') or 'N/A'} seconds
  - URL: {v['url']}"""
        )
    return "\n\n".join(lines)


def format_docs(docs: list[Document]) -> tuple[str, list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    parts: list[str] = []
    for doc in docs:
        vid = doc.metadata.get("video_id", "?")
        idx = doc.metadata.get("chunk_index", 0)
        snippet = doc.page_content[:200].replace("\n", " ")
        sources.append(
            {
                "video_id": vid,
                "chunk_index": idx,
                "content_snippet": snippet,
            }
        )
        parts.append(f"[Video {vid}, chunk {idx}]\n{doc.page_content}")
    return "\n\n".join(parts), sources


def build_metadata_context(state: SessionState) -> str:
    return format_video_metadata(state.videos)
