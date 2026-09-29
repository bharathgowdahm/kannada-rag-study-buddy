import os
import time
from pathlib import Path

import streamlit as st
from google import genai


# ============================================================
# ⚡ ULTRA SONIC SUPER
# Professional Gemini Study Assistant
# ============================================================

st.set_page_config(
    page_title="Ultra Sonic Super",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "⚡ Ultra Sonic Super"

MODEL = "gemini-3.8-flash"

EMBEDDING_MODEL = "models/gemini-embedding-2"

# Low = faster responses.
# Change to "medium" if you want deeper reasoning.
THINKING_LEVEL = "low"


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
# 🔐 API KEY
# ============================================================

try:
    API_KEY = st.secrets.get(
        "GOOGLE_API_KEY",
        os.getenv("GOOGLE_API_KEY"),
    )
except Exception as e:
    st.error("❌ Streamlit Secrets could not be read.")
    st.code(str(e))
    st.stop()


if not API_KEY:
    st.error("❌ GOOGLE_API_KEY is missing.")

    st.markdown(
        """
        Go to:

        **Streamlit → Manage app → Settings → Secrets**

        Add:

        ```toml
        GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
        ```
        """
    )

    st.stop()


# ============================================================
# 🤖 GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_client():
    return genai.Client(api_key=API_KEY)


client = get_client()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "store_name": None,
    "interaction_id": None,
    "messages": [],
    "indexed_files": [],
    "file_upload_status": {},
}


for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 🎨 PROFESSIONAL UI
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1250px;
        padding-top: 1.2rem;
        padding-bottom: 4rem;
    }

    .hero {
        padding: 28px;
        border-radius: 26px;
        margin-bottom: 22px;

        background:
        linear-gradient(
            135deg,
            #111827 0%,
            #312e81 50%,
            #0f766e 100%
        );

        color: white;
    }

    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        margin-top: 12px;
        margin-bottom: 5px;
    }

    .hero-subtitle {
        opacity: .9;
        font-size: 1rem;
    }

    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(255,255,255,.13);
        margin-right: 5px;
        margin-bottom: 5px;
        font-size: .78rem;
    }

    .status-card {
        padding: 15px;
        border-radius: 16px;
        background: rgba(128,128,128,.08);
        margin-bottom: 10px;
    }

    </style>

    <div class="hero">

        <span class="badge">⚡ ULTRA SONIC SUPER</span>
        <span class="badge">🧠 GEMINI 3.8 FLASH</span>
        <span class="badge">📚 RAG</span>
        <span class="badge">📄 FILE SEARCH</span>
        <span class="badge">🖼️ PHOTO AI</span>

        <div class="hero-title">
            Ultra Sonic Super
        </div>

        <div class="hero-subtitle">
            Fast Kannada + English AI Study Assistant
            • Documents • RAG • Photos • Smart Search
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 📚 FILE SEARCH STORE
# ============================================================

def create_store():

    store = client.file_search_stores.create(
        config={
            "display_name": "Ultra Sonic Super Study Files",
            "embedding_model": EMBEDDING_MODEL,
        }
    )

    st.session_state.store_name = store.name

    return store.name


def get_store():

    if st.session_state.store_name:
        return st.session_state.store_name

    return create_store()


# ============================================================
# 📥 FILE INDEXING
# ============================================================

def index_file(uploaded_file):

    store_name = get_store()

    suffix = Path(
        uploaded_file.name
    ).suffix.lower()

    temp_name = (
        "ultra_sonic_"
        + str(abs(hash(uploaded_file.name)))
        + suffix
    )

    temp_path = Path("/tmp") / temp_name

    temp_path.write_bytes(
        uploaded_file.getvalue()
    )

    try:

        operation = (
            client
            .file_search_stores
            .upload_to_file_search_store(
                file=str(temp_path),

                file_search_store_name=store_name,

                config={
                    "display_name":
                        uploaded_file.name,
                },
            )
        )

        # File indexing is asynchronous.
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
            temp_path.unlink()
        except Exception:
            pass


# ============================================================
# 🧠 GEMINI PROMPT
# ============================================================

