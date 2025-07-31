import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd
import docx
import pdfplumber
from transformers import pipeline

# === QA MODEL ===
@st.cache_resource
def load_qa_model():
    return pipeline("question-answering", model="deepset/roberta-base-squad2")

qa_model = load_qa_model()

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")

# === THEME ===
DARK_CSS = """<style>
.stApp {background-color: #202124; color: #eee;}
[data-testid="stSidebar"] {background-color: #111;}
</style>"""
LIGHT_CSS = """<style>
.stApp {background-color: #fafafa; color: #111;}
[data-testid="stSidebar"] {background-color: #fff;}
</style>"""

# === SIDEBAR ===
with st.sidebar:
    st.image("static/Logo_Pertamina_PIS.png", width=150)
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

    for i, chat in enumerate(reversed(st.session_state.chat_sessions[-6:])):
        if chat:
            summary = chat[0][0][:28] + "…" if chat[0][0] else f"Chat {i+1}"
            if st.button(f"🗨️ {summary}", key=f"history{i}", use_container_width=True):
                st.session_state.current_chat = chat

    st.markdown("---")
    st.caption("🧠 **AI for U Controller**")

# === CSS THEME ===
if st.session_state.theme_mode == "dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# === MAIN HEADER ===
st.markdown("## 🧠 AI for U Controller")

# === UPLOAD FILES ===
uploaded_files = st.file_uploader(
    "Upload PDF, Word, Excel", type=['pdf', 'docx', 'xlsx', 'xls'], accept_multiple_files=True
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
                with pdfplumber.open(uploaded_file) as pdf:
                    text_chunks = [page.extract_text() for page in pdf.pages if page.extract_text()]
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(uploaded_file, sheet_name=None)
                for sheet, data in df.items():
                    text_chunks += [str(row) for row in data.astype(str).values.tolist()]
            elif ext == "docx":
                doc = docx.Document(uploaded_file)
                text_chunks = [para.text for para in doc.paragraphs if para.text.strip()]
            elif ext == "doc":
                text_chunks = ["(DOC file format not supported directly. Convert to DOCX.)"]
            all_chunks.extend([(name, chunk) for chunk in text_chunks if len(chunk.strip()) > 20])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal memproses {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil dibaca: " + ", ".join(file_names))

# === TAMPILKAN CHAT HISTORY ===
for chat in st.session_state.current_chat:
    q, a = chat
    st.chat_message("user").markdown(q)
    st.chat_message("assistant").markdown(a)

# === INPUT BOX ===
user_input = st.chat_input("Tanyakan sesuatu…")

# === Q&A HANDLER ===
if user_input:
    question = user_input
    st.chat_message("user").markdown(question)
    chunks = st.session_state.all_text_chunks

    best = {"answer": "", "score": 0.0, "file": ""}
    for fname, context in chunks:
        try:
            result = qa_model(question=question, context=context)
            if result["score"] > best["score"]:
                best = {"answer": result["answer"], "score": result["score"], "file": fname}
        except Exception:
            pass

    if best["score"] > 0.3:
        answer = f"**Dari file: {best['file']}**\n\n{best['answer']}"
    else:
        # Fallback search
        keyword_hits = [ctx for _, ctx in chunks if question.lower() in ctx.lower()]
        if keyword_hits:
            answer = "Maaf tidak bisa menjawab secara langsung. Namun saya menemukan potongan:\n\n" + keyword_hits[0][:500]
        else:
            answer = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."

    st.chat_message("assistant").markdown(answer)
    st.session_state.current_chat.append((question, answer))
