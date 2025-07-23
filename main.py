import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PyPDF2 import PdfReader
from duckduckgo_search import DDGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI for U Controller", layout="wide", initial_sidebar_state="expanded")
openai.api_key = st.secrets["openai_api_key"]

# --- THEME CSS ---
DARK_CSS = """
<style>
.stApp {background: #23272f !important; color: #e8e9ee;}
[data-testid="stSidebar"] > div:first-child {background: #17181c;}
.st-emotion-cache-13ln4jf, .css-1544g2n {background: #23272f !important;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #3a3b43; color: #fff;}
.stChatMessage.assistant {background: #353946; color: #aee8c7;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #23272f; color: #eee;}
.stButton>button, .stButton>button:active {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
LIGHT_CSS = """
<style>
.stApp {background: #f7f8fa !important; color: #222;}
[data-testid="stSidebar"] > div:first-child {background: #fff;}
.st-emotion-cache-13ln4jf, .css-1544g2n {background: #f7f8fa !important;}
.stChatMessage {padding: 0.7em 1em; border-radius: 1.5em; margin-bottom: 0.8em;}
.stChatMessage.user {background: #f1f3f5; color: #222;}
.stChatMessage.assistant {background: #eaf8f1; color: #007860;}
.stTextInput>div>div>input {border-radius: 8px; padding: 13px; background: #fff; color: #222;}
.stButton>button, .stButton>button:active {border-radius: 10px; background-color: #10a37f; color: white;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://chat.openai.com/favicon.ico", width=30)
    st.header("Obrolan")
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "dark"
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
    st.caption("🧠 **AI for U Controller**\n\nv1.0 | Mirip ChatGPT")

# --- CSS THEME ---
if st.session_state.theme_mode == "dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# --- HEADER + UPLOAD BUTTON ---
col_a, col_b = st.columns([12, 1])
with col_a:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:13px;">
        <span style="font-size:2.5em;">🧠</span>
        <span style="font-size:2.0em;font-weight:bold;">AI for U Controller</span>
    </div>
    """, unsafe_allow_html=True)
with col_b:
    uploaded_file = st.file_uploader("", type=['pdf'], label_visibility="collapsed")
    # show upload icon style
    st.markdown("""
    <div style="position:relative;top:-55px;left:37px;">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" height="28" width="28" style="color:#2e90fa;">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
    </div>
    """, unsafe_allow_html=True)

# --- UPLOAD TO GDRIVE IF ANY ---
if uploaded_file:
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    creds = st.secrets["gdrive_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds, scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive_service = build("drive", "v3", credentials=credentials)
    folder_id = st.secrets["gdrive_folder_id"]
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(uploaded_file.name, resumable=True)
    file_metadata = {"name": uploaded_file.name, "parents": [folder_id]}
    try:
        result = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_url = f"https://drive.google.com/file/d/{result['id']}/view"
        st.success(f"✅ File berhasil diupload: [Lihat File]({file_url})")
    except Exception as e:
        st.error(f"❌ Upload gagal: {str(e)}")

# --- LOAD ALL PDF TEXT FROM GDRIVE (CACHE AGAR CEPAT) ---
def extract_all_drive_pdfs():
    creds = st.secrets["gdrive_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds, scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive_service = build("drive", "v3", credentials=credentials)
    folder_id = st.secrets["gdrive_folder_id"]
    # List all PDF files in folder
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/pdf'",
        fields="files(id, name)").execute()
    files = results.get('files', [])
    all_text = ""
    filelist = []
    for f in files:
        filelist.append(f['name'])
        request = drive_service.files().get_media(fileId=f['id'])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        try:
            reader = PdfReader(fh)
            all_text += "\n".join([p.extract_text() or "" for p in reader.pages]) + "\n"
        except Exception as e:
            all_text += f"\n[File '{f['name']}' gagal diekstrak: {e}]\n"
    return all_text, filelist

if "drive_pdf_text" not in st.session_state or "drive_pdf_files" not in st.session_state:
    with st.spinner("Mengambil & memproses seluruh file PDF dari Google Drive..."):
        all_pdf_text, pdf_files = extract_all_drive_pdfs()
        st.session_state.drive_pdf_text = all_pdf_text
        st.session_state.drive_pdf_files = pdf_files

# --- CHAT HISTORY ---
for q, a, _, utype in st.session_state.current_chat:
    st.chat_message("user" if utype == "user" else "assistant", avatar="👤" if utype == "user" else "🤖") \
        .markdown(q if utype == 'user' else a, unsafe_allow_html=True)

# --- INPUT BOX ---
user_input = st.chat_input("Tanyakan sesuatu…")

if user_input:
    st.chat_message("user", avatar="👤").markdown(user_input, unsafe_allow_html=True)
    answer = None
    error_msg = None

    # 1. Cari dari semua PDF di GDrive
    chunks = [p.strip() for p in st.session_state.drive_pdf_text.split("\n") if len(p.strip()) > 30]
    try:
        tfidf = TfidfVectorizer().fit_transform([user_input] + chunks)
        sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
        best_idx = sims.argmax()
        if sims[best_idx] > 0.11:
            answer = chunks[best_idx]
    except Exception as e:
        error_msg = f"PDF Search Error: {e}"

    # 2. Web Search Fallback
    if not answer:
        try:
            with DDGS() as ddgs:
                result = next(ddgs.text(user_input), None)
                if result:
                    answer = result['body']
        except Exception as e:
            error_msg = f"Web Search Error: {e}"

    # 3. Fallback ke OpenAI (SYNTAX openai>=1.0.0)
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
