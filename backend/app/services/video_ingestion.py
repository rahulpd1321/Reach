"""Fetch transcripts and metadata from YouTube and Instagram via yt-dlp."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

YTDLP_CMD = [sys.executable, "-m", "yt_dlp"]


def _ytdlp_base_args() -> list[str]:
    args: list[str] = []
    browser = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()
    if not browser:
        try:
            from app.config import get_settings

            browser = get_settings().ytdlp_cookies_browser.strip()
        except Exception:
            pass
    # Browser cookies only work on a dev machine with that browser installed (not Railway Docker)
    if browser and not os.getenv("RAILWAY_ENVIRONMENT") and not os.path.exists("/.dockerenv"):
        args.extend(["--cookies-from-browser", browser])
    elif browser and (os.getenv("RAILWAY_ENVIRONMENT") or os.path.exists("/.dockerenv")):
        logger.warning(
            "YTDLP_COOKIES_BROWSER ignored in container/Railway; use public Instagram URLs"
        )
    return args

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)

YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


def _run_ytdlp(url: str, extra_args: list[str] | None = None) -> dict[str, Any]:

    url = normalize_youtube_url(url)

    args = [
        *YTDLP_CMD,
        *_ytdlp_base_args(),
        "--extractor-args",
        "youtube:player_client=android,web",
        "--dump-single-json",
        "--no-download",
        "--no-warnings",
        url,
    ]

    if extra_args:
        args = args[:-1] + extra_args + [args[-1]]

    logger.info("Running yt-dlp command: %s", " ".join(args))

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed for {url}: {result.stderr or result.stdout}"
        )

    return json.loads(result.stdout)


def extract_youtube_id(url: str) -> str | None:
    m = YOUTUBE_ID_RE.search(url)
    return m.group(1) if m else None

def normalize_youtube_url(url: str) -> str:
    match = re.search(r"/shorts/([A-Za-z0-9_-]+)", url)

    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    return url


def _fetch_youtube_transcript_api(video_id: str) -> str | None:
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)

        return " ".join(
            snippet.text.strip()
            for snippet in transcript.snippets
            if getattr(snippet, "text", None)
        )

    except Exception as e:
        logger.warning(
            "youtube-transcript-api failed for %s: %s",
            video_id,
            str(e)
        )
        return None


def _fetch_subtitles_via_ytdlp(url: str) -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        out_tpl = str(Path(tmp) / "sub")
        cmd = [
            *YTDLP_CMD,
            *_ytdlp_base_args(),
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang",
            "en.*,en",
            "--sub-format",
            "vtt",
            "-o",
            out_tpl,
            url,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        vtt_files = list(Path(tmp).glob("*.vtt"))
        if not vtt_files:
            return None
        raw = vtt_files[0].read_text(encoding="utf-8", errors="ignore")
        lines = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("WEBVTT") or "-->" in line:
                continue
            if re.match(r"^\d+$", line):
                continue
            if line.startswith("<") and line.endswith(">"):
                continue
            lines.append(re.sub(r"<[^>]+>", "", line))
        # dedupe consecutive
        deduped: list[str] = []
        for ln in lines:
            if not deduped or deduped[-1] != ln:
                deduped.append(ln)
        return " ".join(deduped) if deduped else None


def _parse_upload_date(info: dict[str, Any]) -> str | None:
    ud = info.get("upload_date")
    if ud and len(ud) == 8:
        return f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}"
    return info.get("release_date")


def _safe_int(val: Any) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _engagement_rate(views: int, likes: int, comments: int) -> float:
    if views <= 0:
        return 0.0
    return round(((likes + comments) / views) * 100, 4)


def _platform_from_url(url: str) -> str:
    lower = url.lower()
    if "instagram.com" in lower:
        return "instagram"
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    return "unknown"


def fetch_video_data(url: str, video_id: str) -> dict[str, Any]:
    """Return normalized metadata + full transcript for one video."""

    platform = _platform_from_url(url)

    try:
        info = _run_ytdlp(url)
    except Exception as e:
        logger.warning("yt-dlp metadata failed: %s", str(e))

        info = {
            "id": extract_youtube_id(url),
            "title": "Unknown",
            "description": "",
            "tags": [],
        }

    views = _safe_int(info.get("view_count"))
    likes = _safe_int(info.get("like_count"))
    comments = _safe_int(info.get("comment_count"))

    hashtags: list[str] = []
    for tag in info.get("tags") or []:
        t = str(tag).lstrip("#")
        if t:
            hashtags.append(t)
    # Instagram often puts hashtags in description
    desc = info.get("description") or ""
    for m in re.findall(r"#(\w+)", desc):
        if m not in hashtags:
            hashtags.append(m)

    transcript: str | None = None
    if platform == "youtube":
        yt_id = extract_youtube_id(url) or info.get("id")
        if yt_id:
            transcript = _fetch_youtube_transcript_api(yt_id)
    if not transcript:
        transcript = _fetch_subtitles_via_ytdlp(url)
    if not transcript and desc:
        transcript = desc[:8000]
        logger.warning("Using description as transcript fallback for %s", video_id)

    if not transcript:
        raise RuntimeError(
            f"Could not obtain transcript for video {video_id} ({url}). "
            "Ensure the video has captions or a description."
        )

    follower_count = _safe_int(
        info.get("channel_follower_count")
        or info.get("follower_count")
        or info.get("uploader_follower_count")
    )
    if follower_count == 0:
        follower_count = None

    return {
        "video_id": video_id,
        "platform": platform,
        "url": url,
        "title": info.get("title") or "Untitled",
        "creator": info.get("uploader") or info.get("channel") or "Unknown",
        "follower_count": follower_count,
        "views": views,
        "likes": likes,
        "comments": comments,
        "engagement_rate": _engagement_rate(views, likes, comments),
        "hashtags": hashtags[:30],
        "upload_date": _parse_upload_date(info),
        "duration_seconds": _safe_int(info.get("duration")) or None,
        "thumbnail_url": info.get("thumbnail"),
        "transcript": transcript,
        "transcript_preview": transcript[:280] + ("…" if len(transcript) > 280 else ""),
    }


def ingest_pair(youtube_url: str, instagram_url: str) -> list[dict[str, Any]]:
    return [
        fetch_video_data(youtube_url, "A"),
        fetch_video_data(instagram_url, "B"),
    ]