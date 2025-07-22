import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PyPDF2 import PdfReader
from duckduckgo_search import DDGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
import os

# === CONFIG & THEME ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")
openai.api_key = st.secrets["openai_api_key"]

# Dark theme (comment if want light)
st.markdown("""
<style>
.stApp {background: #23272f !important; color: #e8e9ee;}
[data-testid="stSidebar"] > div:first-child {background: #17181c;}
.st-emotion-cache-13ln4jf, .css-1544g2n {background: #23272f !important;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #3a3b43; color: #fff;}
.stChatMessage.assistant {background: #353946; color: #aee8c7;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #23272f; color: #eee;}
.stButton>button {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# === SIDEBAR (Chat History) ===
with st.sidebar:
    st.image("https://chat.openai.com/favicon.ico", width=30)
    st.header("Obrolan")
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = []
    if st.button("➕ New Chat", use_container_width=True):
        if st.session_state.current_chat:
            st.session_state.chat_sessions.append(st.session_state.current_chat)
        st.session_state.current_chat = []
        st.experimental_rerun()
    for i, chat in enumerate(reversed(st.session_state.chat_sessions[-8:])):
        t = chat[0][2] if chat and len(chat[0]) > 2 else ""
        summary = (chat[0][0][:28] + "...") if chat and chat[0][0] else f"Chat {i+1}"
        if st.button(f"🗨️ {summary} {t}", key=f"history{i}", use_container_width=True):
            st.session_state.current_chat = chat
            st.experimental_rerun()
    st.markdown("---")
    st.caption("🧠 **AI for U Controller**\n\nv1.0 | Mirip ChatGPT")

# === MAIN HEADER ===
st.markdown("""
<div style="display:flex;align-items:center;gap:13px;">
    <span style="font-size:2.5em;">🧠</span>
    <span style="font-size:2.0em;font-weight:bold;">AI for U Controller</span>
</div>
""", unsafe_allow_html=True)

# === UPLOAD PDF ===
uploaded_file = st.file_uploader("Upload file ke Drive Shared (PDF saja, max 200MB)", type=['pdf'], label_visibility="collapsed")
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
        # Ekstrak teks PDF
        reader = PdfReader(uploaded_file)
        text = "\n".join([p.extract_text() or "" for p in reader.pages])
        st.session_state.doc_text = text
        st.session_state.last_uploaded_name = uploaded_file.name
    except Exception as e:
        st.error(f"❌ Upload gagal: {str(e)}")

# === TAMPILKAN CHAT HISTORY (BUBBLE) ===
for q, a, t, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
        .markdown(f"{q if utype=='user' else a}\n<div style='font-size:11px;color:#888;text-align:right'>{t}</div>", unsafe_allow_html=True)

# === QUICK PROMPT BUTTONS ===
col1, col2, col3, col4 = st.columns(4)
if col1.button("Berapa harga ICP bulan lalu?"):
    st.session_state["prompt_pre"] = "Berapa harga ICP bulan lalu?"
    st.experimental_rerun()
if col2.button("Apa kurs USD hari ini?"):
    st.session_state["prompt_pre"] = "Apa kurs USD hari ini?"
    st.experimental_rerun()
if col3.button("Upload laporan PIS terbaru"):
    st.session_state["prompt_pre"] = "Upload laporan PIS terbaru"
    st.experimental_rerun()
if col4.button("Nilai tukar Rupiah sekarang?"):
    st.session_state["prompt_pre"] = "Nilai tukar Rupiah sekarang?"
    st.experimental_rerun()

# === INPUT CHAT ===
if "prompt_pre" in st.session_state:
    question = st.session_state.pop("prompt_pre")
else:
    question = st.chat_input("Tanyakan sesuatu…")

if question:
    now = datetime.now().strftime("%H:%M")
    st.chat_message("user", avatar="👤").markdown(f"{question}\n<div style='font-size:11px;color:#888;text-align:right'>{now}</div>", unsafe_allow_html=True)
    answer = None

    # === 1. PDF Search (TF-IDF)
    if "doc_text" in st.session_state:
        chunks = [p.strip() for p in st.session_state.doc_text.split("\n") if len(p.strip()) > 30]
        try:
            tfidf = TfidfVectorizer().fit_transform([question] + chunks)
            sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
            best_idx = sims.argmax()
            if sims[best_idx] > 0.11:
                answer = chunks[best_idx]
        except:
            pass

    # === 2. Web Search Fallback
    if not answer:
        try:
            with DDGS() as ddgs:
                result = next(ddgs.text(question), None)
                if result:
                    answer = result['body']
        except:
            pass

    # === 3. Fallback ke OpenAI
    if not answer:
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}]
            )
            answer = completion.choices[0].message.content
        except:
            answer = "❌ Maaf, terjadi kesalahan saat mencari informasi."

    st.chat_message("assistant", avatar="🤖").markdown(f"{answer}\n<div style='font-size:11px;color:#bbb;text-align:right'>{now}</div>", unsafe_allow_html=True)
    st.session_state.current_chat.append((question, "", now, "user"))
    st.session_state.current_chat.append(("", answer, now, "assistant"))
    st.experimental_rerun()