def build_system_prompt():

    return """
You are Ultra Sonic Super.

You are a professional Kannada + English
engineering study assistant.

CORE BEHAVIOUR:

• Be accurate.
• Be concise by default.
• Do not invent information.
• Explain difficult concepts simply.
• Preserve important technical terminology.
• If the user asks Kannada, naturally answer in Kannada.
• If the user asks English, answer in English.
• If mixed language is useful, use Kannada + English.

FOR STUDY QUESTIONS:

1. Give the direct answer first.
2. Then explain.
3. Then give important exam points.
4. Use examples when useful.

FOR UPLOADED FILES:

• Treat uploaded study material as the primary source.
• Use File Search when available.
• Do not pretend something came from the file if it did not.
• If the requested information is not found,
  clearly say that.

FOR ENGINEERING:

• Prefer structured explanations.
• Use formulas when necessary.
• Show calculation steps for numerical problems.
• For programming questions, give clean code.
• Explain code briefly after the code.

Keep responses comfortable to read on a mobile phone.
"""


# ============================================================
# 📚 FILE SEARCH CHAT
# ============================================================

def ask_files(question):

    store_name = get_store()

    prompt = (
        build_system_prompt()
        + "\n\nStudent question:\n"
        + question
    )

    kwargs = {
        "model": MODEL,
        "input": prompt,

        "generation_config": {
            "thinking_level": THINKING_LEVEL,
        },

        "tools": [
            {
                "type": "file_search",
                "file_search_store_names": [
                    store_name
                ],
            }
        ],
    }

    # Continue previous conversation when available.
    if st.session_state.interaction_id:

        kwargs[
            "previous_interaction_id"
        ] = st.session_state.interaction_id

    interaction = client.interactions.create(
        **kwargs
    )

    st.session_state.interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# 💬 NORMAL CHAT
# ============================================================

def ask_normal_chat(question):

    kwargs = {
        "model": MODEL,

        "input": (
            build_system_prompt()
            + "\n\nStudent question:\n"
            + question
        ),

        "generation_config": {
            "thinking_level": THINKING_LEVEL,
        },
    }

    if st.session_state.interaction_id:

        kwargs[
            "previous_interaction_id"
        ] = st.session_state.interaction_id

    interaction = client.interactions.create(
        **kwargs
    )

    st.session_state.interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# 🌐 GOOGLE SEARCH CHAT
# ============================================================

def ask_web(question):

    kwargs = {
        "model": MODEL,

        "input": (
            build_system_prompt()
            + """

This request requires current information.

Use Google Search and provide a concise,
accurate answer.

Student question:
"""
            + question
        ),

        "generation_config": {
            "thinking_level": THINKING_LEVEL,
        },

        "tools": [
            {
                "type": "google_search"
            }
        ],
    }

    if st.session_state.interaction_id:

        kwargs[
            "previous_interaction_id"
        ] = st.session_state.interaction_id

    interaction = client.interactions.create(
        **kwargs
    )

    st.session_state.interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# 🖼️ PHOTO AI
# ============================================================

def analyze_photo(uploaded_image, question):

    image_bytes = uploaded_image.getvalue()

    import base64

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    mime_type = uploaded_image.type

    prompt = f"""
You are Ultra Sonic Super Photo AI.

Analyze the uploaded image carefully.

User request:

{question}

Rules:

• Read visible text accurately.
• Do not invent missing information.
• If it is a question, solve it.
• If it is mathematics, show steps.
• If it is engineering, explain clearly.
• If it is a diagram, identify important components.
• If it is handwritten, interpret carefully.
• Answer in Kannada + English when useful.
• Give the direct answer first.
"""

    interaction = client.interactions.create(

        model=MODEL,

        input=[
            {
                "type": "text",
                "text": prompt,
            },

            {
                "type": "image",
                "data": image_base64,
                "mime_type": mime_type,
            },
        ],

        generation_config={
            "thinking_level": THINKING_LEVEL,
        },
    )

    return interaction.output_text


# ============================================================
# 🧹 RESET CHAT
# ============================================================

def clear_chat():

    st.session_state.messages = []

    st.session_state.interaction_id = None

    st.rerun()


