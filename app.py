import os
import time
import base64
import tempfile
from pathlib import Path

import streamlit as st
from google import genai


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "Ultra Sonic Super"

MODEL = "gemini-3.8-flash"
EMBEDDING_MODEL = "models/gemini-embedding-2"

MAX_FILE_SIZE_MB = 50

SUPPORTED_FILES = [
    "pdf",
    "txt",
    "md",
    "csv",
    "json",
    "docx",
    "pptx",
    "png",
    "jpg",
    "jpeg",
    "webp",
]


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

.hero {
    padding: 25px;
    border-radius: 24px;
    margin-bottom: 20px;
    border: 1px solid rgba(128,128,128,0.25);
    background: linear-gradient(
        135deg,
        rgba(100,100,255,0.15),
        rgba(0,200,255,0.08)
    );
}

.hero-title {
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 5px;
}

.hero-subtitle {
    font-size: 16px;
    opacity: 0.75;
}

.status-card {
    padding: 14px;
    border-radius: 16px;
    border: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 10px;
}

.feature-card {
    padding: 18px;
    border-radius: 18px;
    border: 1px solid rgba(128,128,128,0.2);
    min-height: 120px;
}

.small-text {
    font-size: 13px;
    opacity: 0.7;
}

div[data-testid="stChatMessage"] {
    border-radius: 16px;
}

.stButton > button {
    border-radius: 12px;
}

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


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_client(api_key):
    return genai.Client(api_key=api_key)


if not API_KEY:
    st.error(
        """
        ❌ Google API key not found.

        Add this to Streamlit Secrets:

        `GOOGLE_API_KEY = "YOUR_NEW_API_KEY"`

        Then reboot the app.
        """
    )
    st.stop()


client = get_client(API_KEY)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "interaction_id" not in st.session_state:
    st.session_state.interaction_id = None

if "store_name" not in st.session_state:
    st.session_state.store_name = None

if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []

if "file_upload_status" not in st.session_state:
    st.session_state.file_upload_status = {}


# ============================================================
# HELPERS
# ============================================================

def clean_output(text):
    if not text:
        return "I couldn't generate a response."

    return str(text).strip()


def add_message(role, content):
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
        }
    )


def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# ============================================================
# CREATE FILE SEARCH STORE
# ============================================================

def create_store():
    store = client.file_search_stores.create(
        config={
            "display_name": f"{APP_NAME}-Store",
            "embedding_model": EMBEDDING_MODEL,
        }
    )

    return store.name


# ============================================================
# GET OR CREATE STORE
# ============================================================

def get_store():
    if st.session_state.store_name:
        return st.session_state.store_name

    store_name = create_store()

    st.session_state.store_name = store_name

    return store_name


# ============================================================
# INDEX FILE
# ============================================================

def index_file(uploaded_file):

    file_size_mb = uploaded_file.size / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File is too large. Maximum size is "
            f"{MAX_FILE_SIZE_MB} MB."
        )

    suffix = Path(uploaded_file.name).suffix

    temp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_file.write(
                uploaded_file.getbuffer()
            )

            temp_path = temp_file.name

        store_name = get_store()

        operation = client.file_search_stores.upload_to_file_search_store(
            file=temp_path,
            file_search_store_name=store_name,
            config={
                "display_name": uploaded_file.name,
            },
        )

        progress = st.progress(0)

        while not operation.done:

            time.sleep(2)

            operation = client.operations.get(
                operation
            )

            progress.progress(
                min(
                    95,
                    progress._value if hasattr(
                        progress,
                        "_value"
                    )
                    else 50,
                )
            )

        progress.progress(100)

        if uploaded_file.name not in st.session_state.indexed_files:
            st.session_state.indexed_files.append(
                uploaded_file.name
            )

        return True

    finally:

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ============================================================
# NORMAL AI CHAT
# ============================================================

def ask_normal_chat(question):

    interaction = client.interactions.create(
        model=MODEL,
        input=question,
    )

    return clean_output(
        interaction.output_text
    ), interaction.id


# ============================================================
# FILE SEARCH / RAG
# ============================================================

def ask_files(question):

    if not st.session_state.store_name:
        raise ValueError(
            "Please upload a file first."
        )

    interaction = client.interactions.create(
        model=MODEL,
        input=question,
        tools=[
            {
                "type": "file_search",
                "file_search_store_names": [
                    st.session_state.store_name
                ],
            }
        ],
    )

    return clean_output(
        interaction.output_text
    ), interaction.id


# ============================================================
# GOOGLE SEARCH
# ============================================================

def ask_web(question):

    interaction = client.interactions.create(
        model=MODEL,
        input=question,
        tools=[
            {
                "type": "google_search"
            }
        ],
    )

    return clean_output(
        interaction.output_text
    ), interaction.id


# ============================================================
# PHOTO AI
# ============================================================

def analyze_photo(image_bytes, mime_type, question):

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    interaction = client.interactions.create(
        model=MODEL,
        input=[
            {
                "type": "text",
                "text": question,
            },
            {
                "type": "image",
                "data": image_base64,
                "mime_type": mime_type,
            },
        ],
    )

    return clean_output(
        interaction.output_text
    ), interaction.id


# ============================================================
# HERO
# ============================================================

