"""SearchKnowtix - Streamlit front end for the multi-agent research pipeline (jet-black editorial redesign).

Backend contract is unchanged: `pipeline.research_pipeline(topic, progress_callback=..., state=...)`.
Requires Streamlit >= 1.40 (keyed containers, Material icons in labels, form borders).
"""
import html
import os
import re
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st

from database import init_db, save_run, get_all_runs

st.set_page_config(page_title="SearchKnowtix", page_icon="✦", layout="wide",
                   initial_sidebar_state="expanded")

esc = html.escape

# Topic shortcuts and quick actions fill the composer; nothing runs until the user presses Search.
TOPICS = [
    ("AI security", "Risks, regulation & defense", ":material/shield:",
     "Analyze the main risks, regulations and defensive practices in AI security today."),
    ("Renewable energy", "Trends, tech & policy", ":material/eco:",
     "Research recent advances, technology trends and policy developments in renewable energy."),
    ("Market trends", "Industries, data & forecasts", ":material/trending_up:",
     "Investigate current market trends across major industries, with data and forecasts."),
    ("Scientific discoveries", "Research, papers & breakthroughs", ":material/science:",
     "Summarize the most significant recent scientific discoveries and the research behind them."),
]
ACTIONS = [
    ("Read a structured report", "Get a well-organized, cited report", ":material/description:",
     "Write a well-structured, cited report on: "),
    ("Compare AI models", "Side-by-side analysis with sources", ":material/compare_arrows:",
     "Compare leading AI models and their capabilities, side by side, with sources."),
    ("Critique a paper or claim", "Get a balanced, evidence-based review", ":material/fact_check:",
     "Give a balanced, evidence-based critique of this paper or claim: "),
    ("Explore a topic", "Dive deeper with multi-agent research", ":material/explore:",
     "Explore in depth, with multiple perspectives: "),
]
STAGES = [
    ("search", "Searching the web"),
    ("reader", "Reading and extracting sources"),
    ("writer", "Writing the structured report"),
    ("critic", "Reviewing with the critic"),
]
STATUS_LABEL = {"pending": "Waiting", "running": "Working", "done": "Complete",
                "warn": "Attention", "failed": "Failed", "notrun": "Not run"}
RUN_LABEL = {"complete": "Completed", "partial": "Completed with issues", "failed": "Failed"}
RUN_CLS = {"complete": "ok", "partial": "warn", "failed": "bad"}

# --------------------------------------------------------------------------
# Styling: all colors come from CSS variables, swapped by theme
# --------------------------------------------------------------------------


def zigzag(color, opacity):
    """Faint diagonal zigzag line texture as an inline SVG data URI (no external asset)."""
    paths = "".join(f"<path d='M0 {30 + dy} L40 {6 + dy} L120 {30 + dy}'/>" for dy in (-28, -14, 0))
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='120' height='14'>"
           f"<g fill='none' stroke='{color}' stroke-opacity='{opacity}' stroke-width='1'>{paths}</g></svg>")
    return 'url("data:image/svg+xml,' + svg.replace("<", "%3C").replace(">", "%3E") + '")'

THEMES = {
    "dark": dict(bg="#080B0E", side="#090D11", card="#0D1217", elev="#111820", accent="#C4F06A",
                 accent_hover="#D4FF80", accent_text="#C4F06A", on_accent="#080B0E", text="#F5F0E6",
                 text2="#A7B1BF", muted="#778393", border="#26313B", coral="#F07855",
                 ok="#C4F06A", scheme="dark", pattern=zigzag("white", "0.07")),
    "light": dict(bg="#F5F0E6", side="#EFE9DA", card="#FBF8F1", elev="#EAE4D4", accent="#C4F06A",
                  accent_hover="#B4E050", accent_text="#4B6A0C", on_accent="#151A1F", text="#151A1F",
                  text2="#3F4A57", muted="#667180", border="#D3CCBA", coral="#D9623F",
                  ok="#4B6A0C", scheme="light", pattern=zigzag("black", "0.07")),
}


def theme_css(mode):
    t = THEMES[mode]
    return "<style>:root{" + "".join(f"--{k.replace('_', '-')}:{v};" for k, v in t.items()) + "}</style>"


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,500;0,600;1,500;1,600&display=swap');
html,body,.stApp,.stApp p,.stApp li,.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp a,
section[data-testid="stSidebar"]{font-family:'Inter',-apple-system,'Segoe UI',sans-serif;}
.stApp{background-color:var(--bg);background-image:var(--pattern);background-attachment:fixed;
  color:var(--text);color-scheme:var(--scheme);}
.stApp p,.stApp li,.stApp label,.stApp span,.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--text);}
.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] *{color:var(--muted);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.2rem;max-width:1240px;}
section[data-testid="stSidebar"]{background:var(--side);border-right:1px solid var(--border);}
section[data-testid="stSidebar"] .block-container{padding-top:1.2rem;}
:focus-visible{outline:2px solid var(--accent-text);outline-offset:2px;}

/* brand + labels */
.sk-brand{display:flex;align-items:center;gap:.7rem;margin-bottom:1rem;}
.sk-brand .name{font-weight:650;font-size:1.12rem;line-height:1.1;}
.sk-brand .sub{font-size:.62rem;color:var(--muted);letter-spacing:.2em;text-transform:uppercase;margin-top:.2rem;}
.sk-label{font-size:.68rem;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);margin:1.4rem 0 .6rem;}
.sk-label.accent{color:var(--accent-text);margin-top:.2rem;}
.sk-rule{border:0;border-top:1px solid var(--border);margin:1.6rem 0 0;}
.sk-statement{font-family:'Playfair Display',Georgia,serif;font-size:1rem;line-height:1.35;color:var(--text2);margin-top:1.4rem;}
.sk-statement:before{content:"✦ ";color:var(--accent-text);}

