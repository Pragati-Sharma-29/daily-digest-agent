# Daily Digest Agent

Fetches ~70 RSS feeds daily, summarizes them with the Claude API into a structured Markdown digest, and serves them through a GitHub Pages frontend with Executive Summary, Launches, and Full Digest views — plus optional text-to-speech playback. Runs end-to-end on GitHub Actions.

---

## Project Structure

```
daily-digest-agent/
├── agent.py                    # Pipeline: fetch RSS feeds → summarize with Claude → save digest
├── requirements.txt
├── feeds_state.json            # Auto-managed feed health tracking (per-feed failure counts)
├── digests/                    # Auto-created; digest_YYYY-MM-DD.md files land here
├── index.html                  # GitHub Pages frontend (PWA) — reads digests straight from the repo
├── manifest.json / sw.js       # PWA manifest + service worker for index.html
├── genrate_audio                # Optional Google TTS script to pre-generate Neural2 voice audio (not wired into CI)
├── .gitignore
└── .github/
    └── workflows/
        ├── daily_digest.yml    # Runs the pipeline daily, commits the digest + feed state, triggers Pages rebuild
        ├── deploy_pages.yml    # Deploys index.html to GitHub Pages
        └── Claude.yml          # Claude Code GitHub Action — responds to "@claude" in issue/PR comments
```

---

## How it works

1. **Fetch** — `agent.py` pulls entries from `ALL_FEEDS` (grouped by category: AI labs, hyperscalers, VC blogs, cybersecurity, SaaS, data platforms, Economic Times, and more) via `feedparser`, keeping only entries from the last 2 days.
2. **Feed health** — results are tracked in `feeds_state.json`. A feed that fails 3 times in a day is skipped until the next day, when its failure count auto-resets.
3. **Summarize** — all fetched content is sent to the Claude API (`claude-sonnet-4-6`) in one call, with a prompt that enforces this exact structure:
   - **Executive Summary** — a short per-area rundown, always including a dedicated subsection covering Stratechery, TechCrunch, and a16z commentary
   - **Launches** — *only* new product launches / feature releases / GA announcements, grouped into four fixed tracks: AI Labs (Anthropic, OpenAI, DeepMind, Microsoft AI, Meta AI); Hyperscaler Enterprise SaaS & Data Platforms (GCP, Azure, AWS); Databricks, Snowflake, Meta, Rubrik & Atlan; and Grab & OGP
   - **Topic sections** — 6–10 themed sections across all sources, each with "What happened", "Key stories", and "What to watch"
4. **Save & publish** — the digest is written to `digests/digest_YYYY-MM-DD.md` and committed back to the repo, which triggers a GitHub Pages rebuild.
5. **Read** — `index.html`, served via GitHub Pages, fetches the latest digest(s) from the repo through the GitHub API and renders three tabs — **Executive Summary**, **Launches**, **Full Digest** — with per-section "listen" buttons (browser TTS, or pre-generated Neural2 audio if present under `audio/`).

---

## Setup

### 1. Clone & push to GitHub

```bash
git init
git add .
git commit -m "init: daily digest agent"
gh repo create daily-digest-agent --public --push
# or: git remote add origin https://github.com/YOUR_USERNAME/daily-digest-agent.git && git push -u origin main
```

### 2. Add repository secrets

Go to your repo → **Settings → Secrets and variables → Actions** and add:

| Secret | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | From [console.anthropic.com](https://console.anthropic.com/settings/billing) — needs active billing/credits |
| `STRATECHERY_FEED_URL` | Optional | Private Stratechery RSS URL; omit and that source is simply skipped |
| `ASIANOMETRY_FEED_URL` | Optional | Private Asianometry RSS URL; omit and that source is simply skipped |
| `GOOGLE_TTS_KEY` | Optional | Only needed if you run `genrate_audio` yourself to pre-generate Neural2 voice audio |

`GITHUB_TOKEN` is provided automatically by Actions for committing the digest and triggering the Pages deploy.

### 3. Enable GitHub Pages via GitHub Actions

Go to **Settings → Pages → Build and deployment → Source** and select **"GitHub Actions"** (not "Deploy from a branch"). The branch-deploy/Jekyll source will get stuck trying to build this repo and never finish — `deploy_pages.yml` is what actually builds and ships `index.html`.

### 4. Add or adjust feed sources

Edit the `ALL_FEEDS` list in `agent.py`, grouped by category comment headers:

```python
ALL_FEEDS = [
    # ── Enterprise & B2B SaaS ──────────────────────────────────────────
    {"name": "a16z", "url": "https://a16z.com/feed/"},
    # ...
]
```

Currently covers: VC/industry blogs, AI lab blogs (OpenAI, Anthropic, DeepMind, Microsoft AI, Meta AI), cybersecurity (Rubrik, Okta, Hacker News, Krebs, Dark Reading, BleepingComputer), SaaS (SaaStr, Tomasz Tunguz), hyperscalers (GCP, Azure, AWS), data platforms (Databricks, Snowflake, Atlan), Grab & OGP, Andrej Karpathy, Economic Times, and general tech news. A feed that 404s repeatedly will auto-disable for the day — check the Action logs or `feeds_state.json` if a source stops showing up.

### 5. Adjust the schedule (optional)

Edit the cron expression in `.github/workflows/daily_digest.yml`:

```yaml
- cron: '0 14 * * *'   # 2 PM UTC daily
```

Use [crontab.guru](https://crontab.guru) to build your preferred schedule.

---

## Running locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
export STRATECHERY_FEED_URL=your_feed_url_here   # optional
export ASIANOMETRY_FEED_URL=your_feed_url_here   # optional
python agent.py
```

The digest is saved to `digests/digest_YYYY-MM-DD.md`.

---

## Manual GitHub Actions trigger

Go to **Actions → Daily Digest Agent → Run workflow** to trigger it on demand without waiting for the schedule.

---

## Output example

```markdown
# Daily Tech Digest — 2026-11-19

## Executive Summary

### AI & LLMs
Anthropic shipped a new agentic coding feature and OpenAI pushed a reasoning
model update — the bigger story is how fast agent tooling is converging
across labs. ([Source](https://www.anthropic.com/...))

### Stratechery & Analyst Commentary
Stratechery argued that the AI infra moat is shifting toward distribution
rather than model quality. ([Source](https://stratechery.com/...))

## Launches

### AI Labs
- **Claude Sonnet 4.6** — Anthropic released an updated Sonnet model with
  stronger agentic coding performance. ([Source](https://www.anthropic.com/...))

### Hyperscaler Enterprise SaaS & Data Platforms
No new launches today.

### Databricks, Snowflake, Meta, Rubrik & Atlan
- **Databricks Lakebase GA** — Databricks announced general availability of
  its managed Postgres offering. ([Source](https://www.databricks.com/...))

### Grab & OGP
No new launches today.

## Agentic AI

### What happened
...

### Key stories
- **[Story headline]** — ... ([Source](url))

### What to watch
...
```
