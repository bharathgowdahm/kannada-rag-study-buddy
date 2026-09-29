import os
import time
import base64
import hashlib
import tempfile
from pathlib import Path

import streamlit as st
from google import genai


# ============================================================
# ULTRA SONIC SUPER
# ============================================================

APP_NAME = "Ultra Sonic Super"

MODEL = "gemini-3.8-flash"
EMBEDDING_MODEL = "models/gemini-embedding-2"

MAX_FILE_SIZE_MB = 50

SUPPORTED_FILES = [
    "pdf",
    "docx",
    "pptx",
    "txt",
    "md",
    "csv",
    "json",
    "png",
    "jpg",
    "jpeg",
    "webp",
]


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
# CUSTOM CSS
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
    max-width: 1200px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}

.hero {
    padding: 28px;
    border-radius: 24px;
    margin-bottom: 22px;
    border: 1px solid rgba(128,128,128,0.25);
    background:
        linear-gradient(
            135deg,
            rgba(100,100,255,0.15),
            rgba(0,200,255,0.08)
        );
}

.hero-title {
    font-size: 38px;
    font-weight: 800;
    line-height: 1.1;
}

.hero-subtitle {
    margin-top: 8px;
    font-size: 15px;
    opacity: 0.72;
}

.card {
    padding: 18px;
    border-radius: 18px;
    border: 1px solid rgba(128,128,128,0.22);
    margin-bottom: 12px;
}

.file-card {
    padding: 14px;
    border-radius: 15px;
    border: 1px solid rgba(128,128,128,0.20);
    margin-bottom: 8px;
}

.status {
    font-size: 13px;
    opacity: 0.72;
}

.stButton > button {
    border-radius: 12px;
}

.stChatInput {
    border-radius: 16px;
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


if not API_KEY:

    st.error(
        """
        ❌ Google API key not found.

        Add your key to Streamlit Secrets:

        `GOOGLE_API_KEY = "YOUR_NEW_API_KEY"`

        Then reboot the app.
        """
    )

    st.stop()


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_client(api_key):

    return genai.Client(
        api_key=api_key
    )


client = get_client(API_KEY)


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
    "processing_files": {},
}


for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# UTILITY
# ============================================================

def file_hash(uploaded_file):

    data = uploaded_file.getvalue()

    return hashlib.sha256(
        data
    ).hexdigest()


def safe_filename(name):

    return Path(name).name


def format_error(error):

    return (
        f"❌ **Something went wrong**\n\n"
        f"`{error}`"
    )


# ============================================================
# FILE SEARCH STORE
# ============================================================

def create_file_store():

    store = client.file_search_stores.create(
        config={
            "display_name": "ultra-sonic-study-store",
            "embedding_model": EMBEDDING_MODEL,
        }
    )

    return store.name


def get_file_store():

    if st.session_state.file_store_name:

        return st.session_state.file_store_name

    store_name = create_file_store()

    st.session_state.file_store_name = store_name

    return store_name


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(uploaded_file):

    filename = safe_filename(
        uploaded_file.name
    )

    file_size = uploaded_file.size

    size_mb = file_size / (
        1024 * 1024
    )

    if size_mb > MAX_FILE_SIZE_MB:

        raise ValueError(
            f"{filename} is larger than "
            f"{MAX_FILE_SIZE_MB} MB."
        )

    store_name = get_file_store()

    suffix = Path(
        filename
    ).suffix

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

        operation = (
            client.file_search_stores
            .upload_to_file_search_store(
                file=temp_path,
                file_search_store_name=store_name,
                config={
                    "display_name": filename
                },
            )
        )

        while not operation.done:

            time.sleep(2)

            operation = client.operations.get(
                operation
            )

        if getattr(
            operation,
            "error",
            None,
        ):

            raise RuntimeError(
                str(operation.error)
            )

        return True

    finally:

        if (
            temp_path
            and os.path.exists(temp_path)
        ):

            os.remove(temp_path)


# ============================================================
# PROCESS MULTIPLE FILES
# ============================================================

