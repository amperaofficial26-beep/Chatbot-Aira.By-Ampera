from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from groq import Groq

# Variabel & Class pembantu yang dicari app.py
DEFAULT_MODEL_PATH = "qwen-2.5-72b-instruct"

class ModelNotFoundError(Exception):
    """Custom exception untuk app.py"""
    pass

def find_gguf_models(*args, **kwargs):
    """Fungsi pembantu agar app.py tidak error."""
    return [DEFAULT_MODEL_PATH]

def load_model():
    """Membuka koneksi ke Groq API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY belum diatur di Secrets Streamlit!")
    return Groq(api_key=api_key)

# Alias fungsi
load_model_or_mock = load_model

def generate_aira_response(llm_client, user_input: str, context: str = "", history: list = None) -> str:
    """Fungsi pemanggil model Groq yang dicari oleh app.py."""
    system_prompt = (
        "Kamu adalah Aira, asisten AI yang ramah, santai, dan cerdas. "
        "Jawab pertanyaan pengguna dalam Bahasa Indonesia yang natural. "
        "Gunakan konteks berikut jika relevan.\n\n"
        f"Konteks Memori:\n{context if context else 'Tidak ada memori spesifik.'}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        for msg in history[-3:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
    messages.append({"role": "user", "content": user_input})

    response = llm_client.chat.completions.create(
        model="qwen-2.5-72b-instruct",
        messages=messages,
        temperature=0.7,
        max_tokens=512
    )
    
    return response.choices[0].message.content

# Alias cadangan jika app.py memanggil nama ini
generate_response = generate_aira_response
