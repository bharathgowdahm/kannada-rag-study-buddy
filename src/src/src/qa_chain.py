from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA

def get_qa_chain(vector_db):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_db.as_retriever(search_kwargs={"k": 3}),
        chain_type_kwargs={
            "prompt": None
        }
    )
    return qa

SYSTEM_PROMPT = """You are Kannada Study Buddy. Answer ONLY from the given context.
If user asks in Kannada, reply in simple Kannada. If in English, reply in simple English.
If answer not in notes, say: 'This is not in your notes.'
Context: {context}
Question: {question}
"""