def process_uploaded_files(
    uploaded_files
):

    results = []

    if not uploaded_files:

        return results

    for uploaded_file in uploaded_files:

        filename = safe_filename(
            uploaded_file.name
        )

        file_id = file_hash(
            uploaded_file
        )

        if file_id in st.session_state.processed_files:

            continue

        try:

            process_file(
                uploaded_file
            )

            st.session_state.processed_files[
                file_id
            ] = {
                "name": filename,
                "size": uploaded_file.size,
                "status": "ready",
            }

            results.append(
                {
                    "name": filename,
                    "success": True,
                }
            )

        except Exception as error:

            st.session_state.processed_files[
                file_id
            ] = {
                "name": filename,
                "size": uploaded_file.size,
                "status": "error",
                "error": str(error),
            }

            results.append(
                {
                    "name": filename,
                    "success": False,
                    "error": str(error),
                }
            )

    return results


# ============================================================
# LIST FILE SEARCH DOCUMENTS
# ============================================================

def get_store_documents():

    store_name = (
        st.session_state.file_store_name
    )

    if not store_name:

        return []

    try:

        documents = []

        for document in (
            client.file_search_stores
            .documents.list(
                parent=store_name
            )
        ):

            documents.append(
                document
            )

        return documents

    except Exception:

        return []


# ============================================================
# DELETE DOCUMENT
# ============================================================

def delete_document(
    document_name
):

    client.file_search_stores.documents.delete(
        name=document_name,
        config={
            "force": True
        },
    )


# ============================================================
# DELETE ALL FILES
# ============================================================

def delete_all_files():

    store_name = (
        st.session_state.file_store_name
    )

    if store_name:

        try:

            client.file_search_stores.delete(
                name=store_name,
                config={
                    "force": True
                },
            )

        except Exception:
            pass

    st.session_state.file_store_name = None

    st.session_state.processed_files = {}

    st.session_state.file_interaction_id = None


# ============================================================
# NORMAL CHAT
# ============================================================

def ask_chat(question):

    kwargs = {
        "model": MODEL,
        "input": question,
    }

    previous = (
        st.session_state.chat_interaction_id
    )

    if previous:

        kwargs[
            "previous_interaction_id"
        ] = previous

    interaction = (
        client.interactions.create(
            **kwargs
        )
    )

    st.session_state.chat_interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# FILE SEARCH
# ============================================================

def ask_file(question):

    store_name = (
        st.session_state.file_store_name
    )

    if not store_name:

        raise ValueError(
            "Please upload and process a file first."
        )

    kwargs = {
        "model": MODEL,
        "input": question,
        "tools": [
            {
                "type": "file_search",
                "file_search_store_names": [
                    store_name
                ],
            }
        ],
    }

    previous = (
        st.session_state.file_interaction_id
    )

    if previous:

        kwargs[
            "previous_interaction_id"
        ] = previous

    interaction = (
        client.interactions.create(
            **kwargs
        )
    )

    st.session_state.file_interaction_id = (
        interaction.id
    )

    return interaction.output_text, interaction


# ============================================================
# GOOGLE SEARCH
# ============================================================

def ask_web(question):

    kwargs = {
        "model": MODEL,
        "input": question,
        "tools": [
            {
                "type": "google_search"
            }
        ],
    }

    previous = (
        st.session_state.web_interaction_id
    )

    if previous:

        kwargs[
            "previous_interaction_id"
        ] = previous

    interaction = (
        client.interactions.create(
            **kwargs
        )
    )

    st.session_state.web_interaction_id = (
        interaction.id
    )

    return interaction.output_text, interaction


# ============================================================
# PHOTO AI
# ============================================================

def analyze_photo(
    image_bytes,
    mime_type,
    question,
):

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    kwargs = {
        "model": MODEL,
        "input": [
            {
                "type": "text",
                "text": question,
            },
            {
                "type": "image",
                "data": encoded,
                "mime_type": mime_type,
            },
        ],
    }

    previous = (
        st.session_state.photo_interaction_id
    )

    if previous:

        kwargs[
            "previous_interaction_id"
        ] = previous

    interaction = (
        client.interactions.create(
            **kwargs
        )
    )

    st.session_state.photo_interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# FILE CITATIONS
# ============================================================