# ============================================================
# 📱 SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚡ Ultra Sonic")

    mode = st.radio(
        "Mode",
        [
            "💬 AI Chat",
            "📚 Study Files",
            "🖼️ Photo AI",
            "🌐 Web Search",
        ],
    )

    st.divider()

    # --------------------------------------------------------
    # FILE UPLOAD
    # --------------------------------------------------------

    st.subheader("📚 Study Library")

    uploaded_files = st.file_uploader(

        "Add PDF / documents",

        type=SUPPORTED_FILES,

        accept_multiple_files=True,
    )

    if uploaded_files:

        if st.button(
            "⚡ ADD TO STUDY LIBRARY",
            type="primary",
            use_container_width=True,
        ):

            progress = st.progress(0)

            total = len(uploaded_files)

            for index, uploaded_file in enumerate(
                uploaded_files
            ):

                filename = uploaded_file.name

                if filename in (
                    st.session_state.indexed_files
                ):

                    st.info(
                        f"⏭️ Already added: {filename}"
                    )

                else:

                    try:

                        with st.spinner(
                            f"Indexing {filename}..."
                        ):

                            index_file(
                                uploaded_file
                            )

                        st.session_state.indexed_files.append(
                            filename
                        )

                        st.session_state.file_upload_status[
                            filename
                        ] = "Ready"

                        st.success(
                            f"✅ {filename}"
                        )

                    except Exception as e:

                        st.session_state.file_upload_status[
                            filename
                        ] = "Error"

                        st.error(
                            f"❌ {filename}\n\n{e}"
                        )

                progress.progress(
                    (index + 1) / total
                )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    st.divider()

    st.subheader("📊 System Status")

    if st.session_state.store_name:

        st.success(
            "🟢 File Search ready"
        )

    else:

        st.info(
            "⚪ File Search waiting"
        )

    st.caption(
        f"📚 Files: "
        f"{len(st.session_state.indexed_files)}"
    )

    st.caption(
        f"🧠 Model: {MODEL}"
    )

    st.caption(
        f"⚡ Thinking: {THINKING_LEVEL}"
    )

    # --------------------------------------------------------
    # CONTROLS
    # --------------------------------------------------------

    st.divider()

    if st.button(
        "🧹 Clear Chat",
        use_container_width=True,
    ):

        clear_chat()


# ============================================================
# 💬 AI CHAT
# ============================================================

if mode == "💬 AI Chat":

    st.subheader(
        "💬 Ultra Sonic AI"
    )

    st.caption(
        "Fast general-purpose Kannada + English AI."
    )

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    question = st.chat_input(
        "Ask anything..."
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

        with st.chat_message("assistant"):

            with st.spinner(
                "⚡ Thinking..."
            ):

                try:

                    answer = ask_normal_chat(
                        question
                    )

                    st.markdown(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                        }
                    )

                except Exception as e:

                    st.error(
                        f"❌ Gemini error:\n\n{e}"
                    )


# ============================================================
# 📚 STUDY FILE MODE
# ============================================================

elif mode == "📚 Study Files":

    st.subheader(
        "📚 Ask Your Study Material"
    )

    if not st.session_state.store_name:

        st.info(
            "👈 Upload your PDF or study files "
            "from the sidebar first."
        )

    else:

        st.success(
            "🟢 Your study library is ready."
        )

        for message in st.session_state.messages:

            with st.chat_message(
                message["role"]
            ):

                st.markdown(
                    message["content"]
                )

        question = st.chat_input(
            "Ask something from your study material..."
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

            with st.chat_message("assistant"):

                with st.spinner(
                    "🔎 Searching your files..."
                ):

                    try:

                        answer = ask_files(
                            question
                        )

                        st.markdown(answer)

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                            }
                        )

                    except Exception as e:

                        st.error(
                            f"❌ File Search error:\n\n{e}"
                        )


# ============================================================
import os
import time
from pathlib import Path

import streamlit as st
from google import genai


# ============================================================
# ⚡ ULTRA SONIC SUPER
# Professional Gemini Study Assistant
# ============================================================

