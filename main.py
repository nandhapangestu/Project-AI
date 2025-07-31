import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd
import docx
from transformers import pipeline
import fitz  # PyMuPDF
import easyocr
from PIL import Image
import numpy as np
import io

# === CACHING MODELS ===
@st.cache_resource
def load_qa_model():
    return pipeline("question-answering", model="deepset/roberta-base-squad2")

@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en', 'id'], gpu=False)

qa_model = load_qa_model()
summarizer = load_summarizer()
ocr_reader = load_ocr_reader()

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")

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

# === MAIN HEADER ===
st.markdown("<h1>🧠 AI for U Controller</h1>", unsafe_allow_html=True)
st.subheader("Upload PDF, Word, Excel")

# === FILE UPLOADER ===
uploaded_files = st.file_uploader("Drag and drop files here", type=["pdf", "docx", "doc", "xlsx", "xls"], accept_multiple_files=True)

# === INIT STATE ===
if "all_text_chunks" not in st.session_state:
    st.session_state.all_text_chunks = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []
if "summary_doc" not in st.session_state:
    st.session_state.summary_doc = ""

# === PARSE FILES ===
if uploaded_files:
    all_chunks = []
    summary_source = []
    file_names = []
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext = name.split(".")[-1].lower()
        text_chunks = []
        try:
            if ext == "pdf":
                pdf_bytes = uploaded_file.read()
                with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                    for page in doc:
                        text = page.get_text()
                        if not text.strip():
                            pix = page.get_pixmap(dpi=200)
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            result = ocr_reader.readtext(np.array(img), detail=0)
                            text = " ".join(result)
                        text_chunks.append(text)
                uploaded_file.seek(0)
            elif ext in ["xlsx", "xls"]:
                excel = pd.ExcelFile(uploaded_file)
                for sheet in excel.sheet_names:
                    df = excel.parse(sheet)
                    text_chunks += [str(row) for row in df.astype(str).values.tolist()]
            elif ext in ["docx", "doc"]:
                doc = docx.Document(uploaded_file)
                text_chunks = [para.text for para in doc.paragraphs if para.text.strip()]
            file_names.append(name)
            all_chunks.extend([(name, chunk) for chunk in text_chunks if len(chunk.strip()) > 10])
            summary_source.extend(text_chunks)
        except Exception as e:
            st.warning(f"Gagal membaca {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    if summary_source:
        try:
            full_text = "\n".join(summary_source)[:4000]
            result = summarizer(full_text, max_length=180, min_length=30, do_sample=False)
            st.session_state.summary_doc = result[0]["summary_text"]
            st.success("✅ Rangkuman berhasil dibuat")
        except Exception as e:
            st.warning("⚠️ Gagal membuat ringkasan otomatis.")
    st.success("File berhasil dibaca: " + ", ".join(file_names))

# === TAMPILKAN CHAT HISTORY ===
for q, a in st.session_state.current_chat:
    st.chat_message("user").markdown(q)
    st.chat_message("assistant").markdown(a)

# === INPUT BOX ===
user_input = st.chat_input("Tanyakan sesuatu…")

# === JAWABAN ===
if user_input:
    st.chat_message("user").markdown(user_input)
    answer = None
    chunks = st.session_state.all_text_chunks
    best = {"score": 0.0, "answer": "", "file": ""}
    if chunks:
        for fname, context in chunks:
            try:
                result = qa_model(question=user_input, context=context)
                if result["score"] > best["score"]:
                    best = {"score": result["score"], "answer": result["answer"], "file": fname}
            except:
                continue
        if best["score"] > 0.3:
            answer = f"**Jawaban dari file `{best['file']}`:**\n\n{best['answer']}"
        elif st.session_state.summary_doc:
            answer = f"🔎 Tidak ditemukan jawaban spesifik.\n\nBerikut ringkasan dokumen:\n\n{st.session_state.summary_doc}"
        else:
            answer = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."
    else:
        answer = "Silakan upload file terlebih dahulu."

    st.chat_message("assistant").markdown(answer)
    st.session_state.current_chat.append((user_input, answer))
