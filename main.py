
import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd
import docx
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# === HUGGINGFACE LLM ===
def generate_response(prompt):
    headers = {
        "Authorization": f"Bearer {st.secrets['HUGGINGFACE_API_KEY']}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.7,
            "do_sample": True
        }
    }
    response = requests.post(
        "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta",
        headers=headers,
        json=payload
    )
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        return f"Gagal memanggil model: {response.status_code} – {response.text}"

# === STREAMLIT CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide")
st.title("🧠 AI for U Controller")

# === SESSION STATE ===
if "all_text_chunks" not in st.session_state:
    st.session_state.all_text_chunks = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# === FILE UPLOAD ===
uploaded_files = st.file_uploader(
    "Upload file PDF, Excel, atau Word:",
    type=["pdf", "xlsx", "xls", "docx", "doc"],
    accept_multiple_files=True
)

if uploaded_files:
    all_chunks = []
    file_names = []
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        ext = name.split(".")[-1].lower()
        text_chunks = []
        try:
            if ext == "pdf":
                reader = PdfReader(uploaded_file)
                text_chunks = [p.extract_text() or "" for p in reader.pages]
            elif ext in ["xlsx", "xls"]:
                excel = pd.ExcelFile(uploaded_file)
                for sheet in excel.sheet_names:
                    df = excel.parse(sheet)
                    text_chunks += [str(row) for row in df.astype(str).values.tolist()]
            elif ext in ["docx", "doc"]:
                doc = docx.Document(uploaded_file)
                text_chunks = [para.text for para in doc.paragraphs if para.text.strip()]
            all_chunks.extend([(name, chunk) for chunk in text_chunks if len(chunk.strip()) > 10])
            file_names.append(name)
        except Exception as e:
            st.warning(f"Gagal membaca file {name}: {e}")
    st.session_state.all_text_chunks = all_chunks
    st.session_state.file_names = file_names
    st.success("File berhasil diupload dan dibaca: " + ", ".join(file_names))

# === TAMPILKAN HISTORI CHAT ===
for item in st.session_state.chat_history:
    st.chat_message(item["role"]).write(item["content"])

# === INPUT USER ===
user_input = st.chat_input("Tanyakan sesuatu…")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    chunks = st.session_state.all_text_chunks
    answer = ""

    if chunks:
        teks_sumber = [chunk[1] for chunk in chunks]
        sumber_file = [chunk[0] for chunk in chunks]
        try:
            tfidf = TfidfVectorizer().fit_transform([user_input] + teks_sumber)
            sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
            best_idx = sims.argmax()
            if sims[best_idx] > 0.11:
                best_file = sumber_file[best_idx]
                answer = f"**[Dari file: {best_file}]**\n\n{teks_sumber[best_idx]}"
            else:
                answer = "Maaf, jawaban tidak ditemukan pada file yang diupload."
        except Exception as e:
            answer = f"Terjadi kesalahan saat pencarian di file: {e}"
    else:
        answer = generate_response(user_input)

    st.chat_message("assistant").write(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
