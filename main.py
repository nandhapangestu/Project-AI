import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from google.oauth2 import service_account
from googleapiclient.discovery import build
import tempfile
import os
import json

# ============================
# Custom ChatGPT-Style Styling
# ============================
def set_chatgpt_style():
    st.markdown("""
        <style>
        body {
            background-color: #f8f9fa;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 800px;
            margin: auto;
        }
        .stTextInput > div > div > input {
            border-radius: 6px;
            border: 1px solid #ccc;
            padding: 10px;
        }
        .stButton>button {
            background-color: #10a37f;
            color: white;
            border-radius: 6px;
            padding: 8px 20px;
            border: none;
            font-weight: bold;
        }
        .stMarkdown {
            font-size: 16px;
        }
        </style>
    """, unsafe_allow_html=True)

set_chatgpt_style()

# ============================
# Sidebar & API Keys
# ============================
st.set_page_config(page_title="AI for U Controller")
st.title("📁 AI for U Controller")

GDRIVE_FOLDER_ID = st.secrets["GDRIVE_FOLDER_ID"]
GDRIVE_API_KEY = st.secrets["GDRIVE_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
SERVICE_ACCOUNT_JSON = json.loads(st.secrets["gdrive_service_account"])

# ============================
# Google Drive Client Setup
# ============================
credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_JSON,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=credentials)

def list_pdfs(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def download_file(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        downloader = build("drive", "v3", credentials=credentials).files().get_media(fileId=file_id)
        fh = open(tmp_file.name, 'wb')
        downloader = drive_service._http.request("GET", f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media")
        fh.write(downloader[1])
        fh.close()
        return tmp_file.name

# ============================
# Load and Index PDF
# ============================
def load_and_index(file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = splitter.split_documents(documents)
    vectorstore = FAISS.from_documents(split_docs, OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY))
    return vectorstore

# ============================
# App Flow
# ============================
files = list_pdfs(GDRIVE_FOLDER_ID)
file_names = [f["name"] for f in files]

selected_name = st.selectbox("Pilih file dari Google Drive:", [""] + file_names)

if selected_name:
    file_id = next((f["id"] for f in files if f["name"] == selected_name), None)
    file_path = download_file(file_id)
    vectorstore = load_and_index(file_path)

    st.markdown("---")
    st.subheader("Tanya Jawab 🔍")

    user_question = st.text_input("Ajukan pertanyaan berdasarkan isi PDF")
    if user_question:
        qa_chain = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(openai_api_key=OPENAI_API_KEY, temperature=0),
            chain_type="stuff",
            retriever=vectorstore.as_retriever()
        )
        result = qa_chain.run(user_question)
        st.markdown(f"**Jawaban:** {result}")