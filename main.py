import streamlit as st
import pandas as pd
import docx
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from transformers import pipeline
from PyPDF2 import PdfReader
import pdfplumber

# === QA MODEL ===
@st.cache_resource
def load_qa_model():
    return pipeline("question-answering", model="deepset/roberta-base-squad2")

qa_model = load_qa_model()

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")

# === CSS ===
st.markdown("""
<style>
    .stChatMessage.user {background-color: #eef;}
    .stChatMessage.assistant {background-color: #efe;}
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
with st.sidebar:
    st.image("static/Logo_Pertamina_PIS.png", width=130)
    st.header("Obrolan")

    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"
    theme_icon = "☀️ Light" if st.session_state.theme_mode == "dark" else "🌙 Dark"
    if st.button(f"Switch to {theme_icon}", use_container_width=True):
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
    st.caption("🧠 **AI for U Controller**\n\nCopyright 2025 by Management Report & Budget Control")

# === UPLOAD FILE ===
st.title("AI for U Controller")
st.caption("Upload PDF, Word, Excel")

uploaded_files = st.file_uploader("Upload PDF, DOCX, XLS", type=["pdf", "docx", "xlsx", "xls"], accept_multiple_files=True)

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
                        text = page.extract_text() or ""
                        text_chunks.append(text)
                        # OCR fallback jika kosong
                        if not text.strip():
                            pil_img = page.to_image(resolution=300).original
                            ocr_text = pytesseract.image_to_string(pil_img)
                            text_chunks.append(ocr_text)
            elif ext in ["xlsx", "xls"]:
                excel = pd.ExcelFile(uploaded_file)
                for sheet in excel.sheet_names:
                    df = excel.parse(sheet)
                    text_chunks += [str(row) for row in df.astype(str).values.tolist()]
            elif ext in ["docx"]:
                doc = docx.Document(uploaded_file)
                text_chunks = [para.text for para in doc.paragraphs if para.text.strip()]
            all_chunks.extend([(name, chunk) for chunk in text_chunks if len(chunk.strip()) > 10])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal baca file {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil dibaca: " + ", ".join(file_names))

# === TAMPILKAN CHAT HISTORY ===
if "current_chat" in st.session_state:
    for chat in st.session_state.current_chat:
        if len(chat) == 4:
            q, a, _, utype = chat
            st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
                .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# === INPUT BOX ===
user_input = st.chat_input("Tanyakan sesuatu…")

if user_input:
    question = user_input
    st.chat_message("user", avatar="👤").markdown(question, unsafe_allow_html=True)
    answer = ""

    chunks = st.session_state.all_text_chunks if "all_text_chunks" in st.session_state else []
    if chunks:
        best_answer = {"answer": "", "score": 0.0, "file": ""}
        for fname, context in chunks:
            try:
                result = qa_model(question=question, context=context)
                if result['score'] > best_answer['score']:
                    best_answer.update({"answer": result['answer'], "score": result['score'], "file": fname})
            except:
                continue
        if best_answer['score'] > 0.3:
            st.markdown(
                f"""**{best_answer['file']}**

```text
{best_answer['answer']}
```"""
            )
            answer = best_answer['answer']
        else:
            answer = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."
    else:
        answer = "Silakan upload file terlebih dahulu sebelum bertanya."

    st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    st.session_state.current_chat.append((question, answer, "", "user"))
    st.session_state.current_chat.append(("", answer, "", "assistant"))
