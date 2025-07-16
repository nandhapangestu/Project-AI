import os
import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.document_loaders import GoogleDriveLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ======================= CONFIGURATION ==========================
st.set_page_config(page_title="AI for U Controller", layout="wide")
st.markdown("""
    <style>
        body {
            background-color: #f0f2f6;
        }
        .block-container {
            padding: 2rem 3rem;
        }
        .stTextInput>div>div>input {
            font-size: 1.1rem;
        }
        .stChatMessage.user {
            background-color: #e8f0fe;
        }
        .stChatMessage.assistant {
            background-color: #f1f3f4;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h1 style='font-family:Segoe UI; font-weight:600;'>📁 AI for U Controller</h1>
""", unsafe_allow_html=True)

# ======================= LOAD SECRETS ===========================
SERVICE_ACCOUNT_JSON = st.secrets["gdrive_service_account"]
FOLDER_ID = st.secrets["GDRIVE_FOLDER_ID"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_JSON,
    scopes=["https://www.googleapis.com/auth/drive"]
)

def load_documents(folder_id):
    loader = GoogleDriveLoader(
        folder_id=folder_id,
        credentials=credentials,
        file_types=["pdf", "docx", "pptx", "txt"],
        recursive=True
    )
    return loader.load()

def load_and_index_files():
    docs = load_documents(FOLDER_ID)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = splitter.split_documents(docs)
    embeddings = OpenAIEmbeddings()
    vectordb = FAISS.from_documents(split_docs, embeddings)
    return vectordb

# ======================= LOAD VECTORSTORE =======================
@st.cache_resource
def get_qa_chain():
    vectordb = load_and_index_files()
    retriever = vectordb.as_retriever()
    qa = RetrievalQA.from_chain_type(llm=ChatOpenAI(), retriever=retriever)
    return qa

qa_chain = get_qa_chain()

# ======================= UI LAYOUT ==============================
with st.sidebar:
    st.markdown("### Pilih file dari Google Drive:")
    st.info("Semua file dalam folder Drive akan diindeks otomatis.")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ajukan pertanyaan berdasarkan dokumen Google Drive...")

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        response = qa_chain.run(prompt)
        st.chat_message("assistant").markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
    except Exception as e:
        st.chat_message("assistant").markdown(f"**Terjadi error:** {str(e)}")