st.set_page_config(
    page_title="Ultra Sonic Super",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "⚡ Ultra Sonic Super"

MODEL = "gemini-3.8-flash"

EMBEDDING_MODEL = "models/gemini-embedding-2"

# Low = faster responses.
# Change to "medium" if you want deeper reasoning.
THINKING_LEVEL = "low"


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
# 🔐 API KEY
# ============================================================

try:
    API_KEY = st.secrets.get(
        "GOOGLE_API_KEY",
        os.getenv("GOOGLE_API_KEY"),
    )
except Exception as e:
    st.error("❌ Streamlit Secrets could not be read.")
    st.code(str(e))
    st.stop()


if not API_KEY:
    st.error("❌ GOOGLE_API_KEY is missing.")

    st.markdown(
        """
        Go to:

        **Streamlit → Manage app → Settings → Secrets**

        Add:

        ```toml
        GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
        ```
        """
    )

    st.stop()


# ============================================================
# 🤖 GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_client():
    return genai.Client(api_key=API_KEY)


client = get_client()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "store_name": None,
    "interaction_id": None,
    "messages": [],
    "indexed_files": [],
    "file_upload_status": {},
}


for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 🎨 PROFESSIONAL UI
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1250px;
        padding-top: 1.2rem;
        padding-bottom: 4rem;
    }

    .hero {
        padding: 28px;
        border-radius: 26px;
        margin-bottom: 22px;

        background:
        linear-gradient(
            135deg,
            #111827 0%,
            #312e81 50%,
            #0f766e 100%
        );

        color: white;
    }

    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        margin-top: 12px;
        margin-bottom: 5px;
    }

    .hero-subtitle {
        opacity: .9;
        font-size: 1rem;
    }

    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(255,255,255,.13);
        margin-right: 5px;
        margin-bottom: 5px;
        font-size: .78rem;
    }

    .status-card {
        padding: 15px;
        border-radius: 16px;
        background: rgba(128,128,128,.08);
        margin-bottom: 10px;
    }

    </style>

    <div class="hero">

        <span class="badge">⚡ ULTRA SONIC SUPER</span>
        <span class="badge">🧠 GEMINI 3.8 FLASH</span>
        <span class="badge">📚 RAG</span>
        <span class="badge">📄 FILE SEARCH</span>
        <span class="badge">🖼️ PHOTO AI</span>

        <div class="hero-title">
            Ultra Sonic Super
        </div>

        <div class="hero-subtitle">
            Fast Kannada + English AI Study Assistant
            • Documents • RAG • Photos • Smart Search
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 📚 FILE SEARCH STORE
# ============================================================

def create_store():

    store = client.file_search_stores.create(
        config={
            "display_name": "Ultra Sonic Super Study Files",
            "embedding_model": EMBEDDING_MODEL,
        }
    )

    st.session_state.store_name = store.name

    return store.name


def get_store():

    if st.session_state.store_name:
        return st.session_state.store_name

    return create_store()


# ============================================================
# 📥 FILE INDEXING
# ============================================================

def index_file(uploaded_file):

    store_name = get_store()

    suffix = Path(
        uploaded_file.name
    ).suffix.lower()

    temp_name = (
        "ultra_sonic_"
        + str(abs(hash(uploaded_file.name)))
        + suffix
    )

    temp_path = Path("/tmp") / temp_name

    temp_path.write_bytes(
        uploaded_file.getvalue()
    )

    try:

        operation = (
            client
            .file_search_stores
            .upload_to_file_search_store(
                file=str(temp_path),

                file_search_store_name=store_name,

                config={
                    "display_name":
                        uploaded_file.name,
                },
            )
        )

        # File indexing is asynchronous.
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
            temp_path.unlink()
        except Exception:
            pass


# ============================================================
# 🧠 GEMINI PROMPT
# ============================================================

def build_system_prompt():

    return """
You are Ultra Sonic Super.

You are a professional Kannada + English
engineering study assistant.

CORE BEHAVIOUR:

• Be accurate.
• Be concise by default.
• Do not invent information.
• Explain difficult concepts simply.
• Preserve important technical terminology.
• If the user asks Kannada, naturally answer in Kannada.
• If the user asks English, answer in English.
• If mixed language is useful, use Kannada + English.

FOR STUDY QUESTIONS:

1. Give the direct answer first.
2. Then explain.
3. Then give important exam points.
4. Use examples when useful.

FOR UPLOADED FILES:

• Treat uploaded study material as the primary source.
• Use File Search when available.
• Do not pretend something came from the file if it did not.
• If the requested information is not found,
  clearly say that.

FOR ENGINEERING:

• Prefer structured explanations.
• Use formulas when necessary.
• Show calculation steps for numerical problems.
• For programming questions, give clean code.
• Explain code briefly after the code.

Keep responses comfortable to read on a mobile phone.
"""


