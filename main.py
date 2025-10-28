
# (Isi seluruh main.py dari bagian sebelumnya digabung menjadi satu)
# Karena terlalu panjang untuk satu cell, akan digabung dan disimpan sebagai file

import streamlit as st
import os
import pandas as pd
import docx
import pdfplumber
import re
import traceback
import easyocr
import io
import difflib
from transformers import pipeline

@st.cache_resource
def load_model():
    try:
        return pipeline("question-answering", model="deepset/roberta-base-squad2")
    except Exception as e:
        st.error("Gagal load model HuggingFace.")
        st.stop()

qa_model = load_model()
reader = easyocr.Reader(['en'], gpu=False)

FAQ_STATIC = {
    "apa itu pis": "PIS (Pertamina International Shipping) adalah subholding dari PT Pertamina (Persero) yang bergerak di bidang integrated marine logistics. [Sumber: PIS Annual Report 2024, hlm. 6]",
    "siapa pemilik pis": "PIS dimiliki oleh PT Pertamina (Persero). [Sumber: hlm. 6]",
    "apa visi pis": "Visi: Menjadi Asia's Leading Integrated Marine Logistics Company. [Sumber: hlm. 15]",
    "apa misi pis": "Misi: Solusi logistik energi yang aman dan berkelanjutan. [Sumber: hlm. 15]",
    "berapa pendapatan pis tahun 2024": "USD 3,48 miliar. [Sumber: hlm. 11]",
    "berapa pendapatan pis tahun 2023": "USD 3,43 miliar. [Sumber: hlm. 11]",
    "berapa laba pis tahun 2024": "USD 558,6 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 11]",
    "berapa laba pis tahun 2023": "USD 329,9 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 11]",
    "berapa laba pis tahun 2022": "USD 205,0 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 11]",
    "berapa laba pis tahun 2021": "USD 126,2 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 11]",
    "berapa laba pis tahun 2020": "USD 108,3 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 11]",
    "berapa ebitda pis tahun 2024": "USD 875,7 juta. [Sumber: hlm. 11]",
    "berapa ebitda pis tahun 2023": "USD 739,4 juta. [Sumber: hlm. 11]",
    "berapa laba kotor pis tahun 2024": "USD 923,2 juta. [Sumber: hlm. 11]",
    "berapa total aset pis tahun 2024": "USD 8,23 miliar. [Sumber: hlm. 11]",
    "berapa total liabilitas pis tahun 2024": "USD 4,18 miliar. [Sumber: hlm. 11]",
    "berapa total ekuitas pis tahun 2024": "USD 4,05 miliar. [Sumber: hlm. 11]",
    "berapa jumlah kapal pis": "97 kapal (VLCC, tanker gas, dll). [Sumber: hlm. 12]",
    "apa saja lini bisnis pis": "Shipping, marine services, integrated logistics. [Sumber: hlm. 14]",
    "apa komitmen pis terhadap lingkungan": "Dekarbonisasi, green shipping, ISO 14001. [Sumber: hlm. 20]",
    "apakah pis ekspansi global": "Ya, ekspansi ke Singapura & Dubai. [Sumber: hlm. 12]",
    "apa proyek digital pis": "SmartShip, Fleet Management, Port Monitoring. [Sumber: hlm. 23]"
}

python
Copy code
FAQ_STATIC = {
    "apa itu pis": "PIS (Pertamina International Shipping) adalah subholding dari PT Pertamina (Persero) yang bergerak di bidang integrated marine logistics. [Sumber: PIS Annual Report 2024, hlm. 6]",
    "siapa pemilik pis": "PIS dimiliki oleh PT Pertamina (Persero). [Sumber: hlm. 6]",
    "apa visi pis": "Visi: Menjadi Asia's Leading Integrated Marine Logistics Company. [Sumber: hlm. 15]",
    "apa misi pis": "Misi: Solusi logistik energi yang aman dan berkelanjutan. [Sumber: hlm. 15]",
    "berapa pendapatan pis tahun 2024": "USD 3,48 miliar. [Sumber: hlm. 16]",
    "berapa pendapatan pis tahun 2023": "USD 3,43 miliar. [Sumber: hlm. 16]",
    "berapa laba pis tahun 2024": "USD 558,6 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 16]",
    "berapa laba pis tahun 2023": "USD 329,9 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 16]",
    "berapa laba pis tahun 2022": "USD 205,0 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 16]",
    "berapa laba pis tahun 2021": "USD 126,2 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 16]",
    "berapa laba pis tahun 2020": "USD 108,3 juta (laba tahun berjalan / NPAT). [Sumber: hlm. 16]",
    "berapa ebitda pis tahun 2024": "USD 875,7 juta. [Sumber: hlm. 16]",
    "berapa ebitda pis tahun 2023": "USD 739,4 juta. [Sumber: hlm. 16]",
    "berapa laba kotor pis tahun 2024": "USD 923,2 juta. [Sumber: hlm. 16]",
    "berapa total aset pis tahun 2024": "USD 8,23 miliar. [Sumber: hlm. 16]",
    "berapa total liabilitas pis tahun 2024": "USD 4,18 miliar. [Sumber: hlm. 16]",
    "berapa total ekuitas pis tahun 2024": "USD 4,05 miliar. [Sumber: hlm. 16]",
    "berapa jumlah kapal pis": "97 kapal (VLCC, tanker gas, dll). [Sumber: hlm. 12]",
    "apa saja lini bisnis pis": "Shipping, marine services, integrated logistics. [Sumber: hlm. 14]",
    "apa komitmen pis terhadap lingkungan": "Dekarbonisasi, green shipping, ISO 14001. [Sumber: hlm. 20]",
    "apakah pis ekspansi global": "Ya, ekspansi ke Singapura & Dubai. [Sumber: hlm. 12]",
    "apa proyek digital pis": "SmartShip, Fleet Management, Port Monitoring. [Sumber: hlm. 23]"
}

