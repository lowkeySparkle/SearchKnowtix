"""SearchKnowtix - Streamlit front end for the multi-agent research pipeline."""

import html
import os
import re
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st

st.set_page_config(
    page_title="SearchKnowtix",
    page_icon="💭",
    layout="wide",
    initial_sidebar_state="expanded",
)

esc = html.escape

EXAMPLE_TOPICS = [
    "Compare leading AI models and their capabilities.",
    "Research advances in renewable energy.",
    "Investigate the latest cybersecurity trends.",
    "Analyze developments in robotics.",
]

STAGES = [
    ("search", "Search Agent", "Queries the web with Tavily for your topic."),
    ("reader", "Reader Agent", "Scrapes up to two result pages with BeautifulSoup."),
    ("writer", "Writer Agent", "Drafts the report from the collected research."),
    ("critic", "Critic Agent", "Reviews the report for support, clarity and gaps."),
]

STATUS_LABEL = {
    "pending": "Waiting",
    "running": "Working",
    "done": "Complete",
    "warn": "Attention",
    "failed": "Failed",
    "notrun": "Not run",
}

# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------

CSS = """
<style>
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@300,400,500,700,900&display=swap');
.stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label, .stApp button,
.stApp textarea, .stApp input, .stApp li, .stApp a, section[data-testid="stSidebar"]{
  font-family:'Satoshi',-apple-system,'Segoe UI',sans-serif;}
:root{
  --rr-bg:#04254E; --rr-surface:#07305F; --rr-surface2:#052B57;
  --rr-border:rgba(148,163,200,.16); --rr-text:#e6edf7; --rr-muted:#93a1bd;
  --rr-cyan:#8AD5EB; --rr-blue:#5954A4; --rr-violet:#8A54A2;
  --rr-green:#34d399; --rr-amber:#fbbf24; --rr-red:#f87171;
}
.stApp{background:
  radial-gradient(1100px 520px at 85% -8%, rgba(138,84,162,.13), transparent 60%),
  radial-gradient(900px 480px at -5% 0%, rgba(138,213,235,.10), transparent 55%),
  var(--rr-bg);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2.2rem;max-width:1280px;}
h1,h2,h3,h4{letter-spacing:-.01em;}
section[data-testid="stSidebar"]{background:#031d3d;border-right:1px solid var(--rr-border);}
section[data-testid="stSidebar"] .block-container{padding-top:1.2rem;}

.rr-brand{display:flex;align-items:center;gap:.7rem;margin-bottom:.4rem;}
.rr-brand .name{font-weight:700;font-size:1.15rem;line-height:1.1;}
.rr-brand .sub{font-size:.72rem;color:var(--rr-muted);letter-spacing:.08em;text-transform:uppercase;}
.rr-side-h{font-size:.7rem;color:var(--rr-muted);letter-spacing:.12em;text-transform:uppercase;margin:1.1rem 0 .4rem;}
.rr-flow{list-style:none;margin:0;padding:0;}
.rr-flow li{display:flex;gap:.6rem;padding:.35rem 0;font-size:.84rem;color:#c5d0e6;}
.rr-flow .n{flex:0 0 1.35rem;height:1.35rem;border-radius:50%;border:1px solid var(--rr-border);
  font-size:.68rem;display:flex;align-items:center;justify-content:center;color:var(--rr-cyan);}
.rr-side-note{font-size:.76rem;color:var(--rr-muted);line-height:1.45;}
.rr-run-ind{border:1px solid var(--rr-border);border-radius:12px;padding:.6rem .8rem;background:var(--rr-surface2);
  font-size:.82rem;color:#c5d0e6;}
.rr-dot{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;margin-right:.45rem;background:#52607d;}
.rr-dot.run{background:var(--rr-cyan);box-shadow:0 0 0 0 rgba(138,213,235,.6);animation:rrpulse 1.6s infinite;}
.rr-dot.ok{background:var(--rr-green);} .rr-dot.warn{background:var(--rr-amber);} .rr-dot.bad{background:var(--rr-red);}
@keyframes rrpulse{70%{box-shadow:0 0 0 7px rgba(138,213,235,0);}100%{box-shadow:0 0 0 0 rgba(138,213,235,0);}}

.rr-hero{padding:.4rem 0 1.1rem;}
.rr-hero .eyebrow{font-size:.74rem;letter-spacing:.16em;text-transform:uppercase;color:var(--rr-cyan);}
.rr-hero h1{font-size:2.6rem;margin:.15rem 0 .1rem;font-weight:750;
  background:linear-gradient(92deg,#e6edf7 10%,#8AD5EB 55%,#8A54A2 100%);-webkit-background-clip:text;
  background-clip:text;color:transparent;}
.rr-hero .tag{font-size:1.05rem;color:#c5d0e6;margin-bottom:.35rem;}
.rr-hero .desc{max-width:60rem;color:var(--rr-muted);font-size:.95rem;line-height:1.55;}

.rr-h2{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--rr-muted);margin:1.4rem 0 .6rem;}

.rr-stage{position:relative;background:linear-gradient(180deg,var(--rr-surface),var(--rr-surface2));
  border:1px solid var(--rr-border);border-radius:16px;padding:1rem 1rem .9rem;min-height:15.5rem;
  transition:border-color .25s, box-shadow .25s;}
.rr-stage::before{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:#1d4a78;}
.rr-stage.rr-running{border-color:rgba(138,213,235,.55);box-shadow:0 0 0 1px rgba(138,213,235,.18),0 8px 30px rgba(138,213,235,.08);}
.rr-stage.rr-running::before{background:linear-gradient(90deg,var(--rr-cyan),var(--rr-violet));}
.rr-stage.rr-done::before{background:var(--rr-green);}
.rr-stage.rr-warn::before{background:var(--rr-amber);}
.rr-stage.rr-failed::before{background:var(--rr-red);}
.rr-stage.rr-next::after{content:"";position:absolute;right:-1.05rem;top:2.1rem;width:1rem;height:2px;
  background:linear-gradient(90deg,var(--rr-cyan),var(--rr-violet));opacity:.5;}
@media (max-width:640px){.rr-stage.rr-next::after{display:none;}.rr-stage{min-height:0;}}
.rr-stage .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:.15rem;}
.rr-stage .idx{font-size:.7rem;color:var(--rr-muted);letter-spacing:.12em;}
.rr-stage .nm{font-weight:650;font-size:1.02rem;margin:.1rem 0 .1rem;}
.rr-stage .pp{font-size:.8rem;color:var(--rr-muted);margin-bottom:.6rem;line-height:1.4;}
.rr-stage .k{font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--rr-muted);margin-top:.5rem;}
.rr-stage .v{font-size:.84rem;color:#d6dff0;line-height:1.4;word-break:break-word;}
.rr-stage .row{font-size:.8rem;color:#c5d0e6;padding:.18rem 0;word-break:break-all;}
.rr-stage .row .s{color:var(--rr-muted);}
.rr-stage .prev{font-size:.78rem;color:#9fb0cf;border-left:2px solid var(--rr-border);padding-left:.6rem;margin-top:.4rem;line-height:1.45;}

.rr-pill{font-size:.68rem;padding:.16rem .55rem;border-radius:999px;border:1px solid var(--rr-border);color:#c5d0e6;white-space:nowrap;}
.rr-pill.running{color:var(--rr-cyan);border-color:rgba(138,213,235,.5);}
.rr-pill.done{color:var(--rr-green);border-color:rgba(52,211,153,.45);}
.rr-pill.warn{color:var(--rr-amber);border-color:rgba(251,191,36,.45);}
.rr-pill.failed{color:var(--rr-red);border-color:rgba(248,113,113,.45);}

.rr-card{background:linear-gradient(180deg,var(--rr-surface),var(--rr-surface2));border:1px solid var(--rr-border);
  border-radius:16px;padding:1.1rem 1.25rem;margin-bottom:.8rem;}
.rr-card .t{font-size:1.35rem;font-weight:680;line-height:1.3;margin:.1rem 0 .2rem;}
.rr-card .q{color:var(--rr-muted);font-size:.9rem;margin-bottom:.7rem;word-break:break-word;}
.rr-chips{display:flex;flex-wrap:wrap;gap:.45rem;}
.rr-chip{font-size:.76rem;padding:.22rem .65rem;border-radius:8px;background:rgba(148,163,200,.08);
  border:1px solid var(--rr-border);color:#c5d0e6;}
.rr-chip.ok{color:var(--rr-green);} .rr-chip.warn{color:var(--rr-amber);} .rr-chip.bad{color:var(--rr-red);}

.rr-src{display:flex;gap:.8rem;align-items:flex-start;padding:.7rem .9rem;margin-bottom:.45rem;border-radius:12px;
  background:var(--rr-surface2);border:1px solid var(--rr-border);}
.rr-src .num{flex:0 0 1.6rem;color:var(--rr-cyan);font-size:.8rem;padding-top:.1rem;}
.rr-src a{color:#8AD5EB;text-decoration:none;word-break:break-all;}
.rr-src a:hover{text-decoration:underline;}
.rr-src .ti{font-weight:600;color:var(--rr-text);margin-bottom:.1rem;}
.rr-src .meta{font-size:.76rem;color:var(--rr-muted);margin-top:.15rem;}

.st-key-rr-report{background:var(--rr-surface2);border:1px solid var(--rr-border);border-radius:16px;
  padding:1.6rem clamp(1rem,3vw,2.6rem);}
.st-key-rr-report > div{max-width:54rem;margin:0 auto;}
.st-key-rr-report p, .st-key-rr-report li{font-size:1.02rem;line-height:1.75;color:#dbe4f3;}
.st-key-rr-report h1,.st-key-rr-report h2,.st-key-rr-report h3{margin-top:1.6rem;}
.st-key-rr-report a{color:#8AD5EB;}
.st-key-rr-critic{background:linear-gradient(180deg,rgba(138,84,162,.10),rgba(138,84,162,.03));
  border:1px solid rgba(138,84,162,.35);border-left:3px solid var(--rr-violet);border-radius:14px;padding:1.1rem 1.4rem;}

.stButton>button,.stDownloadButton>button{border-radius:10px;transition:all .2s ease;}
/* primary buttons: scampi -> vivid purple */
.stButton>button[kind="primary"],button[data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,#5954A4,#8A54A2);border:1px solid rgba(138,213,235,.35);color:#fff;
  box-shadow:0 4px 18px rgba(89,84,164,.35);}
.stButton>button[kind="primary"]:hover,button[data-testid="stBaseButton-primary"]:hover{
  background:linear-gradient(135deg,#6a64b8,#9c63b5);border-color:#8AD5EB;color:#fff;}
.stButton>button[kind="primary"]:disabled,button[data-testid="stBaseButton-primary"]:disabled{opacity:.45;box-shadow:none;}
/* secondary buttons: denim surface, sky blue accents */
.stButton>button[kind="secondary"],.stDownloadButton>button,
button[data-testid="stBaseButton-secondary"]{
  background:rgba(138,213,235,.06);border:1px solid rgba(138,213,235,.28);color:#e6edf7;}
.stButton>button[kind="secondary"]:hover,.stDownloadButton>button:hover,
button[data-testid="stBaseButton-secondary"]:hover{
  background:rgba(138,213,235,.14);border-color:#8AD5EB;color:#8AD5EB;}
.stButton>button:focus-visible,.stDownloadButton>button:focus-visible{outline:2px solid #8AD5EB;outline-offset:2px;box-shadow:none;}
/* tabs, inputs, expanders */
[data-baseweb="tab-highlight"]{background-color:#8AD5EB !important;}
button[data-baseweb="tab"][aria-selected="true"]{color:#8AD5EB;}
.stTextArea textarea:focus{border-color:#8AD5EB;box-shadow:0 0 0 1px rgba(138,213,235,.5);}
[data-testid="stExpander"] details{border-color:rgba(138,213,235,.2);background:rgba(5,43,87,.5);}
.stTextArea textarea{background:var(--rr-surface2);border:1px solid var(--rr-border);border-radius:12px;font-size:1rem;}
</style>
"""

