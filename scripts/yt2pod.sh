#!/bin/bash
# yt2pod — pipe a YouTube URL into the personal podcast feed.
# Runs locally on Mac: residential IP + live Chrome cookies bypass YouTube anti-abuse.
# Usage:  yt2pod <youtube-url>

set -euo pipefail

URL="${1:-}"
if [ -z "$URL" ]; then
  echo "usage: yt2pod <youtube-url>" >&2
  exit 2
fi

# Repo root (this script lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Load credentials
ENV_FILE="$HOME/.yt-pod-feed.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "missing $ENV_FILE — see scripts/SETUP-LOCAL.md" >&2
  exit 1
fi
# shellcheck source=/dev/null
set -a; source "$ENV_FILE"; set +a

# Use Chrome cookies (live, no maintenance)
export YT_COOKIES_FROM_BROWSER="${YT_COOKIES_FROM_BROWSER:-chrome}"
export EPISODE_PREFIX="${EPISODE_PREFIX:-[YT] }"
export YT_URL="$URL"

echo "▶ $URL"

# Always pull latest yt-dlp before running (auto-stays current with YT changes)
python3 -m pip install --quiet --upgrade yt-dlp boto3 2>&1 | tail -3 || true

python3 scripts/add_episode.py
python3 scripts/build_feed.py

# Commit + push (triggers Netlify deploy via existing workflow)
if git diff --quiet -- episodes.json public/feed.xml; then
  echo "no changes — nothing to push (already in feed?)"
  exit 0
fi

git add episodes.json public/feed.xml
git commit -m "Add episode: $(python3 -c 'import json; eps=json.load(open("episodes.json")); print(eps[-1]["title"])' 2>/dev/null || echo "$URL")"
git push -q

echo "✓ pushed — feed will update at https://yt-pod-feed.netlify.app/feed.xml in ~30s"
echo "  pull-to-refresh in Pocket Casts to see the new episode"
