
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool
from tavily import TavilyClient

# Load .env from this project's folder
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Check API keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

print("Gemini API key loaded:", bool(GOOGLE_API_KEY))
print("Tavily API key loaded:", bool(TAVILY_API_KEY))

if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY not found. Check your .env file."
    )

if not TAVILY_API_KEY:
    raise ValueError(
        "TAVILY_API_KEY not found. Check your .env file."
    )

tavily = TavilyClient(api_key=TAVILY_API_KEY)


@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic."""
    try:
        results = tavily.search(query=query, max_results=5)

        output = []

        for result in results.get("results", []):
            output.append(
                f"Title: {result.get('title', '')}\n"
                f"URL: {result.get('url', '')}\n"
                f"Snippet: {result.get('content', '')[:300]}\n"
            )

        return "\n----\n".join(output) or "No search results found."

    except Exception as e:
        return f"Web search failed: {str(e)}"


@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL."""
    try:
        response = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True)[:3000]

    except Exception as e:
        return f"Could not scrape URL: {str(e)}"
