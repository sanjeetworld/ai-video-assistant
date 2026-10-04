"""
AI Video Assistant — Streamlit frontend ("Obsidian Intelligence").

Frontend only. All AI work is done by the existing backend functions:
    process_input, transcribe_all, generate_title, summarize,
    extract_action_items, extract_key_decisions, extract_questions,
    build_rag_chain, ask_question
This file contains no Whisper / LLM / RAG logic of its own.

Run:  streamlit run app.py        (needs Streamlit >= 1.40)
"""
import html
import json
import os
import re
import shutil
import tempfile
import time
import traceback
import uuid
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components

# Must be the first Streamlit call.
st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Backend imports (unchanged backend). A failure is surfaced in the UI
# instead of crashing the app.
# --------------------------------------------------------------------------
BACKEND_ERROR = None
try:
    from dotenv import load_dotenv

    load_dotenv()
    from utils.audio_processor import process_input
    from core.transcriber import transcribe_all
    from core.summarizer import summarize, generate_title
    from core.extractor import (
        extract_action_items,
        extract_key_decisions,
        extract_questions,
    )
    from core.rag_engine import build_rag_chain, ask_question
except Exception as exc:  # noqa: BLE001
    BACKEND_ERROR = exc


# ==========================================================================
# DESIGN TOKENS — single source of truth for the "Obsidian Intelligence" system
# ==========================================================================
PALETTE = {
    "bg": "#070A12",
    "sidebar": "#0B0F19",
    "surface": "#101624",
    "surface-hover": "#151D2E",
    "surface-elevated": "#182033",
    "border": "#202A3A",
    "border-active": "#334155",
    "text": "#F8FAFC",
    "text-secondary": "#CBD5E1",
    "text-muted": "#94A3B8",
    "text-disabled": "#64748B",
    "primary": "#8B5CF6",
    "primary-hover": "#A78BFA",
    "primary-dark": "#7C3AED",
    "indigo": "#4F46E5",
    "cyan": "#22D3EE",
    "cyan-dark": "#0891B2",
    "success": "#34D399",
    "warning": "#FBBF24",
    "error": "#FB7185",
    "info": "#60A5FA",
    "glow-brand": "rgba(139, 92, 246, 0.12)",
    "glow-cyan": "rgba(34, 211, 238, 0.08)",
    "nav-hover": "#111827",
    "scroll-hover": "#475569",
}

ROOT_CSS = (
    "<style>:root{"
    + "".join(f"--{k}:{v};" for k, v in PALETTE.items())
    + "}</style>"
)

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap');

html, body, .stApp, p, li, label, button, input, textarea, h1, h2, h3, h4,
[data-testid="stMarkdownContainer"], [data-baseweb="tab"], [data-baseweb="select"] {
  font-family: 'Geist', 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}

/* ---------- App shell ---------- */
.stApp {
  background:
    radial-gradient(900px 420px at 88% -8%, var(--glow-brand), transparent 70%),
    radial-gradient(700px 380px at 6% 0%, var(--glow-cyan), transparent 70%),
    linear-gradient(180deg, var(--bg) 0%, #0B1020 100%);
  background-attachment: fixed;
  color: var(--text-secondary);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"], [data-testid="stDeployButton"], [data-testid="stMainMenu"],
[data-testid="stStatusWidget"], footer { display: none !important; }
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1120px; padding-top: 2.2rem; padding-bottom: 5rem;
}
h1, h2, h3, h4, h5 { color: var(--text); letter-spacing: -0.01em; }
p, li { color: var(--text-secondary); }
a { color: var(--primary-hover); }
hr { border-color: var(--border); }
::selection { background: rgba(139,92,246,.35); color: var(--text); }

/* ---------- Scrollbars ---------- */
* { scrollbar-width: thin; scrollbar-color: var(--border-active) var(--sidebar); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--sidebar); }
::-webkit-scrollbar-thumb { background: var(--border-active); border-radius: 8px; border: 2px solid var(--sidebar); }
::-webkit-scrollbar-thumb:hover { background: var(--scroll-hover); }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
  background: var(--sidebar); border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: .4rem; }
.brand { display:flex; align-items:center; gap:.7rem; padding: .9rem .4rem 1.3rem; }
.brand-mark { width:34px; height:34px; border-radius:10px; flex:none;
  background: linear-gradient(145deg, rgba(139,92,246,.28), rgba(34,211,238,.16));
  border: 1px solid var(--border-active); display:grid; place-items:center; }
.brand-name { color: var(--text); font-weight:600; font-size:.82rem; letter-spacing:.08em; line-height:1.15; }
.brand-name span { color: var(--text-muted); font-weight:500; }
.nav-label { color: var(--text-disabled); font-size:.68rem; font-weight:600; letter-spacing:.12em;
  padding: 1.1rem .5rem .35rem; text-transform: uppercase; }

[class*="st-key-nav_"] button {
  justify-content: flex-start !important; gap:.3rem; background: transparent !important;
  border: none !important; box-shadow:none !important; color: var(--text-muted) !important;
  min-height: 2.3rem; padding: .35rem .75rem; border-radius: 8px !important; font-weight:500;
  transition: background .15s ease, color .15s ease;
}
[class*="st-key-nav_"] button p { color: inherit !important; font-size:.9rem; text-align:left; }
[class*="st-key-nav_"] button:hover { background: var(--nav-hover) !important; color: var(--text) !important; }
[class*="st-key-nav_"] button:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }

.status-box { margin-top: 1.6rem; padding: .9rem .85rem; border:1px solid var(--border);
  border-radius: 12px; background: rgba(16,22,36,.6); }
.status-title { color: var(--text-disabled); font-size:.68rem; font-weight:600; letter-spacing:.12em;
  margin-bottom:.6rem; text-transform: uppercase; }
.status-row { display:flex; align-items:center; gap:.55rem; padding:.22rem 0; font-size:.84rem; color: var(--text-secondary); }
.status-row .st-val { margin-left:auto; color: var(--text-muted); font-size:.76rem; }
.dot { width:7px; height:7px; border-radius:50%; flex:none; background: var(--text-disabled); }
.dot.success { background: var(--success); } .dot.warning { background: var(--warning); }
.dot.error { background: var(--error); }     .dot.idle { background: var(--text-disabled); }
.dot.info { background: var(--info); }

