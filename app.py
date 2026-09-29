# ============================================================
# ⚡ ULTRA SUPER SONIC — v3.0
# ============================================================

import os
import io
import time
import json
import base64
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st
from google import genai


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "Ultra Super Sonic"
APP_VERSION = "3.0"
MODEL = "gemini-3.8-flash"
EMBEDDING_MODEL = "models/gemini-embedding-2"

MAX_FILE_SIZE_MB = 50
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGES_PER_MESSAGE = 5

SUPPORTED_FILES = [
    "pdf", "docx", "pptx", "txt", "md",
    "csv", "json", "png", "jpg", "jpeg", "webp",
]
IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "gif"]

MIME_MAP = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "gif": "image/gif",
    "pdf": "application/pdf",
}

# ---- Sonic themes ----
THEMES = {
    "💚 Green Hill": {
        "accent": "#00d97e", "glow": "#7dffb0",
        "grad1": "rgba(0,217,126,0.18)", "grad2": "rgba(0,255,180,0.06)",
    },
    "💙 Chemical Plant": {
        "accent": "#00a8ff", "glow": "#7dd3ff",
        "grad1": "rgba(0,168,255,0.18)", "grad2": "rgba(120,0,255,0.08)",
    },
    "💛 Star Light": {
        "accent": "#ffcc00", "glow": "#ffe680",
        "grad1": "rgba(255,204,0,0.20)", "grad2": "rgba(255,100,0,0.06)",
    },
    "❤️ Death Egg": {
        "accent": "#ff3355", "glow": "#ff8095",
        "grad1": "rgba(255,51,85,0.20)", "grad2": "rgba(60,0,20,0.10)",
    },
}


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "messages": [],
    "chat_interaction_id": None,
    "file_interaction_id": None,
    "photo_interaction_id": None,
    "web_interaction_id": None,
    "file_store_name": None,
    "processed_files": {},
    "photo_history": [],
    "web_history": [],
    "theme": "💙 Chemical Plant",
    "speed": "Super",
    "rings": 0,
    "tokens": 0,
    "session_start": datetime.now().isoformat(),
}

for k, v in DEFAULT_STATE.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ============================================================
# DYNAMIC THEME CSS
# ============================================================