LOGO = """
<svg width="40" height="40" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-label="SearchKnowtix logo">
<defs><linearGradient id="rrg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#8AD5EB"/><stop offset="1" stop-color="#8A54A2"/></linearGradient></defs>
<rect x="1" y="1" width="46" height="46" rx="13" fill="#031d3d" stroke="url(#rrg)" stroke-width="1.5"/>
<path d="M24 8c-4 0-6 3.2-5 6-3.4-.8-6 1.8-4.6 5 2.6-.6 3.6-.2 4.6.2V35l5 4 5-4V19.2c1-.4 2-.8 4.6-.2 1.4-3.2-1.2-5.8-4.6-5 1-2.8-1-6-5-6z" fill="url(#rrg)"/>
<circle cx="24" cy="22" r="1.6" fill="#031d3d"/>
</svg>
"""

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
    """Return the URL if it is a plain http(s) URL, else None."""
    try:
        p = urlparse(str(url).strip())
    except Exception:
        return None
    if p.scheme in ("http", "https") and p.netloc and " " not in url:
        return url.strip()
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
                "This is usually short-lived: wait a minute and run the research again.")
    if "504" in m or "deadline" in m or "timed out" in m or "timeout" in m:
        return ("The request timed out (HTTP 504 or a timeout). "
                "Try again shortly, or use a narrower topic.")
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