/* ---------- Headings ---------- */
.hero { padding: .6rem 0 1.4rem; }
.hero-title { color: var(--text); font-size: 2.05rem; font-weight:600; letter-spacing:-0.025em; line-height:1.15; max-width: 640px; }
.hero-sub { color: var(--text-muted); font-size: 1.02rem; margin-top:.7rem; max-width: 600px; line-height:1.55; }
.page-head { padding: .2rem 0 1.2rem; }
.page-title { color: var(--text); font-size:1.5rem; font-weight:600; letter-spacing:-0.02em; }
.page-sub { color: var(--text-muted); font-size:.95rem; margin-top:.3rem; }
.kicker { color: var(--text-muted); font-size:.72rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase; margin: .2rem 0 .6rem; }

/* ---------- Cards ---------- */
.st-key-analyze_card, .st-key-summary_card, .st-key-transcript_card, .st-key-chat_card {
  background: var(--surface); border:1px solid var(--border); border-radius:18px;
  padding: 1.3rem 1.4rem; box-shadow: 0 10px 30px -18px rgba(0,0,0,.8);
}
.card { background: var(--surface); border:1px solid var(--border); border-radius:14px;
  padding: .95rem 1.05rem; transition: background .15s ease, border-color .15s ease; }
.card:hover { background: var(--surface-hover); border-color: var(--border-active); }
.card-title { color: var(--text); font-weight:600; font-size:.95rem; }
.card-meta { color: var(--text-muted); font-size:.8rem; margin-top:.2rem; }

.badge { display:inline-flex; align-items:center; gap:.4rem; padding:.2rem .6rem; border-radius:999px;
  border:1px solid var(--border); background: var(--surface); color: var(--text-secondary); font-size:.76rem; }
.badges { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:.7rem; }

/* ---------- Metrics ---------- */
.metrics { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:.8rem; margin: 1.1rem 0 1.3rem; }
.metric { background: var(--surface); border:1px solid var(--border); border-radius:14px; padding: .9rem 1rem;
  transition: background .15s ease, border-color .15s ease; }
.metric:hover { background: var(--surface-hover); border-color: var(--border-active); }
.m-top { display:flex; align-items:center; gap:.5rem; }
.m-dot { width:6px; height:6px; border-radius:50%; }
.m-label { color: var(--text-muted); font-size:.72rem; font-weight:600; letter-spacing:.1em; }
.m-value { color: var(--text); font-size:1.7rem; font-weight:600; letter-spacing:-0.02em; margin-top:.35rem; }
.m-sub { color: var(--text-disabled); font-size:.76rem; }
@media (max-width: 760px) { .metrics { grid-template-columns: repeat(2, minmax(0,1fr)); } .hero-title{font-size:1.6rem;} }

/* ---------- Processing stages ---------- */
.stage { display:grid; grid-template-columns: 2.2rem 1fr auto; align-items:center; gap:.7rem;
  padding:.7rem .85rem; border:1px solid var(--border); border-radius:12px; background: var(--surface); margin-bottom:.5rem; }
.stage.active { border-color: var(--border-active); background: var(--surface-elevated); }
.stage.done .s-name { color: var(--text); }
.s-idx { font-family:'Geist Mono', ui-monospace, monospace; color: var(--text-disabled); font-size:.8rem; }
.s-name { color: var(--text-secondary); font-weight:500; font-size:.92rem; }
.s-desc { color: var(--text-disabled); font-size:.78rem; }
.s-state { display:flex; align-items:center; gap:.45rem; font-size:.78rem; color: var(--text-muted); }
.stage.active .dot { animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity:.35; } }
@media (prefers-reduced-motion: reduce) { .stage.active .dot { animation:none; } }

/* ---------- Insight cards ---------- */
.item { display:flex; gap:.8rem; align-items:flex-start; background: var(--surface); border:1px solid var(--border);
  border-radius:14px; padding:.85rem 1rem; margin-bottom:.6rem; transition: background .15s ease, border-color .15s ease; }
.item:hover { background: var(--surface-hover); border-color: var(--border-active); }
.item-body { color: var(--text-secondary); line-height:1.6; font-size:.95rem; }
.item-body strong { color: var(--text); font-weight:600; }
.item-mark { flex:none; width:20px; height:20px; border-radius:6px; margin-top:.15rem; display:grid; place-items:center;
  font-size:.72rem; font-weight:600; border:1.5px solid currentColor; }
.item.task .item-mark { color: var(--success); }
.item.decision { border-left: 3px solid var(--primary); }
.item.decision .item-mark { color: var(--primary-hover); border-color: transparent; background: rgba(139,92,246,.14); }
.item.question .item-mark { color: var(--warning); border-color: transparent; background: rgba(251,191,36,.12); }
.chips { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.5rem; }
.chip { font-size:.72rem; color: var(--text-muted); border:1px solid var(--border); border-radius:6px; padding:.1rem .45rem; }
.panel-head { display:flex; align-items:center; gap:.5rem; margin-bottom:.7rem; color: var(--text); font-weight:600; font-size:.92rem; }
.panel-head .count { color: var(--text-muted); font-weight:500; font-size:.8rem; margin-left:auto; }

/* ---------- Transcript ---------- */
.tstats { display:flex; flex-wrap:wrap; gap:1.6rem; padding-bottom: .9rem; margin-bottom:.9rem; border-bottom:1px solid var(--border); }
.tstat b { display:block; color: var(--text); font-size:1.05rem; font-weight:600; }
.tstat span { color: var(--text-muted); font-size:.74rem; }
.t-body { background: var(--sidebar); border:1px solid var(--border); border-radius:12px; padding: 1rem 1.1rem; }
.t-body.clipped { max-height: 520px; overflow-y:auto; }
.t-line { color: var(--text-secondary); line-height:1.85; font-size:.95rem; margin-bottom:.7rem; }
.t-ts { font-family:'Geist Mono', ui-monospace, monospace; color: var(--cyan); font-size:.78rem; margin-right:.6rem; }
mark { background: rgba(34,211,238,.15); color: var(--text); border-radius:3px; padding:0 2px; }

/* ---------- Empty / error ---------- */
.empty { text-align:center; padding: 3rem 1rem; border:1px dashed var(--border-active); border-radius:18px; background: rgba(16,22,36,.5); }
.empty-icon { width:42px; height:42px; margin: 0 auto .9rem; border-radius:12px; display:grid; place-items:center;
  background: var(--surface-elevated); border:1px solid var(--border-active); }
.empty-title { color: var(--text); font-weight:600; font-size:1.05rem; }
.empty-text { color: var(--text-muted); font-size:.92rem; margin-top:.3rem; }
.err { display:flex; gap:.8rem; background: var(--surface); border:1px solid var(--border); border-left:3px solid var(--error);
  border-radius:14px; padding:.95rem 1.1rem; margin-bottom:.6rem; }
