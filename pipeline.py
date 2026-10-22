import os
import re
import builtins
from rich import print as _rich_print
from tools import web_search, scrape_url
from agents import writer_chain, critic_chain, revision_chain
def print(*args, **kwargs):
    """Terminal logging that can never break the pipeline.

    rich raises on text that looks like broken markup (e.g. "[/x]" inside a
    web snippet), and Windows consoles can raise on non-ASCII characters.
    Logging problems must not abort a research run.
    """
    try:
        _rich_print(*args, **kwargs)
    except Exception:
        try:
            builtins.print(*args, **kwargs)
        except Exception:
            pass
def extract_urls(text):
    """Extract unique URLs and remove trailing punctuation."""
    found = re.findall(r"""https?://[^\s<>"']+""", str(text))

    urls = []
    for url in found:
        url = url.rstrip(".,;:!?)]}")

        if url and url not in urls:
            urls.append(url)

    return urls


def ensure_sources(report, source_urls):
    """Replace the report's Sources section with collected URLs."""
    report = re.sub(
        r"(?im)^#{0,6}\s*(?:\d+[.)]\s*)?Sources\s*$[\s\S]*",
        "",
        report
    ).rstrip()

    if source_urls:
        sources = "\n".join(f"- {url}" for url in source_urls)
    else:
        sources = "No source URLs were successfully extracted."

    return f"{report}\n\n## Sources\n\n{sources}\n"


def _safe_error(exc, limit=300):
    """Short, secret-free description of an exception (for the UI)."""
    text = f"{type(exc).__name__}: {exc}"
    for name in ("GOOGLE_API_KEY", "TAVILY_API_KEY"):
        secret = os.getenv(name)
        if secret:
            text = text.replace(secret, "[redacted]")
    return text[:limit]