# --------------------------------------------------------------------------
# Backend loading
# --------------------------------------------------------------------------


def load_backend():
    """Import the existing pipeline. Returns (module, error_message)."""
    try:
        import pipeline  # noqa: WPS433 (imports agents.py and tools.py)
        return pipeline, None
    except Exception as exc:  # missing keys, missing packages, ...
        return None, f"{type(exc).__name__}: {str(exc)[:240]}"


def backend_config(pipeline_mod):
    cfg = {}
    try:
        import agents
        cfg["model"] = str(getattr(agents.llm, "model", "") or "unknown")
    except Exception:
        cfg["model"] = "unknown"
    cfg["google_key"] = bool(os.getenv("GOOGLE_API_KEY"))
    cfg["tavily_key"] = bool(os.getenv("TAVILY_API_KEY"))
    return cfg


# --------------------------------------------------------------------------
# Stage state (built from real pipeline events)
# --------------------------------------------------------------------------


def new_stages():
    return {
        k: {
            "status": "pending", "detail": "", "url_count": None, "urls": [],
            "pages": {}, "scraped": None, "attempted": None,
            "fallback": False, "revision": None, "revision_note": "",
        }
        for k, _, _ in STAGES
    }


def apply_event(stages, ev):
    stage, event, msg = ev.get("stage"), ev.get("event"), ev.get("message", "")
    if stage == "revision":
        w = stages["writer"]
        w["revision"] = {"started": "running", "completed": "done",
                         "failed": "failed", "skipped": "skipped"}.get(event, w["revision"])
        w["revision_note"] = msg
        return
    s = stages.get(stage)
    if s is None:
        return
    if event == "started":
        s["status"] = "running"
        s["detail"] = msg
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
        s["fallback"] = True
        s["detail"] = msg
    elif event == "completed":
        s["detail"] = msg
        if stage == "search":
            s["url_count"] = ev.get("url_count")
            s["urls"] = list(ev.get("urls", []))
            s["status"] = "warn" if not ev.get("url_count") else "done"
        elif stage == "reader":
            s["scraped"], s["attempted"] = ev.get("scraped"), ev.get("attempted")
            s["status"] = "done" if ev.get("scraped") else "warn"
        elif stage == "writer":
            s["status"] = "warn" if (s["fallback"] or ev.get("fallback")) else "done"
        else:
            s["status"] = "done"
    elif event == "failed":
        s["status"] = "failed"
        s["detail"] = msg


