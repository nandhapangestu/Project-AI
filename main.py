import streamlit as st
import json
import os
import tempfile
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="AI for U Controller", page_icon="📁")
st.markdown("""
    <style>
        .block-container {
            padding: 2rem 2rem 2rem 2rem;
        }
        .stApp {
            background-color: #f8f8f8;
            font-family: 'Segoe UI', sans-serif;
        }
        .css-18e3th9 {
            padding: 1rem;
        }
        h1, h2, h3, h4, h5 {
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📁 AI for U Controller")
st.write("Pilih file dari Google Drive:")

gdrive_api_key = st.secrets["GDRIVE_API_KEY"]
gdrive_folder_id = st.secrets["GDRIVE_FOLDER_ID"]
google_docs_service_account = dict(st.secrets["gdrive_service_account"])
openai_api_key = st.secrets["OPENAI_API_KEY"]

os.environ["OPENAI_API_KEY"] = openai_api_key

# Setup Google Drive API service
credentials = service_account.Credentials.from_service_account_info(google_docs_service_account)
drive_service = build("drive", "v3", credentials=credentials)

def list_pdfs_from_drive(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def download_file(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = tempfile.NamedTemporaryFile(delete=False)
    downloader = build("drive", "v3", credentials=credentials).files().get_media(fileId=file_id)
    file = drive_service.files().get(fileId=file_id).execute()
    request = drive_service.files().get_media(fileId=file_id)
    with open(fh.name, 'wb') as f:
        downloader = drive_service.files().get_media(fileId=file_id)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            f.write(status.data)
    return fh.name

def load_and_index_files(files):
    documents = []
    for file in files:
        loader = PyPDFLoader(file)
        documents.extend(loader.load())
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings()
    return FAISS.from_documents(texts, embeddings)

files = list_pdfs_from_drive(gdrive_folder_id)

file_options = {file["name"]: file["id"] for file in files}
selected_files = st.multiselect("", options=list(file_options.keys()))

if selected_files:
    with st.spinner("Memuat dan memproses file..."):
        downloaded_paths = [download_file(file_options[name]) for name in selected_files]
        vectorstore = load_and_index_files(downloaded_paths)
        retriever = vectorstore.as_retriever()
        qa_chain = RetrievalQA.from_chain_type(llm=ChatOpenAI(), retriever=retriever)

    user_question = st.text_input("Ajukan pertanyaan berdasarkan file yang dipilih:")

    if user_question:
        with st.spinner("Sedang menjawab..."):
            response = qa_chain.run(user_question)
            st.success(response)