# ============================================================
# 📚 FILE SEARCH CHAT
# ============================================================

def ask_files(question):

    store_name = get_store()

    prompt = (
        build_system_prompt()
        + "\n\nStudent question:\n"
        + question
    )

    kwargs = {
        "model": MODEL,
        "input": prompt,

        "generation_config": {
            "thinking_level": THINKING_LEVEL,
        },

        "tools": [
            {
                "type": "file_search",
                "file_search_store_names": [
                    store_name
                ],
            }
        ],
    }

    # Continue previous conversation when available.
    if st.session_state.interaction_id:

        kwargs[
            "previous_interaction_id"
        ] = st.session_state.interaction_id

    interaction = client.interactions.create(
        **kwargs
    )

    st.session_state.interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# 💬 NORMAL CHAT
# ============================================================

def ask_normal_chat(question):

    kwargs = {
        "model": MODEL,

        "input": (
            build_system_prompt()
            + "\n\nStudent question:\n"
            + question
        ),

        "generation_config": {
            "thinking_level": THINKING_LEVEL,
        },
    }

    if st.session_state.interaction_id:

        kwargs[
            "previous_interaction_id"
        ] = st.session_state.interaction_id

    interaction = client.interactions.create(
        **kwargs
    )

    st.session_state.interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# 🌐 GOOGLE SEARCH CHAT
# ============================================================

def ask_web(question):

    kwargs = {
        "model": MODEL,

        "input": (
            build_system_prompt()
            + """

This request requires current information.

Use Google Search and provide a concise,
accurate answer.

Student question:
"""
            + question
        ),

        "generation_config": {
            "thinking_level": THINKING_LEVEL,
        },

        "tools": [
            {
                "type": "google_search"
            }
        ],
    }

    if st.session_state.interaction_id:

        kwargs[
            "previous_interaction_id"
        ] = st.session_state.interaction_id

    interaction = client.interactions.create(
        **kwargs
    )

    st.session_state.interaction_id = (
        interaction.id
    )

    return interaction.output_text


# ============================================================
# 🖼️ PHOTO AI
# ============================================================

def analyze_photo(uploaded_image, question):

    image_bytes = uploaded_image.getvalue()

    import base64

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    mime_type = uploaded_image.type

    prompt = f"""
You are Ultra Sonic Super Photo AI.

Analyze the uploaded image carefully.

User request:

{question}

Rules:

• Read visible text accurately.
• Do not invent missing information.
• If it is a question, solve it.
• If it is mathematics, show steps.
• If it is engineering, explain clearly.
• If it is a diagram, identify important components.
• If it is handwritten, interpret carefully.
• Answer in Kannada + English when useful.
• Give the direct answer first.
"""

    interaction = client.interactions.create(

        model=MODEL,

        input=[
            {
                "type": "text",
                "text": prompt,
            },

            {
                "type": "image",
                "data": image_base64,
                "mime_type": mime_type,
            },
        ],

        generation_config={
            "thinking_level": THINKING_LEVEL,
        },
    )

    return interaction.output_text


# ============================================================
# 🧹 RESET CHAT
# ============================================================

def clear_chat():

    st.session_state.messages = []

    st.session_state.interaction_id = None

    st.rerun()