def finalize_stages(stages):
    """Anything that never finished once the run is over did not complete."""
    for s in stages.values():
        if s["status"] == "running":
            s["status"] = "failed"
            s["detail"] = s["detail"] or "Interrupted before finishing."
        elif s["status"] == "pending":
            s["status"] = "notrun"
    w = stages["writer"]
    if w["revision"] == "running":
        w["revision"] = "failed"


def search_urls_from_state(state):
    text = str((state or {}).get("search_result", ""))
    found = re.findall(r"(?m)^URL:\s*(\S+)", text)
    out = []
    for u in found:
        if u not in out:
            out.append(u)
    return out


def stage_card_html(idx, key, info, topic, state=None):
    _, name, purpose = STAGES[idx]
    state = state or {}
    status = info["status"]
    pill = f'<span class="rr-pill {status}">{STATUS_LABEL[status]}</span>'
    body = []

    def kv(k, v):
        body.append(f'<div class="k">{esc(k)}</div><div class="v">{v}</div>')

    if key == "search":
        kv("Topic", esc(plain_preview(topic, 150)) if topic else "Waiting for a topic")
        if status == "running":
            kv("Status", "Searching the web…")
        elif status in ("done", "warn"):
            n = info["url_count"]
            kv("Result URLs", "None detected" if not n else f"{n} detected")
        elif status == "failed":
            kv("Problem", esc(friendly_error(info["detail"])))
        urls = search_urls_from_state(state) or info["urls"]
        for u in urls[:4]:
            body.append(f'<div class="row">{esc(short_url(u, 48))}</div>')
        if len(urls) > 4:
            body.append(f'<div class="row s">+ {len(urls) - 4} more</div>')

    elif key == "reader":
        body.append('<div class="k">Scope</div><div class="v">The backend reads at most 2 URLs.</div>')
        glyph = {"queued": "·", "reading": "…", "read": "✓", "skipped": "✕"}
        for u, (st_, why) in info["pages"].items():
            label = {"queued": "queued", "reading": "reading", "read": "read", "skipped": "skipped"}[st_]
            body.append(f'<div class="row">{glyph[st_]} {esc(short_url(u, 44))} <span class="s">— {label}</span></div>')
        if info["scraped"] is not None:
            kv("Pages read", f'{info["scraped"]} of {info["attempted"]}')
        if status == "notrun":
            kv("Status", "Not reached")

    elif key == "writer":
        if status == "running":
            kv("Status", "Generating the report…")
        elif status == "done":
            kv("Report", "Generated by the writer model")
        elif status == "warn":
            kv("Report", "Fallback: assembled locally, not written by the model")
        elif status == "failed":
            kv("Problem", esc(friendly_error(info["detail"])))
        elif status == "notrun":
            kv("Status", "Not reached")
        rev = info["revision"]
        if rev:
            text = {"running": "Revising with critic feedback…", "done": "Revised using critic feedback",
                    "failed": "Revision failed; original kept", "skipped": "Skipped (no critic feedback)"}[rev]
            kv("Revision pass", esc(text))
        prev = plain_preview(state.get("initial_report") or state.get("report"))
        if prev and status in ("done", "warn"):
            body.append(f'<div class="prev">{esc(prev)}</div>')

    elif key == "critic":
        if status == "running":
            kv("Status", "Reviewing the report…")
        elif status == "done":
            kv("Review", "Feedback received")
        elif status == "failed":
            kv("Warning", esc(friendly_error(info["detail"])) if info["detail"] else "Review failed")
        elif status == "notrun":
            kv("Status", "Not reached")
        prev = plain_preview(state.get("feedback"))
        if prev and status == "done":
            body.append(f'<div class="prev">{esc(prev)}</div>')

    nxt = " rr-next" if idx < 3 else ""
    return (
        f'<div class="rr-stage rr-{status}{nxt}">'
        f'<div class="top"><span class="idx">STAGE 0{idx + 1}</span>{pill}</div>'
        f'<div class="nm">{esc(name)}</div><div class="pp">{esc(purpose)}</div>'
        + "".join(body) + "</div>"
    )