/* hero */
.sk-hero h1{font-family:'Playfair Display',Georgia,serif;font-weight:500;font-size:clamp(2.3rem,5vw,3.6rem);
  line-height:1.05;letter-spacing:-.015em;margin:.3rem 0 .9rem;padding:0;}
.sk-hero h1 em{font-style:italic;}
.sk-hero p{max-width:40rem;color:var(--text2);font-size:.98rem;line-height:1.6;margin:0 0 1.2rem;}

/* composer: one unified component */
[data-testid="stForm"]{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:.45rem;}
[data-testid="stForm"]:focus-within{border-color:var(--accent-text);}
[data-testid="stForm"] [data-testid="stTextInputRootElement"],
[data-testid="stForm"] [data-baseweb="input"],[data-testid="stForm"] [data-baseweb="base-input"]{
  background:transparent;border:0;box-shadow:none;}
[data-testid="stForm"] input{background:transparent;color:var(--text);font-size:1.02rem;padding:.8rem .5rem;}
[data-testid="stForm"] input::placeholder{color:var(--muted);opacity:1;}
[data-testid="stForm"] button{background:var(--accent);color:var(--on-accent);border:0;border-radius:9px;
  font-weight:650;min-height:3rem;transition:background .15s;}
[data-testid="stForm"] button p{color:var(--on-accent);}
[data-testid="stForm"] button:hover{background:var(--accent-hover);color:var(--on-accent);}
[data-testid="stForm"] button:disabled{opacity:.5;}

/* card-style buttons (topics, recent rows, quick actions) */
.st-key-topics button,.st-key-recent button,.st-key-quick button{
  background:var(--card);border:1px solid var(--border);border-radius:10px;color:var(--text);
  text-align:left;justify-content:flex-start;padding:.8rem .95rem;height:auto;width:100%;
  transition:border-color .15s,background .15s;}
.st-key-topics button p,.st-key-recent button p,.st-key-quick button p{
  text-align:left;white-space:pre-line;font-size:.8rem;line-height:1.45;color:var(--muted);}
.st-key-topics button p strong,.st-key-recent button p strong,.st-key-quick button p strong{
  color:var(--text);font-size:.92rem;font-weight:600;}
.st-key-topics button:hover,.st-key-recent button:hover,.st-key-quick button:hover{
  border-color:var(--accent-text);background:var(--elev);color:var(--text);}
.st-key-topics button span[data-testid="stIconMaterial"]{color:var(--accent-text);}
.st-key-recent button{border-radius:0;border:0;border-bottom:1px solid var(--border);background:transparent;}
.st-key-quickcol{border-left:1px solid var(--border);padding-left:1.2rem;}

/* sidebar buttons */
section[data-testid="stSidebar"] button{border-radius:9px;justify-content:flex-start;text-align:left;
  border:1px solid transparent;background:transparent;color:var(--text2);transition:background .15s;}
section[data-testid="stSidebar"] button p{color:inherit;}
section[data-testid="stSidebar"] button:hover{background:var(--elev);color:var(--text);}
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]{
  background:var(--elev);border-left:2px solid var(--accent-text);color:var(--accent-text);}
.st-key-btn_new button{background:var(--accent) !important;color:var(--on-accent) !important;
  border:0 !important;font-weight:650;justify-content:center;}
.st-key-btn_new button p{color:var(--on-accent) !important;}
.st-key-btn_new button:hover{background:var(--accent-hover) !important;}
.st-key-theme_btn button{background:transparent;border:1px solid var(--border);color:var(--text);border-radius:999px;}

/* current run + agents */
.sk-run{border:1px solid var(--border);border-radius:10px;background:var(--card);padding:.7rem .8rem;font-size:.82rem;
  color:var(--text2);line-height:1.45;}
.sk-run b{color:var(--text);font-weight:600;}
.sk-bar{height:3px;background:var(--border);border-radius:2px;margin-top:.5rem;overflow:hidden;}
.sk-bar i{display:block;height:100%;background:var(--accent-text);transition:width .4s ease;}
.sk-dot{display:inline-block;width:.5rem;height:.5rem;border-radius:50%;margin-right:.45rem;background:var(--muted);}
.sk-dot.run{background:var(--accent-text);animation:skp 1.6s infinite;}
.sk-dot.ok{background:var(--ok);} .sk-dot.warn{background:var(--coral);} .sk-dot.bad{background:var(--coral);}
@keyframes skp{50%{opacity:.35;}}
@media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important;}}
.sk-agents{border:1px solid var(--coral);border-radius:10px;padding:.8rem 1rem;margin-top:.8rem;background:var(--card);}
.sk-agents .t{font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;color:var(--coral);font-weight:600;}
.sk-agents .s{font-size:.8rem;color:var(--text2);margin-top:.3rem;}
.sk-tag{font-family:'Playfair Display',Georgia,serif;font-style:italic;font-size:1.05rem;color:var(--text2);margin-top:1.2rem;}
.sk-tag:after{content:"";display:block;width:2rem;height:2px;background:var(--accent-text);margin-top:.4rem;}

/* timeline */
.sk-tl{border:1px solid var(--border);border-radius:12px;background:var(--card);padding:.4rem 1rem;margin-bottom:1rem;}
.sk-tl .r{display:flex;gap:.8rem;align-items:baseline;padding:.6rem 0;border-bottom:1px solid var(--border);}
.sk-tl .r:last-child{border-bottom:0;}
.sk-tl .n{flex:1;font-size:.9rem;} .sk-tl .d{font-size:.78rem;color:var(--muted);display:block;margin-top:.15rem;word-break:break-word;}
.sk-pill{font-size:.68rem;padding:.14rem .55rem;border-radius:999px;border:1px solid var(--border);color:var(--text2);white-space:nowrap;}
.sk-pill.running,.sk-pill.done{color:var(--accent-text);border-color:var(--accent-text);}
.sk-pill.warn,.sk-pill.failed{color:var(--coral);border-color:var(--coral);}

