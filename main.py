import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PyPDF2 import PdfReader
from duckduckgo_search import DDGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
import os

st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")
openai.api_key = st.secrets["openai_api_key"]

DARK_CSS = """<style> ... </style>"""  # Tempel dari script sebelumnya
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

    # Chat session/history logic
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

    st.markdown("<b>Contoh pertanyaan:</b>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Berapa harga ICP bulan lalu?", key="icpbtn", use_container_width=True):
            st.session_state["prompt_pre"] = "Berapa harga ICP bulan lalu?"
        if st.button("Upload laporan PIS terbaru", key="uploadpis", use_container_width=True):
            st.session_state["prompt_pre"] = "Upload laporan PIS terbaru"
    with c2:
        if st.button("Apa kurs USD hari ini?", key="usd", use_container_width=True):
            st.session_state["prompt_pre"] = "Apa kurs USD hari ini?"
        if st.button("Nilai tukar Rupiah sekarang?", key="rupiah", use_container_width=True):
            st.session_state["prompt_pre"] = "Nilai tukar Rupiah sekarang?"

    st.caption("🧠 **AI for U Controller**\n\nv1.0 | Mirip ChatGPT")

if st.session_state.theme_mode == "dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="display:flex;align-items:center;gap:13px;">
    <span style="font-size:2.5em;">🧠</span>
    <span style="font-size:2.0em;font-weight:bold;">AI for U Controller</span>
</div>
""", unsafe_allow_html=True)

# === TAMPILKAN CHAT HISTORY ===
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
        .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# === Input bar & tombol upload di kanan ===
input_col, upload_col = st.columns([10,1])
with input_col:
    user_input = st.chat_input("Tanyakan sesuatu…")
with upload_col:
    uploaded_file = st.file_uploader("", type=['pdf'], key="uploader2", label_visibility="collapsed")

# === Handle Upload di input box ===
if uploaded_file:
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    creds = st.secrets["gdrive_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds, scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive_service = build("drive", "v3", credentials=credentials)
    folder_id = st.secrets["gdrive_folder_id"]
    media = MediaFileUpload(uploaded_file.name, resumable=True)
    file_metadata = {"name": uploaded_file.name, "parents": [folder_id]}
    try:
        result = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_url = f"https://drive.google.com/file/d/{result['id']}/view"
        os.remove(uploaded_file.name)
        st.success(f"✅ File berhasil diupload: [Lihat File]({file_url})")
        reader = PdfReader(uploaded_file)
        text = "\n".join([p.extract_text() or "" for p in reader.pages])
        st.session_state.doc_text = text
        st.session_state.last_uploaded_name = uploaded_file.name
    except Exception as e:
        st.error(f"❌ Upload gagal: {str(e)}")

# === Logic untuk prompt tombol & input ===
if "prompt_pre" in st.session_state and st.session_state["prompt_pre"]:
    question = st.session_state["prompt_pre"]
    st.session_state["prompt_pre"] = ""
elif user_input:
    question = user_input
else:
    question = None

if question:
    st.chat_message("user", avatar="👤").markdown(question, unsafe_allow_html=True)
    answer = None
    error_msg = None

    # === 1. PDF Search (TF-IDF)
    if "doc_text" in st.session_state:
        chunks = [p.strip() for p in st.session_state.doc_text.split("\n") if len(p.strip()) > 30]
        try:
            tfidf = TfidfVectorizer().fit_transform([question] + chunks)
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
                result = next(ddgs.text(question), None)
                if result:
                    answer = result['body']
        except Exception as e:
            error_msg = f"Web Search Error: {e}"

    # === 3. Fallback ke OpenAI (SYNTAX TERBARU openai>=1.0.0)
    if not answer:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}]
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
    st.session_state.current_chat.append((question, "", "", "user"))
    st.session_state.current_chat.append(("", answer if answer else f"❌ Maaf, terjadi kesalahan saat mencari informasi. {error_msg if error_msg else ''}", "", "assistant"))
