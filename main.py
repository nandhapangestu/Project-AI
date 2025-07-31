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

# === SIDEBAR ===
with st.sidebar:
    st.image("static/Logo_Pertamina_PIS.png", width=130)
    st.header("Obrolan")

    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"
    if st.button("Switch Theme"):
        st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"

    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = []

    if st.button("➕ New Chat"):
        if st.session_state.current_chat:
            st.session_state.chat_sessions.append(st.session_state.current_chat)
        st.session_state.current_chat = []

    st.caption("🧠 **AI for U Controller**\n\nCopyright 2025 by Management Report & Budget Control")

# === MAIN HEADER ===
st.markdown("## 🧠 AI for U Controller")
st.markdown("### Upload PDF, Word, Excel")

# === FILE UPLOADER ===
uploaded_files = st.file_uploader(
    "Drag and drop files here", type=["pdf", "docx", "doc", "xlsx", "xls"], accept_multiple_files=True
)

if "all_text_chunks" not in st.session_state:
    st.session_state.all_text_chunks = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []

if uploaded_files:
    all_chunks = []
    file_names = []
    for file in uploaded_files:
        name = file.name
        ext = name.split(".")[-1].lower()
        texts = []
        try:
            if ext == "pdf":
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        texts.append(page.extract_text() or "")
            elif ext in ["docx", "doc"]:
                d = docx.Document(file)
                texts = [para.text for para in d.paragraphs if para.text.strip()]
            elif ext in ["xlsx", "xls"]:
                xls = pd.ExcelFile(file)
                for sheet in xls.sheet_names:
                    df = xls.parse(sheet)
                    texts += [str(row) for row in df.astype(str).values.tolist()]
            elif ext == "csv":
                df = pd.read_csv(file)
                texts += [str(row) for row in df.astype(str).values.tolist()]
            all_chunks.extend([(name, t) for t in texts if t and len(t.strip()) > 10])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal membaca {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil dibaca: " + ", ".join(file_names))

# === TAMPILKAN CHAT HISTORY ===
for entry in st.session_state.current_chat:
    role, message = entry
    st.chat_message(role).markdown(message)

# === INPUT ===
user_input = st.chat_input("Tanyakan sesuatu…")

if user_input:
    st.chat_message("user").markdown(user_input)
    chunks = st.session_state.all_text_chunks
    best = {"answer": "", "score": 0.0, "file": ""}
    if chunks:
        for fname, context in chunks:
            try:
                res = qa_model(question=user_input, context=context)
                if res["score"] > best["score"]:
                    best = {"answer": res["answer"], "score": res["score"], "file": fname}
            except:
                continue
        if best["score"] > 0.3:
            response = f"**Jawaban (dari file: {best['file']})**\n\n{best['answer']}"
        else:
            response = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."
    else:
        response = "Silakan upload file terlebih dahulu."

    st.chat_message("assistant").markdown(response)
    st.session_state.current_chat.append(("user", user_input))
    st.session_state.current_chat.append(("assistant", response))
