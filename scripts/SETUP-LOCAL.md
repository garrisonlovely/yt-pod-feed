# Mac-local setup

Personal YT → Pocket Casts feed, running entirely on your Mac.

## One-time setup (~10 min)

### 1. Dependencies

```bash
brew install yt-dlp ffmpeg
python3 -m pip install --user boto3
```

### 2. Credentials file

Create `~/.yt-pod-feed.env` with R2 + (optional) overrides. Pulling the values that are already in your GitHub repo secrets — copy from there:

```bash
cat > ~/.yt-pod-feed.env <<'EOF'
R2_ACCESS_KEY_ID=f45706832deb7597288737b0c478ba14
R2_SECRET_ACCESS_KEY=e55c8ae7ada61ee765e2b1072a9add572e6c9db7cf1e2de3624bbd89222415d2
R2_ACCOUNT_ID=fd4be337c12518eab8dd73b47dd8b536
R2_BUCKET=yt-pod-audio
R2_PUBLIC_BASE=https://pub-51495ffc2fcc49d1a6b45df402efbc56.r2.dev
EOF
chmod 600 ~/.yt-pod-feed.env
```

### 3. Shell alias

Add to `~/.zshrc` (or wherever):

```bash
alias yt2pod='~/code/yt-pod-feed/scripts/yt2pod.sh'
```

Reload: `source ~/.zshrc`

### 4. Test

```bash
yt2pod https://www.youtube.com/watch?v=BbIaYFHxW3Y
```

You should see download → upload → push → done. The feed updates at `https://yt-pod-feed.netlify.app/feed.xml` in ~30 seconds.

### 5. Subscribe Pocket Casts (one-time)

Pocket Casts → Profile → Add a podcast → Submit a Feed URL → paste:

```
https://yt-pod-feed.netlify.app/feed.xml
```

Pull-to-refresh after each `yt2pod` run to see the new episode.

## Optional: Mac Shortcut for share-sheet trigger

Lets you hit Share → "Send to Pod Feed" from any YouTube tab in Chrome/Safari.

1. Open **Shortcuts.app** on Mac.
2. New Shortcut → name it `Send to Pod Feed`.
3. Add action: **Run Shell Script**
   - Shell: `/bin/bash`
   - Pass input: `as arguments`
   - Script:
     ```bash
     ~/code/yt-pod-feed/scripts/yt2pod.sh "$1"
     ```
4. Right pane → Shortcut Details:
   - Toggle **Use as Quick Action**
   - Toggle **Services Menu** + **Share Sheet**
   - "Receive: URLs"
5. Save.

Now from any YouTube tab: Share menu → Send to Pod Feed. Done.

## How it works

- yt-dlp uses `--cookies-from-browser chrome` to read your live Chrome cookies — no manual cookie export, no expiry maintenance.
- Your residential IP doesn't trip YouTube's anti-bot.
- Audio gets re-encoded to 96 kbps mono mp3 (small files, fine for talks).
- Uploads to your R2 bucket (free tier, ~10GB).
- Updates `episodes.json` + regenerates `public/feed.xml`.
- `git push` triggers Netlify auto-deploy of the new feed.xml.
- Pocket Casts pulls the feed; new episode appears.

## Notes

- **First run prompts for keychain access**: macOS will ask Chrome to share its cookies with `yt-dlp`. Click Allow once.
- **Chrome must have a YouTube login** for best results (handles age-gated, members-only content).
- **Updates**: the script auto-runs `pip install --upgrade yt-dlp` each time so you stay current with YouTube anti-scraping changes.
- **If a video fails**: try a different format flag, or check that yt-dlp is up to date (`brew upgrade yt-dlp` is also good).