def research_pipeline(topic: str, progress_callback=None, state=None) -> dict:
    """
    Run the research workflow.

    state (optional): a dict the pipeline fills in place. A UI can pass one so
    partial results survive an unexpected exception. Omit it for the original
    behaviour (a new dict is created and returned).

    progress_callback (optional): called as progress_callback(event) with a
    dict: {"stage": "search|reader|writer|critic|revision",
           "event": "started|completed|failed|skipped|url_started|
                     url_completed|url_skipped|fallback",
           "message": str, ...extra fields}
    Callback errors never interrupt the pipeline. Calling
    research_pipeline(topic) behaves exactly as before.
    """

    def emit(stage, event, message="", **extra):
        if progress_callback is None:
            return
        try:
            progress_callback(
                {"stage": stage, "event": event, "message": message, **extra}
            )
        except Exception:
            pass

    if state is None:
        state = {}

    state.update({
        "pages": [],
        "report_method": None,   # "ai" or "fallback"
        "revised": False,
        "search_ok": False,
    })

    # STEP 1: Search using Tavily
    print("\n[bold cyan]Step 1: Searching with Tavily...[/bold cyan]")
    emit("search", "started", "Searching the web with Tavily")

    try:
        state["search_result"] = web_search.invoke({"query": topic})
        print(state["search_result"])

    except Exception as e:
        print(f"[red]Tavily search failed: {e}[/red]")
        state["search_error"] = _safe_error(e)
        emit("search", "failed", state["search_error"])
        return state

    # web_search reports its own failures as plain strings.
    result_text = str(state["search_result"])
    if result_text.startswith("Web search failed:"):
        state["search_error"] = result_text[:300]
        emit("search", "failed", state["search_error"])
    elif result_text.startswith("No search results found"):
        emit("search", "completed", "Search returned no results", url_count=0)
    else:
        state["search_ok"] = True

    state["source_urls"] = extract_urls(state["search_result"])

    if state["search_ok"]:
        emit(
            "search", "completed",
            f"Found {len(state['source_urls'])} URL(s)",
            url_count=len(state["source_urls"]),
            urls=list(state["source_urls"]),
        )

    # STEP 2: Scrape up to two result URLs
    print("\n[bold cyan]Step 2: Reading web pages...[/bold cyan]")

    urls = state["source_urls"][:2]
    pages = []

    emit("reader", "started", f"Reading up to 2 pages ({len(urls)} candidate)",
         urls=list(urls))

    for url in urls:
        print(f"Reading: {url}")
        emit("reader", "url_started", url, url=url)

        try:
            content = scrape_url.invoke({"url": url})

            if content and not str(content).startswith(
                "Could not scrape URL:"
            ):
                pages.append(f"Source: {url}\n{content}")
                state["pages"].append(
                    {"url": url, "status": "scraped", "chars": len(str(content))}
                )
                emit("reader", "url_completed", url, url=url)
            else:
                print("[yellow]Could not read this page.[/yellow]")
                reason = str(content)[:200] if content else "Empty page"
                state["pages"].append(
                    {"url": url, "status": "skipped", "reason": reason}
                )
                emit("reader", "url_skipped", reason, url=url)

        except Exception as e:
            print(f"[yellow]Skipping page: {e}[/yellow]")
            state["pages"].append(
                {"url": url, "status": "skipped", "reason": _safe_error(e)}
            )
            emit("reader", "url_skipped", _safe_error(e), url=url)

    state["scraped_content"] = "\n\n".join(pages)

    for url in extract_urls(state["scraped_content"]):
        if url not in state["source_urls"]:
            state["source_urls"].append(url)

    scraped_count = sum(1 for p in state["pages"] if p["status"] == "scraped")
    emit("reader", "completed",
         f"{scraped_count} of {len(urls)} page(s) read",
         scraped=scraped_count, attempted=len(urls))

    # STEP 3: Writer creates the initial report
    print("\n[bold cyan]Step 3: Writing research report...[/bold cyan]")
    emit("writer", "started", "Writing the research report")

    try:
        research = (
            f"SEARCH RESULTS:\n{str(state['search_result'])[:5000]}"
            f"\n\nPAGE CONTENT:\n{state['scraped_content'][:3000]}"
        )

        state["report"] = writer_chain.invoke({
            "topic": topic,
            "research": research
        })

        state["report"] = ensure_sources(
            state["report"],
            state["source_urls"]
        )
        state["report_method"] = "ai"
        emit("writer", "completed", "Report generated by the writer model")

    except Exception as e:
        print(f"[yellow]Writer failed: {e}[/yellow]")
        print("[yellow]Building a fallback report...[/yellow]")
        state["writer_error"] = _safe_error(e)
        emit("writer", "fallback", state["writer_error"])

        state["report"] = (
            f"# Research Report: {topic}\n\n"
            "## 1. Introduction\n\n"
            f"This report organizes collected research on {topic}.\n\n"
            "## 2. Search Findings\n\n"
            f"{state['search_result']}\n\n"
            "## 3. Additional Page Content\n\n"
            f"{state['scraped_content'] or 'No page content was retrieved.'}\n\n"
            "## 4. Conclusion\n\n"
            "Verify important claims against the original sources."
        )

        state["report"] = ensure_sources(
            state["report"],
            state["source_urls"]
        )
        state["report_method"] = "fallback"
        emit("writer", "completed",
             "Fallback report assembled locally", fallback=True)

    state["initial_report"] = state["report"]

    print("\n[bold green]INITIAL RESEARCH REPORT[/bold green]\n")
    print(state["report"])

    # STEP 4: Critic reviews the report
    print("\n[bold cyan]Step 4: Critic is reviewing the report...[/bold cyan]")
    emit("critic", "started", "Critic is reviewing the report")

    try:
        state["feedback"] = critic_chain.invoke({
            "report": state["report"][:6000]
        })

        print("\n[bold yellow]CRITIC FEEDBACK[/bold yellow]\n")
        print(state["feedback"])

        if state["feedback"] and str(state["feedback"]).strip():
            emit("critic", "completed", "Critic review complete")
        else:
            state["feedback"] = None
            state["critic_error"] = "The critic returned no feedback."
            emit("critic", "failed", state["critic_error"])

    except Exception as e:
        state["feedback"] = None
        state["critic_error"] = _safe_error(e)
        print(f"[red]Critic review failed: {e}[/red]")
        emit("critic", "failed", state["critic_error"])

    # STEP 5: Writer revises using critic feedback
    if state["feedback"]:
        print("\n[bold cyan]Step 5: Improving the report...[/bold cyan]")
        emit("revision", "started", "Revising the report using critic feedback")

        try:
            revised_report = revision_chain.invoke({
                "topic": topic,
                "report": state["report"][:10000],
                "feedback": str(state["feedback"])[:4000],
                "research": (
                    f"{str(state['search_result'])[:5000]}\n\n"
                    f"{state['scraped_content'][:3000]}"
                ),
            })

            state["report"] = ensure_sources(
                revised_report,
                state["source_urls"]
            )
            state["revised"] = True
            emit("revision", "completed", "Revised report ready")

            print("\n[bold green]IMPROVED FINAL REPORT[/bold green]\n")
            print(state["report"])

        except Exception as e:
            state["revision_error"] = _safe_error(e)
            print(f"[red]Revision failed: {e}[/red]")
            print("[yellow]Keeping the original report.[/yellow]")
            emit("revision", "failed", state["revision_error"])

    else:
        print("[yellow]Revision skipped because critic feedback is unavailable.[/yellow]")
        emit("revision", "skipped",
             "Revision skipped because critic feedback is unavailable")

    return state


if __name__ == "__main__":
    topic = input("\nEnter a research topic: ").strip()

    if topic:
        try:
            research_pipeline(topic)
        except Exception as e:
            print(f"\n[bold red]Pipeline failed: {e}[/bold red]")
    else:
        print("[red]Please enter a topic.[/red]")