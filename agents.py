
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from tools import scrape_url, web_search

# Load environment variables from this project's .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env")

# Initialize the Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=GOOGLE_API_KEY,
    temperature=0,
    timeout=120,
    max_retries=3,
    max_output_tokens=700,
)

# First agent: Web search agent
def search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt=(
            "You are a fast research search agent. "
            "Call web_search once for the user's topic. "
            "Return the most useful results with titles, "
            "short summaries, and URLs. Be concise."
        )
    )


# Second agent: Web page reader agent
def reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url],
        system_prompt=(
            "You are a research reading agent. "
            "Use the scrape_url tool to read relevant webpages. "
            "Summarize important facts and preserve source URLs."
        )
    )


# Writer chain

writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert research writer.

Write clear, structured, factual, and insightful research reports.

IMPORTANT SOURCE RULES:
- Preserve source URLs exactly as provided in the research.
- Copy every complete source URL without shortening or modifying it.
- Never invent URLs or add incomplete URLs.
- Include only URLs actually present in the research.
- If a URL is incomplete in the research, do not guess the missing part.
- Make sure the Sources section is complete before finishing the report.
- Do not stop writing while a URL is incomplete."""
    ),
    (
        "human",
        """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Use this exact report structure:

1. Introduction
2. Key Findings
   - Include at least 3 well-explained points.
3. Conclusion
4. Sources
   - List each complete source URL on a separate line.
   - Do not add unfinished entries.

Use the supplied research, avoid unsupported claims,
and write in a professional style."""
    ),
])

writer_chain = (
    writer_prompt
    | llm
    | StrOutputParser()
).with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True,
)
# Critic chain
critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a sharp and constructive research critic. "
        "Evaluate reports honestly and specifically."
    ),
    (
        "human",
        """Review the research report below.

Report:
{report}

Evaluate factual support, clarity, completeness, and organization.
Respond in this format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line Verdict:
..."""
    ),
])

critic_chain = critic_chain = (
    critic_prompt
    | llm
    | StrOutputParser()
).with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True,
)

# Third chain: Writer revises the report using critic feedback
revision_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert research editor.

Improve research reports using the critic's feedback.

Rules:
- Correct factual errors when the supplied research supports a correction.
- Improve clarity, structure, reasoning, and completeness.
- Address every actionable criticism.
- Do not invent facts, citations, or URLs.
- Do not claim that unsupported facts are verified.
- Preserve useful content from the original report.
- Return the complete revised report, not just a list of changes.
- Do not include a separate explanation of your edits.
- The Python pipeline will append the verified source list afterward."""
    ),
    (
        "human",
        """Research topic:
{topic}

Original report:
{report}

Critic feedback:
{feedback}

Original research material:
{research}

Revise the report using the feedback and available evidence."""
    ),
])

revision_chain = (
    revision_prompt
    | llm
    | StrOutputParser()
).with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True,
)
