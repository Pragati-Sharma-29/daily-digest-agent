import os
import asyncio
import feedparser
from datetime import datetime
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ─── RSS Feeds to read ────────────────────────────────────────────────────────
RSS_FEEDS = [
    {"name": "TechCrunch AI",  "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "Hacker News",    "url": "https://news.ycombinator.com/rss"},
    {"name": "MIT Tech Review","url": "https://www.technologyreview.com/feed/"},
    {"name": "Wired AI",       "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
]

# ─── Tools ────────────────────────────────────────────────────────────────────

def fetch_all_rss_feeds() -> str:
    """Fetches all RSS feeds and returns combined content as a single string.

    Returns:
        Formatted string of all feed entries combined.
    """
    all_content = []

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            entries = []
            for entry in feed.entries[:5]:  # top 5 per feed
                title   = entry.get("title", "No title")
                link    = entry.get("link", "")
                summary = entry.get("summary", "")[:200]
                entries.append(f"  - {title}\n    {link}\n    {summary}")

            section = f"[{feed_info['name']}]\n" + "\n".join(entries)
            all_content.append(section)
            print(f"Fetched {len(feed.entries)} entries from {feed_info['name']}")

        except Exception as e:
            all_content.append(f"[{feed_info['name']}] ERROR: {str(e)}")

    return "\n\n".join(all_content)


def save_digest(digest: str) -> str:
    """Saves the daily digest to a Markdown file.

    Args:
        digest: The full digest text to save.

    Returns:
        Confirmation message with the filename.
    """
    os.makedirs("digests", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"digests/digest_{date_str}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(digest)
    print(f"Digest saved to {filename}")
    return f"Digest saved to {filename}"


# ─── Single agent that fetches + summarizes in one step ───────────────────────
# No parallel agents = no rate limit issues

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

summarizer_agent = LlmAgent(
    name="summarizer",
    model="gemini-3-flash-preview",
    instruction=f"""
        You are a daily tech news digest writer. Read the raw RSS feed content 
        from session state key 'raw_feeds' and write a clean Markdown digest.

        Format:
        # Daily Tech Digest — {datetime.now().strftime('%Y-%m-%d')}

        One ## section per feed source with 3-5 bullet point takeaways.
        End with a ## Top Story section highlighting the single most important item.

        Be concise, factual, and scannable.
    """,
    output_key="daily_digest",
)

saver_agent = LlmAgent(
    name="saver",
    model="gemini-3-flash-preview",
    instruction="Retrieve the value of 'daily_digest' from session state and save it using save_digest.",
    tools=[FunctionTool(save_digest)],
)

# ─── Pipeline: fetch → summarize → save (sequential, minimal API calls) ───────
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

    # Read digest directly from session state
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
        # Fallback: save raw feeds if summarizer didn't run
        save_digest(f"# Daily Digest — {datetime.now().strftime('%Y-%m-%d')}\n\n{raw_feeds}")
        print("Saved raw feeds as fallback.")
    else:
        print("WARNING: No content found in session state.")


if __name__ == "__main__":
    asyncio.run(run())

    # Save from final response
    if final_text:
        save_digest(final_text)
    else:
        session = await session_service.get_session(
            app_name="daily_digest",
            user_id="system",
            session_id="daily_run",
        )
        digest = session.state.get("daily_digest", "")
        if digest:
            save_digest(digest)
            print("Digest saved from session state.")
        else:
            print("WARNING: No digest content found.")


if __name__ == "__main__":
    asyncio.run(run())