.err-title { color: var(--text); font-weight:600; }
.err-text { color: var(--text-secondary); font-size:.92rem; margin-top:.15rem; }

/* ---------- Inputs ---------- */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
  background: var(--sidebar) !important; border-color: var(--border) !important; border-radius: 10px !important;
}
[data-baseweb="input"] input, [data-baseweb="select"] div, textarea { color: var(--text) !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {
  border-color: var(--primary) !important; box-shadow: 0 0 0 1px var(--primary) !important;
}
input::placeholder, textarea::placeholder { color: var(--text-disabled) !important; opacity:1; }
[data-testid="stFileUploaderDropzone"] { background: var(--sidebar); border:1px dashed var(--border-active); border-radius:12px; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--primary); }
[data-testid="stWidgetLabel"] p { color: var(--text-muted); font-size:.82rem; }

/* ---------- Buttons ---------- */
[data-testid="stBaseButton-primary"], button[kind="primary"] {
  background: linear-gradient(135deg, var(--primary), var(--indigo)) !important; color:#FFFFFF !important;
  border:none !important; border-radius: 10px !important; min-height: 2.6rem; font-weight:500;
  transition: filter .15s ease, transform .1s ease;
}
[data-testid="stBaseButton-primary"]:hover, button[kind="primary"]:hover { filter: brightness(1.12); }
[data-testid="stBaseButton-primary"]:active, button[kind="primary"]:active { background: var(--primary-dark) !important; transform: translateY(1px); }
[data-testid="stBaseButton-secondary"], button[kind="secondary"], [data-testid="stPopover"] > div > button {
  background: var(--surface-elevated); color: var(--text-secondary); border:1px solid var(--border);
  border-radius: 10px; min-height: 2.6rem; transition: background .15s ease, border-color .15s ease, color .15s ease;
}
[data-testid="stBaseButton-secondary"]:hover, button[kind="secondary"]:hover, [data-testid="stPopover"] > div > button:hover {
  background: var(--surface-hover); border-color: var(--border-active); color: var(--text);
}
button:focus-visible { outline: 2px solid var(--primary) !important; outline-offset: 2px; }
button:disabled { opacity:.5; }
[data-baseweb="popover"] > div { background: var(--surface-elevated) !important; border:1px solid var(--border-active); border-radius: 12px; }

/* ---------- Segmented control / radio ---------- */
[data-testid="stSegmentedControl"] button[aria-checked="true"], [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
  background: rgba(139,92,246,.14) !important; color: var(--primary-hover) !important; border-color: var(--primary) !important;
}

/* ---------- Tabs ---------- */
[data-baseweb="tab-list"] { gap: 1.4rem; border-bottom:1px solid var(--border); }
button[data-baseweb="tab"] { background: transparent !important; color: var(--text-muted); padding: .5rem 0; }
button[data-baseweb="tab"]:hover { color: var(--text); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--text); }
[data-baseweb="tab-highlight"] { background-color: var(--primary) !important; height:2px; }
[data-baseweb="tab-border"] { background-color: var(--border) !important; }

/* ---------- Expander / status / progress ---------- */
[data-testid="stExpander"], [data-testid="stStatus"] { background: var(--surface); border:1px solid var(--border) !important; border-radius:14px; }
[data-testid="stExpander"] summary, [data-testid="stStatus"] summary { color: var(--text-secondary); }
[data-testid="stProgress"] [role="progressbar"] > div { background: linear-gradient(90deg, var(--primary), var(--indigo)); }
[data-testid="stProgress"] [role="progressbar"] { background: var(--surface-elevated); }
[data-testid="stCode"], pre { background: var(--sidebar) !important; border:1px solid var(--border); border-radius: 10px; }

