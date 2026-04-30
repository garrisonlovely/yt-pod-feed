# YT-to-podcast feed — setup

Personal pipeline: paste a YouTube URL anywhere, audio appears in Pocket Casts.

## Architecture

`YT URL → GitHub repository_dispatch → Action runs yt-dlp → MP3 uploads to Cloudflare R2 → episodes.json updated → feed.xml regenerated → committed to repo → Netlify auto-deploys → Pocket Casts polls feed.xml`

## One-time setup

### 1. Cloudflare R2 (audio host)

1. Open https://dash.cloudflare.com → R2 (sidebar).
2. If prompted, click **Enable R2** (free tier, no card needed for ≤10 GB/mo).
3. **Create bucket**: name `yt-pod-audio`, region "Automatic". Hit Create.
4. Open the bucket → **Settings** → **Public access** → **Allow Access** for `r2.dev`. Note the public dev URL (looks like `https://pub-XXXXXXXXXX.r2.dev`).
5. Top-right → **Manage R2 API tokens** → **Create API token**:
   - Token name: `yt-pod-feed`
   - Permissions: **Object Read & Write**
   - Specify bucket: `yt-pod-audio`
   - TTL: leave default
6. Copy:
   - **Access Key ID**
   - **Secret Access Key**
   - **Account ID** (visible top-right of any R2 page, or in URL)
   - **Public R2.dev URL** (from step 4)

### 2. GitHub secrets

In the GitHub repo settings → Secrets and variables → Actions, add:

| Name | Value |
|---|---|
| `R2_ACCESS_KEY_ID` | from step 5 |
| `R2_SECRET_ACCESS_KEY` | from step 5 |
| `R2_ACCOUNT_ID` | from step 5 |
| `R2_BUCKET` | `yt-pod-audio` |
| `R2_PUBLIC_BASE` | the `https://pub-XXX.r2.dev` URL from step 4 |
| `NETLIFY_AUTH_TOKEN` | (already set up — can reuse the existing one) |
| `NETLIFY_SITE_ID` | from the new Netlify site for this repo |

(I'll wire NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID for you once the Netlify site is created.)

### 3. iOS Shortcut (phone trigger)

Create a fine-grained PAT scoped just to this repo:

1. https://github.com/settings/personal-access-tokens/new
2. Token name: `yt-pod-shortcut`
3. Resource owner: `garrisonlovely`
4. Repository access: only `garrisonlovely/yt-pod-feed`
5. Repository permissions:
   - **Contents**: Read and write
   - **Metadata**: Read-only (auto-set)
6. Generate, copy the `github_pat_…` token.

Then on iPhone:

1. Open the **Shortcuts** app → "+" to create a new shortcut.
2. Name it `Send to Pod Feed`.
3. Add actions:
   - **Get URLs from Input** (Action library: "URLs")
   - **Get contents of URL** action with these settings:
     - URL: `https://api.github.com/repos/garrisonlovely/yt-pod-feed/dispatches`
     - Method: `POST`
     - Headers:
       - `Accept` → `application/vnd.github+json`
       - `Authorization` → `Bearer github_pat_YOUR_TOKEN_HERE`
       - `X-GitHub-Api-Version` → `2022-11-28`
     - Request Body: JSON
       - `event_type` → `add-episode`
       - `client_payload` → Dictionary:
         - `url` → "Shortcut Input" (variable, the YouTube URL)
4. (Optional) Add **Show Notification** action: "Sent to feed: [Shortcut Input]"
5. Settings (top-right "i" icon) → toggle **Use with Share Sheet** ON. Share Sheet types: limit to URLs (otherwise it appears for everything).

Now from any YouTube link on your phone: Share → Send to Pod Feed. Done.

### 4. Pocket Casts subscription

1. Open Pocket Casts → Profile → Add a podcast → **Submit a Feed URL** (might be under "Add Podcast" → URL option).
2. Paste your Netlify feed URL: `https://yt-pod-feed.netlify.app/feed.xml` (or whatever subdomain you set).
3. Subscribe.

New episodes typically appear within 30–60 minutes of submission. Pull-to-refresh in Pocket Casts to force a feed re-poll.

## Mac CLI alternative

If you'd rather submit from your Mac:

```bash
# Add to ~/.zshrc (or wherever)
export YT2POD_TOKEN=github_pat_YOUR_TOKEN_HERE
yt2pod() {
  curl -sS -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $YT2POD_TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    https://api.github.com/repos/garrisonlovely/yt-pod-feed/dispatches \
    -d "{\"event_type\":\"add-episode\",\"client_payload\":{\"url\":\"$1\"}}" \
    && echo "queued: $1"
}
```

Usage: `yt2pod https://www.youtube.com/watch?v=...`

## Operational notes

- **First deploy** rebuilds an empty `feed.xml`. Pocket Casts may complain about an empty feed; just submit your first video and refresh.
- **yt-dlp updates**: the Action installs the latest yt-dlp on every run, so it auto-keeps up with YouTube anti-scraping changes.
- **R2 free tier**: 10 GB storage, 1M Class A ops/month, 10M Class B ops/month — covers personal usage by 100×.
- **Long videos**: a 2-hour video at 96 kbps mono ≈ 80 MB. Max episode size in Pocket Casts is well above this.
- **Editing manually**: `episodes.json` is the source of truth. You can rename titles, edit descriptions, etc., then run `python3 scripts/build_feed.py` and push.
