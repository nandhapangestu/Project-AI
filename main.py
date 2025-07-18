import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
from bs4 import BeautifulSoup
import json
import os

# ==============================
# Konfigurasi Dasar
# ==============================
st.set_page_config(page_title="AI for U Controller", layout="wide")
st.markdown("""
    <style>
    .block-container {padding-top: 2rem;}
    .stTextInput > div > div > input {border-radius: 10px; padding: 10px;}
    .stButton>button {border-radius: 10px; background-color: #10a37f; color: white;}
    </style>
""", unsafe_allow_html=True)

# ==============================
# Sidebar (New Chat & Riwayat)
# ==============================
with st.sidebar:
    st.header("\U0001F4D1 Obrolan")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if st.button("+ New Chat"):
        st.session_state.chat_history = []
    for i, (q, a) in enumerate(st.session_state.chat_history[::-1]):
        st.markdown(f"**Q{i+1}:** {q}\n\n*A: {a}*")

# ==============================
# Upload GDrive kanan atas
# ==============================
uploaded_file = st.file_uploader("\U0001F4E5 Upload file ke GDrive Shared", type=None)
if uploaded_file:
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gdrive_service_account"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive_service = build("drive", "v3", credentials=credentials)
    folder_id = st.secrets["gdrive_folder_id"]

    media = MediaFileUpload(uploaded_file.name, resumable=True)
    file_metadata = {"name": uploaded_file.name, "parents": [folder_id]}
    drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    os.remove(uploaded_file.name)
    st.success("File berhasil diupload ke GDrive.")

# ==============================
# Kolom Chat Utama
# ==============================
st.title("\U0001F9E0 AI for U Controller")
st.write("Silakan masukkan pertanyaan Anda:")

question = st.text_input("", placeholder="Tanyakan sesuatu…")

# Fungsi Web Scraping ICP
@st.cache_data(show_spinner=False)
def get_icp_info():
    url = "https://migas.esdm.go.id/post/harga-minyak-mentah"
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        result = soup.find("div", class_="entry-content")
        return result.text.strip()[:1000] if result else "Informasi ICP tidak ditemukan."
    except:
        return "Gagal mengambil data ICP dari website."

# Fungsi Web Scraping Kurs BI
@st.cache_data(show_spinner=False)
def get_kurs_info():
    url = "https://www.bi.go.id/id/statistik/informasi-kurs/transaksi-bi/default.aspx"
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")
        return table.text.strip()[:1000] if table else "Data kurs tidak tersedia."
    except:
        return "Gagal mengambil data kurs dari website."

# Fungsi Jawaban Chat
def jawab(question):
    lower = question.lower()
    if any(k in lower for k in ["harga minyak", "icp", "crude price"]):
        return get_icp_info()
    elif any(k in lower for k in ["kurs", "exchange", "nilai tukar", "usd", "rupiah"]):
        return get_kurs_info()
    elif any(k in lower for k in ["upload", "laporan", "drive"]):
        return "Silakan upload dokumen via kanan atas. File akan disimpan di GDrive bersama."
    else:
        return "Mungkin saya bisa menambahkan informasi jika informasi tersebut dimasukan ke dalam cloud Gdrive dan Hubungi Admin Fungsi Controller (MRBC)."

# Proses Pertanyaan
if question:
    answer = jawab(question)
    st.session_state.chat_history.append((question, answer))
    st.chat_message("user").markdown(question)
    st.chat_message("assistant").markdown(answer)

# ==============================
# Contoh Pertanyaan (Glosari)
# ==============================
st.markdown("""
<hr>
<h4>Contoh pertanyaan:</h4>
<ul>
    <li>Berapa harga ICP bulan lalu?</li>
    <li>Apa kurs USD hari ini?</li>
    <li>Upload laporan PIS terbaru</li>
    <li>Nilai tukar Rupiah sekarang?</li>
    <li>ICP Maret 2024 berapa?</li>
</ul>
""", unsafe_allow_html=True)
