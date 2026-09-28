import streamlit as st
import os
from dotenv import load_dotenv
from src.pdf_loader import load_and_split
from src.vector_store import create_vector_store
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

load_dotenv()

st.set_page_config(page_title="Kannada RAG Study Buddy", page_icon="📚")
st.title("📚 Kannada RAG Study Buddy")
st.write("Upload your VTU PDF, ask in Kannada / English")

uploaded_file = st.file_uploader("Upload PDF notes", type="pdf")

if uploaded_file:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    with st.spinner("Reading your notes..."):
        chunks = load_and_split("temp.pdf")
        db = create_vector_store(chunks)
        
        prompt_template = """You are a helpful study buddy for Karnataka students.
        Answer ONLY from the context below. If user asks in Kannada, answer in simple Kannada. If English, answer in simple English.
        If not found, say 'Ivvu nimma notes nalli illa' / 'Not in your notes.'
        
        Context: {context}
        Question: {question}
        Answer:"""
        
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=db.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": PROMPT}
        )
        st.session_state['qa'] = qa
    st.success("Ready! Ask your question below.")

question = st.text_input("Nimma prashne keli / Ask your question:")
if question and 'qa' in st.session_state:
    with st.spinner("Thinking..."):
        answer = st.session_state['qa'].run(question)
        st.write("**Answer:**")
        st.write(answer)
