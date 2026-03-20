"""
Daily Digest Agent — Google ADK pipeline
Scrapes a set of sites in parallel, summarizes, and saves a Markdown digest.
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ─── Sites to scrape ──────────────────────────────────────────────────────────
# Add or remove sites here as needed
SITES = [
    {"name": "TechCrunch_AI",  "url": "https://techcrunch.com/category/artificial-intelligence/"},
    {"name": "Hacker_News",    "url": "https://news.ycombinator.com/"},
    {"name": "The_Verge_Tech", "url": "https://www.theverge.com/tech"},
]

# ─── Tools ────────────────────────────────────────────────────────────────────

def fetch_site_content(site_name: str, url: str) -> str:
    """Fetches and cleans text content from a given site URL.

    Args:
        site_name: Human-readable name of the site.
        url: The URL to fetch content from.

    Returns:
        Cleaned text content from the site, capped at 4000 characters.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyDigestBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Strip boilerplate tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        lines = [l for l in text.splitlines() if l.strip()]
        cleaned = "\n".join(lines)

        return f"[{site_name}]\n{cleaned[:4000]}"

    except Exception as e:
        return f"[{site_name}] ERROR fetching {url}: {str(e)}"


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
    print(f"✅ Digest saved → {filename}")
    return f"Digest saved to {filename}"


# ─── Build scraper sub-agents (one per site, run in parallel) ─────────────────

def make_scraper_agent(site: dict) -> LlmAgent:
    return LlmAgent(
        name=f"scraper_{site['name']}",
        model="gemini-2.0-flash",
        instruction=f"""
            You are a web scraper. Your ONLY job is to fetch content from:
            Site name : {site['name']}
            URL       : {site['url']}

            Call fetch_site_content with site_name="{site['name']}" and url="{site['url']}".
            Store the result exactly as returned — do not summarize or modify it.
        """,
        tools=[FunctionTool(fetch_site_content)],
        output_key=f"raw_{site['name']}",
    )


scraper_agents = [make_scraper_agent(s) for s in SITES]

parallel_scraper = ParallelAgent(
    name="parallel_scraper",
    sub_agents=scraper_agents,
)

# ─── Summarizer ───────────────────────────────────────────────────────────────

summarizer = LlmAgent(
    name="summarizer",
    model="gemini-2.0-flash",
    instruction="""
        You are a daily tech news digest writer. Session state contains raw scraped 
        content from multiple websites under keys like 'raw_<SiteName>'.

        Write a clean, well-structured Markdown digest with:
        - A top-level heading: "# Daily Tech Digest — {today's date}"
        - One section per site (## Site Name) with 3–5 bullet-point takeaways
        - A final "## ⭐ Top Story" section highlighting the single most important item

        Be concise, factual, and scannable. Omit ads, navigation text, and boilerplate.
    """,
    output_key="daily_digest",
)

# ─── Saver ────────────────────────────────────────────────────────────────────

saver = LlmAgent(
    name="saver",
    model="gemini-2.0-flash",
    instruction="""
        Retrieve the value of the 'daily_digest' key from session state.
        Pass it to save_digest to persist it to disk.
    """,
    tools=[FunctionTool(save_digest)],
)

# ─── Root pipeline ────────────────────────────────────────────────────────────

root_agent = SequentialAgent(
    name="daily_digest_pipeline",
    sub_agents=[
        parallel_scraper,  # Step 1: scrape all sites simultaneously
        summarizer,        # Step 2: summarize into a digest
        saver,             # Step 3: save to digests/digest_YYYY-MM-DD.md
    ],
)

# ─── Runner (entry point) ─────────────────────────────────────────────────────

def run():
    print(f"🚀 Starting daily digest pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    session_service = InMemorySessionService()
    session = session_service.create_session(
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

    for event in runner.run(
        user_id="system",
        session_id="daily_run",
        new_message=content,
    ):
        if event.is_final_response():
            print("✅ Pipeline complete.")
            if event.content and event.content.parts:
                print(event.content.parts[0].text)


if __name__ == "__main__":
    run()