st.markdown(
    f"""
<div class="hero">

<div class="hero-title">
⚡ {APP_NAME}
</div>

<div class="hero-subtitle">
Your fast AI workspace for Chat, Study Files, Photo AI and Web Search.
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("⚡ Ultra Sonic")

    st.caption(
        "Gemini 3.8 Flash AI Workspace"
    )

    st.divider()

    mode = st.radio(
        "Choose a mode",
        [
            "🤖 AI Chat",
            "📚 Study Files",
            "📷 Photo AI",
            "🌐 Web Search",
        ],
    )

    st.divider()

    st.subheader("📁 Files")

    uploaded_files = st.file_uploader(
        "Upload files for AI study",
        type=SUPPORTED_FILES,
        accept_multiple_files=True,
        help=(
            "Upload PDFs, documents, images, text files "
            "and supported study material."
        ),
    )

    if uploaded_files:

        for uploaded_file in uploaded_files:

            if (
                uploaded_file.name
                not in st.session_state.indexed_files
            ):

                if st.button(
                    f"📥 Add {uploaded_file.name}",
                    key=f"index_{uploaded_file.name}",
                    use_container_width=True,
                ):

                    with st.spinner(
                        f"Indexing {uploaded_file.name}..."
                    ):

                        try:

                            index_file(
                                uploaded_file
                            )

                            st.success(
                                "File added!"
                            )

                        except Exception as e:

                            st.error(
                                f"Indexing failed:\n{e}"
                            )

    if st.session_state.indexed_files:

        st.subheader("✅ Indexed")

        for filename in st.session_state.indexed_files:

            st.caption(
                f"📄 {filename}"
            )

    st.divider()

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True,
    ):

        st.session_state.messages = []
        st.session_state.interaction_id = None

        st.rerun()

    st.divider()

    st.caption(
        "Model: Gemini 3.8 Flash"
    )

    st.caption(
        "Built with Google Gemini API"
    )


# ============================================================
# AI CHAT
# ============================================================

if mode == "🤖 AI Chat":

    st.subheader("🤖 AI Chat")

    st.caption(
        "Ask anything. Kannada and English are supported."
    )

    display_chat_history()

    question = st.chat_input(
        "Ask Ultra Sonic anything..."
    )

    if question:

        add_message(
            "user",
            question,
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner(
                "⚡ Thinking..."
            ):

                try:

                    answer, interaction_id = (
                        ask_normal_chat(
                            question
                        )
                    )

                    st.markdown(answer)

                    st.session_state.interaction_id = (
                        interaction_id
                    )

                    add_message(
                        "assistant",
                        answer,
                    )

                except Exception as e:

                    error_message = (
                        f"❌ AI error:\n\n{e}"
                    )

                    st.error(
                        error_message
                    )

                    add_message(
                        "assistant",
                        error_message,
                    )


# ============================================================
# STUDY FILES
# ============================================================

elif mode == "📚 Study Files":

    st.subheader("📚 Study Files")

    if not st.session_state.indexed_files:

        st.info(
            """
            📁 Upload a PDF or document from the sidebar.

            Then click **Add** to create your searchable study knowledge base.
            """
        )

    else:

        st.success(
            f"{len(st.session_state.indexed_files)} "
            "file(s) ready for study."
        )

        for filename in st.session_state.indexed_files:

            st.caption(
                f"📄 {filename}"
            )

        st.divider()

        question = st.chat_input(
            "Ask something about your files..."
        )

        if question:

            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):

                with st.spinner(
                    "📚 Searching your files..."
                ):

                    try:

                        answer, interaction_id = (
                            ask_files(
                                question
                            )
                        )

                        st.markdown(answer)

                        st.session_state.interaction_id = (
                            interaction_id
                        )

                    except Exception as e:

                        st.error(
                            f"❌ File Search error:\n\n{e}"
                        )


# ============================================================
# PHOTO AI
# ============================================================

elif mode == "📷 Photo AI":

    st.subheader("📷 Photo AI")

    st.caption(
        "Upload an image and ask Gemini to analyze it."
    )

    photo = st.file_uploader(
        "Choose an image",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],
        key="photo_upload",
    )

    if photo:

        st.image(
            photo,
            caption=photo.name,
            use_container_width=True,
        )

        question = st.text_area(
            "What should I analyze?",
            value=(
                "Analyze this image carefully. "
                "Describe what you see and explain "
                "the important details."
            ),
            height=120,
        )

        if st.button(
            "🔍 Analyze Photo",
            type="primary",
            use_container_width=True,
        ):

            with st.spinner(
                "📷 Analyzing image..."
            ):

                try:

                    image_bytes = photo.getvalue()

                    answer, interaction_id = (
                        analyze_photo(
                            image_bytes,
                            photo.type,
                            question,
                        )
                    )

                    st.markdown("### 🧠 AI Analysis")

                    st.markdown(
                        answer
                    )

                    st.session_state.interaction_id = (
                        interaction_id
                    )

                except Exception as e:

                    st.error(
                        f"❌ Photo AI error:\n\n{e}"
                    )


# ============================================================
# WEB SEARCH
# ============================================================

elif mode == "🌐 Web Search":

    st.subheader(
        "🌐 Current Information Search"
    )

    st.caption(
        "Uses Google Search for information "
        "that needs current web data."
    )

    question = st.chat_input(
        "What do you want to search?"
    )

    if question:

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner(
                "🌐 Searching..."
            ):

                try:

                    answer, interaction_id = (
                        ask_web(
                            question
                        )
                    )

                    st.markdown(
                        answer
                    )

                    st.session_state.interaction_id = (
                        interaction_id
                    )

                except Exception as e:

                    st.error(
                        f"❌ Search error:\n\n{e}"
                    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "⚡ Ultra Sonic Super • Gemini 3.8 Flash • "
    "AI Chat • File Search • Photo AI • Google Search"
        )
