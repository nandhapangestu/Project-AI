import requests

HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"  # Ganti sesuai model tersedia
HF_API_KEY = st.secrets["hf_token"] if "hf_token" in st.secrets else "your_hf_token_here"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

def ask_huggingface_model(prompt):
    payload = {"inputs": prompt}
    try:
        response = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=40)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"]
        elif isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        elif isinstance(data, list):
            return data[0]
        else:
            return str(data)
    except Exception as e:
        return f"Gagal memanggil model: {e}"

# === TANYAKAN SESUATU ===
if user_input:
    question = user_input
    st.chat_message("user", avatar="👤").markdown(question, unsafe_allow_html=True)
    answer = None
    chunks = st.session_state.all_text_chunks if "all_text_chunks" in st.session_state else []

    if chunks:
        teks_sumber = [chunk[1] for chunk in chunks]
        sumber_file = [chunk[0] for chunk in chunks]
        try:
            tfidf = TfidfVectorizer().fit_transform([question] + teks_sumber)
            sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
            best_idx = sims.argmax()
            if sims[best_idx] > 0.11:
                best_file = sumber_file[best_idx]
                context = teks_sumber[best_idx]
                prompt = f"""Pertanyaan: {question}

Jawaban berdasarkan file {best_file} berikut:
{context}
"""
                answer = ask_huggingface_model(prompt)
                answer = f"**[Dari file: {best_file}]**\n\n{answer}"
            else:
                prompt = f"""Pertanyaan: {question}

Jawaban: """
                answer = ask_huggingface_model(prompt)
        except Exception as e:
            answer = f"File Search Error: {e}"
    else:
        prompt = f"""Pertanyaan: {question}

Jawaban: """
        answer = ask_huggingface_model(prompt)

    st.chat_message("assistant", avatar="🤖").markdown(answer, unsafe_allow_html=True)
    st.session_state.current_chat.append((question, "", "", "user"))
    st.session_state.current_chat.append(("", answer, "", "assistant"))
