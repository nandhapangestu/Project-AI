import streamlit as st
import os
import io
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI

# Setup UI ChatGPT-like
st.set_page_config(page_title="AI for U Controller", layout="wide")
st.markdown("""
<style>
    .chat-message { border-radius: 12px; padding: 10px; margin: 10px 0; line-height: 1.5; }
    .chat-message.user { background-color: #dcf8c6; text-align: right; }
    .chat-message.bot { background-color: #f1f0f0; text-align: left; }
</style>
""", unsafe_allow_html=True)
st.title("🧠 AI for U Controller")

# Load secrets
drive_creds = st.secrets["gdrive_service_account"]
folder_id = st.secrets["GDRIVE_FOLDER_ID"]
openai_key = st.secrets["OPENAI_API_KEY"]

# Setup Google Drive API
credentials = service_account.Credentials.from_service_account_info(
    drive_creds, scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=credentials)

@st.cache_data(show_spinner=False)
def list_files(folder_id):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType)"
    ).execute()
    return results.get("files", [])

@st.cache_resource(show_spinner=True)
def build_vectorstore(files):
    docs = []
    for f in files:
        request = drive_service.files().get_media(fileId=f["id"])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)

        suffix = ".pdf" if "pdf" in f["mimeType"] else ".docx" if "word" in f["mimeType"] else ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(fh.read())
            path = tmp.name

        loader = PyPDFLoader(path) if suffix == ".pdf" else Docx2txtLoader(path) if suffix == ".docx" else TextLoader(path)
        docs.extend(loader.load())

    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
    return FAISS.from_documents(chunks, embeddings)

# UI
files = list_files(folder_id)
filenames = [f["name"] for f in files]
selected = st.multiselect("📂 Pilih file dari Google Drive:", filenames)

if selected:
    selected_files = [f for f in files if f["name"] in selected]
    with st.spinner("🔍 Memuat dan memproses dokumen..."):
        vectorstore = build_vectorstore(selected_files)
        qa_chain = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(openai_api_key=openai_key),
            chain_type="stuff",
            retriever=vectorstore.as_retriever()
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "bot"
        st.markdown(f'<div class="chat-message {role}">{msg["content"]}</div>', unsafe_allow_html=True)

    if prompt := st.chat_input("💬 Tanyakan sesuatu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("✍️ Menjawab..."):
            response = qa_chain.run(prompt)
        st.session_state.messages.append({"role": "bot", "content": response})
        st.markdown(f'<div class="chat-message bot">{response}</div>', unsafe_allow_html=True)
else:
    st.info("👈 Pilih file dari Google Drive untuk memulai.")
