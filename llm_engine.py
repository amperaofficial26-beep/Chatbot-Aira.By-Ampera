import os
from groq import Groq

# Variabel yang dibutuhkan oleh app.py
DEFAULT_MODEL_PATH = "qwen-2.5-72b-instruct"

def find_gguf_models(*args, **kwargs):
    """Fungsi pembantu agar app.py tidak error saat mencari model lokal."""
    return [DEFAULT_MODEL_PATH]

def load_model():
    """Membuka koneksi ke Groq API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY belum diatur di Secrets Streamlit!")
    return Groq(api_key=api_key)

# Alias fungsi agar kompatibel dengan app.py
load_model_or_mock = load_model

def generate_aira_response(llm_client, user_input, context="", history=None):
    """Membangkitkan respons Aira lewat Groq API."""
    system_prompt = (
        "Kamu adalah Aira, asisten AI yang ramah, santai, dan cerdas. "
        "Jawab pertanyaan pengguna dalam Bahasa Indonesia yang natural. "
        "Gunakan konteks berikut jika relevan.\n\n"
        f"Konteks Memori:\n{context if context else 'Tidak ada memori spesifik.'}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        for msg in history[-3:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    messages.append({"role": "user", "content": user_input})

    response = llm_client.chat.completions.create(
        model="qwen-2.5-72b-instruct",
        messages=messages,
        temperature=0.7,
        max_tokens=512
    )
    
    return response.choices[0].message.content