def get_file_citations(
    interaction
):

    citations = []

    try:

        for step in interaction.steps:

            if step.type != "model_output":

                continue

            for content in step.content:

                annotations = getattr(
                    content,
                    "annotations",
                    None,
                )

                if not annotations:

                    continue

                for annotation in annotations:

                    if (
                        getattr(
                            annotation,
                            "type",
                            None,
                        )
                        == "file_citation"
                    ):

                        page = getattr(
                            annotation,
                            "page_number",
                            None,
                        )

                        title = getattr(
                            annotation,
                            "title",
                            None,
                        )

                        citations.append(
                            {
                                "page": page,
                                "title": title,
                            }
                        )

    except Exception:

        pass

    return citations


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
AI Chat • Study Files • Photo AI • Google Search
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
        "Gemini 3.8 Flash"
    )

    st.divider()

    mode = st.radio(
        "Choose mode",
        [
            "🤖 AI Chat",
            "📚 Study Files",
            "📷 Photo AI",
            "🌐 Web Search",
        ],
    )

    st.divider()

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True,
    ):

        st.session_state.messages = []

        st.session_state.chat_interaction_id = None

        st.session_state.file_interaction_id = None

        st.session_state.photo_interaction_id = None

        st.session_state.web_interaction_id = None

        st.rerun()

    st.divider()

    st.caption(
        "Fast AI workspace"
    )

    st.caption(
        "Kannada + English supported"
    )


# ============================================================
# AI CHAT
# ============================================================

if mode == "🤖 AI Chat":

    st.subheader(
        "🤖 AI Chat"
    )

    st.caption(
        "Ask anything in Kannada or English."
    )

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    question = st.chat_input(
        "Ask Ultra Sonic..."
    )

    if question:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        with st.chat_message("user"):

            st.markdown(question)

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "⚡ Thinking..."
            ):

                try:

                    answer = ask_chat(
                        question
                    )

                    st.markdown(
                        answer
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                        }
                    )

                except Exception as error:

                    st.error(
                        format_error(error)
                    )


# ============================================================
# STUDY FILES
# ============================================================

