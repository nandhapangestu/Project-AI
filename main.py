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

# === CONFIG ===
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")
openai.api_key = st.secrets["openai_api_key"]

# === FULL FLAT CSS MIRIP CHATGPT ===
st.markdown("""
<style>
/* SIDEBAR */
[data-testid="stSidebar"], .st-emotion-cache-1lcbmhc {
    background: #f7f7f8 !important; 
    border-right: 1px solid #e7e7ef;
    min-width:240px;max-width:270px;
    padding-top:14px;
}
.st-emotion-cache-18ni7ap {background: #f7f7f8 !important;}
/* Logo + judul */
.sidebar-logo-row {display:flex;align-items:center;gap:13px;padding:5px 0 19px 0;}
.sidebar-logo {width:36px;}
/* New Chat Button */
.stButton>button, .stButton>button:active {
    border-radius: 8px;
    background: #ececf1;
    color: #202123;
    font-weight: 600;
    margin-bottom: 13px;
    width:100%;
    border: none;
    box-shadow:none;
}
.stButton>button:hover {background: #d9e2fa; color: #156ef2;}
/* Chat sidebar/history */
.sidebar-chats {font-size:0.97em;color:#23232a;margin-top:12px;margin-bottom:7px;}
.sidebar-chat-btn {
    display:flex;align-items:center;
    gap:8px;background:transparent;border:none;cursor:pointer;
    padding: 8px 5px 8px 3px;width:100%;
    border-radius: 6px;
    margin-bottom:2px;
    font-size:1em;
    color:#23232a;
}
.sidebar-chat-btn:hover {background:#ececf1;}
/* Theme switcher */
.theme-switch-row {margin:19px 0 7px 0;}
.theme-switch-btn {width:100%;border-radius:8px;padding:10px 0;border:none;background:#ececf1;font-weight:600;}
.theme-switch-btn:hover {background:#e7eafd;color:#1877fa;}
/* Sidebar copyright */
.sidebar-footer {margin-top:35px;font-size:.96em;color:#b1b1b9;}
/* CHAT WINDOW */
.main-wrap {padding:0 0 0 0;}
/* Chat header */
.chat-header-row {
    display:flex;align-items:center;gap:15px;
    padding:16px 0 9px 0;margin-bottom:5px;
}
.chat-header-title {
    font-size:2.15em;font-weight:800;letter-spacing:-1.3px;color:#222;
}
/* Chat bubbles */
.stChatMessage {padding: 0.7em 1em; border-radius: 1.4em; margin-bottom: 0.82em;}
.stChatMessage.user {background: #fff;}
.stChatMessage.assistant {background: #e7f6ef;}
/* Input area fixed bottom */
.st-emotion-cache-13ln4jf {
    position:fixed;bottom:0;left:270px;right:0;z-index:999;
    background:#fff;padding:16px 24% 12px 0;border-top:1.5px solid #f1f1f3;
}
@media (max-width:1100px){
    .st-emotion-cache-13ln4jf {padding-right:2vw;}
}
/* Input + upload */
.stTextInput>div>div>input, .stTextInput input {
    border-radius: 20px !important; 
    padding: 17px !important; 
    background: #fff; 
    color: #222;
    font-size: 1.08em;
    border: 1.5px solid #ececf1 !important;
}
.upload-btn-box {
    position:absolute;right:85px;top:10px;
    z-index:88;
}
.upload-btn {
    border:none;background:#ececf1;border-radius:99px;
    padding:9px 14px;font-size:1.42em;cursor:pointer;
    box-shadow:none;
}
.upload-btn:hover {background:#e0e7fd;}
label[for^=uploader] {font-size:0;}
/* Chat input box fix */
.stChatInputContainer {position:relative;}
/* Hide footer */
#MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo-row">'
        '<img src="https://chat.openai.com/favicon.ico" class="sidebar-logo">'
        '<span style="font-size:1.16em;font-weight:800;letter-spacing:-.7px;color:#23232a;">AI for U Controller</span>'
        '</div>', unsafe_allow_html=True)
    if st.button("New Chat", use_container_width=True):
        if st.session_state.get("current_chat", []):
            st.session_state.setdefault("chat_sessions", []).append(st.session_state.current_chat)
        st.session_state.current_chat = []

    st.markdown('<div class="sidebar-chats">Chats</div>', unsafe_allow_html=True)
    for i, chat in enumerate(reversed(st.session_state.get("chat_sessions", [])[-8:])):
        summary = (chat[0][0][:30] + "...") if chat and chat[0][0] else f"Chat {i+1}"
        if st.button(f"💬 {summary}", key=f"history{i}", use_container_width=True):
            st.session_state.current_chat = chat

    st.markdown('<div class="theme-switch-row"></div>', unsafe_allow_html=True)
    # Theme Switch (dummy, Streamlit default = light)
    if st.button("Switch to 🌙 Dark", key="themebtn3", use_container_width=True):
        st.warning("Dark mode belum fully didukung (limitasi Streamlit).", icon="🌑")

    st.markdown('<div class="sidebar-footer">v1.0 | Mirip ChatGPT</div>', unsafe_allow_html=True)

# === CHAT HEADER (atas) ===
st.markdown(
    '<div class="chat-header-row">'
    '<span style="font-size:2.15em;">🧠</span>'
    '<span class="chat-header-title">AI for U Controller</span>'
    '</div>',
    unsafe_allow_html=True
)

# === CHAT MESSAGE (riwayat) ===
if "current_chat" not in st.session_state:
    st.session_state.current_chat = []
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
        .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# === INPUT FIXED + UPLOAD ===
input_key = "chat_input_main"
if "prompt_pre" in st.session_state and st.session_state["prompt_pre"]:
    default_input = st.session_state["prompt_pre"]
    st.session_state["prompt_pre"] = ""
else:
    default_input = ""

chat_box = st.container()
with chat_box:
    chatcol1, chatcol2 = st.columns([13, 1])
    with chatcol1:
        user_input = st.text_input("Tanyakan sesuatu…", value=default_input, key=input_key, label_visibility="collapsed", placeholder="Tanyakan sesuatu…")
    with chatcol2:
        uploaded_file = st.file_uploader("", type=['pdf'], key="uploader_main", label_visibility="collapsed")
        st.markdown(
            '<div class="upload-btn-box">'
            '<button class="upload-btn" title="Upload file PDF" onclick="document.getElementById(\'uploader_main\').click()">+</button>'
            '</div>', unsafe_allow_html=True
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

# === PROMPT BUTTONS MINIMAL (Bawah chat input, bukan di tengah) ===
st.markdown('<div style="display:flex;gap:11px;margin:15px 0 8px 0;justify-content:left;">', unsafe_allow_html=True)
if st.button("Berapa harga ICP bulan lalu?", key="icpbtnqq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Berapa harga ICP bulan lalu?"
    st.experimental_rerun()
if st.button("Apa kurs USD hari ini?", key="usdqq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Apa kurs USD hari ini?"
    st.experimental_rerun()
if st.button("Upload laporan PIS terbaru", key="uploadpisqq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Upload laporan PIS terbaru"
    st.experimental_rerun()
if st.button("Nilai tukar Rupiah sekarang?", key="rupiahqq", help="Prompt otomatis"):
    st.session_state["prompt_pre"] = "Nilai tukar Rupiah sekarang?"
    st.experimental_rerun()
st.markdown('</div>', unsafe_allow_html=True)

# === LOGIC QnA ===
if user_input:
    st.chat_message("user", avatar="👤").markdown(user_input, unsafe_allow_html=True)
    answer = None
    error_msg = None

    # PDF Search (TF-IDF)
    if "doc_text" in st.session_state:
        chunks = [p.strip() for p in st.session_state.doc_text.split("\n") if len(p.strip()) > 30]
        try:
            tfidf = TfidfVectorizer().fit_transform([user_input] + chunks)
            sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
            best_idx = sims.argmax()
            if sims[best_idx] > 0.11:
                answer = chunks[best_idx]
        except Exception as e:
            error_msg = f"PDF Search Error: {e}"

    # Web Search Fallback
    if not answer:
        try:
            with DDGS() as ddgs:
                result = next(ddgs.text(user_input), None)
                if result:
                    answer = result['body']
        except Exception as e:
            error_msg = f"Web Search Error: {e}"

    # OpenAI fallback
    if not answer:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_input}]
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
    st.session_state.current_chat.append((user_input, "", "", "user"))
    st.session_state.current_chat.append(("", answer if answer else f"❌ Maaf, terjadi kesalahan saat mencari informasi. {error_msg if error_msg else ''}", "", "assistant"))
    st.experimental_rerun()
