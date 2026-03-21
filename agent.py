import os
import json
import asyncio
import feedparser
from datetime import datetime
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ─── Master feed list ─────────────────────────────────────────────────────────
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
    {"name": "TechCrunch",         "url": "https://techcrunch.com/feed/"},
    {"name": "The_Verge_Tech",     "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Hacker_News",        "url": "https://news.ycombinator.com/rss"},
    {"name": "MIT_Tech_Review",    "url": "https://www.technologyreview.com/feed/"},
    {"name": "Wired_AI",           "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss"},
    {"name": "VentureBeat_AI",     "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Ars_Technica",       "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
]

FEEDS_STATE_FILE = "feeds_state.json"

# ─── Feed state management ────────────────────────────────────────────────────

def load_feeds_state() -> dict:
    """Loads feed health state from JSON file."""
    if os.path.exists(FEEDS_STATE_FILE):
        with open(FEEDS_STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_feeds_state(state: dict):
    """Saves feed health state to JSON file."""
    try:
        with open(FEEDS_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        print(f"Feed state saved to {FEEDS_STATE_FILE}")
    except Exception as e:
        print(f"WARNING: Could not save feed state — {str(e)}")


def get_active_feeds(state: dict) -> list:
    """Returns feeds that haven't failed more than 3 consecutive times."""
    active = []
    for feed in ALL_FEEDS:
        feed_state = state.get(feed["name"], {"failures": 0})
        if feed_state["failures"] < 3:
            active.append(feed)
        else:
            print(f"⏭️  Skipping {feed['name']} — failed {feed_state['failures']} times in a row")
    return active


# ─── Tools ────────────────────────────────────────────────────────────────────

def fetch_all_rss_feeds() -> str:
    """Tests and fetches all active RSS feeds, updating health state.

    Returns:
        Combined content from all working feeds.
    """
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

                entries = []
                for entry in feed.entries[:5]:
                    title   = entry.get("title", "No title")
                    link    = entry.get("link", "")
                    summary = entry.get("summary", "")[:200]
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
                "last_error": str(e),
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

    return "\n\n".join(all_content) if all_content else "No feed content available."


def save_digest(digest: str) -> str:
    """Saves the daily digest to a Markdown file."""
    os.makedirs("digests", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"digests/digest_{date_str}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(digest)
    print(f"Digest saved to {filename}")
    return f"Digest saved to {filename}"


# ─── Agents ───────────────────────────────────────────────────────────────────

fetcher_agent = LlmAgent(
    name="rss_fetcher",
    model="gemini-3-flash-preview",
    instruction="""
        Call fetch_all_rss_feeds to get the latest news from all RSS feeds.
        Store the raw content in session state under key 'raw_feeds'.
    """,
    tools=[FunctionTool(fetch_all_rss_feeds)],
    output_key="raw_feeds",
)

today = datetime.now().strftime("%Y-%m-%d")

summarizer_agent = LlmAgent(
    name="summarizer",
    model="gemini-3-flash-preview",
    instruction=f"""
        You are a daily tech news digest writer. Read the raw RSS feed content
        from session state key 'raw_feeds' and write a clean Markdown digest.

        IMPORTANT RULES:
        - Do NOT organize by source. Instead group stories by TOPIC.
        - Identify the major themes and topics across ALL sources combined.
        - For each topic write 3-5 bullet points summarizing key insights.
        - Each bullet point must end with a source reference link in this format:
          ([Source Name](url))
        - If multiple sources cover the same topic, combine them under one section.

        Use this exact format:

        # Daily Tech Digest — {today}

        ## [Topic Name e.g. "Agentic AI"]
        - Key insight or development from across sources ([Source Name](url))
        - Another insight ([Source Name](url))
        - Another insight ([Source Name](url))

        ## [Next Topic e.g. "Enterprise Security"]
        - Key insight ([Source Name](url))
        - Another insight ([Source Name](url))

        ## Top Story
        A 2-3 sentence summary of the single most important story today,
        with a link to the source.

        Aim for 5-8 topic sections. Be concise, factual, and scannable.
    """,
    output_key="daily_digest",
)

saver_agent = LlmAgent(
    name="saver",
    model="gemini-3-flash-preview",
    instruction="Retrieve the value of 'daily_digest' from session state and save it using save_digest.",
    tools=[FunctionTool(save_digest)],
)

# ─── Pipeline ─────────────────────────────────────────────────────────────────

root_agent = SequentialAgent(
    name="daily_digest_pipeline",
    sub_agents=[fetcher_agent, summarizer_agent, saver_agent],
)

# ─── Runner ───────────────────────────────────────────────────────────────────

async def run():
    print(f"Starting pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="daily_digest",
        user_id="system",
        session_id="daily_run",
    )

    runner = Runner(
        agent=root_agent,
        app_name="daily_digest",
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text="Run the daily digest pipeline now.")],
    )

    async for event in runner.run_async(
        user_id="system",
        session_id="daily_run",
        new_message=content,
    ):
        if event.is_final_response():
            print("Pipeline complete.")

    session = await session_service.get_session(
        app_name="daily_digest",
        user_id="system",
        session_id="daily_run",
    )

    digest = session.state.get("daily_digest", "")
    raw_feeds = session.state.get("raw_feeds", "")

    print(f"Session state keys: {list(session.state.keys())}")

    if digest:
        save_digest(digest)
        print("Digest saved from session state.")
    elif raw_feeds:
        save_digest(f"# Daily Digest — {today}\n\n{raw_feeds}")
        print("Saved raw feeds as fallback.")
    else:
        print("WARNING: No content found in session state.")


if __name__ == "__main__":
    asyncio.run(run())