st.set_page_config(page_title="AI for U Controller", layout="wide")

DARK_CSS = """<style>
.stApp {background: #23272f !important; color: #e8e9ee;}
[data-testid="stSidebar"] > div:first-child {background: #17181c;}
.stChatMessage.user {background: #3a3b43; color: #fff;}
.stChatMessage.assistant {background: #353946; color: #aee8c7;}
</style>"""

LIGHT_CSS = """<style>
.stApp {background: #f7f8fa !important; color: #222;}
[data-testid="stSidebar"] > div:first-child {background: #fff;}
.stChatMessage.user {background: #f1f3f5; color: #222;}
.stChatMessage.assistant {background: #eaf8f1; color: #007860;}
</style>"""

def main():
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = []
    if "faq_input" not in st.session_state:
        st.session_state.faq_input = ""

    with st.sidebar:
        logo_path = "static/Logo_Pertamina_PIS.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=130)
        st.header("Obrolan")
        theme_icon = "☀️ Light" if st.session_state.theme_mode == "dark" else "🌙 Dark"
        if st.button(f"Switch to {theme_icon}", use_container_width=True):
            st.session_state.theme_mode = "light" if st.session_state.theme_mode == "dark" else "dark"
        if st.button("➕ New Chat", use_container_width=True):
            if st.session_state.current_chat:
                st.session_state.chat_sessions.append(st.session_state.current_chat)
            st.session_state.current_chat = []
        st.markdown("---")
        st.caption("© 2025 MRBC")

    st.markdown(DARK_CSS if st.session_state.theme_mode == "dark" else LIGHT_CSS, unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Upload PDF, Excel, atau Word", type=["pdf", "xlsx", "xls", "docx"], label_visibility="collapsed", accept_multiple_files=True)

    if "all_text_chunks" not in st.session_state:
        st.session_state.all_text_chunks = []
    if uploaded_files:
        all_chunks = []
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
                                    img = page.to_image(resolution=300).original
                                    buf = io.BytesIO()
                                    img.save(buf, format="PNG")
                                    result = reader.readtext(buf.getvalue(), detail=0, paragraph=True)
                                    text_chunks.append("\n".join(result))
                                except: pass
                elif ext in ["xlsx", "xls"]:
                    excel = pd.ExcelFile(uploaded_file)
                    for sheet in excel.sheet_names:
                        df = excel.parse(sheet)
                        text_chunks += [str(row) for row in df.astype(str).values.tolist()]
                elif ext == "docx":
                    doc = docx.Document(uploaded_file)
                    text_chunks = [p.text for p in doc.paragraphs if p.text.strip()]
                all_chunks.extend([(name, c) for c in text_chunks if len(c.strip()) > 10])
            except Exception as e:
                st.warning(f"Gagal baca {name}: {e}")
        st.session_state.all_text_chunks = all_chunks

    for q, a, _, utype in st.session_state.current_chat:
        st.chat_message("user" if utype == "user" else "assistant").markdown(q if utype=="user" else a, unsafe_allow_html=True)

    st.markdown("#### 💬 Pertanyaan Umum tentang PIS")
    cols = st.columns(3)
    for i, q in enumerate(list(FAQ_STATIC.keys())[:6]):
        if cols[i % 3].button(q.capitalize() + " ❓", key=f"faqbtn_{i}"):
            st.session_state.faq_input = q

    user_input = st.chat_input("Tanyakan sesuatu…", key="chatbox")
    if st.session_state.faq_input and not user_input:
        user_input = st.session_state.faq_input
        st.session_state.faq_input = ""

    if user_input:
        st.chat_message("user").markdown(user_input, unsafe_allow_html=True)
        q_lower = user_input.lower()
        match = difflib.get_close_matches(q_lower, FAQ_STATIC.keys(), n=1, cutoff=0.6)
        if match:
            answer = FAQ_STATIC[match[0]]
        elif st.session_state.all_text_chunks:
            best = {"answer": "", "score": 0.0, "file": ""}
            for fname, context in st.session_state.all_text_chunks:
                try:
                    result = qa_model(question=q_lower, context=context)
                    if result["score"] > best["score"]:
                        best = {"answer": result["answer"], "score": result["score"], "file": fname}
                except: continue
            if best["score"] > 0.3:
                answer = f"**Jawaban (dari file: {best['file']})**\n\n{best['answer']}"
            else:
                answer = "Maaf, saya tidak menemukan jawaban yang relevan."
        else:
            answer = "Silakan upload file terlebih dahulu atau ajukan pertanyaan umum."
        st.chat_message("assistant").markdown(answer, unsafe_allow_html=True)
        st.session_state.current_chat.append((user_input, "", "", "user"))
        st.session_state.current_chat.append(("", answer, "", "assistant"))

try:
    main()
except Exception as e:
    st.error("Terjadi error saat menjalankan aplikasi.")
    st.text(str(e))
    st.text(traceback.format_exc())
