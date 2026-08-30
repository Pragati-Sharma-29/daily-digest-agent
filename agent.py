import os
import re
import json
import feedparser
import anthropic
from html import unescape
from datetime import datetime, timedelta
from urllib.parse import urlparse

ALL_FEEDS = [
    # ── Enterprise & B2B SaaS ──────────────────────────────────────────────
    {"name": "a16z",               "url": "https://a16z.com/feed/"},
    {"name": "Bessemer",           "url": "https://www.bvp.com/atlas/rss.xml"},
    {"name": "Battery_Ventures",   "url": "https://www.battery.com/feed/"},
    {"name": "Insight_Partners",   "url": "https://www.insightpartners.com/feed/"},
    {"name": "Sapphire_Ventures",  "url": "https://sapphireventures.com/feed/"},

    # ── Security ───────────────────────────────────────────────────────────
    {"name": "Sequoia",            "url": "https://www.sequoiacap.com/feed/"},
    {"name": "YL_Ventures",        "url": "https://ylventures.com/feed/"},
    {"name": "Team8",              "url": "https://team8.vc/feed/"},
    {"name": "NightDragon",        "url": "https://nightdragon.com/feed/"},

    # ── Industry & Deep Tech ───────────────────────────────────────────────
    {"name": "Greylock",           "url": "https://greylock.com/feed/"},
    {"name": "Lightspeed",         "url": "https://lsvp.com/feed/"},
    {"name": "Redpoint",           "url": "https://www.redpoint.com/feed/"},
    {"name": "First_Round_Review", "url": "https://review.firstround.com/feed.xml"},
    {"name": "NFX",                "url": "https://www.nfx.com/feed"},

    # ── Agentic AI & LLMs ─────────────────────────────────────────────────
    {"name": "Madrona",            "url": "https://www.madrona.com/feed/"},
    {"name": "Felicis",            "url": "https://www.felicis.com/feed/"},
    {"name": "LangChain_Blog",     "url": "https://blog.langchain.dev/rss/"},
    {"name": "Conviction",         "url": "https://www.conviction.com/feed"},

    # ── Operator Blogs ─────────────────────────────────────────────────────
    {"name": "OpenAI",             "url": "https://openai.com/blog/rss.xml"},
    {"name": "Anthropic",          "url": "https://www.anthropic.com/feed.xml"},
    {"name": "Google_DeepMind",    "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "Microsoft_AI",       "url": "https://blogs.microsoft.com/ai/feed/"},

    # ── Tech News ─────────────────────────────────────────────────────────
    {"name": "TechCrunch_AI",      "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "Stratechery",        "url": os.environ.get("STRATECHERY_FEED_URL", "")},
    {"name": "Asianometry",        "url": os.environ.get("ASIANOMETRY_FEED_URL", "")},
    {"name": "TechCrunch",         "url": "https://techcrunch.com/feed/"},
    {"name": "The_Verge_Tech",     "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Hacker_News",        "url": "https://news.ycombinator.com/rss"},
    {"name": "MIT_Tech_Review",    "url": "https://www.technologyreview.com/feed/"},
    {"name": "Wired_AI",           "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss"},
    {"name": "VentureBeat_AI",     "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Ars_Technica",       "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},

    # ── GCP AI & Machine Learning ─────────────────────────────────────────
    {"name": "GCP_AI_ML",           "url": "https://cloudblog.withgoogle.com/products/ai-machine-learning/rss/"},
    {"name": "GCP_Vertex_AI",       "url": "https://cloudblog.withgoogle.com/products/ai-machine-learning/rss/"},
    {"name": "Google_Research",     "url": "https://research.google/blog/rss/"},
    {"name": "GCP_Developers",      "url": "https://cloudblog.withgoogle.com/topics/developers-practitioners/rss/"},

    # ── GCP Data Analytics ────────────────────────────────────────────────
    {"name": "GCP_Data_Analytics",  "url": "https://cloudblog.withgoogle.com/products/data-analytics/rss/"},
    {"name": "GCP_BigQuery",        "url": "https://cloudblog.withgoogle.com/products/bigquery/rss/"},
    {"name": "GCP_Dataplex",        "url": "https://cloudblog.withgoogle.com/products/data-analytics/rss/"},
    {"name": "GCP_Looker",          "url": "https://cloudblog.withgoogle.com/products/looker/rss/"},

    # ── GCP Databases ─────────────────────────────────────────────────────
    {"name": "GCP_Databases",       "url": "https://cloudblog.withgoogle.com/products/databases/rss/"},
    {"name": "GCP_AlloyDB",         "url": "https://cloudblog.withgoogle.com/products/alloydb/rss/"},
    {"name": "GCP_Spanner",         "url": "https://cloudblog.withgoogle.com/products/spanner/rss/"},
    {"name": "GCP_Cloud_SQL",       "url": "https://cloudblog.withgoogle.com/products/cloud-sql/rss/"},

    # ── GCP General ───────────────────────────────────────────────────────
    {"name": "GCP_Blog",            "url": "https://cloudblog.withgoogle.com/rss/"},
    {"name": "GCP_Inside",          "url": "https://cloudblog.withgoogle.com/topics/inside-google-cloud/rss/"},

    # ── Economic Times ────────────────────────────────────────────────────
    {"name": "ET_Tech",             "url": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms"},
    {"name": "ET_AI",               "url": "https://economictimes.indiatimes.com/tech/artificial-intelligence/rssfeeds/78570561.cms"},
    {"name": "ET_Startups",         "url": "https://economictimes.indiatimes.com/tech/startups/rssfeeds/78570561.cms"},
    {"name": "ET_Markets",          "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"},
    {"name": "ET_Economy",          "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"},
    {"name": "ET_IT",               "url": "https://economictimes.indiatimes.com/tech/information-tech/rssfeeds/13357270.cms"},
    # ── Andrej Karpathy ────────────────────────────────────────────────────
    {"name": "Andrej_Karpathy",     "url": "https://karpathy.github.io/feed.xml"},
    # ── Cybersecurity (Rubrik, Okta & Industry) ───────────────────────────
    {"name": "Rubrik_Blog",         "url": "https://www.rubrik.com/blog/feed"},
    {"name": "Okta_Blog",           "url": "https://www.okta.com/blog/feed/"},
    {"name": "The_Hacker_News",     "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "Krebs_On_Security",   "url": "https://krebsonsecurity.com/feed/"},
    {"name": "Dark_Reading",        "url": "https://www.darkreading.com/rss.xml"},
    {"name": "BleepingComputer",    "url": "https://www.bleepingcomputer.com/feed/"},
    # ── SaaS ────────────────────────────────────────────────────────────────
    {"name": "SaaStr",              "url": "https://www.saastr.com/feed/"},
    {"name": "Tomasz_Tunguz",       "url": "https://tomtunguz.com/index.xml"},
]

FEEDS_STATE_FILE = "feeds_state.json"
MAX_SUMMARY_LENGTH = 200
MAX_FAILURES = 3


def strip_html(text) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = str(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_entry_recent(entry, max_age_days: int = 2) -> bool:
    cutoff = datetime.now() - timedelta(days=max_age_days)
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        try:
            entry_dt = datetime(*published[:6])
            return entry_dt >= cutoff
        except (TypeError, ValueError):
            pass
    return True


def validate_feed_url(url: str) -> bool:
    if not url:
        return False
    if not url.startswith("https://"):
        return False
    blocked = ["localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.", "10.", "192.168.", "172.16."]
    hostname = urlparse(url).hostname or ""
    for prefix in blocked:
        if hostname.startswith(prefix) or hostname == prefix.rstrip("."):
            return False
    return True


def load_feeds_state() -> dict:
    if os.path.exists(FEEDS_STATE_FILE):
        with open(FEEDS_STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_feeds_state(state: dict):
    try:
        with open(FEEDS_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        print(f"Feed state saved to {FEEDS_STATE_FILE}")
    except Exception as e:
        print(f"WARNING: Could not save feed state — {str(e)}")


def get_active_feeds(state: dict) -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    active = []
    for feed in ALL_FEEDS:
        if not validate_feed_url(feed["url"]):
            print(f"⏭️  Skipping {feed['name']} — invalid or missing URL")
            continue
        feed_state = state.get(feed["name"], {"failures": 0})
        last_failure = feed_state.get("last_failure", "")
        if last_failure and last_failure != today and feed_state.get("failures", 0) >= MAX_FAILURES:
            feed_state["failures"] = 0
            state[feed["name"]] = feed_state
            print(f"🔄 {feed['name']} — reset failures (last failure was {last_failure})")
        if feed_state["failures"] < MAX_FAILURES:
            active.append(feed)
        else:
            print(f"⏭️  Skipping {feed['name']} — failed {feed_state['failures']} times today")
    return active


def fetch_all_rss_feeds() -> str:
    state = load_feeds_state()
    active_feeds = get_active_feeds(state)
    all_content = []
    working = []
    failed = []

    print(f"\nTesting {len(active_feeds)} active feeds...\n")

    for feed_info in active_feeds:
        try:
            feed = feedparser.parse(feed_info["url"])

            if feed.entries:
                state[feed_info["name"]] = {
                    "failures": 0,
                    "last_success": datetime.now().strftime("%Y-%m-%d"),
                    "url": feed_info["url"],
                }
                working.append(feed_info["name"])
                print(f"✅ {feed_info['name']} — {len(feed.entries)} entries")

                recent_entries = [e for e in feed.entries if is_entry_recent(e)]
                entries = []
                for entry in recent_entries[:5]:
                    title   = strip_html(entry.get("title", "No title"))
                    link    = entry.get("link", "") or ""
                    if isinstance(link, bytes):
                        link = link.decode("utf-8", errors="replace")
                    summary = strip_html(entry.get("summary", ""))[:MAX_SUMMARY_LENGTH]
                    entries.append(f"  - {title}\n    {link}\n    {summary}")

                section = f"[{feed_info['name']}]\n" + "\n".join(entries)
                all_content.append(section)

            else:
                raise ValueError("No entries found")

        except Exception as e:
            current_failures = state.get(feed_info["name"], {}).get("failures", 0)
            state[feed_info["name"]] = {
                "failures": current_failures + 1,
                "last_failure": datetime.now().strftime("%Y-%m-%d"),
                "last_error": type(e).__name__,
                "url": feed_info["url"],
            }
            failed.append(feed_info["name"])
            print(f"❌ {feed_info['name']} — {str(e)} (failure #{current_failures + 1})")

    print(f"\n── Feed Summary ─────────────────────")
    print(f"✅ Working : {len(working)}")
    print(f"❌ Failed  : {len(failed)}")
    if failed:
        print(f"Failed feeds: {', '.join(failed)}")

    for feed_name, feed_state in state.items():
        if feed_state.get("failures", 0) >= 3:
            print(f"🚫 DISABLED: {feed_name} — failed 3+ times, skipping until manually re-enabled")

    save_feeds_state(state)

    return "\n\n".join(all_content) if all_content else ""


def summarize_with_claude(raw_feeds: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=f"""You are a daily tech news digest writer. You will receive raw RSS feed
content and must write a comprehensive Markdown digest.

Use this EXACT format in this EXACT order:

# Daily Tech Digest — {today}

## Executive Summary

Write a comprehensive executive summary organized by area. For each major area
covered today, write a subsection:

### [Area Name e.g. "AI & LLMs"]
2-3 sentences summarizing the top developments in this area. Include the most
important story with a link to the source: ([Source](url)). Be opinionated about
why it matters and what the implications are.

### [Next Area e.g. "Cloud & Infrastructure"]
...

### Stratechery & Analyst Commentary
Always include this subsection. Summarize any commentary or analysis from
Stratechery, TechCrunch, and a16z. If they covered specific stories, note their
take and link to their articles. If none of these sources had content today,
note that explicitly.

The Executive Summary should cover 4-8 areas and be self-contained — a reader
should get a complete picture of the day's tech news just from this section.

## [Topic Name e.g. "Agentic AI"]

### What happened
2-3 sentences summarizing the key developments in this topic today across
all sources. Synthesize — do not list sources separately.

### Key stories
- **[Story headline]** — Detailed 2-3 sentence explanation of what happened,
  why it matters, and what the implications are for the industry. ([Source](url))
- **[Story headline]** — Detailed 2-3 sentence explanation. ([Source](url))
- **[Story headline]** — Detailed 2-3 sentence explanation. ([Source](url))

### What to watch
1-2 sentences on what to follow next in this topic — upcoming announcements,
open questions, or trends to monitor.

## [Next Topic e.g. "Enterprise Security"]

### What happened
...

### Key stories
...

### What to watch
...

IMPORTANT RULES:
- The Executive Summary must have ### subsections for each area, plus a
  "Stratechery & Analyst Commentary" subsection that covers Stratechery,
  TechCrunch, and a16z perspectives
- Always start with Executive Summary
- Aim for 6-10 topic sections — cover ALL major themes from the feeds
- Every topic MUST have all three subsections: What happened, Key stories, What to watch
- Each Key story bullet must be 2-3 sentences — not just a headline
- Every story must end with a source link ([Source Name](url))
- Do NOT organize by source — group strictly by theme across all sources
- Be thorough — if the feeds have content, capture it. Depth over brevity here.""",
        messages=[
            {"role": "user", "content": f"Here is today's raw RSS feed content. Write the daily digest.\n\n{raw_feeds}"}
        ],
    )

    return message.content[0].text


def save_digest(digest: str) -> str:
    os.makedirs("digests", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"digests/digest_{date_str}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(digest)
    print(f"Digest saved to {filename}")
    return filename


def main():
    print(f"Starting pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n── Step 1: Fetching RSS feeds ──")
    raw_feeds = fetch_all_rss_feeds()

    if not raw_feeds:
        print("ERROR: No feed content available. Exiting.")
        raise SystemExit(1)

    print(f"\n── Step 2: Summarizing with Claude ({len(raw_feeds)} chars) ──")
    try:
        digest = summarize_with_claude(raw_feeds)
    except Exception as e:
        print(f"ERROR: Claude API call failed: {type(e).__name__}: {e}")
        raise

    print(f"\n── Step 3: Saving digest ({len(digest)} chars) ──")
    save_digest(digest)

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
