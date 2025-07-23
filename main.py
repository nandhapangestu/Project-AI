import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PyPDF2 import PdfReader
from duckduckgo_search import DDGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
import io, os

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")
openai.api_key = st.secrets["openai_api_key"]

# === CSS THEME ===
DARK_CSS = """<style> ... </style>""" # pakai CSS kamu sebelumnya
LIGHT_CSS = """<style> ... </style>"""

# === SIDEBAR ===
with st.sidebar:
    st.image("https://chat.openai.com/favicon.ico", width=30)
    st.header("Obrolan")
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "dark"
    theme_icon = "☀️ Light" if st.session_state.theme_mode == "dark" else "🌙 Dark"
    if st.button(f"Switch to {theme_icon}", key="themebtn", use_container_width=True):
        st.session_state.theme_mode = "light" if st.session_state.theme_mode == "dark" else "dark"
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = []
    if st.button("➕ New Chat", use_container_width=True):
        if st.session_state.current_chat:
            st.session_state.chat_sessions.append(st.session_state.current_chat)
        st.session_state.current_chat = []
    for i, chat in enumerate(reversed(st.session_state.chat_sessions[-8:])):
        summary = (chat[0][0][:28] + "...") if chat and chat[0][0] else f"Chat {i+1}"
        if st.button(f"🗨️ {summary}", key=f"history{i}", use_container_width=True):
            st.session_state.current_chat = chat
    st.markdown("---")
    st.caption("🧠 **AI for U Controller**\n\nv1.0 | Mirip ChatGPT")

# === CSS ===
if st.session_state.theme_mode == "dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# === HEADER ===
st.markdown("""
<div style="display:flex;align-items:center;gap:13px;">
    <span style="font-size:2.5em;">🧠</span>
    <span style="font-size:2.0em;font-weight:bold;">AI for U Controller</span>
    <div style='margin-left:auto;'>
        <form action="" method="post" enctype="multipart/form-data">
            <label for="file_uploader">
                <span style="padding:7px 12px;border-radius:12px;background:#eef2f4;border:1px solid #e2e6ea;cursor:pointer;vertical-align:middle;">
                    <svg style="width:1.2em;height:1.2em;vertical-align:middle;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                </span>
                <input id="file_uploader" name="file_uploader" type="file" style="display:none;" onchange="this.form.submit()"/>
            </label>
        </form>
    </div>
</div>
""", unsafe_allow_html=True)

# === AUTOLOAD & EXTRACT ALL PDF FROM GOOGLE DRIVE ===
def extract_all_drive_pdfs():
    creds = st.secrets["gdrive_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds, scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive_service = build("drive", "v3", credentials=credentials)
    folder_id = st.secrets["gdrive_folder_id"]

    # List all PDF files in folder
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/pdf'",
        fields="files(id, name)").execute()
    files = results.get('files', [])

    all_text = ""
    filelist = []
    for f in files:
        filelist.append(f['name'])
        request = drive_service.files().get_media(fileId=f['id'])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        try:
            reader = PdfReader(fh)
            all_text += "\n".join([p.extract_text() or "" for p in reader.pages]) + "\n"
        except Exception as e:
            all_text += f"\n[File '{f['name']}' gagal diekstrak: {e}]\n"
    return all_text, filelist

# **Cache supaya cepat**
if "drive_pdf_text" not in st.session_state or "drive_pdf_files" not in st.session_state:
    with st.spinner("Mengambil & memproses seluruh file PDF dari Google Drive..."):
        all_pdf_text, pdf_files = extract_all_drive_pdfs()
        st.session_state.drive_pdf_text = all_pdf_text
        st.session_state.drive_pdf_files = pdf_files

# === CHAT HISTORY (tanpa jam) ===
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
        .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# === INPUT BOX ===
user_input = st.chat_input("Tanyakan sesuatu…")

if user_input:
    st.chat_message("user", avatar="👤").markdown(user_input, unsafe_allow_html=True)
    answer = None
    error_msg = None

    # === 1. Cari dari semua PDF di GDrive
    chunks = [p.strip() for p in st.session_state.drive_pdf_text.split("\n") if len(p.strip()) > 30]
    try:
        tfidf = TfidfVectorizer().fit_transform([user_input] + chunks)
        sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
        best_idx = sims.argmax()
        if sims[best_idx] > 0.11:
            answer = chunks[best_idx]
    except Exception as e:
        error_msg = f"PDF Search Error: {e}"

    # === 2. Web Search Fallback
    if not answer:
        try:
            with DDGS() as ddgs:
                result = next(ddgs.text(user_input), None)
                if result:
                    answer = result['body']
        except Exception as e:
            error_msg = f"Web Search Error: {e}"

    # === 3. Fallback ke OpenAI (SYNTAX openai>=1.0.0)
    if not answer:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_input}]
            )
            answer = response.choices[0].message.content
        except Exception as e:
            error_msg = f"OpenAI Error: {e}"

    if answer:
        st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    else:
        st.chat_message("assistant", avatar="🤖").markdown(
            f"❌ Maaf, terjadi kesalahan saat mencari informasi. {error_msg if error_msg else ''}",
            unsafe_allow_html=True
        )
    st.session_state.current_chat.append((user_input, "", "", "user"))
    st.session_state.current_chat.append(("", answer if answer else f"❌ Maaf, terjadi kesalahan saat mencari informasi. {error_msg if error_msg else ''}", "", "assistant"))
