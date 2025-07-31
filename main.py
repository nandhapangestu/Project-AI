import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd
import docx
import re
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

st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# === MAIN HEADER ===
st.markdown("""
<div style="display:flex;align-items:center;gap:13px;">
    <span style="font-size:2.5em;">🧠</span>
    <span style="font-size:2.0em;font-weight:bold;">AI for U Controller</span>
</div>
""", unsafe_allow_html=True)

# === UPLOAD FILES ===
uploaded_files = st.file_uploader(
    "Upload PDF, Excel, atau Word (PDF, XLSX, DOCX, DOC, max 200MB per file)", 
    type=['pdf', 'xlsx', 'xls', 'docx', 'doc'],
    label_visibility="collapsed",
    accept_multiple_files=True
)

if "full_context" not in st.session_state:
    st.session_state.full_context = ""

if uploaded_files:
    texts = []
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext = name.split(".")[-1].lower()
        try:
            if ext == "pdf":
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        texts.append(page.extract_text() or "")
            elif ext in ["xlsx", "xls"]:
                excel = pd.ExcelFile(uploaded_file)
                for sheet in excel.sheet_names:
                    df = excel.parse(sheet)
                    texts += [str(row) for row in df.astype(str).values.tolist()]
            elif ext in ["docx", "doc"]:
                doc = docx.Document(uploaded_file)
                texts = [para.text for para in doc.paragraphs if para.text.strip()]
        except Exception as e:
            st.warning(f"Gagal baca file {name}: {e}")
    st.session_state.full_context = "\n".join(texts)
    st.success("File berhasil dibaca.")

# === TAMPILKAN CHAT HISTORY ===
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖")         .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# === INPUT BOX ===
user_input = st.chat_input("Tanyakan sesuatu…")

# === JAWABAN ===
if user_input:
    question = user_input
    st.chat_message("user", avatar="👤").markdown(question, unsafe_allow_html=True)
    answer = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."
    ctx = st.session_state.full_context

    if ctx.strip():
        try:
            result = qa_model(question=question, context=ctx)
            if result["score"] > 0.35:
                answer = f"**Jawaban:** {result['answer']}"
            else:
                # fallback regex pattern
                if "lng" in question.lower():
                    match = re.search(r"LNG.*?(\d[\d\.]+)", ctx, re.IGNORECASE)
                    if match:
                        answer = f"**Perkiraan jawaban berdasarkan pencarian langsung:** {match.group(1)}"
        except Exception as e:
            answer = f"Gagal menjawab: {e}"

    st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    st.session_state.current_chat.append((question, "", "", "user"))
    st.session_state.current_chat.append(("", answer, "", "assistant"))
