from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

DEFAULT_MODEL_PATH = "qwen2.5-3b-instruct-q4_k_m.gguf"

class ModelNotFoundError(Exception):
    """Custom exception untuk menangani model yang tidak ditemukan."""
    pass

def find_gguf_models(directory: str = ".") -> List[str]:
    """Mencari file model berformat .gguf di direktori."""
    if not os.path.exists(directory):
        return [DEFAULT_MODEL_PATH]
    models = [f for f in os.listdir(directory) if f.endswith(".gguf")]
    return models if models else [DEFAULT_MODEL_PATH]

def load_model(model_path: str = DEFAULT_MODEL_PATH):
    """Memuat model GGUF secara lokal menggunakan llama-cpp-python."""
    target_path = model_path if os.path.exists(model_path) else DEFAULT_MODEL_PATH
    if not os.path.exists(target_path):
        raise ModelNotFoundError(f"File model {target_path} tidak ditemukan.")
    try:
        from llama_cpp import Llama
        return Llama(model_path=target_path, n_ctx=2048, verbose=False)
    except Exception as e:
        raise RuntimeError(f"Gagal memuat model GGUF: {e}")

# Alias fungsi wajib agar app.py tidak error
load_model_or_mock = load_model

def generate_response(prompt: str, model: Any = None, max_tokens: int = 512, **kwargs) -> str:
    """Menghasilkan respons teks dari model lokal."""
    if model is not None:
        try:
            output = model(prompt, max_tokens=max_tokens, stop=["User:", "\n\n"], echo=False)
            return output["choices"][0]["text"].strip()
        except Exception as e:
            return f"Error saat menghasilkan respons: {e}"
    return "Model LLM belum dimuat."

def generate_aira_response(model, user_input: str, context: str = "", history: list = None, **kwargs) -> str:
    """Fungsi pembantu generator respons Aira."""
    formatted_prompt = f"Konteks:\n{context}\n\nPertanyaan: {user_input}\nJawaban:" if context else f"Pertanyaan: {user_input}\nJawaban:"
    return generate_response(formatted_prompt, model=model)
