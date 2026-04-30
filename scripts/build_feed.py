#!/usr/bin/env python3
"""
build_feed.py — Generate a podcast-spec RSS feed from episodes.json.
"""
import json
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

REPO_ROOT = Path(__file__).resolve().parent.parent
EPISODES_PATH = REPO_ROOT / "episodes.json"
OUT_PATH = REPO_ROOT / "public" / "feed.xml"

FEED_TITLE = os.environ.get("FEED_TITLE", "Garrison's YouTube Pod Feed")
FEED_DESCRIPTION = os.environ.get(
    "FEED_DESCRIPTION",
    "A personal podcast feed of YouTube videos extracted as audio.",
)
FEED_LINK = os.environ.get("FEED_LINK", "https://yt-pod-feed.netlify.app/")
FEED_AUTHOR = os.environ.get("FEED_AUTHOR", "Garrison Lovely")
FEED_EMAIL = os.environ.get("FEED_EMAIL", "me@garrisonlovely.com")
FEED_LANG = os.environ.get("FEED_LANG", "en-us")
FEED_IMAGE = os.environ.get("FEED_IMAGE", "")  # optional cover art URL


def parse_dt(s: str) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def main():
    episodes = json.loads(EPISODES_PATH.read_text() or "[]")
    # newest first
    episodes.sort(key=lambda e: e.get("added_at", ""), reverse=True)

    now_rfc = format_datetime(datetime.now(timezone.utc))

    items_xml = []
    for ep in episodes:
        title = escape(ep.get("title", "Untitled"))
        description = escape(ep.get("description", ""))
        audio_url = ep.get("audio_url", "")
        audio_size = ep.get("audio_size_bytes", 0)
        duration = ep.get("duration_seconds", 0)
        guid = ep.get("yt_id") or audio_url
        pub_rfc = format_datetime(parse_dt(ep.get("added_at", "")))
        thumbnail = ep.get("thumbnail_url", "") or FEED_IMAGE
        yt_url = ep.get("yt_url", "")
        author = escape(ep.get("uploader", FEED_AUTHOR))

        link_block = ""
        if yt_url:
            link_block = f"<link>{escape(yt_url)}</link>"

        image_block = ""
        if thumbnail:
            image_block = f'<itunes:image href="{escape(thumbnail)}"/>'

        items_xml.append(f"""    <item>
      <title>{title}</title>
      {link_block}
      <description><![CDATA[{ep.get("description", "")}]]></description>
      <pubDate>{pub_rfc}</pubDate>
      <guid isPermaLink="false">{escape(guid)}</guid>
      <enclosure url="{escape(audio_url)}" length="{audio_size}" type="audio/mpeg"/>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:author>{author}</itunes:author>
      {image_block}
      <itunes:explicit>false</itunes:explicit>
    </item>""")

    image_global = ""
    if FEED_IMAGE:
        image_global = f"""    <image>
      <url>{escape(FEED_IMAGE)}</url>
      <title>{escape(FEED_TITLE)}</title>
      <link>{escape(FEED_LINK)}</link>
    </image>
    <itunes:image href="{escape(FEED_IMAGE)}"/>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{escape(FEED_TITLE)}</title>
    <link>{escape(FEED_LINK)}</link>
    <description>{escape(FEED_DESCRIPTION)}</description>
    <language>{FEED_LANG}</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <itunes:author>{escape(FEED_AUTHOR)}</itunes:author>
    <itunes:summary>{escape(FEED_DESCRIPTION)}</itunes:summary>
    <itunes:owner>
      <itunes:name>{escape(FEED_AUTHOR)}</itunes:name>
      <itunes:email>{escape(FEED_EMAIL)}</itunes:email>
    </itunes:owner>
    <itunes:category text="Technology"/>
    <itunes:explicit>false</itunes:explicit>
    <atom:link href="{escape(FEED_LINK)}feed.xml" rel="self" type="application/rss+xml"/>
{image_global}
{chr(10).join(items_xml)}
  </channel>
</rss>
"""
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(rss)
    print(f"Wrote {OUT_PATH} with {len(episodes)} episodes")


if __name__ == "__main__":
    main()
