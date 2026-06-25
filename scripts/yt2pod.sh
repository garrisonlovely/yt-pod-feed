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

# yt-dlp is managed by brew on Mac — `brew upgrade yt-dlp` to update.
# boto3 is the only Python dep we manage.
python3 -c "import boto3" 2>/dev/null || python3 -m pip install --quiet --user --break-system-packages boto3

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
echo "✓ pushed to GitHub"

# Deploy to Netlify from this Mac (the local CLI is authenticated; the
# push-triggered GitHub Action is disabled because its token kept expiring).
DEPLOY_PATH="$(command -v netlify || echo /opt/homebrew/bin/netlify)"
if [ -x "$DEPLOY_PATH" ]; then
  "$DEPLOY_PATH" deploy --prod --dir public --no-build \
    --message "feed update: $(git log -1 --pretty=%s)" \
    && echo "✓ deployed to Netlify" \
    || echo "⚠ netlify deploy failed — content is in git; run 'netlify deploy --prod --dir public --no-build' from $REPO_ROOT"
else
  echo "⚠ netlify CLI not found — run 'netlify deploy --prod --dir public --no-build' from $REPO_ROOT to publish"
fi

echo "✓ feed live at https://yt-pod-feed.netlify.app/feed.xml — pull-to-refresh in Pocket Casts"