/* ---------- Chat ---------- */
[data-testid="stChatMessage"] { border:1px solid var(--border); border-radius:14px; padding: .85rem 1rem; background: var(--surface); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: var(--surface-elevated); }
[data-testid="stChatMessageAvatarAssistant"] { background: linear-gradient(145deg, var(--primary-dark), var(--indigo)) !important; color:#fff !important; }
[data-testid="stChatMessageAvatarUser"] { background: var(--border-active) !important; color: var(--text) !important; }
[data-testid="stChatInput"] { background: var(--sidebar); border:1px solid var(--border); border-radius: 14px; }
[data-testid="stChatInput"]:focus-within { border-color: var(--primary); }
[data-testid="stChatInput"] button { background: var(--primary) !important; color:#fff !important; }
[data-testid="stChatInput"] button:hover { background: var(--primary-hover) !important; }
</style>
"""


# ==========================================================================
# Small helpers
# ==========================================================================
def esc(value) -> str:
    return html.escape(str(value), quote=True)


def md_inline(text: str) -> str:
    """Escape, then allow **bold** only."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(text))


def as_text(value) -> str:
    """Coerce any backend return value (str / message object / dict / list) to text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("answer", "result", "output_text", "text", "content", "output"):
            if key in value:
                return as_text(value[key])
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if isinstance(value, (list, tuple)):
        return "\n".join(as_text(v) for v in value)
    content = getattr(value, "content", None)
    if content is not None:
        return as_text(content)
    return str(value)


_TEXT_KEYS = ("task", "action", "action_item", "decision", "question", "description", "text", "item", "content", "title")
_META_KEYS = ("owner", "assignee", "assigned_to", "deadline", "due", "due_date", "priority", "speaker", "timestamp")
_BULLET_RE = re.compile(r"^\s*(?:[-*•–]|\d+[.)])\s+")
_EMPTY_RE = re.compile(r"^\s*(none|no\b|n/?a\b|nothing|not (?:mentioned|specified|found))", re.I)


def as_items(value) -> list:
    """Return [{'text': str, 'meta': [(key, value), ...]}]. Meta only if the backend supplied it."""
    items = []
    if value is None:
        return items
    if isinstance(value, (list, tuple)):
        for entry in value:
            if isinstance(entry, dict):
                text = next((str(entry[k]) for k in _TEXT_KEYS if entry.get(k)), "")
                meta = [(k, str(entry[k])) for k in _META_KEYS if entry.get(k)]
                if not text:
                    text = "; ".join(f"{k}: {v}" for k, v in entry.items() if v)
                if text.strip():
                    items.append({"text": text.strip(), "meta": meta})
            else:
                text = _BULLET_RE.sub("", as_text(entry)).strip()
                if text:
                    items.append({"text": text, "meta": []})
    else:
        lines = [ln for ln in as_text(value).splitlines() if ln.strip()]
        if lines and lines[0].rstrip().endswith(":"):
            lines = lines[1:]
        for ln in lines:
            text = _BULLET_RE.sub("", ln).strip()
            if text:
                items.append({"text": text, "meta": []})
    if len(items) == 1 and _EMPTY_RE.match(items[0]["text"]):
        return []
    return items


def fmt_int(n: int) -> str:
    return f"{n:,}"


def short_source(src: str) -> str:
    if not src:
        return "—"
    if src.lower().startswith(("http://", "https://")):
        host = urlparse(src).netloc.replace("www.", "")
        return host or src
    return os.path.basename(src)


def scrub(text: str) -> str:
    """Remove API keys / tokens from any text before it is shown."""
    for name, val in os.environ.items():
        if any(t in name.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD")) and val and len(val) >= 6:
            text = text.replace(val, "••••••")
    return re.sub(r"\b(?:sk|gsk|hf|key)[-_][A-Za-z0-9_\-]{10,}", "••••••", text)


def classify_error(exc: Exception) -> tuple:
    msg = f"{type(exc).__name__}: {exc}".lower()
    if any(s in msg for s in ("rate limit", "ratelimit", "429", "too many requests", "quota")):
        return ("Rate limit reached", "The AI service is temporarily rate-limited. Please wait and try again.")
    if any(s in msg for s in ("api key", "api_key", "apikey", "unauthorized", "401", "authentication", "not set")):
        return ("Configuration missing", "AI API configuration is missing.")
    if any(s in msg for s in ("youtube", "yt_dlp", "yt-dlp", "video unavailable", "unable to download", "downloaderror", "http error 40")):
        return ("Video unavailable", "Unable to retrieve this video. Check the URL or try another source.")
    if "ffmpeg" in msg or "ffprobe" in msg:
        return ("FFmpeg not found", "Audio processing needs FFmpeg. Install it and make sure it is on your PATH.")
    if "no speech" in msg or "empty transcript" in msg:
        return ("No speech found", "The transcription came back empty. Try a source with clear spoken audio.")
    if isinstance(exc, FileNotFoundError):
        return ("File not found", "The selected file could not be found. Upload it again and retry.")
    return ("Analysis failed", "Something went wrong while processing this video. Open the technical details below for more information.")


def copy_button(text: str, label: str = "Copy", key: str = "copy") -> None:
    """Real clipboard copy through a tiny component; falls back to st.code."""
    payload = json.dumps(text).replace("</", "<\\/")
    p = PALETTE
    page = f"""
<style>
 html,body{{margin:0;background:transparent;}}
 button{{width:100%;height:38px;cursor:pointer;font:500 13px 'Geist','Inter',system-ui,sans-serif;
  color:{p['text-secondary']};background:{p['surface-elevated']};border:1px solid {p['border']};border-radius:10px;
  transition:all .15s ease;}}
 button:hover{{background:{p['surface-hover']};border-color:{p['border-active']};color:{p['text']};}}
 button:focus-visible{{outline:2px solid {p['primary']};}}
</style>
<button id="b" type="button">{esc(label)}</button>
<script>
 const t={payload}; const b=document.getElementById('b'); const l=b.textContent;
 b.onclick=async()=>{{
  try{{ await navigator.clipboard.writeText(t); }}
  catch(e){{ const a=document.createElement('textarea'); a.value=t; document.body.appendChild(a); a.select(); document.execCommand('copy'); a.remove(); }}
  b.textContent='Copied'; setTimeout(()=>b.textContent=l,1400);
 }};
</script>"""
    try:
        if hasattr(st, "iframe"):
            st.iframe(page, height=42)
        else:
            components.html(page, height=42)
    except Exception:  # noqa: BLE001
        with st.expander(label):
            st.code(text, language=None)


# ==========================================================================
# Session state
# ==========================================================================
def init_session_state() -> None:
    defaults = {
        "page": "overview",
        "analysis_result": None,
        "source": "",
        "language": "english",
        "transcript": "",
        "summary": "",
        "title": "",
        "action_items": [],
        "key_decisions": [],
        "open_questions": [],
        "rag_chain": None,
        "chat_history": [],
        "analysis_complete": False,
        "processing": False,
        "job": None,
        "error": None,
        "history": [],
        "current_id": None,
        "summary_expanded": False,
        "stage_states": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def go(page: str) -> None:
    st.session_state.page = page


def _stash_chat() -> None:
    cid = st.session_state.current_id
    for entry in st.session_state.history:
        if entry["id"] == cid:
            entry["chat"] = list(st.session_state.chat_history)


def load_result(result: dict, source: str, language: str, chat=None) -> None:
    st.session_state.analysis_result = result
    st.session_state.source = source
    st.session_state.language = language
    st.session_state.title = as_text(result.get("title")).strip() or "Untitled analysis"
    st.session_state.transcript = as_text(result.get("transcript"))
    st.session_state.summary = as_text(result.get("summary"))
    st.session_state.action_items = as_items(result.get("action_items"))
    st.session_state.key_decisions = as_items(result.get("key_decisions"))
    st.session_state.open_questions = as_items(result.get("open_questions"))
    st.session_state.rag_chain = result.get("rag_chain")
    st.session_state.chat_history = list(chat or [])
    st.session_state.analysis_complete = True
    st.session_state.summary_expanded = False


def open_history(entry_id: str) -> None:
    _stash_chat()
    for entry in st.session_state.history:
        if entry["id"] == entry_id:
            load_result(entry["result"], entry["source"], entry["language"], entry.get("chat"))
            st.session_state.current_id = entry_id
            st.session_state.page = "analyze"


def reset_for_new() -> None:
    _stash_chat()
    st.session_state.analysis_complete = False
    st.session_state.current_id = None
    st.session_state.analysis_result = None
    st.session_state.rag_chain = None
    st.session_state.chat_history = []
    st.session_state.transcript = ""
    st.session_state.error = None
    st.session_state.page = "analyze"


# ==========================================================================
# CSS injection
# ==========================================================================
def inject_css() -> None:
    st.markdown(ROOT_CSS, unsafe_allow_html=True)
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    active = st.session_state.page
    # Active nav item: soft violet tint, violet text and a 3px left indicator (no pills).
    st.markdown(
        f"<style>.st-key-nav_{active} button{{background: rgba(139,92,246,.12) !important;"
        f"color: var(--primary-hover) !important; box-shadow: inset 3px 0 0 var(--primary) !important;}}"
        f".st-key-nav_{active} button p{{color: var(--primary-hover) !important;}}</style>",
        unsafe_allow_html=True,
    )
    if not st.session_state.summary_expanded:
        st.markdown(
            "<style>.st-key-summary_body{max-height:230px;overflow:hidden;position:relative;"
            "-webkit-mask-image:linear-gradient(180deg,#000 70%,transparent);"
            "mask-image:linear-gradient(180deg,#000 70%,transparent);}</style>",
            unsafe_allow_html=True,
        )


# ==========================================================================
# Sidebar
# ==========================================================================
LOGO_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none">'
    '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#A78BFA"/><stop offset="1" stop-color="#22D3EE"/></linearGradient></defs>'
    '<path d="M8 5.5v13l11-6.5-11-6.5Z" stroke="url(#lg)" stroke-width="1.8" stroke-linejoin="round"/></svg>'
)

NAV_GROUPS = [
    (None, [("overview", "Overview", ":material/space_dashboard:"),
            ("analyze", "Analyze", ":material/graphic_eq:"),
            ("transcript", "Transcript", ":material/notes:")]),
    ("Intelligence", [("insights", "AI Insights", ":material/auto_awesome:"),
                      ("actions", "Action Items", ":material/task_alt:"),
                      ("decisions", "Decisions", ":material/gavel:"),
                      ("questions", "Questions", ":material/help:")]),
    ("AI", [("chat", "Chat", ":material/forum:")]),
]


def _status_rows() -> list:
    ss = st.session_state
    keys = ("MISTRAL_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY")
    key_found = any(os.getenv(k) for k in keys)
    busy = ss.processing
    err = ss.error is not None
    backend = ("Import failed", "error") if BACKEND_ERROR else (("Working", "warning") if busy else ("Connected", "success"))
    if BACKEND_ERROR or err and ss.stage_states.get("transcription") == "error":
        whisper = ("Error", "error")
    elif busy:
        whisper = ("Processing", "warning")
    elif ss.analysis_complete:
        whisper = ("Ready", "success")
    else:
        whisper = ("Idle", "idle")
    if not key_found:
        ai = ("No API key", "error")
    elif busy:
        ai = ("Processing", "warning")
    else:
        ai = ("Configured", "success")
    if busy:
        rag = ("Processing", "warning")
    elif ss.rag_chain is not None:
        rag = ("Ready", "success")
    else:
        rag = ("Idle", "idle")
    return [("Backend", *backend), ("Whisper", *whisper), ("AI Engine", *ai), ("RAG", *rag)]


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="brand"><div class="brand-mark">{LOGO_SVG}</div>'
            '<div class="brand-name">AI VIDEO<br><span>INTELLIGENCE</span></div></div>',
            unsafe_allow_html=True,
        )
        for label, entries in NAV_GROUPS:
            if label:
                st.markdown(f'<div class="nav-label">{label}</div>', unsafe_allow_html=True)
            for page, text, icon in entries:
                st.button(text, key=f"nav_{page}", icon=icon, on_click=go, args=(page,), use_container_width=True)
        rows = "".join(
            f'<div class="status-row"><span class="dot {cls}"></span>{name}<span class="st-val">{val}</span></div>'
            for name, val, cls in _status_rows()
        )
        st.markdown(f'<div class="status-box"><div class="status-title">System status</div>{rows}</div>', unsafe_allow_html=True)


# ==========================================================================
# Shared UI pieces
# ==========================================================================
def render_header(title: str, subtitle: str = "", hero: bool = False) -> None:
    if hero:
        st.markdown(
            f'<div class="hero"><div class="hero-title">{esc(title)}</div><div class="hero-sub">{esc(subtitle)}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        sub = f'<div class="page-sub">{esc(subtitle)}</div>' if subtitle else ""
        st.markdown(f'<div class="page-head"><div class="page-title">{esc(title)}</div>{sub}</div>', unsafe_allow_html=True)


def render_empty_state(title: str, text: str, action: str = None, target: str = None, key: str = "empty") -> None:
    icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="1.7"><rect x="3.5" y="5" width="17" height="14" rx="3"/><path d="M10 9.5v5l4.2-2.5L10 9.5Z"/></svg>'
    st.markdown(
        f'<div class="empty"><div class="empty-icon">{icon}</div><div class="empty-title">{esc(title)}</div>'
        f'<div class="empty-text">{esc(text)}</div></div>',
        unsafe_allow_html=True,
    )
    if action and target:
        _, mid, _ = st.columns([2, 1.4, 2])
        mid.button(action, key=key, on_click=go, args=(target,), use_container_width=True, type="primary")


def render_error() -> None:
    err = st.session_state.error
    if not err:
        return
    st.markdown(
        f'<div class="err"><div><div class="err-title">{esc(err["title"])}</div>'
        f'<div class="err-text">{esc(err["message"])}</div></div></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Technical details"):
        st.code(err.get("details") or "No further details.", language=None)
    st.button("Dismiss", key="dismiss_err", on_click=lambda: st.session_state.update(error=None))


def _store_error(exc: Exception) -> None:
    title, message = classify_error(exc)
    st.session_state.error = {"title": title, "message": message, "details": scrub(traceback.format_exc())}


# ==========================================================================
# Overview + Analyze input
# ==========================================================================
def _start_job(source: str, label: str, language: str, cleanup=None) -> None:
    st.session_state.job = {"source": source, "label": label, "language": language, "cleanup": cleanup}
    st.session_state.processing = True
    st.session_state.error = None
    st.session_state.stage_states = {}
    st.session_state.page = "analyze"
    st.rerun()


def render_analyze() -> None:
    """The analysis input card."""
    if BACKEND_ERROR:
        st.session_state.error = {
            "title": "Backend not available",
            "message": "The analysis modules could not be imported. Check your project structure and installed packages.",
            "details": scrub("".join(traceback.format_exception(BACKEND_ERROR))),
        }
        render_error()
        return
    with st.container(key="analyze_card"):
        options = ["YouTube URL", "Upload file"]
        if hasattr(st, "segmented_control"):
            mode = st.segmented_control("Source", options, default=options[0], key="mode", label_visibility="collapsed")
        else:
            mode = st.radio("Source", options, horizontal=True, key="mode", label_visibility="collapsed")
        mode = mode or options[0]

        url, upload = "", None
        if mode == options[0]:
            url = st.text_input("YouTube URL", placeholder="Paste a YouTube URL", key="url_input", label_visibility="collapsed")
        else:
            upload = st.file_uploader(
                "Media file", key="file_input", label_visibility="collapsed",
                type=["mp4", "mkv", "mov", "avi", "webm", "mp3", "wav", "m4a", "flac", "ogg", "aac"],
                help="Drag and drop a video or audio file.",
            )

        c1, c2 = st.columns([1, 2.2], vertical_alignment="bottom")
        lang = c1.selectbox("Language", ["English", "Hinglish"], key="lang_input")
        go_click = c2.button("✦ Analyze Video", type="primary", use_container_width=True, key="analyze_btn")
        st.caption("Powered by local Whisper + AI analysis + RAG")

        if go_click:
            if mode == options[0]:
                if not url.strip():
                    st.warning("Paste a YouTube URL to continue.")
                elif not url.strip().lower().startswith(("http://", "https://")):
                    st.warning("That doesn't look like a valid URL. It should start with https://")
                else:
                    _start_job(url.strip(), url.strip(), lang.lower())
            else:
                if upload is None:
                    st.warning("Choose a media file to continue.")
                else:
                    tmp = tempfile.mkdtemp(prefix="vidassist_")
                    path = os.path.join(tmp, os.path.basename(upload.name))
                    with open(path, "wb") as fh:
                        fh.write(upload.getvalue())
                    _start_job(path, upload.name, lang.lower(), cleanup=tmp)


def render_overview() -> None:
    render_header(
        "Turn videos into actionable intelligence.",
        "Transcribe, understand and chat with your meetings, lectures and research videos.",
        hero=True,
    )
    if not st.session_state.processing:
        render_error()
    render_analyze()
    st.markdown('<div class="kicker" style="margin-top:1.8rem">Recent analyses</div>', unsafe_allow_html=True)
    hist = st.session_state.history
    if not hist:
        render_empty_state("Your intelligence workspace is empty.", "Analyze a video to get started.")
        return
    for entry in reversed(hist[-5:]):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(
            f'<div class="card"><div class="card-title">{esc(entry["title"])}</div>'
            f'<div class="card-meta">{esc(short_source(entry["source"]))} · {esc(entry["language"].title())} · '
            f'{fmt_int(entry["words"])} words · {esc(entry["time"])}</div></div>',
            unsafe_allow_html=True,
        )
        c2.button("Open", key=f"open_{entry['id']}", on_click=open_history, args=(entry["id"],), use_container_width=True)


# ==========================================================================
# Processing (real backend stages, never faked)
# ==========================================================================
STAGES = [
    ("source", "Source", "Resolving the input"),
    ("audio", "Audio", "Extracting and chunking audio"),
    ("transcription", "Transcription", "Whisper speech-to-text"),
    ("analysis", "AI analysis", "Title and executive summary"),
    ("extraction", "Extraction", "Actions, decisions and questions"),
    ("knowledge", "Knowledge", "Building the RAG index"),
]
_STATE_TEXT = {"pending": ("Waiting", "idle"), "active": ("In progress", "warning"), "done": ("Done", "success"), "error": ("Failed", "error")}


def _stage_html(states: dict, times: dict) -> str:
    out = []
    for i, (key, name, desc) in enumerate(STAGES, 1):
        state = states.get(key, "pending")
        label, cls = _STATE_TEXT[state]
        extra = f" · {times[key]:.1f}s" if state == "done" and key in times else ""
        out.append(
            f'<div class="stage {state}"><span class="s-idx">{i:02d}</span>'
            f'<div><div class="s-name">{name}</div><div class="s-desc">{desc}</div></div>'
            f'<span class="s-state"><span class="dot {cls}"></span>{label}{extra}</span></div>'
        )
    return "".join(out)


def render_processing() -> None:
    job = st.session_state.job
    render_header("Analyzing your video", short_source(job["label"]))
    states, times = {}, {}
    result = {}

    with st.status("Starting analysis…", expanded=True) as status:
        bar = st.progress(0.0)
        tracker = st.empty()

        def paint():
            tracker.markdown(_stage_html(states, times), unsafe_allow_html=True)
            bar.progress(sum(1 for s in states.values() if s == "done") / len(STAGES))
            st.session_state.stage_states = dict(states)

        def step(keys, label, fn):
            for k in keys:
                states[k] = "active"
            status.update(label=label)
            paint()
            t0 = time.perf_counter()
            try:
                out = fn()
            except Exception:
                for k in keys:
                    states[k] = "error"
                paint()
                raise
            dt = time.perf_counter() - t0
            for k in keys:
                states[k] = "done"
                times[k] = dt
            paint()
            return out

        try:
            paint()
            chunks = step(("source", "audio"), "Preparing audio…", lambda: process_input(job["source"]))
            transcript = as_text(step(("transcription",), "Transcribing with Whisper…", lambda: transcribe_all(chunks, job["language"])))
            if not transcript.strip():
                states["transcription"] = "error"
                raise ValueError("No speech detected: empty transcript")

            def analysis():
                return generate_title(transcript), summarize(transcript)

            title, summary = step(("analysis",), "Generating title and summary…", analysis)

            def extraction():
                return extract_action_items(transcript), extract_key_decisions(transcript), extract_questions(transcript)

            actions, decisions, questions = step(("extraction",), "Extracting insights…", extraction)
            rag_chain = step(("knowledge",), "Building knowledge index…", lambda: build_rag_chain(transcript))

            result = {
                "title": title, "transcript": transcript, "summary": summary,
                "action_items": actions, "key_decisions": decisions,
                "open_questions": questions, "rag_chain": rag_chain,
            }
            status.update(label="Analysis complete", state="complete", expanded=False)
        except Exception as exc:  # noqa: BLE001
            _store_error(exc)
            status.update(label="Analysis failed", state="error", expanded=True)
            result = {}
        finally:
            if job.get("cleanup"):
                shutil.rmtree(job["cleanup"], ignore_errors=True)

    st.session_state.processing = False
    st.session_state.job = None
    if result:
        _stash_chat()
        load_result(result, job["label"], job["language"])
        entry_id = uuid.uuid4().hex[:8]
        st.session_state.current_id = entry_id
        st.session_state.history.append({
            "id": entry_id, "title": st.session_state.title, "source": job["label"],
            "language": job["language"], "words": len(st.session_state.transcript.split()),
            "time": datetime.now().strftime("%d %b, %H:%M"), "result": result, "chat": [],
        })
    st.rerun()


# ==========================================================================
# Dashboard: header, metrics, summary
# ==========================================================================
def _report_markdown() -> str:
    ss = st.session_state

    def section(name, items):
        body = "\n".join(f"- {i['text']}" + (" (" + ", ".join(f"{k}: {v}" for k, v in i["meta"]) + ")" if i["meta"] else "") for i in items)
        return f"## {name}\n\n{body or '_None found._'}\n"

    return "\n".join([
        f"# {ss.title}", "",
        f"- Source: {ss.source}", f"- Language: {ss.language.title()}",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
        "## Executive summary", "", ss.summary or "_No summary._", "",
        section("Action items", ss.action_items), section("Key decisions", ss.key_decisions),
        section("Open questions", ss.open_questions),
        "## Transcript", "", ss.transcript,
    ])


def render_export() -> None:
    ss = st.session_state
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", ss.title).strip("_")[:60] or "analysis"
    with st.popover("Export", use_container_width=True, icon=":material/download:"):
        st.download_button("Download transcript", ss.transcript, file_name=f"{safe}_transcript.txt", mime="text/plain", use_container_width=True, key="dl_t")
        st.download_button("Download summary", f"# {ss.title}\n\n{ss.summary}\n", file_name=f"{safe}_summary.md", mime="text/markdown", use_container_width=True, key="dl_s")
        st.download_button("Download full report", _report_markdown(), file_name=f"{safe}_report.md", mime="text/markdown", use_container_width=True, key="dl_r")


def render_dashboard() -> None:
    ss = st.session_state
    words = len(ss.transcript.split())
    left, right = st.columns([4, 1.2], vertical_alignment="top")
    with left:
        st.markdown(f'<div class="page-title" style="font-size:1.7rem">{esc(ss.title)}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="badges"><span class="badge">Language · {esc(ss.language.title())}</span>'
            f'<span class="badge">Source · {esc(short_source(ss.source))}</span>'
            f'<span class="badge"><span class="dot success"></span>Analysis complete</span></div>',
            unsafe_allow_html=True,
        )
    with right:
        render_export()
        st.button("New analysis", key="new_analysis", on_click=reset_for_new, use_container_width=True)

    metrics = [
        ("TRANSCRIPT", fmt_int(len(ss.transcript)), "characters", "var(--cyan)"),
        ("WORDS", fmt_int(words), "in transcript", "var(--info)"),
        ("ACTION ITEMS", fmt_int(len(ss.action_items)), "extracted", "var(--success)"),
        ("DECISIONS", fmt_int(len(ss.key_decisions)), "extracted", "var(--primary)"),
    ]
    cells = "".join(
        f'<div class="metric"><div class="m-top"><span class="m-dot" style="background:{c}"></span>'
        f'<span class="m-label">{label}</span></div><div class="m-value">{value}</div><div class="m-sub">{sub}</div></div>'
        for label, value, sub, c in metrics
    )
    st.markdown(f'<div class="metrics">{cells}</div>', unsafe_allow_html=True)


def render_summary() -> None:
    ss = st.session_state
    with st.container(key="summary_card"):
        top, b1, b2 = st.columns([5, 1, 1.4], vertical_alignment="center")
        top.markdown(
            '<div class="panel-head"><span class="dot" style="background:var(--primary)"></span>Executive summary</div>',
            unsafe_allow_html=True,
        )
        with b1:
            copy_button(ss.summary, "Copy", key="copy_summary")
        if ss.summary_expanded:
            b2.button("Collapse", key="collapse_sum", on_click=lambda: st.session_state.update(summary_expanded=False), use_container_width=True)
        else:
            b2.button("Expand", key="expand_sum", on_click=lambda: st.session_state.update(summary_expanded=True), use_container_width=True)
        with st.container(key="summary_body"):
            st.markdown(ss.summary or "_No summary was returned._")


# ==========================================================================
# Insights
# ==========================================================================
def _items_html(items: list, kind: str) -> str:
    out = []
    for i, it in enumerate(items, 1):
        mark = {"task": "✓", "decision": "◆", "question": str(i)}[kind]
        chips = "".join(f'<span class="chip">{esc(k.replace("_", " ").title())}: {esc(v)}</span>' for k, v in it["meta"])
        chips = f'<div class="chips">{chips}</div>' if chips else ""
        out.append(
            f'<div class="item {kind}"><span class="item-mark">{mark}</span>'
            f'<div><div class="item-body">{md_inline(it["text"])}</div>{chips}</div></div>'
        )
    return "".join(out)


def _insight_section(items: list, kind: str, empty_text: str) -> None:
    if items:
        st.markdown(_items_html(items, kind), unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="empty" style="padding:1.6rem"><div class="empty-text">{esc(empty_text)}</div></div>', unsafe_allow_html=True)


def render_insights(section: str = None) -> None:
    ss = st.session_state
    acts, decs, qs = ss.action_items, ss.key_decisions, ss.open_questions
    none_a, none_d, none_q = "No action items were found in this video.", "No key decisions were found in this video.", "No open questions were found in this video."
    if section == "actions":
        _insight_section(acts, "task", none_a)
    elif section == "decisions":
        _insight_section(decs, "decision", none_d)
    elif section == "questions":
        _insight_section(qs, "question", none_q)
    else:
        tab_o, tab_a, tab_d, tab_q = st.tabs(["Overview", f"Action items ({len(acts)})", f"Decisions ({len(decs)})", f"Questions ({len(qs)})"])
        with tab_o:
            cols = st.columns(3)
            panels = [
                ("Action items", "var(--success)", acts, "task", none_a),
                ("Key decisions", "var(--primary)", decs, "decision", none_d),
                ("Open questions", "var(--warning)", qs, "question", none_q),
            ]
            for col, (name, color, items, kind, empty) in zip(cols, panels):
                with col:
                    st.markdown(
                        f'<div class="panel-head"><span class="dot" style="background:{color}"></span>{name}'
                        f'<span class="count">{len(items)}</span></div>',
                        unsafe_allow_html=True,
                    )
                    if items:
                        st.markdown(_items_html(items[:3], kind), unsafe_allow_html=True)
                        if len(items) > 3:
                            st.caption(f"+ {len(items) - 3} more in the {name.split()[-1].lower()} tab")
                    else:
                        st.caption(empty)
        with tab_a:
            _insight_section(acts, "task", none_a)
        with tab_d:
            _insight_section(decs, "decision", none_d)
        with tab_q:
            _insight_section(qs, "question", none_q)


# ==========================================================================
# Transcript
# ==========================================================================
_TS_RE = re.compile(
    r"^\s*[\[\(]?((?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d+)?(?:\s*[-–]+>?\s*(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d+)?)?)[\]\)]?\s*[:\-–]?\s*"
)


def _blocks(text: str) -> list:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 3:
        return lines
    sentences = re.split(r"(?<=[.!?।])\s+", text.strip())
    return [" ".join(sentences[i:i + 4]) for i in range(0, len(sentences), 4)] or lines


def render_transcript() -> None:
    ss = st.session_state
    text = ss.transcript
    if not ss.analysis_complete or not text.strip():
        render_empty_state("No transcript yet.", "Analyze a video to see its transcript here.", "Go to overview", "overview", key="t_empty")
        return
    blocks = _blocks(text)
    has_ts = any(_TS_RE.match(b) for b in blocks)
    words = len(text.split())
    with st.container(key="transcript_card"):
        stats = [
            (fmt_int(words), "words"), (fmt_int(len(text)), "characters"), (fmt_int(len(blocks)), "segments"),
            (f"{max(1, round(words / 200))} min", "est. read time"), ("Yes" if has_ts else "No", "timestamps in source"),
        ]
        st.markdown(
            '<div class="tstats">' + "".join(f'<div class="tstat"><b>{v}</b><span>{k}</span></div>' for v, k in stats) + "</div>",
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4 = st.columns([4, 1, 1, 1.4], vertical_alignment="bottom")
        query = c1.text_input("Search transcript", placeholder="Search transcript", key="t_query", label_visibility="collapsed").strip()
        with c2:
            copy_button(text, "Copy", key="copy_t")
        c3.download_button("Download", text, file_name="transcript.txt", mime="text/plain", use_container_width=True, key="dl_t2")
        full = c4.toggle("Show full", key="t_full", value=False)

        if query:
            shown = [b for b in blocks if query.lower() in b.lower()][:200]
            st.caption(f"{len(shown)} matching segment{'s' if len(shown) != 1 else ''}")
            clipped = False
        else:
            limit = 30
            shown = blocks if full else blocks[:limit]
            clipped = full is False and len(blocks) > limit
            if clipped:
                st.caption(f"Showing the first {limit} of {len(blocks)} segments. Turn on “Show full” to read everything.")
        pattern = re.compile(re.escape(esc(query)), re.I) if query else None
        lines = []
        for b in shown:
            m = _TS_RE.match(b)
            ts, body = (m.group(1).strip(), b[m.end():]) if m else ("", b)
            body_html = esc(body)
            if pattern:
                body_html = pattern.sub(lambda mm: f"<mark>{mm.group(0)}</mark>", body_html)
            ts_html = f'<span class="t-ts">{esc(ts)}</span>' if ts else ""
            lines.append(f'<div class="t-line">{ts_html}{body_html}</div>')
        if not lines:
            lines = ['<div class="t-line">No matches found.</div>']
        st.markdown(f'<div class="t-body {"clipped" if clipped or (not full and not query) else ""}">{"".join(lines)}</div>', unsafe_allow_html=True)


# ==========================================================================
# Chat
# ==========================================================================
SUGGESTIONS = [
    "What are the main ideas?",
    "What decisions were made?",
    "What actions should I follow up on?",
    "What questions remain unanswered?",
]


def _ask(question: str) -> None:
    st.session_state.pending_q = question


def render_chat() -> None:
    ss = st.session_state
    render_header("Chat with your video", "Ask anything about the analyzed content.")
    ready = ss.analysis_complete and ss.rag_chain is not None
    if not ready:
        render_empty_state("Your AI conversation will appear here after analysis.", "Analyze a video to start chatting.", "Go to overview", "overview", key="c_empty")
        st.chat_input("Analyze a video to start chatting", disabled=True)
        return

    if not ss.chat_history:
        st.markdown('<div class="kicker">Suggested prompts</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, prompt in enumerate(SUGGESTIONS):
            cols[i % 2].button(prompt, key=f"sug_{i}", on_click=_ask, args=(prompt,), use_container_width=True)

    for msg in ss.chat_history:
        with st.chat_message(msg["role"], avatar=":material/auto_awesome:" if msg["role"] == "assistant" else ":material/person:"):
            st.markdown(msg["content"])

    typed = st.chat_input("Ask about this video…")  # always rendered so it never flickers away
    question = ss.pop("pending_q", None) or typed
    if question:
        ss.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(question)
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            try:
                with st.spinner("Thinking…"):
                    answer = as_text(ask_question(ss.rag_chain, question)).strip() or "I couldn't find an answer in the transcript."
                st.markdown(answer)
                ss.chat_history.append({"role": "assistant", "content": answer})
            except Exception as exc:  # noqa: BLE001
                _store_error(exc)
                render_error()
                ss.chat_history.pop()  # drop the unanswered question so it can be retried
    if ss.chat_history:
        st.button("Clear conversation", key="clear_chat", on_click=lambda: st.session_state.update(chat_history=[]))


# ==========================================================================
# Page router
# ==========================================================================
def render_analyze_page() -> None:
    ss = st.session_state
    if ss.processing and ss.job:
        render_processing()
        return
    if ss.analysis_complete:
        render_dashboard()
        render_summary()
        st.markdown('<div class="kicker" style="margin-top:1.6rem">AI insights</div>', unsafe_allow_html=True)
        render_insights()
        return
    render_header("Analyze a video", "Paste a YouTube URL or upload a recording to start.")
    render_error()
    render_analyze()


def _needs_result(title: str, subtitle: str, key: str) -> bool:
    render_header(title, subtitle)
    if st.session_state.analysis_complete:
        return False
    render_empty_state("Your intelligence workspace is empty.", "Analyze a video to get started.", "Go to overview", "overview", key=key)
    return True


def main() -> None:
    init_session_state()
    inject_css()
    render_sidebar()
    page = st.session_state.page

    if st.session_state.processing and st.session_state.job and page != "analyze":
        st.session_state.page = page = "analyze"

    if page == "overview":
        render_overview()
    elif page == "analyze":
        render_analyze_page()
    elif page == "transcript":
        render_header("Transcript", "Search, copy and download the full text.")
        render_transcript()
    elif page == "insights":
        if not _needs_result("AI insights", "Action items, decisions and open questions from the video.", "i_empty"):
            render_insights()
    elif page == "actions":
        if not _needs_result("Action items", "Follow-ups extracted from the video.", "a_empty"):
            render_insights("actions")
    elif page == "decisions":
        if not _needs_result("Decisions", "Key decisions extracted from the video.", "d_empty"):
            render_insights("decisions")
    elif page == "questions":
        if not _needs_result("Questions", "Questions left open in the video.", "q_empty"):
            render_insights("questions")
    elif page == "chat":
        render_chat()


main()