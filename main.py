import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PyPDF2 import PdfReader
from duckduckgo_search import DDGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")
openai.api_key = st.secrets["openai_api_key"]

# === CSS STYLING CHATGPT-LIKE ===
st.markdown("""
<style>
/* Sidebar */
[data-testid="stSidebar"] {
    background: #f7f8fa !important;
    border-right: 1.5px solid #ededed;
    min-width: 260px;
    max-width: 310px;
}
.st-emotion-cache-18ni7ap {background: #f7f8fa !important;}
/* Sidebar logo + button */
.sidebar-header {display:flex;align-items:center;gap:13px;padding:20px 0 5px 12px;}
.sidebar-logo {width:36px;}
.stButton>button, .stButton>button:active {
    border-radius: 8px;
    background: #ececf1;
    color: #202123;
    font-weight: 500;
    margin-bottom: 8px;
}
.stButton>button:hover {background: #d9e2fa; color: #156ef2;}
/* Chat bubble */
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #f3f3f3;}
.stChatMessage.assistant {background: #e9f5ef;}
/* Chat input + upload bar */
.stChatInputContainer {display:flex;align-items:center;gap:10px;}
.stTextInput>div>div>input, .stTextInput input {
    border-radius: 24px !important; 
    padding: 18px !important; 
    background: #fff; 
    color: #222;
    font-size: 1.07em;
    border: 1.7px solid #ececf1 !important;
}
.upload-btn {
    border: none; 
    background: #ececf1;
    border-radius: 999px;
    padding: 9px 13px;
    font-size: 1.45em;
    margin-left: -54px; 
    cursor: pointer;
    position: absolute; right: 80px; top: 6px;
}
.upload-btn:hover {background: #e0e7fd;}
/* Prompt row under input */
.quick-prompts-row {
    display:flex;gap:20px;margin:10px 0 14px 0;justify-content:center;
}
.quick-btn {
    padding:10px 22px;
    background:#ececf1;
    border:none;
    border-radius:12px;
    font-size:1em;
    color:#202123;
    font-weight:500;
    cursor:pointer;
    transition:.18s;
}
.quick-btn:hover {background:#d9e2fa;color:#156ef2;}
/* Hide upload label */
label[for^=uploader] {font-size: 0;}
/* Hide default menu/footer */
#MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
with st.sidebar:
    st.markdown(
        '<div class="sidebar-header">'
        '<img src="https://chat.openai.com/favicon.ico" class="sidebar-logo">'
        '<span style="font-size:1.2em;font-weight:bold;letter-spacing:-.7px;">AI for U Controller</span>'
        '</div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin-top:3px;margin-bottom:12px;border:.8px solid #ececf1;border-radius:2px;">', unsafe_allow_html=True)
    if st.button("+ New Chat", use_container_width=True):
        if "current_chat" in st.session_state and st.session_state.current_chat:
            if "chat_sessions" not in st.session_state:
                st.session_state.chat_sessions = []
            st.session_state.chat_sessions.append(st.session_state.current_chat)
        st.session_state.current_chat = []

    # Riwayat (versi simple)
    st.markdown('<div style="margin-bottom:5px;font-weight:600;color:#6e6e80;font-size:0.93em;">Chats</div>', unsafe_allow_html=True)
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = []

    for i, chat in enumerate(reversed(st.session_state.chat_sessions[-8:])):
        summary = (chat[0][0][:30] + "...") if chat and chat[0][0] else f"Chat {i+1}"
        if st.button(f"💬 {summary}", key=f"history{i}", use_container_width=True):
            st.session_state.current_chat = chat

    st.markdown("---")
    # Theme Switcher
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"
    theme_icon = "🌙 Dark" if st.session_state.theme_mode == "light" else "☀️ Light"
    if st.button(f"Switch to {theme_icon}", key="themebtn2", use_container_width=True):
        st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"

    st.caption("v1.0 | Mirip ChatGPT")

# === CHAT WINDOW HEADER ===
st.markdown(
    '<div style="display:flex;align-items:center;gap:15px;padding:20px 0 4px 0;">'
    '<span style="font-size:2.2em;">🧠</span>'
    '<span style="font-size:2.0em;font-weight:800;">AI for U Controller</span>'
    '</div>',
    unsafe_allow_html=True
)

# === TAMPILKAN CHAT HISTORY ===
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
        .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# === CHAT INPUT + ATTACH BUTTON ===
chat_col = st.container()
with chat_col:
    # Row input + tombol attachment upload
    c1, c2 = st.columns([12, 1])
    with c1:
        user_input = st.chat_input("Tanyakan sesuatu…")
    with c2:
        # Tombol upload bentuk +
        uploaded_file = st.file_uploader("", type=['pdf'], key="uploader2", label_visibility="collapsed")
        st.markdown(
            '<button class="upload-btn" title="Upload file PDF" onclick="document.getElementById(\'uploader2\').click()">+</button>',
            unsafe_allow_html=True
        )

# === Handle Upload ===
if uploaded_file:
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    creds = st.secrets["gdrive_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds, scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive_service = build("drive", "v3", credentials=credentials)
    folder_id = st.secrets["gdrive_folder_id"]
    media = MediaFileUpload(uploaded_file.name, resumable=True)
    file_metadata = {"name": uploaded_file.name, "parents": [folder_id]}
    try:
        result = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_url = f"https://drive.google.com/file/d/{result['id']}/view"
        os.remove(uploaded_file.name)
        st.success(f"✅ File berhasil diupload: [Lihat File]({file_url})")
        reader = PdfReader(uploaded_file)
        text = "\n".join([p.extract_text() or "" for p in reader.pages])
        st.session_state.doc_text = text
        st.session_state.last_uploaded_name = uploaded_file.name
    except Exception as e:
        st.error(f"❌ Upload gagal: {str(e)}")

# === QUICK PROMPT BUTTONS (Horizontal di bawah chat input) ===
st.markdown('<div class="quick-prompts-row">', unsafe_allow_html=True)
if st.button("Berapa harga ICP bulan lalu?", key="icpbtnq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Berapa harga ICP bulan lalu?"
if st.button("Apa kurs USD hari ini?", key="usdq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Apa kurs USD hari ini?"
if st.button("Upload laporan PIS terbaru", key="uploadpisq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Upload laporan PIS terbaru"
if st.button("Nilai tukar Rupiah sekarang?", key="rupiahq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Nilai tukar Rupiah sekarang?"
st.markdown('</div>', unsafe_allow_html=True)

# === Logic prompt tombol & input ===
if "prompt_pre" in st.session_state and st.session_state["prompt_pre"]:
    question = st.session_state["prompt_pre"]
    st.session_state["prompt_pre"] = ""
elif user_input:
    question = user_input
else:
    question = None

if question:
    st.chat_message("user", avatar="👤").markdown(question, unsafe_allow_html=True)
    answer = None
    error_msg = None

    # === 1. PDF Search (TF-IDF)
    if "doc_text" in st.session_state:
        chunks = [p.strip() for p in st.session_state.doc_text.split("\n") if len(p.strip()) > 30]
        try:
            tfidf = TfidfVectorizer().fit_transform([question] + chunks)
            sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
            best_idx = sims.argmax()
            if sims[best_idx] > 0.11:
                answer = chunks[best_idx]
        except Exception as e:
            error_msg = f"PDF Search Error: {e}"

    # === 2. Web Search Fallback
    if not answer:
        try:
            with DDGS() as ddgs:
                result = next(ddgs.text(question), None)
                if result:
                    answer = result['body']
        except Exception as e:
            error_msg = f"Web Search Error: {e}"

    # === 3. Fallback ke OpenAI
    if not answer:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}]
            )
            answer = response.choices[0].message.content
        except Exception as e:
            error_msg = f"OpenAI Error: {e}"

    if answer:
        st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    else:
        st.chat_message("assistant", avatar="🤖").markdown(
            f"❌ Maaf, terjadi kesalahan saat mencari informasi. {error_msg if error_msg else ''}",
            unsafe_allow_html=True
        )
    st.session_state.current_chat.append((question, "", "", "user"))
    st.session_state.current_chat.append(("", answer if answer else f"❌ Maaf, terjadi kesalahan saat mencari informasi. {error_msg if error_msg else ''}", "", "assistant"))
