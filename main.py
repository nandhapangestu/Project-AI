
import streamlit as st
from PyPDF2 import PdfReader
import pdfplumber
import pandas as pd
import docx
from transformers import pipeline

# === MODEL QA ===
@st.cache_resource
def load_model():
    return pipeline("question-answering", model="deepset/roberta-base-squad2")
qa_model = load_model()

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide")

# === SIDEBAR ===
with st.sidebar:
    st.image("static/Logo_Pertamina_PIS.png", width=130)
    st.header("Obrolan")
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"
    if st.button("Switch to 🌙 Dark" if st.session_state.theme_mode == "light" else "☀️ Light"):
        st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"
    if st.button("➕ New Chat"):
        st.session_state.current_chat = []
    st.caption("🧠 AI for U Controller\n\nCopyright 2025")

# === UPLOAD FILE ===
uploaded_files = st.file_uploader("Upload PDF, Word, Excel", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)

if "doc_chunks" not in st.session_state:
    st.session_state.doc_chunks = []
if "current_chat" not in st.session_state:
    st.session_state.current_chat = []

# === EKSTRAKSI ===
def extract_all_text(uploaded_file):
    name = uploaded_file.name
    ext = name.split(".")[-1].lower()
    contents = []
    try:
        if ext == "pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text()
                    tables = page.extract_tables()
                    if txt: contents.append(txt)
                    for table in tables:
                        for row in table:
                            if row and any(cell for cell in row):
                                contents.append(" : ".join([str(c) for c in row]))
        elif ext == "docx":
            doc = docx.Document(uploaded_file)
            contents = [para.text for para in doc.paragraphs if para.text.strip()]
        elif ext == "xlsx":
            xls = pd.ExcelFile(uploaded_file)
            for sheet in xls.sheet_names:
                df = xls.parse(sheet)
                for row in df.astype(str).values.tolist():
                    contents.append(" : ".join(row))
    except Exception as e:
        st.warning(f"Gagal membaca {name}: {e}")
    return [(name, chunk) for chunk in contents if len(chunk.strip()) > 10]

if uploaded_files:
    all_chunks = []
    for file in uploaded_files:
        chunks = extract_all_text(file)
        all_chunks.extend(chunks)
    st.session_state.doc_chunks = all_chunks
    st.success("File berhasil dibaca: " + ", ".join([f.name for f in uploaded_files]))

# === RIWAYAT CHAT ===
for q, a in st.session_state.current_chat:
    st.chat_message("user").markdown(q)
    st.chat_message("assistant").markdown(a)

# === INPUT ===
question = st.chat_input("Tanyakan sesuatu…")
if question:
    st.chat_message("user").markdown(question)
    best = {"answer": "", "score": 0.0, "source": ""}
    full_context = "\n".join([x[1] for x in st.session_state.doc_chunks])
    # QA Model
    try:
        for fname, context in st.session_state.doc_chunks:
            result = qa_model(question=question, context=context)
            if result["score"] > best["score"]:
                best.update({"answer": result["answer"], "score": result["score"], "source": fname})
    except:
        pass
    # Fallback Keyword Search
    if best["score"] < 0.3:
        for fname, chunk in st.session_state.doc_chunks:
            if question.lower() in chunk.lower():
                best["answer"] = chunk
                best["source"] = fname
                break
        if not best["answer"]:
            best["answer"] = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."

    jawaban = f"**Dari file: {best['source']}**\n\n{best['answer']}"
    st.chat_message("assistant").markdown(jawaban)
    st.session_state.current_chat.append((question, jawaban))
