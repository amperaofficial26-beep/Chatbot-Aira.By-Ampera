from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

def load_model(model_path: str = "model.gguf"):
    """Fungsi utama pemuat model GGUF."""
    if not os.path.exists(model_path):
        return None
    try:
        from llama_cpp import Llama
        return Llama(model_path=model_path, n_ctx=2048, verbose=False)
    except Exception:
        return None

# Alias nama fungsi agar sesuai dengan pemanggilan di app.py
load_model_or_mock = load_model

def generate_response(prompt: str, model: Any = None, max_tokens: int = 512) -> str:
    """Menghasilkan respon dari model atau jawaban standar jika model tidak ada."""
    if model is not None:
        try:
            output = model(prompt, max_tokens=max_tokens, stop=["User:", "\n\n"])
            return output["choices"][0]["text"].strip()
        except Exception as e:
            return f"Error saat menghasilkan respon: {e}"
    
    return "Model LLM belum dimuat secara lokal. Silakan unggah atau tentukan file .gguf terlebih dahulu."
