
import streamlit as st
import os
import requests
from PyPDF2 import PdfReader
import pandas as pd
import docx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")

DARK_CSS = """<style>
.stApp {background: #23272f !important; color: #e8e9ee;}
[data-testid="stSidebar"] > div:first-child {background: #17181c;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #3a3b43; color: #fff;}
.stChatMessage.assistant {background: #353946; color: #aee8c7;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #23272f; color: #eee;}
.stButton>button, .stButton>button:active {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu, footer {visibility: hidden;}
</style>"""
LIGHT_CSS = """<style>
.stApp {background: #f7f8fa !important; color: #222;}
[data-testid="stSidebar"] > div:first-child {background: #fff;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #f1f3f5; color: #222;}
.stChatMessage.assistant {background: #eaf8f1; color: #007860;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #fff; color: #222;}
.stButton>button, .stButton>button:active {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu, footer {visibility: hidden;}
</style>"""

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

uploaded_files = st.file_uploader(
    "Upload PDF, Excel, atau Word (PDF, XLSX, DOCX, DOC, max 200MB per file)",
    type=['pdf', 'xlsx', 'xls', 'docx', 'doc'],
    label_visibility="collapsed",
    accept_multiple_files=True
)
if "all_text_chunks" not in st.session_state:
    st.session_state.all_text_chunks = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []

if uploaded_files:
    all_chunks = []
    file_names = []
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext = name.split(".")[-1].lower()
        text_chunks = []
        try:
            if ext == "pdf":
                reader = PdfReader(uploaded_file)
                text_chunks = [p.extract_text() or "" for p in reader.pages]
            elif ext in ["xlsx", "xls"]:
                excel = pd.ExcelFile(uploaded_file)
                for sheet in excel.sheet_names:
                    df = excel.parse(sheet)
                    text_chunks += [str(row) for row in df.astype(str).values.tolist()]
            elif ext in ["docx", "doc"]:
                doc = docx.Document(uploaded_file)
                text_chunks = [para.text for para in doc.paragraphs if para.text.strip()]
            all_chunks.extend([(name, chunk) for chunk in text_chunks if len(chunk.strip()) > 10])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal baca file {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil dibaca: " + ", ".join(file_names))

for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖")         .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

user_input = st.chat_input("Tanyakan sesuatu…")

if user_input:
    question = user_input
    st.chat_message("user", avatar="👤").markdown(question, unsafe_allow_html=True)
    answer = None
    chunks = st.session_state.all_text_chunks if "all_text_chunks" in st.session_state else []

    if chunks:
        teks_sumber = [chunk[1] for chunk in chunks]
        sumber_file = [chunk[0] for chunk in chunks]
        try:
            tfidf = TfidfVectorizer().fit_transform([question] + teks_sumber)
            sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
            best_idx = sims.argmax()
            if sims[best_idx] > 0.11:
                best_file = sumber_file[best_idx]
                answer = f"**[Dari file: {best_file}]**\n\n{teks_sumber[best_idx]}"
            else:
                answer = None
        except Exception as e:
            answer = f"File Search Error: {e}"

    if answer is None:
        try:
            headers = {
                "Authorization": f"Bearer {st.secrets['HUGGINGFACE_API_KEY']}"
            }
            payload = {
                "inputs": question,
                "parameters": {"temperature": 0.7, "max_new_tokens": 300}
            }
            response = requests.post(
                "https://api-inference.huggingface.co/models/google/flan-t5-base",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            answer = result[0]["generated_text"].replace(question, "").strip()
        except Exception as e:
            answer = f"Gagal memanggil model: {e}"

    st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    st.session_state.current_chat.append((question, "", "", "user"))
    st.session_state.current_chat.append(("", answer, "", "assistant"))
