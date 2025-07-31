
import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd
import docx
from transformers import pipeline
import pdfplumber

# === QA MODEL ===
@st.cache_resource
def load_qa_model():
    return pipeline("question-answering", model="deepset/roberta-base-squad2")

qa_model = load_qa_model()

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")

# === THEME CSS ===
DARK_CSS = """
<style>
.stApp {background: #23272f !important; color: #e8e9ee;}
[data-testid="stSidebar"] > div:first-child {background: #17181c;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #3a3b43; color: #fff;}
.stChatMessage.assistant {background: #353946; color: #aee8c7;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #23272f; color: #eee;}
.stButton>button, .stButton>button:active {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu, footer {visibility: hidden;}
</style>
"""

LIGHT_CSS = """
<style>
.stApp {background: #f7f8fa !important; color: #222;}
[data-testid="stSidebar"] > div:first-child {background: #fff;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #f1f3f5; color: #222;}
.stChatMessage.assistant {background: #eaf8f1; color: #007860;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #fff; color: #222;}
.stButton>button, .stButton>button:active {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu, footer {visibility: hidden;}
</style>
"""

# === SIDEBAR ===
with st.sidebar:
    st.image("static/Logo_Pertamina_PIS.png", width=130)
    st.header("Obrolan")

    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"
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
    st.caption("🧠 **AI for U Controller**

Copyright 2025 by Management Report & Budget Control")

# === CSS ===
st.markdown(DARK_CSS if st.session_state.theme_mode == "dark" else LIGHT_CSS, unsafe_allow_html=True)

# === HEADER ===
st.markdown("### 🧠 AI for U Controller")

# === UPLOAD FILES ===
uploaded_files = st.file_uploader("Upload PDF, Word, Excel", type=["pdf", "docx", "xlsx", "xls"], accept_multiple_files=True)

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
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        txt = page.extract_text()
                        if txt:
                            text_chunks.append(txt)
            elif ext in ["docx"]:
                doc = docx.Document(uploaded_file)
                text_chunks = [p.text for p in doc.paragraphs if p.text.strip()]
            elif ext in ["xlsx", "xls"]:
                xls = pd.ExcelFile(uploaded_file)
                for sheet in xls.sheet_names:
                    df = xls.parse(sheet)
                    text_chunks += df.astype(str).fillna("").apply(lambda x: " ".join(x), axis=1).tolist()
            all_chunks.extend([(name, c) for c in text_chunks if len(c.strip()) > 10])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal memproses {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil dibaca: " + ", ".join(file_names))

# === RIWAYAT CHAT ===
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖")         .markdown(q if utype == "user" else a, unsafe_allow_html=True)

# === INPUT ===
user_input = st.chat_input("Tanyakan sesuatu…")

# === QA ===
if user_input:
    st.chat_message("user", avatar="👤").markdown(user_input)
    chunks = st.session_state.all_text_chunks if "all_text_chunks" in st.session_state else []
    answer = None

    if chunks:
        best_answer = {"answer": "", "score": 0.0, "file": ""}
        fallback_found = None
        for fname, context in chunks:
            try:
                result = qa_model(question=user_input, context=context)
                if result["score"] > best_answer["score"]:
                    best_answer = {"answer": result["answer"], "score": result["score"], "file": fname}
                if user_input.lower() in context.lower() and not fallback_found:
                    fallback_found = (fname, context)
            except:
                pass

        if best_answer["score"] > 0.3:
            answer = f"**(Dari file: {best_answer['file']})**

{best_answer['answer']}"
        elif fallback_found:
            answer = f"**(Ditemukan konteks dari file: {fallback_found[0]})**

{fallback_found[1][:500]}..."
        else:
            answer = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."
    else:
        answer = "Silakan upload file terlebih dahulu."

    st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    st.session_state.current_chat.append((user_input, "", "", "user"))
    st.session_state.current_chat.append(("", answer, "", "assistant"))
