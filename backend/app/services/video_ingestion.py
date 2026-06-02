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

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)

YTDLP_CMD = [sys.executable, "-m", "yt_dlp"]

YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
)

_BOT_MARKERS = ("sign in to confirm", "not a bot", "cookies-from-browser", "confirm you're not a bot")


def _is_container_env() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT")) or os.path.exists("/.dockerenv")


def _cookie_settings() -> tuple[str, str]:
    """Return (browser_name, cookies_file_path) from env/settings."""
    browser = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()
    cookies_file = os.getenv("YTDLP_COOKIES_FILE", "").strip()
    if not browser or not cookies_file:
        try:
            from app.config import get_settings

            s = get_settings()
            browser = browser or (s.ytdlp_cookies_browser or "").strip()
            cookies_file = cookies_file or (s.ytdlp_cookies_file or "").strip()
        except Exception:
            pass
    return browser, cookies_file


def _ytdlp_auth_args() -> list[str]:
    """Browser or cookies.txt — skipped in Railway/Docker unless cookies file is mounted."""
    browser, cookies_file = _cookie_settings()
    args: list[str] = []

    if cookies_file and Path(cookies_file).is_file():
        args.extend(["--cookies", cookies_file])
        logger.info("yt-dlp using cookies file: %s", cookies_file)
        return args

    if _is_container_env():
        if browser:
            logger.warning(
                "YTDLP_COOKIES_BROWSER=%s ignored in container; set YTDLP_COOKIES_FILE "
                "to a mounted cookies.txt for YouTube bot checks",
                browser,
            )
        return args

    if browser:
        args.extend(["--cookies-from-browser", browser])
        logger.info("yt-dlp using cookies from browser: %s", browser)
    return args


def _format_ytdlp_error(url: str, stderr: str) -> str:
    err = (stderr or "").strip()
    if any(m in err.lower() for m in _BOT_MARKERS):
        if _is_container_env():
            return (
                f"YouTube blocked yt-dlp for {url} (bot check). On Railway, export cookies.txt "
                "from your browser (logged into YouTube) and set YTDLP_COOKIES_FILE=/path/in/container. "
                "See https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
            )
        return (
            f"YouTube blocked yt-dlp for {url} (bot check). Fix locally: add to backend/.env:\n"
            "  YTDLP_COOKIES_BROWSER=chrome\n"
            "(or edge / firefox — browser must be installed and you logged into YouTube)\n"
            "Then restart the backend. Alternative: export cookies.txt and set YTDLP_COOKIES_FILE=./cookies.txt\n\n"
            f"Raw error: {err[:500]}"
        )
    return f"yt-dlp failed for {url}: {err[:800]}"


def _run_ytdlp_once(url: str, extra: list[str]) -> subprocess.CompletedProcess:
    args = [
        *YTDLP_CMD,
        *_ytdlp_auth_args(),
        *extra,
        "--dump-single-json",
        "--no-download",
        "--no-warnings",
        url,
    ]
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _run_ytdlp(url: str, extra_args: list[str] | None = None) -> dict[str, Any]:
    """Run yt-dlp with auth cookies and YouTube client fallbacks on bot errors."""
    extras_list: list[list[str]] = [extra_args or []]
    # Extra attempts when YouTube serves the "not a bot" page (no cookies yet)
    if "youtube" in url.lower() or "youtu.be" in url.lower():
        extras_list.append(
            ["--extractor-args", "youtube:player_client=android,web"]
        )
        extras_list.append(
            ["--extractor-args", "youtube:player_client=ios,web"]
        )

    last_stderr = ""
    seen: set[tuple[str, ...]] = set()
    for extra in extras_list:
        key = tuple(extra)
        if key in seen:
            continue
        seen.add(key)
        result = _run_ytdlp_once(url, list(extra))
        if result.returncode == 0:
            return json.loads(result.stdout)
        last_stderr = result.stderr or result.stdout or ""
        if not any(m in last_stderr.lower() for m in _BOT_MARKERS):
            break

    raise RuntimeError(_format_ytdlp_error(url, last_stderr))


def extract_youtube_id(url: str) -> str | None:
    m = YOUTUBE_ID_RE.search(url)
    return m.group(1) if m else None


def _fetch_youtube_transcript_api(video_id: str) -> str | None:
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)
        return " ".join(
            snippet.text.strip()
            for snippet in transcript.snippets
            if getattr(snippet, "text", None)
        )
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
        logger.info("youtube-transcript-api: %s", e)
        return None


def _fetch_subtitles_via_ytdlp(url: str) -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        out_tpl = str(Path(tmp) / "sub")
        cmd = [
            *YTDLP_CMD,
            *_ytdlp_auth_args(),
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


def _fetch_youtube_with_transcript_fallback(url: str, video_id: str) -> dict[str, Any]:
    """If yt-dlp metadata is blocked, still try transcript API + minimal metadata."""
    yt_id = extract_youtube_id(url) or video_id
    transcript = _fetch_youtube_transcript_api(yt_id) if yt_id else None
    if not transcript:
        transcript = _fetch_subtitles_via_ytdlp(url)
    if not transcript:
        raise RuntimeError(_format_ytdlp_error(url, "No transcript after bot-block fallback"))

    return {
        "video_id": video_id,
        "platform": "youtube",
        "url": url,
        "title": f"YouTube video {yt_id}",
        "creator": "Unknown",
        "follower_count": None,
        "views": 0,
        "likes": 0,
        "comments": 0,
        "engagement_rate": 0.0,
        "hashtags": [],
        "upload_date": None,
        "duration_seconds": None,
        "thumbnail_url": f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg" if yt_id else None,
        "transcript": transcript,
        "transcript_preview": transcript[:280] + ("…" if len(transcript) > 280 else ""),
    }


def fetch_video_data(url: str, video_id: str) -> dict[str, Any]:
    """Return normalized metadata + full transcript for one video."""
    platform = _platform_from_url(url)

    try:
        info = _run_ytdlp(url)
    except RuntimeError as e:
        if platform == "youtube" and any(m in str(e).lower() for m in _BOT_MARKERS):
            logger.warning("yt-dlp bot block for %s; trying transcript-only fallback", url)
            return _fetch_youtube_with_transcript_fallback(url, video_id)
        raise

    views = _safe_int(info.get("view_count"))
    likes = _safe_int(info.get("like_count"))
    comments = _safe_int(info.get("comment_count"))

    hashtags: list[str] = []
    for tag in info.get("tags") or []:
        t = str(tag).lstrip("#")
        if t:
            hashtags.append(t)
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
