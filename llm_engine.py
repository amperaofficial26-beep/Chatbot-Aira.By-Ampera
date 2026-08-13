import os
from groq import Groq

def load_model():
    """Membuka koneksi ke Groq API menggunakan API Key."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY belum diatur di environment variable / Secrets.")
    return Groq(api_key=api_key)

def generate_aira_response(llm_client, user_input, context="", history=None):
    """Generasi respons Aira menggunakan Groq API (Model Qwen 2.5 72B / Llama 3)."""
    system_prompt = (
        "Kamu adalah Aira, asisten AI lokal yang ramah, santai, dan cerdas. "
        "Jawab pertanyaan pengguna dalam Bahasa Indonesia yang natural. "
        "Gunakan konteks berikut jika relevan.\n\n"
        f"Konteks Memori:\n{context if context else 'Tidak ada memori spesifik.'}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        for msg in history[-3:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    messages.append({"role": "user", "content": user_input})

    # Menggunakan model Qwen 2.5 72B super cepat via Groq
    response = llm_client.chat.completions.create(
        model="qwen-2.5-72b-instruct",
        messages=messages,
        temperature=0.7,
        max_tokens=512
    )
    
    return response.choices[0].message.content