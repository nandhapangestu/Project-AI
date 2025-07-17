import streamlit as st
import json
import os
import pandas as pd
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from bs4 import BeautifulSoup

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="AI for U Controller", page_icon="🧠", layout="wide")
st.markdown("""
    <style>
        .block-container {
            padding: 2rem;
        }
        .stChatInput input {
            border-radius: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# ========== HEADER ==========
st.markdown("## 🧠 AI for U Controller")
st.write("Silakan masukkan pertanyaan Anda:")

# ========== LOAD SERVICE ACCOUNT ==========
SERVICE_ACCOUNT_JSON = st.secrets["gdrive_service_account"]
credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_JSON,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=credentials)

# ========== DEFINE DATA SOURCES ==========
ICP_URL = "https://migas.esdm.go.id/post/harga-minyak-mentah"
KURS_URL = "https://www.bi.go.id/id/statistik/informasi-kurs/transaksi-bi/default.aspx"
GDRIVE_FOLDER_ID = "1hkN3DA67cpUKiQaR23BUXc3-k_mVb5wr"

# ========== LOAD FILES FROM GDRIVE ==========
def list_files_in_folder(service, folder_id):
    results = service.files().list(q=f"'{folder_id}' in parents and trashed = false",
                                   fields="files(id, name, mimeType)").execute()
    return results.get("files", [])

def get_icp_info():
    response = requests.get(ICP_URL)
    soup = BeautifulSoup(response.content, "html.parser")
    content = soup.find("div", class_="blog-post").text
    return content.strip()

def get_kurs_info():
    response = requests.get(KURS_URL)
    soup = BeautifulSoup(response.content, "html.parser")
    kurs_table = soup.find("table")
    return kurs_table.text if kurs_table else "Informasi kurs tidak ditemukan."

def handle_query(query):
    query = query.lower()
    if "icp" in query or "harga minyak" in query:
        return get_icp_info()
    elif "kurs" in query or "rupiah" in query:
        return get_kurs_info()
    elif "file" in query or "data" in query:
        files = list_files_in_folder(drive_service, GDRIVE_FOLDER_ID)
        if not files:
            return "Tidak ditemukan file di Google Drive."
        return "\n".join([f"- {f['name']}" for f in files])
    else:
        return "Mungkin saya bisa menambahkan informasi jika informasi tersebut dimasukan ke dalam cloud Gdrive dan Hubungi Admin Fungsi Controller (MRBC)."

# ========== USER CHAT INTERFACE ==========
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

if user_input := st.chat_input("Tanyakan sesuatu..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").markdown(user_input)

    response = handle_query(user_input)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("assistant").markdown(response)
