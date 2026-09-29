import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.title("📚 Kannada RAG Study Buddy")
st.write("Upload your VTU notes PDF and ask questions in Kannada / English.")

api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

pdf_file = st.file_uploader("Upload PDF", type="pdf")

if pdf_file:
    reader = PdfReader(pdf_file)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text() or ""
    st.success(f"PDF loaded! {len(reader.pages)} pages")

    question = st.text_input("Ask your question:")
    if st.button("Ask") and question:
        with st.spinner("Thinking..."):
            prompt = f"Answer from these notes in simple Kannada/English:\n\nNotes:\n{pdf_text[:15000]}\n\nQuestion: {question}"
            response = model.generate_content(prompt)
            st.success("Answer:")
            st.write(response.text)
