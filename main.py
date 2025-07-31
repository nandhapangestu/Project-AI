import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd
import docx
from transformers import pipeline
from pdf2image import convert_from_bytes
from PIL import Image
import requests
from io import BytesIO

# === OCR via OCR.Space API ===
def ocr_space_image(image_bytes, api_key='helloworld'):
    response = requests.post(
        'https://api.ocr.space/parse/image',
        files={'filename': image_bytes},
        data={'apikey': api_key, 'language': 'eng'},
    )
    result = response.json()
    if result.get('IsErroredOnProcessing', True):
        return ""
    return result['ParsedResults'][0]['ParsedText']

# === QA MODEL ===
@st.cache_resource
def load_qa_model():
    return pipeline("question-answering", model="deepset/roberta-base-squad2")

qa_model = load_qa_model()

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")

# === THEME CSS ===
DARK_CSS = """<style>.stApp{background:#23272f!important;color:#e8e9ee;}[data-testid="stSidebar"]>div:first-child{background:#17181c;}...</style>"""
LIGHT_CSS = """<style>.stApp{background:#f7f8fa!important;color:#222;}[data-testid="stSidebar"]>div:first-child{background:#fff;}...</style>"""

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
    st.caption("🧠 **AI for U Controller**\n\nCopyright 2025 by Management Report & Budget Control")

# === CSS ===
st.markdown(DARK_CSS if st.session_state.theme_mode == "dark" else LIGHT_CSS, unsafe_allow_html=True)

# === MAIN HEADER ===
st.markdown("""
<div style="display:flex;align-items:center;gap:13px;">
    <span style="font-size:2.5em;">🧠</span>
    <span style="font-size:2.0em;font-weight:bold;">AI for U Controller</span>
</div>
""", unsafe_allow_html=True)

# === FILE UPLOAD ===
uploaded_files = st.file_uploader(
    "Upload PDF, Excel, atau Word", 
    type=['pdf', 'xlsx', 'xls', 'docx', 'doc'],
    label_visibility="collapsed",
    accept_multiple_files=True
)

if "all_text_chunks" not in st.session_state:
    st.session_state.all_text_chunks = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []

if uploaded_files:
    all_chunks, file_names = [], []
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext = name.split(".")[-1].lower()
        text_chunks = []
        try:
            if ext == "pdf":
                reader = PdfReader(uploaded_file)
                text_chunks = [p.extract_text() or "" for p in reader.pages]
                if not any(text_chunks):
                    uploaded_file.seek(0)
                    images = convert_from_bytes(uploaded_file.read())
                    for img in images:
                        buf = BytesIO()
                        img.save(buf, format="JPEG")
                        buf.seek(0)
                        text = ocr_space_image(buf.read())
                        if text.strip():
                            text_chunks.append(text)
            elif ext in ["xlsx", "xls"]:
                excel = pd.ExcelFile(uploaded_file)
                for sheet in excel.sheet_names:
                    df = excel.parse(sheet)
                    text_chunks += [str(row) for row in df.astype(str).values.tolist()]
            elif ext in ["docx", "doc"]:
                doc_file = docx.Document(uploaded_file)
                text_chunks = [para.text for para in doc_file.paragraphs if para.text.strip()]
            all_chunks.extend([(name, t) for t in text_chunks if len(t.strip()) > 10])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal baca file {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil dibaca: " + ", ".join(file_names))

# === CHAT HISTORY ===
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
        .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# === INPUT & QA ===
user_input = st.chat_input("Tanyakan sesuatu…")
if user_input:
    st.chat_message("user", avatar="👤").markdown(user_input, unsafe_allow_html=True)
    best_answer = {"answer": "", "score": 0.0, "file": ""}
    for fname, context in st.session_state.all_text_chunks:
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

    st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    st.session_state.current_chat.append((user_input, "", "", "user"))
    st.session_state.current_chat.append(("", answer, "", "assistant"))
