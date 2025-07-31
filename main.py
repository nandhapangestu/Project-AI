import streamlit as st
import pandas as pd
import docx
import pdfplumber
from PyPDF2 import PdfReader
from transformers import pipeline
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

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
.stApp {background-color: #f7f8fa;}
.stChatMessage {padding: 0.8em; margin-bottom: 1em; border-radius: 10px;}
.stChatMessage.user {background-color: #eaeaea;}
.stChatMessage.assistant {background-color: #dff6eb;}
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
with st.sidebar:
    st.image("static/Logo_Pertamina_PIS.png", width=130)
    st.header("Obrolan")
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"
    st.button("Switch to 🌙 Dark" if st.session_state.theme_mode == "light" else "Switch to ☀️ Light")
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = []
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_sessions.append(st.session_state.current_chat)
        st.session_state.current_chat = []
    for i, chat in enumerate(reversed(st.session_state.chat_sessions[-5:])):
        if st.button(f"🗨️ Chat {i+1}"):
            st.session_state.current_chat = chat
    st.caption("**AI for U Controller**\n\nCopyright 2025 by MRBC")

# === UPLOAD FILES ===
uploaded_files = st.file_uploader(
    "Upload PDF, Word, Excel", type=['pdf', 'docx', 'doc', 'xlsx', 'xls'], accept_multiple_files=True)

if "all_text_chunks" not in st.session_state:
    st.session_state.all_text_chunks = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []

# === TEXT EXTRACTION ===
def extract_text_with_fallback(file):
    texts = []
    try:
        with pdfplumber.open(file) as pdf:
            texts = [page.extract_text() for page in pdf.pages if page.extract_text()]
        if texts:
            return texts
    except:
        pass
    try:
        images = convert_from_bytes(file.read(), dpi=300)
        return [pytesseract.image_to_string(img) for img in images]
    except:
        return []

if uploaded_files:
    all_chunks = []
    file_names = []
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext = name.split(".")[-1].lower()
        text_chunks = []
        try:
            if ext == "pdf":
                text_chunks = extract_text_with_fallback(uploaded_file)
            elif ext in ["docx", "doc"]:
                doc = docx.Document(uploaded_file)
                text_chunks = [para.text for para in doc.paragraphs if para.text.strip()]
            elif ext in ["xlsx", "xls"]:
                excel = pd.ExcelFile(uploaded_file)
                for sheet in excel.sheet_names:
                    df = excel.parse(sheet)
                    text_chunks += [str(row) for row in df.astype(str).values.tolist()]
            all_chunks.extend([(name, chunk) for chunk in text_chunks if len(chunk.strip()) > 10])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal baca file {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil dibaca: " + ", ".join(file_names))

# === COMBINE TEXT CHUNKS ===
chunks = st.session_state.all_text_chunks
combined_chunks = []
buffer = ""
for i, (name, chunk) in enumerate(chunks):
    buffer += " " + chunk.strip()
    if i % 3 == 0:
        combined_chunks.append((name, buffer.strip()))
        buffer = ""
if buffer:
    combined_chunks.append((name, buffer.strip()))

# === SHOW TEXT FOR DEBUG ===
if st.checkbox("🔍 Lihat potongan teks yang diparsing"):
    for fname, txt in combined_chunks:
        st.markdown(f"**{fname}**\n\n```
{txt[:1000]}
```")

# === TAMPILKAN CHAT HISTORY ===
for q, a in st.session_state.current_chat:
    st.chat_message("user").markdown(q)
    st.chat_message("assistant").markdown(a)

# === INPUT BOX ===
user_input = st.chat_input("Tanyakan sesuatu…")

# === QA ===
if user_input:
    st.chat_message("user").markdown(user_input)
    best_answer = {"answer": "", "score": 0.0, "file": ""}
    for fname, context in combined_chunks:
        try:
            result = qa_model(question=user_input, context=context)
            if result["score"] > best_answer["score"]:
                best_answer.update({"answer": result["answer"], "score": result["score"], "file": fname})
        except:
            continue

    if best_answer["score"] > 0.3:
        answer = f"**Jawaban (dari file: {best_answer['file']})**\n\n{best_answer['answer']}"
    else:
        answer = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."

    st.chat_message("assistant").markdown(answer)
    st.session_state.current_chat.append((user_input, answer))