elif mode == "📚 Study Files":

    st.subheader(
        "📚 Study Files"
    )

    st.caption(
        "Upload your study material and ask questions from it."
    )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    uploaded_files = st.file_uploader(
        "📁 Upload your files",
        type=SUPPORTED_FILES,
        accept_multiple_files=True,
        help=(
            "PDF, DOCX, PPTX, TXT, MD, CSV, JSON, "
            "PNG, JPG, JPEG and WEBP."
        ),
    )

    if uploaded_files:

        new_files = []

        for uploaded_file in uploaded_files:

            file_id = file_hash(
                uploaded_file
            )

            if (
                file_id
                not in st.session_state.processed_files
            ):

                new_files.append(
                    uploaded_file
                )

        # ----------------------------------------------------
        # AUTOMATIC PROCESSING
        # ----------------------------------------------------

        if new_files:

            st.info(
                f"⚡ Processing {len(new_files)} "
                f"new file(s)..."
            )

            progress = st.progress(0)

            for index, uploaded_file in enumerate(
                new_files
            ):

                filename = safe_filename(
                    uploaded_file.name
                )

                st.write(
                    f"📄 **{filename}**"
                )

                try:

                    with st.spinner(
                        f"Indexing {filename}..."
                    ):

                        process_file(
                            uploaded_file
                        )

                    file_id = file_hash(
                        uploaded_file
                    )

                    st.session_state.processed_files[
                        file_id
                    ] = {
                        "name": filename,
                        "size": uploaded_file.size,
                        "status": "ready",
                    }

                    st.success(
                        f"✅ {filename} ready"
                    )

                except Exception as error:

                    file_id = file_hash(
                        uploaded_file
                    )

                    st.session_state.processed_files[
                        file_id
                    ] = {
                        "name": filename,
                        "size": uploaded_file.size,
                        "status": "error",
                        "error": str(error),
                    }

                    st.error(
                        f"❌ {filename}: {error}"
                    )

                progress.progress(
                    (index + 1)
                    / len(new_files)
                )

    # --------------------------------------------------------
    # FILE STATUS
    # --------------------------------------------------------

    ready_files = [
        data
        for data in
        st.session_state.processed_files.values()
        if data.get("status") == "ready"
    ]

    error_files = [
        data
        for data in
        st.session_state.processed_files.values()
        if data.get("status") == "error"
    ]

    if ready_files:

        st.divider()

        st.success(
            f"✅ {len(ready_files)} file(s) ready for questions."
        )

        for file_data in ready_files:

            col1, col2 = st.columns(
                [5, 1]
            )

            with col1:

                st.markdown(
                    f"📄 **{file_data['name']}**"
                )

            with col2:

                st.caption("READY")

    if error_files:

        st.warning(
            f"{len(error_files)} file(s) failed."
        )

    # --------------------------------------------------------
    # CLEAR ALL FILES
    # --------------------------------------------------------

    if ready_files:

        st.divider()

        if st.button(
            "🗑️ Clear all study files",
            use_container_width=True,
        ):

            delete_all_files()

            st.success(
                "All study files cleared."
            )

            st.rerun()

    # --------------------------------------------------------
    # QUESTIONS
    # --------------------------------------------------------

    if ready_files:

        st.divider()

        st.markdown(
            "### 💬 Ask your files"
        )

        st.caption(
            "Ultra Sonic will search your uploaded documents "
            "before answering."
        )

        question = st.chat_input(
            "Ask anything about your files..."
        )

        if question:

            with st.chat_message(
                "user"
            ):

                st.markdown(
                    question
                )

            with st.chat_message(
                "assistant"
            ):

                with st.spinner(
                    "📚 Searching your files..."
                ):

                    try:

                        answer, interaction = (
                            ask_file(
                                question
                            )
                        )

                        st.markdown(
                            answer
                        )

                        citations = (
                            get_file_citations(
                                interaction
                            )
                        )

                        if citations:

                            st.caption(
                                "📌 File references"
                            )

                            shown = set()

                            for citation in citations:

                                key = (
                                    citation.get(
                                        "title"
                                    ),
                                    citation.get(
                                        "page"
                                    ),
                                )

                                if key in shown:

                                    continue

                                shown.add(key)

                                page = citation.get(
                                    "page"
                                )

                                title = citation.get(
                                    "title"
                                )

                                if page:

                                    st.caption(
                                        f"📄 {title or 'Document'} "
                                        f"— Page {page}"
                                    )

                                else:

                                    st.caption(
                                        f"📄 {title or 'Document'}"
                                    )

                    except Exception as error:

                        st.error(
                            format_error(error)
                        )

    else:

        st.markdown(
            """
            <div class="card">

            ### 📁 Start studying

            Upload one or more PDFs or documents above.

            Once processing finishes:

            **Upload → Process → Ready → Ask questions**

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# PHOTO AI
# ============================================================

elif mode == "📷 Photo AI":

    st.subheader(
        "📷 Photo AI"
    )

    st.caption(
        "Upload an image and ask Gemini to understand it."
    )

    photo = st.file_uploader(
        "🖼️ Choose an image",
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
            "What do you want to know?",
            value=(
                "Analyze this image carefully. "
                "Explain the important details."
            ),
            height=120,
        )

        if st.button(
            "🔍 Analyze",
            type="primary",
            use_container_width=True,
        ):

            with st.spinner(
                "📷 Analyzing..."
            ):

                try:

                    answer = analyze_photo(
                        photo.getvalue(),
                        photo.type,
                        question,
                    )

                    st.markdown(
                        "### 🧠 Analysis"
                    )

                    st.markdown(
                        answer
                    )

                except Exception as error:

                    st.error(
                        format_error(error)
                    )


# ============================================================
# WEB SEARCH
# ============================================================

elif mode == "🌐 Web Search":

    st.subheader(
        "🌐 Google Search"
    )

    st.caption(
        "Use this mode for current information from the web."
    )

    question = st.chat_input(
        "What do you want to search?"
    )

    if question:

        with st.chat_message(
            "user"
        ):

            st.markdown(
                question
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "🌐 Searching the web..."
            ):

                try:

                    answer, interaction = (
                        ask_web(
                            question
                        )
                    )

                    st.markdown(
                        answer
                    )

                except Exception as error:

                    st.error(
                        format_error(error)
                    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "⚡ Ultra Sonic Super • "
    "Gemini 3.8 Flash • "
    "File Search • Photo AI • Google Search"
    )