def render_css():
    t = THEMES[st.session_state.theme]
    st.markdown(
        f"""
<style>
#MainMenu, footer, header {{ visibility: hidden; }}

.block-container {{
    max-width: 1250px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}}

/* ---- Hero ---- */
.hero {{
    padding: 32px;
    border-radius: 28px;
    margin-bottom: 22px;
    border: 1px solid {t['accent']}44;
    background: linear-gradient(135deg, {t['grad1']}, {t['grad2']});
    position: relative;
    overflow: hidden;
}}
.hero::before {{
    content: "";
    position: absolute;
    top: -50%; right: -20%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, {t['glow']}55, transparent 70%);
    animation: pulse 4s ease-in-out infinite;
}}
@keyframes pulse {{
    0%,100% {{ transform: scale(1); opacity: .6; }}
    50%     {{ transform: scale(1.15); opacity: .3; }}
}}
.hero-title {{
    font-size: 42px; font-weight: 900; line-height: 1.05;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, {t['accent']}, {t['glow']});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    position: relative; z-index: 1;
}}
.hero-subtitle {{
    margin-top: 10px; font-size: 15px; opacity: 0.75;
    position: relative; z-index: 1;
}}
.hero-rings {{
    position: absolute; top: 20px; right: 30px;
    font-size: 26px; letter-spacing: 4px; opacity: .35;
    animation: spin 8s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}

/* ---- HUD ---- */
.hud {{
    display: flex; gap: 12px; flex-wrap: wrap;
    margin-bottom: 16px;
}}
.hud-card {{
    flex: 1; min-width: 130px;
    padding: 12px 16px;
    border-radius: 14px;
    border: 1px solid {t['accent']}33;
    background: {t['grad2']};
}}
.hud-label {{
    font-size: 11px; text-transform: uppercase;
    letter-spacing: 1px; opacity: .6;
}}
.hud-value {{
    font-size: 22px; font-weight: 800;
    color: {t['accent']};
    margin-top: 2px;
}}

/* ---- Cards ---- */
.card {{
    padding: 18px; border-radius: 18px;
    border: 1px solid {t['accent']}33;
    margin-bottom: 12px; background: {t['grad2']};
}}
.file-card {{
    padding: 14px; border-radius: 15px;
    border: 1px solid {t['accent']}22;
    margin-bottom: 8px;
}}

/* ---- Badges ---- */
.badge {{
    display: inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: 11px;
    font-weight: 700; letter-spacing: .5px;
}}
.badge-ready {{ background: {t['accent']}25; color: {t['accent']}; }}
.badge-error {{ background: #ff335530; color: #ff5570; }}
.badge-scan  {{ background: #ffcc0030; color: #ffcc00; }}

.attachment-pill {{
    display: inline-block; padding: 4px 10px;
    margin: 2px 4px 2px 0; border-radius: 12px;
    background: {t['accent']}22; font-size: 12px;
}}

.stButton > button {{
    border-radius: 12px;
    transition: transform .12s ease;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    border-color: {t['accent']};
}}
.stChatInput {{ border-radius: 16px; }}
.msg-meta {{ font-size: 11px; opacity: .55; margin-top: 6px; }}

.speed-pill {{
    display: inline-block; padding: 5px 14px;
    border-radius: 20px; font-weight: 800;
    font-size: 12px; letter-spacing: 1px;
    background: {t['accent']}22;
    color: {t['accent']};
    border: 1px solid {t['accent']}55;
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    try:
        key = st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        key = None
    if not key:
        key = os.getenv("GOOGLE_API_KEY")
    return key


API_KEY = get_api_key()
if not API_KEY:
    st.error(
        """
        ❌ Google API key not found.
        Add `GOOGLE_API_KEY = "YOUR_API_KEY"` to Streamlit Secrets.
        """
    )
    st.stop()


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_client(api_key):
    return genai.Client(api_key=api_key)


client = get_client(API_KEY)


# ============================================================
# UTILITIES
# ============================================================

def file_hash(uploaded_file):
    return hashlib.sha256(uploaded_file.getvalue()).hexdigest()


def safe_filename(name):
    return Path(name).name


def human_size(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def format_error(e):
    return f"❌ **Something went wrong**\n\n`{e}`"


def guess_mime(name):
    return MIME_MAP.get(Path(name).suffix.lower().lstrip("."), "application/octet-stream")


def is_image(name):
    return Path(name).suffix.lower().lstrip(".") in IMAGE_TYPES


def bump_rings(n=1):
    st.session_state.rings += n


def bump_tokens(text: str):
    # rough estimate
    st.session_state.tokens += len(text) // 4


# ============================================================
# FILE SEARCH STORE
# ============================================================

def create_file_store():
    store = client.file_search_stores.create(
        config={
            "display_name": "super-sonic-vault",
            "embedding_model": EMBEDDING_MODEL,
        }
    )
    return store.name


def get_file_store():
    if st.session_state.file_store_name:
        return st.session_state.file_store_name
    st.session_state.file_store_name = create_file_store()
    return st.session_state.file_store_name


def process_file(uploaded_file) -> str:
    name = safe_filename(uploaded_file.name)
    if uploaded_file.size / (1024 * 1024) > MAX_FILE_SIZE_MB:
        raise ValueError(f"{name} exceeds {MAX_FILE_SIZE_MB} MB.")

    store = get_file_store()
    suffix = Path(name).suffix
    tmp = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(uploaded_file.getbuffer())
            tmp = f.name

        op = client.file_search_stores.upload_to_file_search_store(
            file=tmp,
            file_search_store_name=store,
            config={"display_name": name},
        )
        while not op.done:
            time.sleep(2)
            op = client.operations.get(op)

        if getattr(op, "error", None):
            raise RuntimeError(str(op.error))

        doc_name = ""
        try:
            meta = getattr(op, "metadata", None)
            if meta and getattr(meta, "document", None):
                doc_name = getattr(meta.document, "name", "")
        except Exception:
            pass
        return doc_name

    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def delete_document(doc_name):
    client.file_search_stores.documents.delete(
        name=doc_name, config={"force": True}
    )


def delete_all_files():
    store = st.session_state.file_store_name
    if store:
        try:
            client.file_search_stores.delete(
                name=store, config={"force": True}
            )
        except Exception:
            pass
    st.session_state.file_store_name = None
    st.session_state.processed_files = {}
    st.session_state.file_interaction_id = None


def delete_single_file(fid):
    data = st.session_state.processed_files.get(fid)
    if data and data.get("document_name"):
        try:
            delete_document(data["document_name"])
        except Exception:
            pass
    st.session_state.processed_files.pop(fid, None)


# ============================================================
# GEMINI CALLS
# ============================================================

def build_multimodal_input(question, attachments):
    parts = []
    if question:
        parts.append({"type": "text", "text": question})
    for a in attachments:
        parts.append({
            "type": "image",
            "data": base64.b64encode(a["bytes"]).decode("utf-8"),
            "mime_type": a["mime"],
        })
    return parts if parts else question


def ask_chat(question, attachments=None):
    attachments = attachments or []
    payload = build_multimodal_input(question, attachments)

    kwargs = {"model": MODEL, "input": payload}
    if st.session_state.chat_interaction_id:
        kwargs["previous_interaction_id"] = st.session_state.chat_interaction_id

    interaction = client.interactions.create(**kwargs)
    st.session_state.chat_interaction_id = interaction.id
    answer = interaction.output_text
    bump_tokens(answer)
    return answer


def ask_file(question):
    store = st.session_state.file_store_name
    if not store:
        raise ValueError("Upload and process a file first.")

    kwargs = {
        "model": MODEL,
        "input": question,
        "tools": [{
            "type": "file_search",
            "file_search_store_names": [store],
        }],
    }
    if st.session_state.file_interaction_id:
        kwargs["previous_interaction_id"] = st.session_state.file_interaction_id

    interaction = client.interactions.create(**kwargs)
    st.session_state.file_interaction_id = interaction.id
    answer = interaction.output_text
    bump_tokens(answer)
    return answer, interaction


def ask_web(question):
    kwargs = {
        "model": MODEL,
        "input": question,
        "tools": [{"type": "google_search"}],
    }
    if st.session_state.web_interaction_id:
        kwargs["previous_interaction_id"] = st.session_state.web_interaction_id

    interaction = client.interactions.create(**kwargs)
    st.session_state.web_interaction_id = interaction.id
    answer = interaction.output_text
    bump_tokens(answer)
    return answer, interaction


def analyze_photos(images, question):
    parts = [{"type": "text", "text": question}]
    for img in images:
        parts.append({
            "type": "image",
            "data": base64.b64encode(img["bytes"]).decode("utf-8"),
            "mime_type": img["mime"],
        })

    kwargs = {"model": MODEL, "input": parts}
    if st.session_state.photo_interaction_id:
        kwargs["previous_interaction_id"] = st.session_state.photo_interaction_id

    interaction = client.interactions.create(**kwargs)
    st.session_state.photo_interaction_id = interaction.id
    answer = interaction.output_text
    bump_tokens(answer)
    return answer


# ============================================================
# CITATIONS
# ============================================================

def get_file_citations(interaction):
    out = []
    try:
        for step in interaction.steps:
            if step.type != "model_output":
                continue
            for content in step.content:
                anns = getattr(content, "annotations", None) or []
                for a in anns:
                    if getattr(a, "type", None) == "file_citation":
                        out.append({
                            "page": getattr(a, "page_number", None),
                            "title": getattr(a, "title", None),
                        })
    except Exception:
        pass
    return out


def get_web_citations(interaction):
    out = []
    try:
        for step in interaction.steps:
            if step.type != "model_output":
                continue
            for content in step.content:
                anns = getattr(content, "annotations", None) or []
                for a in anns:
                    if getattr(a, "type", None) == "url_citation":
                        out.append({
                            "title": getattr(a, "title", None) or "Source",
                            "url": getattr(a, "url", None),
                        })
    except Exception:
        pass
    return out


# ============================================================
# EXPORT
# ============================================================

def export_messages_markdown():
    lines = [
        f"# {APP_NAME} — Chat Export",
        f"_Exported: {datetime.now():%Y-%m-%d %H:%M}_",
        "",
        "---",
        "",
    ]
    for m in st.session_state.messages:
        role = "🧑 **You**" if m["role"] == "user" else "⚡ **Sonic**"
        lines.append(f"### {role}")
        lines.append("")
        lines.append(m["content"])
        lines.append("")
        if m.get("attachments"):
            atts = ", ".join(a["name"] for a in m["attachments"])
            lines.append(f"*Attachments: {atts}*")
            lines.append("")
    return "\n".join(lines)


# ============================================================
# RENDER CSS + HERO
# ============================================================

render_css()

st.markdown(
    f"""
<div class="hero">
  <div class="hero-rings">💍 💍 💍</div>
  <div class="hero-title">⚡ {APP_NAME}</div>
  <div class="hero-subtitle">
    Gotta go fast — AI Chat • Files • Photos • Web • Voice
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("⚡ Sonic Control")
    st.caption(f"Gemini 3.8 Flash · v{APP_VERSION}")
    st.divider()

    # ---- Speed ----
    st.markdown("**🏃 Speed**")
    st.session_state.speed = st.radio(
        "Speed",
        ["Sonic", "Super", "Hyper"],
        index=["Sonic", "Super", "Hyper"].index(st.session_state.speed),
        label_visibility="collapsed",
        horizontal=True,
    )
    st.markdown(
        f'<div class="speed-pill">⚡ {st.session_state.speed.upper()} MODE</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ---- Theme ----
    st.markdown("**🎨 Zone**")
    st.session_state.theme = st.selectbox(
        "Theme",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme),
        label_visibility="collapsed",
    )

    st.divider()

    # ---- Mode ----
    st.markdown("**🎯 Mission**")
    mode = st.radio(
        "Mode",
        [
            "🤖 AI Chat",
            "📚 File Vault",
            "📷 Photo Scanner",
            "🌐 Web Radar",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # ---- HUD stats ----
    ready_count = len([
        f for f in st.session_state.processed_files.values()
        if f.get("status") == "ready"
    ])
    st.caption(f"💍 Rings: **{st.session_state.rings}**")
    st.caption(f"📚 Files: **{ready_count}**")
    st.caption(f"💬 Msgs: **{len(st.session_state.messages)}**")
    st.caption(f"🔢 Tokens ~**{st.session_state.tokens}**")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Reset", use_container_width=True):
            for k in ["messages", "chat_interaction_id",
                      "file_interaction_id", "photo_interaction_id",
                      "web_interaction_id"]:
                st.session_state[k] = [] if k == "messages" else None
            st.session_state.rings = 0
            st.session_state.tokens = 0
            st.rerun()
    with c2:
        if st.session_state.messages:
            st.download_button(
                "💾 Save",
                data=export_messages_markdown(),
                file_name=f"sonic_{datetime.now():%Y%m%d_%H%M}.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ============================================================
# HUD BAR
# ============================================================

st.markdown(
    f"""
<div class="hud">
  <div class="hud-card">
    <div class="hud-label">Rings</div>
    <div class="hud-value">💍 {st.session_state.rings}</div>
  </div>
  <div class="hud-card">
    <div class="hud-label">Files</div>
    <div class="hud-value">📚 {ready_count}</div>
  </div>
  <div class="hud-card">
    <div class="hud-label">Messages</div>
    <div class="hud-value">💬 {len(st.session_state.messages)}</div>
  </div>
  <div class="hud-card">
    <div class="hud-label">Tokens</div>
    <div class="hud-value">🔢 {st.session_state.tokens}</div>
  </div>
  <div class="hud-card">
    <div class="hud-label">Zone</div>
    <div class="hud-value">{st.session_state.theme.split()[0]}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# MODE: AI CHAT
# ============================================================

if mode == "🤖 AI Chat":
    st.subheader("🤖 AI Chat")
    st.caption("Ask anything. Attach images for vision.")

    # quick prompts
    with st.expander("⚡ Quick actions", expanded=False):
        qp = st.columns(4)
        presets = [
            "Explain this in simple terms",
            "Summarize the key points",
            "Translate to Kannada",
            "Give me 5 examples",
        ]
        for i, p in enumerate(presets):
            with qp[i]:
                if st.button(p, key=f"qp_{i}", use_container_width=True):
                    st.session_state["_preset"] = p

    # history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("attachments"):
                pills = " ".join(
               