def render_stage_cards(stages, topic, state=None, placeholders=None):
    if placeholders is None:
        cols = st.columns(4, gap="large")
        for i, (key, _, _) in enumerate(STAGES):
            cols[i].markdown(stage_card_html(i, key, stages[key], topic, state), unsafe_allow_html=True)
        return None
    for i, (key, _, _) in enumerate(STAGES):
        placeholders[i].markdown(stage_card_html(i, key, stages[key], topic, state), unsafe_allow_html=True)
    return placeholders


# --------------------------------------------------------------------------
# Run records
# --------------------------------------------------------------------------

STATE_FIELDS = (
    "search_result", "scraped_content", "report", "initial_report", "feedback",
    "source_urls", "pages", "report_method", "revised", "search_ok",
    "search_error", "writer_error", "critic_error", "revision_error",
)


def compute_status(state, error):
    if not state.get("report"):
        return "failed"
    problems = (
        error, state.get("search_error"), not state.get("search_ok", True),
        state.get("report_method") == "fallback", state.get("critic_error"),
        state.get("revision_error"),
        (state.get("pages") is not None and len(state.get("pages", [])) > 0
         and not any(p.get("status") == "scraped" for p in state.get("pages", []))),
    )
    return "partial" if any(problems) else "complete"


def pages_summary(state):
    pages = state.get("pages") or []
    if not pages and state.get("scraped_content") is None:
        return None
    ok = sum(1 for p in pages if p.get("status") == "scraped")
    return ok, len(pages)


def run_notices(run):
    s, out = run["state"], []
    if run.get("error"):
        err = run["error"]
        if "progress_callback" in err or "unexpected keyword" in err:
            out.append(("error",
                        "Your pipeline.py is the old version (it does not accept progress_callback / state). "
                        "Replace it with the updated pipeline.py provided with this app, then restart Streamlit."))
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
        extra = (" The critic's feedback was then used by the revision model to rewrite it, "
                 "so the final text below is a model revision of that fallback draft." if s.get("revised") else "")
        out.append(("warning",
                    "Fallback report: the writer model failed, so the initial draft was assembled locally "
                    "from the collected research rather than generated by the writer." + extra
                    + (f" {friendly_error(s['writer_error'])}" if s.get("writer_error") else "")))
    if s.get("report") and not s.get("feedback"):
        out.append(("warning",
                    "The critic review failed or returned no feedback. The report is shown without a review. "
                    + friendly_error(s.get("critic_error", ""))))
    if s.get("revision_error"):
        out.append(("warning", "The revision pass failed, so the original report is shown. "
                    + friendly_error(s["revision_error"])))
    return out


