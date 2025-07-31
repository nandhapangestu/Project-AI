import streamlit as st
import os
import pandas as pd
import docx
import pdfplumber
import re
import traceback
import easyocr
import io
from transformers import pipeline

# === Load QA Model ===
@st.cache_resource
def load_model():
    try:
        return pipeline("question-answering", model="deepset/roberta-base-squad2")
    except Exception as e:
        st.error("Gagal load model HuggingFace.")
        st.stop()

qa_model = load_model()
reader = easyocr.Reader(['en'], gpu=False)

# === Page Setup ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")

# === Theme CSS ===
DARK_CSS = """<style>
.stApp {background: #23272f !important; color: #e8e9ee;}
[data-testid="stSidebar"] > div:first-child {background: #17181c;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #3a3b43; color: #fff;}
.stChatMessage.assistant {background: #353946; color: #aee8c7;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #23272f; color: #eee;}
.stButton>button {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu, footer {visibility: hidden;}
</style>"""

LIGHT_CSS = """<style>
.stApp {background: #f7f8fa !important; color: #222;}
[data-testid="stSidebar"] > div:first-child {background: #fff;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #f1f3f5; color: #222;}
.stChatMessage.assistant {background: #eaf8f1; color: #007860;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #fff; color: #222;}
.stButton>button {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu, footer {visibility: hidden;}
</style>"""

# === Main App ===
def main():
    with st.sidebar:
        logo_path = "static/Logo_Pertamina_PIS.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=130)
        else:
            st.warning("Logo tidak ditemukan.")

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
        st.caption("🧠 AI for U Controller — © 2025 Management Report & Budget Control")

    st.markdown(DARK_CSS if st.session_state.theme_mode == "dark" else LIGHT_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;align-items:center;gap:13px;">
        <span style="font-size:2.5em;">🧠</span>
        <span style="font-size:2.0em;font-weight:bold;">AI for U Controller</span>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload PDF, Excel, atau Word (PDF, XLSX, DOCX, max 200MB)",
        type=['pdf', 'xlsx', 'xls', 'docx'],
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
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text and len(text.strip()) > 20:
                                text_chunks.append(text)
                            else:
                                try:
                                    pil_image = page.to_image(resolution=300).original
                                    img_bytes = io.BytesIO()
                                    pil_image.save(img_bytes, format="PNG")
                                    img_bytes.seek(0)
                                    result = reader.readtext(img_bytes, detail=0, paragraph=True)
                                    ocr_text = "\n".join(result)
                                    if len(ocr_text.strip()) > 10:
                                        text_chunks.append(ocr_text)
                                except Exception as ocr_error:
                                    st.warning(f"OCR gagal di halaman PDF: {ocr_error}")
                elif ext in ["xlsx", "xls"]:
                    excel = pd.ExcelFile(uploaded_file)
                    for sheet in excel.sheet_names:
                        df = excel.parse(sheet)
                        text_chunks += [str(row) for row in df.astype(str).values.tolist()]
                elif ext == "docx":
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
        st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
            .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

    user_input = st.chat_input("Tanyakan sesuatu…")

    if user_input:
        st.chat_message("user", avatar="👤").markdown(user_input, unsafe_allow_html=True)
        question = user_input
        answer = None
        chunks = st.session_state.all_text_chunks

        if chunks:
            best = {"answer": "", "score": 0.0, "file": ""}
            for fname, context in chunks:
                try:
                    result = qa_model(question=question, context=context)
                    if result["score"] > best["score"]:
                        best.update({"answer": result["answer"], "score": result["score"], "file": fname})
                except Exception:
                    continue

            if best["score"] < 0.3:
                for fname, context in chunks:
                    if question.lower() in context.lower():
                        numbers = re.findall(r"[\d\.\,]+", context)
                        if numbers:
                            best = {
                                "answer": f"Angka ditemukan: {', '.join(numbers[:3])}",
                                "score": 0.5,
                                "file": fname
                            }
                            break

            if best["score"] > 0.3:
                answer = f"**Jawaban (dari file: {best['file']})**\n\n{best['answer']}"
            else:
                answer = "Maaf, saya tidak menemukan jawaban yang relevan di dokumen."
        else:
            answer = "Silakan upload file terlebih dahulu sebelum bertanya."

        st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
        st.session_state.current_chat.append((question, "", "", "user"))
        st.session_state.current_chat.append(("", answer, "", "assistant"))

# === Jalankan dengan error handler ===
try:
    main()
except Exception as e:
    st.error("❌ Terjadi error saat menjalankan aplikasi.")
    st.text(str(e))
    st.text(traceback.format_exc())
