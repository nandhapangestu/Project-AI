import streamlit as st
import os
import json
import tempfile
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI

# Setup halaman
st.set_page_config(page_title="AI for U Controller", layout="wide")
st.title("📁 AI for U Controller")

# Load secrets
drive_config = json.loads(st.secrets["gdrive_service_account"])
folder_id = st.secrets["GDRIVE_FOLDER_ID"]
openai_api_key = st.secrets["OPENAI_API_KEY"]

# Setup Google Drive API
credentials = service_account.Credentials.from_service_account_info(drive_config)
drive_service = build("drive", "v3", credentials=credentials)

@st.cache_data(show_spinner=False)
def list_drive_files(folder_id):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType)"
    ).execute()
    return results.get("files", [])

# 🔧 Nonaktifkan cache sementara untuk debugging
# @st.cache_resource(show_spinner=True)
def load_and_index_files(files):
    docs = []
    for file in files:
        request = drive_service.files().get_media(fileId=file["id"])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)

        suffix = ".pdf" if "pdf" in file["mimeType"] else ".docx" if "word" in file["mimeType"] else ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(fh.read())
            path = tmp.name

        try:
            if suffix == ".pdf":
                loader = PyPDFLoader(path)
            elif suffix == ".docx":
                loader = Docx2txtLoader(path)
            else:
                loader = TextLoader(path)
            docs.extend(loader.load())
        except Exception as e:
            st.error(f"Gagal memuat file: {file['name']}. Error: {e}")

    if not docs:
        st.warning("Tidak ada dokumen yang berhasil dimuat.")
        return None

    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    return vectorstore

# Tampilkan daftar file
drive_files = list_drive_files(folder_id)
filenames = [f["name"] for f in drive_files]
selected_files = st.multiselect("Pilih file dari Google Drive:", filenames)

if selected_files:
    selected = [f for f in drive_files if f["name"] in selected_files]
    with st.spinner("📚 Memuat & mengindeks dokumen..."):
        vectorstore = load_and_index_files(selected)
        if vectorstore:
            qa_chain = RetrievalQA.from_chain_type(
                llm=ChatOpenAI(temperature=0, openai_api_key=openai_api_key),
                chain