def execute_run(topic, backend):
    """Run the real pipeline, updating the UI from real progress events."""
    started = datetime.now()
    t0 = time.perf_counter()
    stages, events, state, error = new_stages(), [], {}, None

    st.markdown('<div class="rr-h2">Live workflow</div>', unsafe_allow_html=True)
    cols = st.columns(4, gap="large")
    holders = [c.empty() for c in cols]
    render_stage_cards(stages, topic, None, holders)
    log = st.status("Research in progress…", expanded=True)

    def on_event(ev):
        ev = dict(ev)
        ev["t"] = round(time.perf_counter() - t0, 1)
        events.append(ev)
        apply_event(stages, ev)
        render_stage_cards(stages, topic, None, holders)
        msg = plain_preview(ev.get("message", ""), 150)
        log.text(f"+{ev['t']:>5.1f}s  {ev.get('stage')} · {ev.get('event')}  {msg}")

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
    render_stage_cards(stages, topic, snapshot, holders)
    log.update(
        label={"complete": "Research complete", "partial": "Research finished with issues",
               "failed": "Research failed"}[status],
        state={"complete": "complete", "partial": "complete", "failed": "error"}[status],
        expanded=False,
    )

    run = {
        "id": uuid.uuid4().hex[:8], "topic": topic, "started_at": started,
        "duration": round(time.perf_counter() - t0, 1), "status": status,
        "state": snapshot, "events": events, "error": error,
    }
    st.session_state.runs.append(run)
    st.session_state.active_run = run["id"]
    st.session_state.view = "dashboard"
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
        out.append({
            "url": u, "title": titles.get(u),
            "origin": "Search result" if u in search_urls else "Found in page content",
            "read": page_status.get(u),
        })
    return out