# ============================================================
# 📱 SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚡ Ultra Sonic")

    mode = st.radio(
        "Mode",
        [
            "💬 AI Chat",
            "📚 Study Files",
            "🖼️ Photo AI",
            "🌐 Web Search",
        ],
    )

    st.divider()

    # --------------------------------------------------------
    # FILE UPLOAD
    # --------------------------------------------------------

    st.subheader("📚 Study Library")

    uploaded_files = st.file_uploader(

        "Add PDF / documents",

        type=SUPPORTED_FILES,

        accept_multiple_files=True,
    )

    if uploaded_files:

        if st.button(
            "⚡ ADD TO STUDY LIBRARY",
            type="primary",
            use_container_width=True,
        ):

            progress = st.progress(0)

            total = len(uploaded_files)

            for index, uploaded_file in enumerate(
                uploaded_files
            ):

                filename = uploaded_file.name

                if filename in (
                    st.session_state.indexed_files
                ):

                    st.info(
                        f"⏭️ Already added: {filename}"
                    )

                else:

                    try:

                        with st.spinner(
                            f"Indexing {filename}..."
                        ):

                            index_file(
                                uploaded_file
                            )

                        st.session_state.indexed_files.append(
                            filename
                        )

                        st.session_state.file_upload_status[
                            filename
                        ] = "Ready"

                        st.success(
                            f"✅ {filename}"
                        )

                    except Exception as e:

                        st.session_state.file_upload_status[
                            filename
                        ] = "Error"

                        st.error(
                            f"❌ {filename}\n\n{e}"
                        )

                progress.progress(
                    (index + 1) / total
                )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    st.divider()

    st.subheader("📊 System Status")

    if st.session_state.store_name:

        st.success(
            "🟢 File Search ready"
        )

    else:

        st.info(
            "⚪ File Search waiting"
        )

    st.caption(
        f"📚 Files: "
        f"{len(st.session_state.indexed_files)}"
    )

    st.caption(
        f"🧠 Model: {MODEL}"
    )

    st.caption(
        f"⚡ Thinking: {THINKING_LEVEL}"
    )

    # --------------------------------------------------------
    # CONTROLS
    # --------------------------------------------------------

    st.divider()

    if st.button(
        "🧹 Clear Chat",
        use_container_width=True,
    ):

        clear_chat()


# ============================================================
# 💬 AI CHAT
# ============================================================

if mode == "💬 AI Chat":

    st.subheader(
        "💬 Ultra Sonic AI"
    )

    st.caption(
        "Fast general-purpose Kannada + English AI."
    )

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    question = st.chat_input(
        "Ask anything..."
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

        with st.chat_message("assistant"):

            with st.spinner(
                "⚡ Thinking..."
            ):

                try:

                    answer = ask_normal_chat(
                        question
                    )

                    st.markdown(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                        }
                    )

                except Exception as e:

                    st.error(
                        f"❌ Gemini error:\n\n{e}"
                    )


# ============================================================
# 📚 STUDY FILE MODE
# ============================================================

elif mode == "📚 Study Files":

    st.subheader(
        "📚 Ask Your Study Material"
    )

    if not st.session_state.store_name:

        st.info(
            "👈 Upload your PDF or study files "
            "from the sidebar first."
        )

    else:

        st.success(
            "🟢 Your study library is ready."
        )

        for message in st.session_state.messages:

            with st.chat_message(
                message["role"]
            ):

                st.markdown(
                    message["content"]
                )

        question = st.chat_input(
            "Ask something from your study material..."
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

            with st.chat_message("assistant"):

                with st.spinner(
                    "🔎 Searching your files..."
                ):

                    try:

                        answer = ask_files(
                            question
                        )

                        st.markdown(answer)

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                            }
                        )

                    except Exception as e:

                        st.error(
                            f"❌ File Search error:\n\n{e}"
                        )


# ============================================================
# 🖼️ PHOTO AI
# ============================================================

elif mode == "🖼️ Photo AI":

    st.subheader(
        "🖼️ Ultra Sonic Photo AI"
    )

    image = st.file_uploader(

        "Upload a photo",

        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],

        key="photo_ai",
    )

    question = st.text_area(

        "What should I do with this image?",

        value=(
            "Solve this question and "
            "explain it step by step."
        ),

        height=100,
    )

    if image:

        st.image(
            image,
            caption="Uploaded image",
            use_container_width=True,
        )

        if st.button(
            "⚡ ANALYZE",
            type="primary",
            use_container_width=True,
        ):

            with st.spinner(
                "⚡ Analyzing image..."
            ):

                try:

                    answer = analyze_photo(
                        image,
                        question,
                    )

                    st.markdown(
                        "### 🧠 Answer"
                    )

                    st.markdown(answer)

                except Exception as e:

                    st.error(
                        f"❌ Photo AI error:\n\n{e}"
                    )


# ============================================================
# 🌐 WEB SEARCH
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

     
