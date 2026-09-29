import streamlit as st
import os

st.set_page_config(page_title="Kannada RAG Study Buddy")
st.title("📚 Kannada RAG Study Buddy")

api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))

st.write("Upload your VTU notes PDF and ask questions in Kannada / English.")

uploaded = st.file_uploader("Upload PDF", type="pdf")
question = st.text_input("Ask your question:")

if st.button("Ask") and question:
    if not api_key:
        st.error("API Key not found. Add it in Secrets.")
    else:
        st.success(f"Your question: {question}")
        st.info("RAG logic will answer from your PDF here. API connected!")