def render_sources(state):
    sources = collect_sources(state)
    if not sources:
        st.info("No source URLs were collected for this run.")
        return
    st.caption("URLs collected from the search results and scraped pages. "
               "They are listed as retrieved and have not been independently verified.")
    rows = []
    for i, s in enumerate(sources, 1):
        link = safe_url(s["url"])
        label = esc(s["url"])
        anchor = (f'<a href="{esc(link, quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>'
                  if link else f"{label} <span class='meta'>(not a valid web link)</span>")
        title = f'<div class="ti">{esc(s["title"])}</div>' if s["title"] else ""
        read = {"scraped": "page read", "skipped": "page could not be read"}.get(
            s["read"], "not read (the backend reads at most 2 pages)")
        rows.append(
            f'<div class="rr-src"><div class="num">{i:02d}</div><div>{title}{anchor}'
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
        st.warning("No critic feedback is available for this run. "
                   + friendly_error(s.get("critic_error", "")))
        if s.get("critic_error"):
            st.caption(f"Details: {s['critic_error']}")
        return
    if s.get("revised"):
        st.caption("The critic reviewed the initial report. The final report was then revised "
                   "by the writer using this feedback.")
    parsed = parse_critic(fb)
    with keyed_container("rr-critic"):
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
    st.markdown('<div class="rr-h2">Copy report text</div>', unsafe_allow_html=True)
    st.caption("Use the copy icon at the top-right of the block below.")
    if _supports_wrap():
        st.code(report, language="markdown", wrap_lines=True)
    else:
        st.code(report, language="markdown")


def _supports_wrap():
    try:
        import inspect
        return "wrap_lines" in inspect.signature(st.code).parameters
    except Exception:
        return False


def method_label(state):
    m = state.get("report_method")
    base = {"ai": "Generated by the writer model", "fallback": "Fallback draft (assembled locally)"}.get(
        m, "Generation method unknown")
    if state.get("revised"):
        base += " · revised with critic feedback"
    return base


def render_overview(run):
    s = run["state"]
    status = run["status"]
    cls = {"complete": "ok", "partial": "warn", "failed": "bad"}[status]
    label = {"complete": "Completed", "partial": "Completed with issues", "failed": "Failed"}[status]
    ps = pages_summary(s)
    chips = [f'<span class="rr-chip {cls}">{label}</span>',
             f'<span class="rr-chip {"warn" if s.get("report_method") == "fallback" else ""}">{esc(method_label(s))}</span>']
    if ps and ps[1]:
        chips.append(f'<span class="rr-chip">{ps[0]} of {ps[1]} pages scraped</span>')
    chips.append(f'<span class="rr-chip">{esc(fmt_time(run["started_at"]))} · {run["duration"]}s</span>')
    title = "Research report" if s.get("report") else "No report generated"
    st.markdown(
        f'<div class="rr-card"><div class="t">{title}</div>'
        f'<div class="q">{esc(run["topic"])}</div><div class="rr-chips">{"".join(chips)}</div></div>',
        unsafe_allow_html=True,
    )


def render_run(run):
    stages = new_stages()
    for ev in run["events"]:
        apply_event(stages, ev)
    finalize_stages(stages)
    st.markdown('<div class="rr-h2">Workflow</div>', unsafe_allow_html=True)
    render_stage_cards(stages, run["topic"], run["state"])

    st.markdown('<div class="rr-h2">Results</div>', unsafe_allow_html=True)
    render_overview(run)
    for level, text in run_notices(run):
        getattr(st, level)(text)

    t_report, t_sources, t_critic, t_raw, t_export = st.tabs(
        ["Final report", "Sources", "Critic review", "Raw research", "Export"])
    with t_report:
        report = run["state"].get("report")
        if report:
            with keyed_container("rr-report"):
                st.markdown(report)
            st.caption("The report is model-generated (or assembled from raw research) and its claims "
                       "have not been independently verified. Check important points against the sources.")
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


def cb_clear():
    st.session_state.topic_input = ""
    st.session_state.input_error = None


def cb_example(text):
    st.session_state.topic_input = text
    st.session_state.input_error = None


def cb_new():
    st.session_state.active_run = None
    st.session_state.view = "dashboard"
    st.session_state.topic_input = ""
    st.session_state.input_error = None


def cb_view(name):
    st.session_state.view = name


def cb_open(run_id):
    st.session_state.active_run = run_id
    st.session_state.view = "dashboard"


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------


def get_run(run_id):
    for r in st.session_state.runs:
        if r["id"] == run_id:
            return r
    return None


def render_sidebar(backend, backend_err, running, running_topic):
    ss = st.session_state
    with st.sidebar:
        st.markdown(
            f'<div class="rr-brand">{LOGO}<div><div class="name">SearchKnowtix</div>'
            f'<div class="sub">AI research workspace</div></div></div>', unsafe_allow_html=True)
        stretch(st.button, "＋  New Research", type="primary", on_click=cb_new,
                disabled=running, key="btn_new")

        st.markdown('<div class="rr-side-h">Navigate</div>', unsafe_allow_html=True)
        stretch(st.button, "Dashboard", on_click=cb_view, args=("dashboard",), disabled=running,
                type="primary" if ss.view == "dashboard" else "secondary", key="nav_dash")
        stretch(st.button, f"Research History ({len(ss.runs)})", on_click=cb_view, args=("history",),
                disabled=running, type="primary" if ss.view == "history" else "secondary", key="nav_hist")

        if ss.runs:
            st.markdown('<div class="rr-side-h">Recent</div>', unsafe_allow_html=True)
            glyph = {"complete": "●", "partial": "◐", "failed": "✕"}
            for r in reversed(ss.runs[-6:]):
                stretch(st.button, f"{glyph[r['status']]}  {plain_preview(r['topic'], 34)}",
                        on_click=cb_open, args=(r["id"],), disabled=running, key=f"recent_{r['id']}",
                        help=r["topic"])

        st.markdown('<div class="rr-side-h">Current run</div>', unsafe_allow_html=True)
        if running:
            st.markdown(f'<div class="rr-run-ind"><span class="rr-dot run"></span>Running: '
                        f'{esc(plain_preview(running_topic, 60))}</div>', unsafe_allow_html=True)
        elif ss.active_run and get_run(ss.active_run):
            r = get_run(ss.active_run)
            dot = {"complete": "ok", "partial": "warn", "failed": "bad"}[r["status"]]
            st.markdown(f'<div class="rr-run-ind"><span class="rr-dot {dot}"></span>Viewing: '
                        f'{esc(plain_preview(r["topic"], 60))}<br><span class="rr-side-note">'
                        f'{esc(fmt_time(r["started_at"]))}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="rr-run-ind"><span class="rr-dot"></span>Idle</div>', unsafe_allow_html=True)

        st.markdown('<div class="rr-side-h">How it works</div>', unsafe_allow_html=True)
        st.markdown(
            '<ul class="rr-flow">'
            '<li><span class="n">1</span><span><b>Search</b> the web with Tavily</span></li>'
            '<li><span class="n">2</span><span><b>Read</b> up to two result pages</span></li>'
            '<li><span class="n">3</span><span><b>Write</b> a structured report</span></li>'
            '<li><span class="n">4</span><span><b>Review</b> it with a critic</span></li></ul>'
            '<div class="rr-side-note">After the review, the writer revises the report once using the '
            "critic's feedback.</div>", unsafe_allow_html=True)

        st.markdown('<div class="rr-side-h">Backend configuration</div>', unsafe_allow_html=True)
        if backend is None:
            st.markdown(f'<div class="rr-side-note"><span class="rr-dot bad"></span>Backend not loaded</div>',
                        unsafe_allow_html=True)
        else:
            cfg = backend_config(backend)
            yn = lambda b: "loaded" if b else "missing"
            st.markdown(
                '<div class="rr-side-note">'
                f'Model: {esc(cfg["model"])}<br>'
                f'Gemini API key: {yn(cfg["google_key"])}<br>'
                f'Tavily API key: {yn(cfg["tavily_key"])}<br>'
                'Search: up to 5 results<br>Reader: up to 2 pages'
                '</div>', unsafe_allow_html=True)


def render_composer(backend, running):
    ss = st.session_state
    st.markdown('<div class="rr-h2">Start a research run</div>', unsafe_allow_html=True)
    st.text_area(
        "Research topic", key="topic_input", height=120, max_chars=1000, disabled=running,
        label_visibility="collapsed",
        placeholder="Describe what you want researched. Detailed questions work, not just keywords.",
    )
    if ss.get("input_error"):
        st.error(ss.input_error)
    c1, c2, c3 = st.columns([2, 1, 4])
    with c1:
        stretch(st.button, "Start Research", type="primary", on_click=cb_start,
                disabled=running or backend is None, key="btn_start")
    with c2:
        stretch(st.button, "Clear", on_click=cb_clear, disabled=running, key="btn_clear")
    with c3:
        if running:
            st.caption("A research run is in progress. Inputs are locked until it finishes.")
        else:
            st.caption("Very long questions may exceed the search provider's query limit; "
                       "if the search stage fails, try a shorter question.")
    st.caption("Try an example (fills the box, does not run anything):")
    cols = st.columns(len(EXAMPLE_TOPICS))
    for i, ex in enumerate(EXAMPLE_TOPICS):
        with cols[i]:
            stretch(st.button, ex, on_click=cb_example, args=(ex,), disabled=running, key=f"ex_{i}")


def render_history():
    runs = st.session_state.runs
    st.markdown('<div class="rr-h2">Research history (this session)</div>', unsafe_allow_html=True)
    if not runs:
        st.info("No research runs yet. Completed runs from this session will appear here.")
        return
    st.caption("History lives in this browser session only and is cleared when the session ends.")
    for r in reversed(runs):
        cls = {"complete": "ok", "partial": "warn", "failed": "bad"}[r["status"]]
        label = {"complete": "Completed", "partial": "Completed with issues", "failed": "Failed"}[r["status"]]
        c1, c2 = st.columns([6, 1])
        c1.markdown(
            f'<div class="rr-card" style="margin-bottom:.2rem"><div class="q" style="margin:0 0 .5rem">'
            f'{esc(plain_preview(r["topic"], 200))}</div><div class="rr-chips">'
            f'<span class="rr-chip {cls}">{label}</span>'
            f'<span class="rr-chip">{esc(fmt_time(r["started_at"]))}</span>'
            f'<span class="rr-chip">{esc(method_label(r["state"]))}</span></div></div>',
            unsafe_allow_html=True)
        with c2:
            stretch(st.button, "Open", on_click=cb_open, args=(r["id"],), key=f"hist_open_{r['id']}")


def main():
    ss = st.session_state
    ss.setdefault("runs", [])
    ss.setdefault("active_run", None)
    ss.setdefault("view", "dashboard")
    ss.setdefault("topic_input", "")
    ss.setdefault("input_error", None)

    st.markdown(CSS, unsafe_allow_html=True)

    # A pending topic is consumed exactly once, so reruns never repeat the pipeline.
    pending = ss.pop("pending_topic", None)
    running = pending is not None

    backend, backend_err = load_backend()
    render_sidebar(backend, backend_err, running, pending)

    st.markdown(
        '<div class="rr-hero"><div class="eyebrow">Multi-agent research</div><h1>SearchKnowtix</h1>'
        '<div class="tag">Your AI-powered research workspace</div>'
        '<div class="desc">SearchKnowtix searches the web, extracts information from result pages, '
        'generates a structured report, and has a critic review the findings. Search deeper. '
        'Think smarter. Research with confidence.</div></div>', unsafe_allow_html=True)

    if backend is None:
        st.error("The research backend could not be loaded, so research is unavailable.")
        st.markdown(f"**Details:** `{backend_err}`")
        st.markdown(
            "Check that `.env` in the project folder defines `GOOGLE_API_KEY` and `TAVILY_API_KEY`, "
            "and that dependencies are installed: `pip install -r requirements.txt`.")

    if ss.view == "history" and not running:
        render_history()
        return

    render_composer(backend, running)

    if running:
        execute_run(pending, backend)  # ends with st.rerun()
        return

    run = get_run(ss.active_run) if ss.active_run else None
    if run:
        render_run(run)
    else:
        st.markdown('<div class="rr-h2">Workflow</div>', unsafe_allow_html=True)
        render_stage_cards(new_stages(), "", None)
        st.caption("Nothing has run yet. Each stage reports its real status once you start a research run.")


main()