/* result overview */
.sk-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.1rem 1.25rem;margin-bottom:.8rem;}
.sk-card .t{font-family:'Playfair Display',Georgia,serif;font-size:1.5rem;line-height:1.25;}
.sk-card .q{color:var(--text2);font-size:.9rem;margin:.2rem 0 .7rem;word-break:break-word;}
.sk-chips{display:flex;flex-wrap:wrap;gap:.45rem;}
.sk-chip{font-size:.75rem;padding:.2rem .6rem;border-radius:7px;background:var(--elev);border:1px solid var(--border);color:var(--text2);}
.sk-chip.ok{color:var(--ok);} .sk-chip.warn,.sk-chip.bad{color:var(--coral);}
.sk-src{display:flex;gap:.8rem;padding:.7rem .9rem;margin-bottom:.45rem;border-radius:10px;background:var(--card);border:1px solid var(--border);}
.sk-src .num{flex:0 0 1.6rem;color:var(--accent-text);font-size:.8rem;}
.sk-src a{color:var(--accent-text);word-break:break-all;}
.sk-src .ti{font-weight:600;color:var(--text);} .sk-src .meta{font-size:.76rem;color:var(--muted);margin-top:.15rem;}

/* report: warm paper reading surface in both themes */
.st-key-sk-report{background:#F5F0E6;border:1px solid var(--border);border-radius:12px;padding:1.8rem clamp(1rem,3vw,2.8rem);}
.st-key-sk-report > div{max-width:46rem;margin:0 auto;}
.stApp .st-key-sk-report,.stApp .st-key-sk-report *{color:#151A1F;}
.stApp .st-key-sk-report code,.stApp .st-key-sk-report pre{background:#E9E2D0;}
.st-key-sk-report p,.st-key-sk-report li{font-size:1.02rem;line-height:1.75;}
.stApp .st-key-sk-report h1,.stApp .st-key-sk-report h2,.stApp .st-key-sk-report h3,
.stApp .st-key-sk-report h4{font-family:'Inter',-apple-system,'Segoe UI',sans-serif !important;
  font-weight:600 !important;letter-spacing:-.005em;margin-top:1.6rem;}
.stApp .st-key-sk-report a,.stApp .st-key-sk-report a *{color:#2F5D00;text-decoration:underline;}
.st-key-sk-critic{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--coral);
  border-radius:10px;padding:1rem 1.3rem;}

/* secondary widgets */
.stDownloadButton>button{background:var(--card);border:1px solid var(--border);color:var(--text);border-radius:9px;}
.stDownloadButton>button:hover{border-color:var(--accent-text);color:var(--accent-text);}
[data-baseweb="tab-highlight"]{background-color:var(--accent-text) !important;}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--accent-text);}
[data-testid="stExpander"] details{border-color:var(--border);background:var(--card);}
.stTextArea textarea{background:var(--card);color:var(--text);border:1px solid var(--border);}
</style>
"""

LOGO = ('<svg width="34" height="34" viewBox="0 0 24 24" aria-label="SearchKnowtix"><path d="M12 1C12.6 7.5 16.5 11.4 23 12'
        'C16.5 12.6 12.6 16.5 12 23C11.4 16.5 7.5 12.6 1 12C7.5 11.4 11.4 7.5 12 1Z" fill="#C4F06A"/></svg>')

# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def stretch(fn, *args, **kwargs):
    """Call a Streamlit widget full-width across Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        return fn(*args, use_container_width=True, **kwargs)


def keyed_container(key):
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()


def safe_url(url):
    try:
        p = urlparse(str(url).strip())
    except Exception:
        return None
    if p.scheme in ("http", "https") and p.netloc and " " not in str(url).strip():
        return str(url).strip()
    return None


def short_url(url, n=64):
    try:
        p = urlparse(url)
        text = p.netloc + (p.path if p.path != "/" else "")
    except Exception:
        text = str(url)
    return text if len(text) <= n else text[: n - 1] + "…"


def plain_preview(text, n=230):
    text = re.sub(r"[#*_`>]+", "", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def friendly_error(msg):
    m = (msg or "").lower()
    if "503" in m or "unavailable" in m or "overloaded" in m:
        return ("The model provider is temporarily unavailable (HTTP 503). "
                "Wait a minute and run the research again.")
    if "504" in m or "deadline" in m or "timed out" in m or "timeout" in m:
        return "The request timed out. Try again shortly, or use a narrower topic."
    if "429" in m or "quota" in m or "rate limit" in m or "resource_exhausted" in m:
        return "A rate limit or quota was reached. Wait a while before trying again."
    if any(s in m for s in ("api key", "api_key", "401", "403", "permission", "unauthorized")):
        return "The service rejected the credentials. Check the API keys in your .env file."
    if "connection" in m or "network" in m or "name resolution" in m:
        return "A network problem occurred. Check your internet connection and try again."
    return "This step failed. See the details below, then try again or rephrase the topic."


def fmt_time(dt):
    return dt.strftime("%d %b %Y, %H:%M")


def slugify(text, n=40):
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return (s[:n].strip("-")) or "report"


def to_plain_text(md):
    t = str(md)
    t = re.sub(r"```[a-zA-Z]*\n?", "", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", t)
    return t


def load_backend():
    """Import the existing pipeline. Returns (module, error_message)."""
    try:
        import pipeline  # noqa: WPS433 (imports agents.py and tools.py)
        return pipeline, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {str(exc)[:240]}"


# --------------------------------------------------------------------------
# Stage state (built from real pipeline events; unchanged logic)
# --------------------------------------------------------------------------


def new_stages():
    return {k: {"status": "pending", "detail": "", "url_count": None, "urls": [], "pages": {},
                "scraped": None, "attempted": None, "fallback": False, "revision": None,
                "revision_note": ""} for k, _ in STAGES}


def apply_event(stages, ev):
    stage, event, msg = ev.get("stage"), ev.get("event"), ev.get("message", "")
    if stage == "revision":
        w = stages["writer"]
        w["revision"] = {"started": "running", "completed": "done", "failed": "failed",
                         "skipped": "skipped"}.get(event, w["revision"])
        w["revision_note"] = msg
        return
    s = stages.get(stage)
    if s is None:
        return
    if event == "started":
        s["status"], s["detail"] = "running", msg
        if stage == "reader":
            s["urls"] = list(ev.get("urls", []))
            for u in s["urls"]:
                s["pages"].setdefault(u, ("queued", ""))
    elif event == "url_started":
        s["pages"][ev.get("url")] = ("reading", "")
    elif event == "url_completed":
        s["pages"][ev.get("url")] = ("read", "")
    elif event == "url_skipped":
        s["pages"][ev.get("url")] = ("skipped", msg)
    elif event == "fallback":
        s["fallback"], s["detail"] = True, msg
    elif event == "completed":
        s["detail"] = msg
        if stage == "search":
            s["url_count"], s["urls"] = ev.get("url_count"), list(ev.get("urls", []))
            s["status"] = "warn" if not ev.get("url_count") else "done"
        elif stage == "reader":
            s["scraped"], s["attempted"] = ev.get("scraped"), ev.get("attempted")
            s["status"] = "done" if ev.get("scraped") else "warn"
        elif stage == "writer":
            s["status"] = "warn" if (s["fallback"] or ev.get("fallback")) else "done"
        else:
            s["status"] = "done"
    elif event == "failed":
        s["status"], s["detail"] = "failed", msg


def finalize_stages(stages):
    for s in stages.values():
        if s["status"] == "running":
            s["status"] = "failed"
            s["detail"] = s["detail"] or "Interrupted before finishing."
        elif s["status"] == "pending":
            s["status"] = "notrun"
    if stages["writer"]["revision"] == "running":
        stages["writer"]["revision"] = "failed"


def search_urls_from_state(state):
    found = re.findall(r"(?m)^URL:\s*(\S+)", str((state or {}).get("search_result", "")))
    return list(dict.fromkeys(found))


def timeline_html(stages):
    """One row per real pipeline stage, plus the revision pass once it has started."""
    rows = []

    def row(name, status, detail=""):
        d = f'<span class="d">{esc(plain_preview(detail, 140))}</span>' if detail else ""
        rows.append(f'<div class="r"><div class="n">{esc(name)}{d}</div>'
                    f'<span class="sk-pill {status}">{STATUS_LABEL.get(status, status)}</span></div>')

    for key, name in STAGES:
        s = stages[key]
        detail = ""
        if s["status"] == "failed":
            detail = friendly_error(s["detail"])
        elif key == "search" and s["url_count"] is not None:
            detail = f'{s["url_count"]} result URL(s) found'
        elif key == "reader" and s["scraped"] is not None:
            detail = f'{s["scraped"]} of {s["attempted"]} page(s) read'
        elif key == "writer" and s["status"] == "warn":
            detail = "Fallback: assembled locally, not written by the model"
        elif s["status"] in ("running", "warn"):
            detail = s["detail"]
        row(name, s["status"], detail)
        if key == "writer" and s["revision"]:
            rev = {"running": ("running", "Revising with critic feedback"),
                   "done": ("done", "Revised using critic feedback"),
                   "failed": ("failed", "Revision failed; original kept"),
                   "skipped": ("notrun", "Revision skipped (no critic feedback)")}[s["revision"]]
            row("Revising the report", rev[0], rev[1])
    return f'<div class="sk-tl">{"".join(rows)}</div>'


def progress_of(stages):
    """Genuine progress: finished stages out of 4."""
    return sum(1 for s in stages.values() if s["status"] in ("done", "warn")), len(stages)


def current_stage_name(stages):
    for key, name in STAGES:
        if stages[key]["status"] == "running":
            return name
    return None


# --------------------------------------------------------------------------
# Run records
# --------------------------------------------------------------------------

STATE_FIELDS = ("search_result", "scraped_content", "report", "initial_report", "feedback", "source_urls",
                "pages", "report_method", "revised", "search_ok", "search_error", "writer_error",
                "critic_error", "revision_error")


def compute_status(state, error):
    if not state.get("report"):
        return "failed"
    pages = state.get("pages")
    problems = (error, state.get("search_error"), not state.get("search_ok", True),
                state.get("report_method") == "fallback", state.get("critic_error"),
                state.get("revision_error"),
                (pages is not None and len(pages) > 0 and not any(p.get("status") == "scraped" for p in pages)))
    return "partial" if any(problems) else "complete"


def pages_summary(state):
    pages = state.get("pages") or []
    if not pages and state.get("scraped_content") is None:
        return None
    return sum(1 for p in pages if p.get("status") == "scraped"), len(pages)


def run_notices(run):
    s, out = run["state"], []
    if run.get("error"):
        err = run["error"]
        if "progress_callback" in err or "unexpected keyword" in err:
            out.append(("error", "Your pipeline.py is the old version (it does not accept progress_callback / state). "
                        "Replace it with the updated pipeline.py, then restart Streamlit."))
        else:
            out.append(("error", f"The run stopped unexpectedly. {friendly_error(err)}"))
        out.append(("info", f"Technical detail: {err}"))
    if s.get("search_error"):
        out.append(("error", f"Search failed. {friendly_error(s['search_error'])}"))
    elif s.get("search_ok") is False and "search_result" in s:
        out.append(("warning", "The search returned no usable results, so the report has little to draw on."))
    ps = pages_summary(s)
    if ps and ps[1] > 0 and ps[0] == 0:
        out.append(("warning", "None of the attempted pages could be read; the report relies on search snippets only."))
    elif ps and 0 < ps[0] < ps[1]:
        out.append(("info", f"{ps[1] - ps[0]} of {ps[1]} attempted page(s) could not be read."))
    if s.get("report_method") == "fallback":
        extra = (" The critic's feedback was then used to rewrite it, so the final text is a model revision "
                 "of that fallback draft." if s.get("revised") else "")
        out.append(("warning", "Fallback report: the writer model failed, so the initial draft was assembled locally "
                    "from the collected research." + extra
                    + (f" {friendly_error(s['writer_error'])}" if s.get("writer_error") else "")))
    if s.get("report") and not s.get("feedback"):
        out.append(("warning", "The critic review failed or returned no feedback. The report is shown without a review. "
                    + friendly_error(s.get("critic_error", ""))))
    if s.get("revision_error"):
        out.append(("warning", "The revision pass failed, so the original report is shown. "
                    + friendly_error(s["revision_error"])))
    return out


def run_panel_html(topic, stages, elapsed=None, running=False, status=None):
    """Sidebar 'Current run' panel, built only from real state."""
    if running:
        done, total = progress_of(stages)
        stage = current_stage_name(stages) or "Starting"
        el = f" · {elapsed:.0f}s elapsed" if elapsed is not None else ""
        return (f'<div class="sk-run"><span class="sk-dot run"></span><b>Running</b>{el}<br>'
                f'{esc(plain_preview(topic, 70))}<br>{esc(stage)}…'
                f'<div class="sk-bar"><i style="width:{100 * done / total:.0f}%"></i></div>'
                f'<span style="font-size:.72rem">{done} of {total} stages done</span></div>')
    if status:
        return (f'<div class="sk-run"><span class="sk-dot {RUN_CLS[status]}"></span><b>{RUN_LABEL[status]}</b><br>'
                f'{esc(plain_preview(topic, 70))}</div>')
    return '<div class="sk-run"><span class="sk-dot"></span>Idle. No research in progress.</div>'


def execute_run(topic, backend, side_ph):
    """Run the real pipeline, updating the UI from real progress events."""
    started = datetime.now()
    t0 = time.perf_counter()
    stages, events, state, error = new_stages(), [], {}, None

    st.markdown('<div class="sk-label">Live workflow</div>', unsafe_allow_html=True)
    holder = st.empty()
    holder.markdown(timeline_html(stages), unsafe_allow_html=True)
    side_ph.markdown(run_panel_html(topic, stages, 0, True), unsafe_allow_html=True)
    log = st.status("Research in progress…", expanded=False)

    def on_event(ev):
        ev = dict(ev)
        ev["t"] = round(time.perf_counter() - t0, 1)
        events.append(ev)
        apply_event(stages, ev)
        holder.markdown(timeline_html(stages), unsafe_allow_html=True)
        side_ph.markdown(run_panel_html(topic, stages, ev["t"], True), unsafe_allow_html=True)
        log.text(f"+{ev['t']:>5.1f}s  {ev.get('stage')} · {ev.get('event')}  "
                 f"{plain_preview(ev.get('message', ''), 150)}")

    try:
        backend.research_pipeline(topic, progress_callback=on_event, state=state)
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)}"
        for _k in ("GOOGLE_API_KEY", "TAVILY_API_KEY"):
            if os.getenv(_k):
                error = error.replace(os.getenv(_k), "[redacted]")
        error = error[:300]
    finalize_stages(stages)

    snapshot = {k: state[k] for k in STATE_FIELDS if k in state}
    status = compute_status(snapshot, error)
    log.update(label={"complete": "Research complete", "partial": "Research finished with issues",
                      "failed": "Research failed"}[status],
               state={"complete": "complete", "partial": "complete", "failed": "error"}[status], expanded=False)
    run = {"id": uuid.uuid4().hex[:8], "topic": topic, "started_at": started,
           "duration": round(time.perf_counter() - t0, 1), "status": status,
           "state": snapshot, "events": events, "error": error}

    st.session_state.runs.append(run)  # available immediately in this session
    try:
        save_run(run)  # persist to the database
    except Exception as exc:  # shown after the rerun; the run stays visible either way
        st.session_state.save_error = f"Could not save this run to the database: {exc}"
    st.session_state.active_run = run["id"]
    st.session_state.view = "run"
    st.rerun()


# --------------------------------------------------------------------------
# Result rendering
# --------------------------------------------------------------------------


def parse_titles(search_result):
    titles = {}
    for m in re.finditer(r"(?m)^Title:\s*(.*)\n+URL:\s*(\S+)", str(search_result or "")):
        titles[m.group(2).rstrip(".,;:!?)]}")] = m.group(1).strip()
    return titles


def split_pages(scraped):
    parts = re.split(r"(?m)^Source: (https?://\S+)\n", str(scraped or ""))
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def collect_sources(state):
    titles = parse_titles(state.get("search_result"))
    search_urls = set(search_urls_from_state(state))
    page_status = {p.get("url"): p.get("status") for p in (state.get("pages") or [])}
    seen, out = set(), []
    for u in state.get("source_urls") or []:
        if u in seen:
            continue
        seen.add(u)
        out.append({"url": u, "title": titles.get(u),
                    "origin": "Search result" if u in search_urls else "Found in page content",
                    "read": page_status.get(u)})
    return out


def render_sources(state):
    sources = collect_sources(state)
    if not sources:
        st.info("No source URLs were collected for this run.")
        return
    st.caption("URLs collected from the search results and scraped pages, listed as retrieved and not independently verified.")
    rows = []
    for i, s in enumerate(sources, 1):
        link = safe_url(s["url"])
        label = esc(s["url"])
        anchor = (f'<a href="{esc(link, quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>'
                  if link else f"{label} <span class='meta'>(not a valid web link)</span>")
        title = f'<div class="ti">{esc(s["title"])}</div>' if s["title"] else ""
        read = {"scraped": "page read", "skipped": "page could not be read"}.get(
            s["read"], "not read (the backend reads at most 2 pages)")
        rows.append(f'<div class="sk-src"><div class="num">{i:02d}</div><div>{title}{anchor}'
                    f'<div class="meta">{esc(s["origin"])} · {esc(read)}</div></div></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)


def parse_critic(fb):
    fb = str(fb or "")
    out = {}
    m = re.search(r"Score\W*(\d+(?:\.\d+)?)\s*/\s*10", fb, re.I)
    if m:
        out["score"] = m.group(1)
    s = re.search(r"Strengths\W*\n(.*?)(?=\n[\s*#]*Areas to Improve|\Z)", fb, re.I | re.S)
    a = re.search(r"Areas to Improve\W*\n(.*?)(?=\n[\s*#]*(?:One line )?Verdict|\Z)", fb, re.I | re.S)
    v = re.search(r"Verdict\W*\s*(.+)", fb, re.I | re.S)
    if s and a:
        out["strengths"], out["areas"] = s.group(1).strip(), a.group(1).strip()
    if v:
        out["verdict"] = v.group(1).strip()
    return out


def render_critic(run):
    s = run["state"]
    fb = s.get("feedback")
    if not fb:
        st.warning("No critic feedback is available for this run. " + friendly_error(s.get("critic_error", "")))
        if s.get("critic_error"):
            st.caption(f"Details: {s['critic_error']}")
        return
    if s.get("revised"):
        st.caption("The critic reviewed the initial report. The final report was then revised using this feedback.")
    parsed = parse_critic(fb)
    with keyed_container("sk-critic"):
        if "score" in parsed:
            st.markdown(f"**Critic's score:** {esc(parsed['score'])}/10")
        if "strengths" in parsed:
            c1, c2 = st.columns(2, gap="large")
            c1.markdown("**Strengths**")
            c1.markdown(parsed["strengths"])
            c2.markdown("**Areas to improve**")
            c2.markdown(parsed["areas"])
            if parsed.get("verdict"):
                st.markdown(f"**Verdict:** {parsed['verdict']}")
        else:
            st.markdown(str(fb))
    if "strengths" in parsed:
        with st.expander("Full critic feedback (as returned)"):
            st.text(str(fb))
    if s.get("revised") and s.get("initial_report"):
        with st.expander("Initial report reviewed by the critic"):
            st.markdown(s["initial_report"])


def render_raw(run):
    s = run["state"]
    with st.expander("Raw search results"):
        if s.get("search_result"):
            st.text_area("Raw search results", str(s["search_result"]), height=280, disabled=True,
                         label_visibility="collapsed", key=f"{run['id']}-raw-search")
        else:
            st.caption("No search results were returned.")
    with st.expander("Extracted webpage content"):
        pages = split_pages(s.get("scraped_content"))
        if not pages:
            st.caption("No webpage content was extracted.")
        for i, (url, text) in enumerate(pages):
            st.markdown(f"**{esc(short_url(url, 90))}**")
            st.text_area(url, text, height=200, disabled=True, label_visibility="collapsed",
                         key=f"{run['id']}-page-{i}")
    with st.expander("Run log"):
        if not run["events"]:
            st.caption("No progress events were recorded.")
        for ev in run["events"]:
            st.text(f"+{ev.get('t', 0):>5.1f}s  {ev.get('stage')} · {ev.get('event')}  "
                    f"{plain_preview(ev.get('message', ''), 150)}")


def _supports_wrap():
    try:
        import inspect
        return "wrap_lines" in inspect.signature(st.code).parameters
    except Exception:
        return False


def render_export(run):
    report = run["state"].get("report") or ""
    if not report:
        st.info("There is no report to export for this run.")
        return
    base = f"searchknowtix-{slugify(run['topic'])}-{run['started_at'].strftime('%Y%m%d-%H%M')}"
    c1, c2 = st.columns(2, gap="large")
    with c1:
        stretch(st.download_button, "Download as Markdown (.md)", report, file_name=f"{base}.md",
                mime="text/markdown", key=f"{run['id']}-dl-md")
    with c2:
        stretch(st.download_button, "Download as plain text (.txt)", to_plain_text(report),
                file_name=f"{base}.txt", mime="text/plain", key=f"{run['id']}-dl-txt")
    st.markdown('<div class="sk-label">Copy report text</div>', unsafe_allow_html=True)
    st.caption("Use the copy icon at the top-right of the block below.")
    if _supports_wrap():
        st.code(report, language="markdown", wrap_lines=True)
    else:
        st.code(report, language="markdown")


def method_label(state):
    base = {"ai": "Written by the writer model", "fallback": "Fallback draft (assembled locally)"}.get(
        state.get("report_method"), "Generation method unknown")
    return base + (" · revised with critic feedback" if state.get("revised") else "")


def render_overview(run):
    s = run["state"]
    ps = pages_summary(s)
    chips = [f'<span class="sk-chip {RUN_CLS[run["status"]]}">{RUN_LABEL[run["status"]]}</span>',
             f'<span class="sk-chip">{esc(method_label(s))}</span>']
    if ps and ps[1]:
        chips.append(f'<span class="sk-chip">{ps[0]} of {ps[1]} pages scraped</span>')
    if s.get("source_urls"):
        chips.append(f'<span class="sk-chip">{len(s["source_urls"])} sources</span>')
    chips.append(f'<span class="sk-chip">{esc(fmt_time(run["started_at"]))} · {run["duration"]}s</span>')
    title = "Research report" if s.get("report") else "No report generated"
    st.markdown(f'<div class="sk-card"><div class="t">{title}</div><div class="q">{esc(run["topic"])}</div>'
                f'<div class="sk-chips">{"".join(chips)}</div></div>', unsafe_allow_html=True)


def render_run(run):
    stages = new_stages()
    for ev in run["events"]:
        apply_event(stages, ev)
    finalize_stages(stages)
    render_overview(run)
    for level, text in run_notices(run):
        getattr(st, level)(text)
    st.markdown(timeline_html(stages), unsafe_allow_html=True)

    t_report, t_sources, t_critic, t_raw, t_export = st.tabs(
        ["Final report", "Sources", "Critic review", "Raw research", "Export"])
    with t_report:
        report = run["state"].get("report")
        if report:
            with keyed_container("sk-report"):
                st.markdown(report)
            st.caption("The report is model-generated (or assembled from raw research); its claims have not been "
                       "independently verified. Check important points against the sources.")
        else:
            st.info("No report was produced. Partial research data, if any, is under “Raw research”.")
    with t_sources:
        render_sources(run["state"])
    with t_critic:
        render_critic(run)
    with t_raw:
        render_raw(run)
    with t_export:
        render_export(run)


# --------------------------------------------------------------------------
# Callbacks (run before the script body on the next rerun)
# --------------------------------------------------------------------------


def cb_start():
    topic = (st.session_state.get("topic_input") or "").strip()
    if not topic:
        st.session_state.input_error = "Enter a research topic or question first."
        return
    st.session_state.input_error = None
    st.session_state.pending_topic = topic


def cb_fill(text):
    st.session_state.topic_input = text
    st.session_state.input_error = None
    st.session_state.view = "home"


def cb_new():
    st.session_state.active_run = None
    st.session_state.view = "home"
    st.session_state.topic_input = ""
    st.session_state.input_error = None


def cb_view(name):
    st.session_state.view = name


def cb_open(run_id):
    st.session_state.active_run = run_id
    st.session_state.view = "run"


def cb_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"


def normalise_runs(rows):
    """Make rows from the database safe for the UI: datetimes, defaults, oldest first."""
    out = []
    for r in rows or []:
        r = dict(r)
        t = r.get("started_at")
        if isinstance(t, str):
            try:
                t = datetime.fromisoformat(t)
            except ValueError:
                t = datetime.now()
        r["started_at"] = t or datetime.now()
        r.setdefault("id", uuid.uuid4().hex[:8])
        r.setdefault("topic", "")
        r["state"] = r.get("state") or {}
        r["events"] = r.get("events") or []
        r["duration"] = r.get("duration") or 0
        r["error"] = r.get("error")
        if r.get("status") not in RUN_LABEL:
            r["status"] = "failed"
        out.append(r)
    out.sort(key=lambda r: r["started_at"])
    return out


def get_run(run_id):
    return next((r for r in st.session_state.runs if r["id"] == run_id), None)


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------


def render_sidebar(running):
    ss = st.session_state
    with st.sidebar:
        st.markdown(f'<div class="sk-brand">{LOGO}<div><div class="name">SearchKnowtix</div>'
                    f'<div class="sub">snooping, academically.</div></div></div>', unsafe_allow_html=True)
        stretch(st.button, "＋  New research", on_click=cb_new, disabled=running, key="btn_new")
        st.write("")
        nav = [("home", "Home", ":material/home:"), ("history", "Research history", ":material/history:"),
               ("projects", "Projects", ":material/folder:")]
        for name, label, icon in nav:
            active = ss.view == name or (name == "home" and ss.view == "run")
            stretch(st.button, f"{icon}  {label}", on_click=cb_view, args=(name,), disabled=running,
                    type="primary" if active else "secondary", key=f"nav_{name}")

        st.markdown('<div class="sk-label">Current run</div>', unsafe_allow_html=True)
        side_ph = st.empty()
        r = get_run(ss.active_run) if ss.active_run else None
        if r:
            side_ph.markdown(run_panel_html(r["topic"], new_stages(), status=r["status"]), unsafe_allow_html=True)
            if not running and ss.view != "run":
                stretch(st.button, "Open this run", on_click=cb_open, args=(r["id"],), key="btn_open_active")
        else:
            side_ph.markdown(run_panel_html("", new_stages()), unsafe_allow_html=True)
        st.markdown('<div class="sk-statement">Better questions.<br>Deeper answers.</div>', unsafe_allow_html=True)
    return side_ph


def render_hero():
    st.markdown(
        '<div class="sk-hero"><div class="sk-label accent">Multi-agent research</div>'
        '<h1>Big question energy.</h1>'
        '<p>SearchKnowtix uses multiple AI agents to research, read, analyze and deliver structured, '
        'reliable insights — with sources you can trust.</p></div>', unsafe_allow_html=True)


def render_composer(backend, running):
    # A form makes Enter submit; while a run is active the widgets are disabled (no duplicate submissions).
    with st.form("composer", border=False):
        c1, c2 = st.columns([6, 1.3], gap="small")
        c1.text_input("Research topic", key="topic_input", disabled=running, max_chars=1000,
                      label_visibility="collapsed", placeholder="What do you want to understand?")
        c2.form_submit_button("Search  →", on_click=cb_start, disabled=running or backend is None)
    if st.session_state.get("input_error"):
        st.error(st.session_state.input_error)
    if running:
        st.caption("A research run is in progress. Inputs are locked until it finishes.")


def render_topics(running):
    st.markdown('<div class="sk-label">Explore topics</div>', unsafe_allow_html=True)
    with keyed_container("topics"):
        cols = st.columns(len(TOPICS), gap="small")
        for i, (title, sub, icon, prompt) in enumerate(TOPICS):
            with cols[i]:
                stretch(st.button, f"{icon} **{title}**  \n{sub}", on_click=cb_fill, args=(prompt,),
                        disabled=running, key=f"tp_{i}")


def recent_rows(limit=None):
    runs = list(reversed(st.session_state.runs))
    for r in (runs[:limit] if limit else runs):
        s = r["state"]
        summary = plain_preview(s.get("report"), 120) or "No report was produced for this run."
        n = len(s.get("source_urls") or [])
        meta = f"{RUN_LABEL[r['status']]} · {fmt_time(r['started_at'])}" + (f" · {n} sources" if n else "")
        stretch(st.button, f"**{plain_preview(r['topic'], 90)}**  \n{summary}  \n{meta}  ›",
                on_click=cb_open, args=(r["id"],), key=f"row_{r['id']}")


def render_recent():
    h1, h2 = st.columns([3, 1])
    h1.markdown('<div class="sk-label">Recent research</div>', unsafe_allow_html=True)
    if len(st.session_state.runs) > 4:
        with h2:
            stretch(st.button, "View all →", on_click=cb_view, args=("history",), key="btn_viewall")
    if not st.session_state.runs:
        st.info("No research yet. Ask a question above or pick a topic to run your first research. "
                "Runs from this session will appear here.")
        return
    with keyed_container("recent"):
        recent_rows(4)


def render_quick_actions(running):
    with keyed_container("quickcol"):
        st.markdown('<div class="sk-label">Quick actions</div>', unsafe_allow_html=True)
        with keyed_container("quick"):
            for i, (title, sub, icon, prompt) in enumerate(ACTIONS):
                stretch(st.button, f"{icon} **{title}**  \n{sub}", on_click=cb_fill, args=(prompt,),
                        disabled=running, key=f"qa_{i}")
        r = get_run(st.session_state.active_run) if st.session_state.active_run else None
        if r:
            stages = new_stages()
            for ev in r["events"]:
                apply_event(stages, ev)
            finalize_stages(stages)
            done, total = progress_of(stages)
            line = f"Last run: {done} of {total} agent stages completed"
        else:
            line = "Idle · agents start when you run a search"
        st.markdown(f'<div class="sk-agents"><div class="t">AI agents at work</div>'
                    f'<div class="s">Research · Analyze · Synthesize · Review</div>'
                    f'<div class="s" style="color:var(--muted)">{esc(line)}</div></div>'
                    '<div class="sk-tag">Curiosity fuels progress.</div>', unsafe_allow_html=True)



def render_history():
    st.markdown(
        '<div class="sk-label">Research history</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.runs:
        st.info("No research yet. Completed runs will appear here.")
        return

    st.caption("Your completed research runs are saved locally.")
    with keyed_container("recent"):
        recent_rows()


def main():
    ss = st.session_state
    ss.setdefault("runs", [])
    ss.setdefault("active_run", None)
    ss.setdefault("view", "home")
    ss.setdefault("topic_input", "")
    ss.setdefault("input_error", None)
    ss.setdefault("theme", "dark")
    if "runs_loaded" not in ss:
        try:
            init_db()
            ss["runs"] = normalise_runs(get_all_runs())
        except Exception as exc:
            ss["runs"] = []
            ss["save_error"] = f"Could not load saved research history: {exc}"
        ss["runs_loaded"] = True

    st.markdown(theme_css(ss.theme) + CSS, unsafe_allow_html=True)

    pending = ss.pop("pending_topic", None)  # consumed once so reruns never repeat the pipeline
    running = pending is not None
    backend, backend_err = load_backend()
    side_ph = render_sidebar(running)

    _, tcol = st.columns([12, 1])
    with tcol:
        st.button("☀" if ss.theme == "dark" else "☾", on_click=cb_theme, key="theme_btn",
                  help="Switch to light theme" if ss.theme == "dark" else "Switch to dark theme")

    if backend is None:
        st.error("The research backend could not be loaded, so research is unavailable.")
        st.markdown(f"**Details:** `{backend_err}`")
        st.markdown("Check that `.env` defines `GOOGLE_API_KEY` and `TAVILY_API_KEY`, and that dependencies "
                    "are installed: `pip install -r requirements.txt`.")

    if ss.view == "history" and not running:
        render_history()
        return
    if ss.view == "projects" and not running:
        st.markdown('<div class="sk-label">Projects</div>', unsafe_allow_html=True)
        st.info("Projects are not available yet. Your research runs are under Research history.")
        return

    if ss.get("save_error"):
        st.warning(ss.pop("save_error"))

    # Each render_* call below happens exactly once per script run (unique widget keys).
    if running:
        render_hero()
        render_composer(backend, running)
        execute_run(pending, backend, side_ph)  # ends with st.rerun()
        return

    if ss.view == "run" and ss.active_run and get_run(ss.active_run):
        render_composer(backend, running)
        render_run(get_run(ss.active_run))
        return
    ss.view = "home" if ss.view == "run" else ss.view

    render_hero()
    render_composer(backend, running)
    render_topics(running)
    st.markdown('<hr class="sk-rule">', unsafe_allow_html=True)
    left, right = st.columns([2.2, 1], gap="large")
    with left:
        render_recent()
    with right:
        render_quick_actions(running)


main()