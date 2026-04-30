#!/usr/bin/env python3
"""
add_episode.py — Download a YouTube video as audio, upload to R2, and append to episodes.json.

Usage (CI):
  YT_URL=https://youtu.be/... python3 scripts/add_episode.py

Required env vars:
  YT_URL            YouTube URL to fetch
  R2_ACCESS_KEY_ID  Cloudflare R2 access key
  R2_SECRET_ACCESS_KEY
  R2_ACCOUNT_ID
  R2_BUCKET         e.g. yt-pod-audio
  R2_PUBLIC_BASE    Public URL prefix for the bucket (e.g. https://pub-xxxxx.r2.dev or custom domain)
  EPISODE_PREFIX    Optional title prefix (default "[YT] ")
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config

YT_URL = os.environ["YT_URL"].strip()
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET = os.environ["R2_BUCKET"]
R2_PUBLIC_BASE = os.environ["R2_PUBLIC_BASE"].rstrip("/")
EPISODE_PREFIX = os.environ.get("EPISODE_PREFIX", "[YT] ")

REPO_ROOT = Path(__file__).resolve().parent.parent
EPISODES_PATH = REPO_ROOT / "episodes.json"


def slugify(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    text = re.sub(r"[\s-]+", "-", text)
    return text[:max_len].strip("-").lower() or "episode"


# yt-dlp args to bypass YouTube's bot detection on cloud IPs
# tv_embedded + ios player clients still serve metadata + streams without auth
YTDLP_BYPASS = [
    "--extractor-args", "youtube:player_client=tv,ios,web_safari",
    "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "--retries", "3",
    "--sleep-interval", "1",
]


def run_yt_dlp(args, **kw):
    proc = subprocess.run(
        ["yt-dlp", *YTDLP_BYPASS, *args],
        capture_output=True, text=True, **kw,
    )
    if proc.returncode != 0:
        sys.stderr.write(f"yt-dlp failed (rc={proc.returncode})\n")
        sys.stderr.write("--- stdout ---\n" + proc.stdout[-2000:] + "\n")
        sys.stderr.write("--- stderr ---\n" + proc.stderr[-2000:] + "\n")
        raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
    return proc


def fetch_metadata(url: str) -> dict:
    """Use yt-dlp to get video metadata without downloading."""
    result = run_yt_dlp(["-J", "--no-warnings", url])
    return json.loads(result.stdout)


def download_audio(url: str, out_dir: Path) -> Path:
    """Download best audio, encode to 96kbps mono mp3, return path."""
    template = str(out_dir / "%(id)s.%(ext)s")
    run_yt_dlp([
        "-f", "bestaudio/best",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "96K",
        "--postprocessor-args", "-ac 1",
        "-o", template,
        "--embed-metadata",
        "--no-warnings",
        url,
    ])
    mp3s = list(out_dir.glob("*.mp3"))
    if not mp3s:
        raise RuntimeError("no mp3 produced")
    return mp3s[0]


def upload_to_r2(local_path: Path, key: str) -> str:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
    s3.upload_file(
        str(local_path),
        R2_BUCKET,
        key,
        ExtraArgs={"ContentType": "audio/mpeg"},
    )
    return f"{R2_PUBLIC_BASE}/{key}"


def main():
    print(f"Fetching: {YT_URL}")
    meta = fetch_metadata(YT_URL)

    title = meta.get("title", "Untitled")
    description = meta.get("description") or meta.get("uploader", "")
    if len(description) > 4000:
        description = description[:4000] + "…"
    uploader = meta.get("uploader") or meta.get("channel", "Unknown")
    duration = int(meta.get("duration") or 0)
    yt_id = meta.get("id", uuid.uuid4().hex[:11])
    thumbnail = meta.get("thumbnail")
    upload_date = meta.get("upload_date")
    pub_dt = datetime.now(timezone.utc).isoformat()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        print("Downloading audio…")
        mp3 = download_audio(YT_URL, tmp_path)
        size = mp3.stat().st_size
        print(f"  {mp3.name} ({size/1024/1024:.1f} MB)")

        key = f"audio/{yt_id}-{slugify(title)}.mp3"
        print(f"Uploading to R2: {key}")
        url = upload_to_r2(mp3, key)
        print(f"  {url}")

    episodes = json.loads(EPISODES_PATH.read_text() or "[]")
    if any(e.get("yt_id") == yt_id for e in episodes):
        print(f"Episode {yt_id} already exists; skipping append.")
        return

    episodes.append({
        "yt_id": yt_id,
        "title": f"{EPISODE_PREFIX}{title}",
        "description": description,
        "uploader": uploader,
        "duration_seconds": duration,
        "audio_url": url,
        "audio_size_bytes": size,
        "thumbnail_url": thumbnail,
        "yt_url": YT_URL,
        "upload_date": upload_date,
        "added_at": pub_dt,
    })

    EPISODES_PATH.write_text(json.dumps(episodes, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(episodes)} episodes to {EPISODES_PATH}")


if __name__ == "__main__":
    main()
