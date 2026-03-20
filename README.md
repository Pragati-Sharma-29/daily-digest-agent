# Daily Digest Agent

An ADK-powered agent that scrapes a set of websites daily, summarizes the content using Gemini, and saves a Markdown digest — scheduled via GitHub Actions.

---

## Project Structure

```
daily-digest-agent/
├── agent.py                          # ADK pipeline (scrape → summarize → save)
├── requirements.txt
├── .gitignore
├── digests/                          # Auto-created; digest_YYYY-MM-DD.md files land here
└── .github/
    └── workflows/
        └── daily_digest.yml          # GitHub Actions schedule (runs daily at 8 AM UTC)
```

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

### 2. Add your Google API key as a secret

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `GOOGLE_API_KEY`
4. Value: your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 3. Configure your sites

Edit the `SITES` list in `agent.py`:

```python
SITES = [
    {"name": "My_Blog",    "url": "https://myblog.com/"},
    {"name": "Hacker_News","url": "https://news.ycombinator.com/"},
    # Add as many as you need
]
```

### 4. Adjust the schedule (optional)

Edit the cron expression in `.github/workflows/daily_digest.yml`:

```yaml
- cron: '0 8 * * *'   # 8 AM UTC daily
```

Use [crontab.guru](https://crontab.guru) to build your preferred schedule.

---

## Running locally

```bash
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key_here
python agent.py
```

The digest is saved to `digests/digest_YYYY-MM-DD.md`.

---

## Manual GitHub Actions trigger

Go to **Actions → Daily Digest Agent → Run workflow** to trigger it on demand without waiting for the schedule.

---

## Output example

```markdown
# Daily Tech Digest — 2026-03-20

## TechCrunch AI
- OpenAI releases new reasoning model...
- EU AI Act enforcement begins...

## Hacker News
- Show HN: Build your own vector DB...

## ⭐ Top Story
The EU AI Act enforcement kick-off is the most significant...
```
