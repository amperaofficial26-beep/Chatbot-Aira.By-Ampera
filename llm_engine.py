from __future__ import annotations

import os
from typing import Any, List
import streamlit as st
from groq import Groq

DEFAULT_MODEL_PATH = "qwen2.5-3b-instruct-q4_k_m.gguf"

class ModelNotFoundError(Exception):
    pass

class GroqModelWrapper:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            try:
                api_key = st.secrets.get("GROQ_API_KEY", "")
            except Exception:
                api_key = ""
                
        if not api_key:
            raise ValueError("GROQ_API_KEY belum diatur di Secrets Streamlit!")
            
        self.client = Groq(api_key=api_key)
        self.model_name = "qwen-2.5-72b-instruct"

    def __call__(self, prompt: str, max_tokens: int = 512, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            text = response.choices[0].message.content
            return {"choices": [{"text": text}]}
        except Exception as e:
            return {"choices": [{"text": f"Error Groq API: {e}"}]}

def find_gguf_models(directory: str = ".", *args, **kwargs) -> List[str]:
    if not os.path.exists(directory):
        return [DEFAULT_MODEL_PATH]
    models = [f for f in os.listdir(directory) if f.endswith(".gguf")]
    return models if models else [DEFAULT_MODEL_PATH]

def load_model(model_path: str = DEFAULT_MODEL_PATH, *args, **kwargs):
    if os.path.exists(model_path):
        try:
            from llama_cpp import Llama
            return Llama(model_path=model_path, n_ctx=2048, verbose=False)
        except Exception:
            pass
    return GroqModelWrapper()

load_model_or_mock = load_model

def generate_response(prompt: str, model: Any = None, max_tokens: int = 512, *args, **kwargs) -> str:
    if model is not None:
        if isinstance(model, GroqModelWrapper):
            res = model(prompt, max_tokens=max_tokens)
            return res["choices"][0]["text"].strip()
        try:
            output = model(prompt, max_tokens=max_tokens, stop=["User:", "\n\n"], echo=False)
            return output["choices"][0]["text"].strip()
        except Exception as e:
            return f"Error saat menghasilkan respons: {e}"
    return "Model LLM belum dimuat."

def generate_aira_response(*args, **kwargs) -> str:
    """Fungsi fleksibel untuk menangani berbagai bentuk argumen dari app.py tanpa TypeError."""
    try:
        model = kwargs.get("model") or (args[0] if len(args) > 0 else None)
        user_input = kwargs.get("user_input") or kwargs.get("prompt") or (args[1] if len(args) > 1 else None)
        
        # Jika argumen pertama adalah string (posisi input tertukar dengan model)
        if isinstance(model, str) and not user_input:
            user_input = model
            model = None

        if not user_input and len(args) > 0 and isinstance(args[0], str):
            user_input = args[0]

        if not model:
            model = load_model()

        context = kwargs.get("context", "")
        history = kwargs.get("history", [])

        system_instruction = (
            "Kamu adalah Aira, asisten AI yang ramah, santai, dan cerdas. "
            "Jawab pertanyaan pengguna dalam Bahasa Indonesia yang natural."
        )

        if isinstance(model, GroqModelWrapper):
            messages = [{"role": "system", "content": system_instruction}]
            if history and isinstance(history, list):
                for h in history[-3:]:
                    if isinstance(h, dict):
                        messages.append({"role": h.get("role", "user"), "content": str(h.get("content", ""))})
            if context:
                messages.append({"role": "system", "content": f"Konteks Memori:\n{context}"})
            messages.append({"role": "user", "content": str(user_input)})
            
            response = model.client.chat.completions.create(
                model=model.model_name,
                messages=messages,
                max_tokens=512,
                temperature=0.7
            )
            return response.choices[0].message.content

        formatted_prompt = f"System: {system_instruction}\n\nKonteks:\n{context}\n\nUser: {user_input}\nAssistant:" if context else f"System: {system_instruction}\n\nUser: {user_input}\nAssistant:"
        return generate_response(formatted_prompt, model=model, max_tokens=512)
    except Exception as e:
        return f"Aduh, ada kendala waktu aku merangkkai jawaban. Detail teknis: {type(e).__name__} ({e})."
