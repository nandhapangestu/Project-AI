import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import json
from datetime import datetime
import base64
import requests
from duckduckgo_search import DDGS
from pypdf import PdfReader  # ✅ GANTI DARI PyPDF2 ke pypdf

# Page Config
st.set_page_config(page_title="AI for U Controller", layout="wide")

# UI Styling
st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem;}
    .stTextInput input {border-radius: 10px; padding: 10px;}
    .stButton>button {border-radius: 10px; background-color: #10a37f; color: white;}
    .css-1544g2n {padding-top: 1rem;}
    .example-button {display:inline-block;margin:0 8px 8px 0;padding:8px 16px;background:#efefef;border-radius:8px;cursor:pointer;}
    </style>
""", unsafe_allow_html=True)

# Sidebar - Chat History
with st.sidebar:
    st.header("\U0001F4D1 Obrolan")
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = []

    if st.button("New Chat"):
        if st.session_state.current_chat:
            st.session_state.chat_sessions.append(st.session_state.current_chat)
        st.session_state.current_chat = []

    for i, chat in enumerate(reversed(st.session_state.chat_sessions)):
        if st.button(f"Q{i+1}: {chat[0][0][:30]}..."):
            st.session_state.current_chat = chat

    for q, a in st.session_state.current_chat:
        st.markdown(f"**Q:** {q}\n\n*A: {a}*")

# Upload File Area (GDrive)
st.subheader("\U0001F4C2 Upload file ke Drive Shared")
uploaded_file = st.file_uploader("Upload file", type=['pdf'])
if uploaded_file:
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())

    gdrive_creds = json.loads(st.secrets["gdrive_service_account"])
    credentials = service_account.Credentials.from_service_account_info(
        gdrive_creds,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive_service = build("drive", "v3", credentials=credentials)

    folder_id = st.secrets["gdrive_folder_id"]
    media = MediaFileUpload(uploaded_file.name, resumable=True)
    file_metadata = {
        "name": uploaded_file.name,
        "parents": [folder_id]
    }
    try:
        uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_url = f"https://drive.google.com/file/d/{uploaded['id']}/view"
        os.remove(uploaded_file.name)
        st.success(f"File berhasil diupload ke GDrive: [Lihat File]({file_url})")
        # Extract text for chat
        reader = PdfReader(uploaded_file)
        content = "\n".join([page.extract_text() or "" for page in reader.pages])
        st.session_state.last_uploaded_text = content
    except Exception as e:
        st.error("Upload gagal: " + str(e))

# Chat Area
st.title("\U0001F9E0 AI for U Controller")
st.write("Silakan masukkan pertanyaan Anda:")

question = st.text_input("", placeholder="Tanyakan sesuatu…")
response = ""

# Keyword rules
icp_keywords = ["harga minyak", "ICP", "crude price"]
kurs_keywords = ["kurs", "rupiah", "exchange rate", "USD", "nilai tukar"]
ucapan_keywords = ["halo", "hai", "hi"]

if question:
    st.chat_message("user").markdown(question)
    if any(k in question.lower() for k in icp_keywords):
        response = "Informasi ICP dapat dicek di https://migas.esdm.go.id/post/harga-minyak-mentah"
    elif any(k in question.lower() for k in kurs_keywords):
        response = "Informasi kurs BI tersedia di https://www.bi.go.id/id/statistik/informasi-kurs/transaksi-bi/default.aspx"
    elif any(k in question.lower() for k in ucapan_keywords):
        response = "Halo! Apakah ada yang bisa saya bantu?"
    elif "last_uploaded_text" in st.session_state and st.session_state.last_uploaded_text:
        if question.lower() in st.session_state.last_uploaded_text.lower():
            response = f"Ditemukan dalam dokumen: {question}"
        else:
            response = "Saya telah menerima dokumen, tapi tidak menemukan jawaban langsung. Mohon pastikan kata kunci tepat."
    else:
        try:
            with DDGS() as ddgs:
                result = next(ddgs.text(question), None)
                if result:
                    response = result['body']
                else:
                    response = "Mungkin saya bisa menambahkan informasi jika informasi tersebut dimasukan ke dalam cloud Gdrive dan Hubungi Admin Fungsi Controller (MRBC)."
        except:
            response = "Maaf, terjadi kesalahan saat mencari informasi."

    st.chat_message("assistant").markdown(response)
    st.session_state.current_chat.append((question, response))

# Example prompt tools
st.markdown("""
---
<h4>Contoh pertanyaan:</h4>
<div class="example-button" onclick="window.location.href='?q=Berapa harga ICP bulan lalu?'">Berapa harga ICP bulan lalu?</div>
<div class="example-button" onclick="window.location.href='?q=Apa kurs USD hari ini?'">Apa kurs USD hari ini?</div>
<div class="example-button" onclick="window.location.href='?q=Upload laporan PIS terbaru'">Upload laporan PIS terbaru</div>
<div class="example-button" onclick="window.location.href='?q=Nilai tukar Rupiah sekarang?'">Nilai tukar Rupiah sekarang?</div>
""", unsafe_allow_html=True)
