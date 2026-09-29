import os
import time
from pathlib import Path

import streamlit as st
from google import genai


# =========================================================
# APP CONFIG
# =========================================================

st.set_page_config(
    page_title="Ultra Sonic Super",
    page_icon="⚡",
    layout="wide"
)

APP_NAME = "⚡ Ultra Sonic Super"
MODEL = "gemini-3.8-flash"
EMBEDDING_MODEL = "models/gemini-embedding-2"


# =========================================================
# API KEY
# =========================================================

API_KEY = st.secrets.get(
    "GOOGLE_API_KEY",
    os.getenv("GOOGLE_API_KEY")
)

if not API_KEY:
    st.error("❌ GOOGLE_API_KEY is missing.")
    st.info(
        "Go to Streamlit → Manage app → Settings → Secrets "
        "and add GOOGLE_API_KEY."
    )
    st.stop()


client = genai.Client(
    api_key=API_KEY
)


# =========================================================
# SESSION
# =========================================================

if "store_name" not in st.session_state:
    st.session_state.store_name = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# =========================================================
# ULTRA SONIC UI
# =========================================================

st.markdown("""
<style>

.block-container {
    max-width: 1200px;
    padding-top: 1.5rem;
}

.hero {
    padding: 25px;
    border-radius: 25px;
    color: white;
    margin-bottom: 20px;

    background:
    linear-gradient(
        135deg,
        #111827,
        #312e81,
        #0f766e
    );
}

.hero h1 {
    margin: 5px 0;
    font-size: 2.4rem;
}

.hero p {
    margin: 0;
    opacity: .9;
}

.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,.15);
    margin-right: 5px;
    font-size: .8rem;
}

</style>

<div class="hero">

<span class="badge">⚡ ULTRA SONIC SUPER</span>
<span class="badge">🧠 GEMINI</span>
<span class="badge">📚 RAG</span>
<span class="badge">🖼️ PHOTO AI</span>

<h1>Kannada RAG Study Buddy</h1>

<p>
Ask in Kannada or English • Search your files •
Analyze photos • Study smarter
</p>

</div>
""", unsafe_allow_html=True)


# =========================================================
# CREATE RAG STORE
# =========================================================

def create_rag_store():

    store = client.file_search_stores.create(

        config={
            "display_name":
                "Ultra Sonic Super Study Files",

            "embedding_model":
                EMBEDDING_MODEL
        }
    )

    st.session_state.store_name = store.name

    return store.name


def get_rag_store():

    if st.session_state.store_name:

        return st.session_state.store_name

    return create_rag_store()


# =========================================================
# INDEX FILE
# =========================================================

def index_file(uploaded_file):

    store_name = get_rag_store()

    extension = Path(
        uploaded_file.name
    ).suffix

    temp_file = Path(
        "/tmp"
    ) / (
        "ultra_sonic_"
        + str(abs(hash(uploaded_file.name)))
        + extension
    )

    temp_file.write_bytes(
        uploaded_file.getvalue()
    )

    try:

        operation = (
            client
            .file_search_stores
            .upload_to_file_search_store(

                file=str(temp_file),

                file_search_store_name=
                    store_name,

                config={
                    "display_name":
                        uploaded_file.name
                }
            )
        )

        while not operation.done:

            time.sleep(2)

            operation = (
                client.operations.get(
                    operation
                )
            )

        if getattr(operation, "error", None):

            raise RuntimeError(
                str(operation.error)
            )

        return True

    finally:

        try:
            temp_file.unlink()
        except:
            pass


# =========================================================
# ASK STUDY FILES
# =========================================================

def ask_study_buddy(question):

    store_name = get_rag_store()

    response = client.interactions.create(

        model=MODEL,

        input=f"""
You are Ultra Sonic Super,
a powerful Kannada + English engineering
study assistant.

Use the student's uploaded study files
as the primary source.

Rules:

1. Do not invent information.

2. If the answer exists in the uploaded
   files, use that information.

3. If the answer is not found in the files,
   clearly say so.

4. Explain difficult topics simply.

5. If the user asks in Kannada,
   answer in natural Kannada.

6. Keep technical terms in English
   when useful.

7. For exam questions:
   give the direct answer first,
   then explanation,
   then important points.

Student question:

{question}
""",

        tools=[
            {
                "type": "file_search",

                "file_search_store_names": [
                    store_name
                ]
            }
        ]
    )

    return response.output_text


# =========================================================
# PHOTO AI
# =========================================================

def analyze_photo(
    uploaded_image,
    question
):

    uploaded = client.files.upload(

        file=uploaded_image,

        config={
            "display_name":
                uploaded_image.name
        }
    )

    response = client.interactions.create(

        model=MODEL,

        input=[
            {
                "type": "text",

                "text": f"""
Analyze this image carefully.

Do not invent information.

Answer in Kannada + English
where useful.

Question:

{question}
"""
            },

            {
                "type": "file",

                "uri": uploaded.uri,

                "mime_type":
                    uploaded.mime_type
            }
        ]
    )

    return response.output_text


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("⚡ Ultra Sonic Controls")

    mode = st.radio(

        "Choose Mode",

        [
            "📚 Study Files",
            "🖼️ Photo AI"
        ]
    )

    st.divider()

    st.subheader(
        "📥 Add Study Material"
    )

    files = st.file_uploader(

        "Upload your files",

        type=[
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
            "webp"
        ],

        accept_multiple_files=True
    )

    if files:

        if st.button(
            "⚡ INDEX MY FILES",
            type="primary",
            use_container_width=True
        ):

            progress = st.progress(0)

            for i, file in enumerate(files):

                try:

                    index_file(file)

                    st.success(
                        f"✅ {file.name}"
                    )

                except Exception as e:

                    st.error(
                        f"❌ {file.name}: {e}"
                    )

                progress.progress(
                    (i + 1) / len(files)
                )


# =========================================================
# STUDY MODE
# =========================================================

if mode == "📚 Study Files":

    st.subheader(
        "🔎 Ask Your Study Material"
    )

    for message in (
        st.session_state.messages
    ):

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    question = st.chat_input(
        "Ask in Kannada or English..."
    )

    if question:

        st.session_state.messages.append({

            "role":
                "user",

            "content":
                question
        })

        with st.chat_message("user"):

            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner(
                "⚡ Searching your study files..."
            ):

                try:

                    answer = (
                        ask_study_buddy(
                            question
                        )
                    )

                    st.markdown(answer)

                    st.session_state.messages.append({

                        "role":
                            "assistant",

                        "content":
                            answer
                    })

                except Exception as e:

                    st.error(
                        f"❌ Error: {e}"
                    )


# =========================================================
# PHOTO MODE
# =========================================================

else:

    st.subheader(
        "🖼️ Ultra Sonic Photo AI"
    )

    image = st.file_uploader(

        "Upload an image",

        type=[
            "png",
            "jpg",
            "jpeg",
            "webp"
        ],

        key="photo"
    )

    question = st.text_input(

        "What should I do with this image?",

        value=(
            "Solve this question and "
            "explain it step by step."
        )
    )

    if image:

        st.image(
            image,
            use_container_width=True
        )

        if st.button(
            "⚡ ANALYZE",
            type="primary"
        ):

            with st.spinner(
                "⚡ Ultra Sonic is analyzing..."
            ):

                try:

                    answer = analyze_photo(
                        image,
                        question
                    )

                    st.markdown(
                        "### 🧠 Answer"
                    )

                    st.markdown(answer)

                except Exception as e:

                    st.error(
                        f"❌ Error: {e}"
                    )
