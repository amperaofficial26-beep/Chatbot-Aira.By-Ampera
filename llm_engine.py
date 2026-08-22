from __future__ import annotations

import os
import re
from typing import Any, List
import streamlit as st

DEFAULT_MODEL_PATH = "groq/compound"

class ModelNotFoundError(Exception):
    pass


def sanitize_aira_response(text: str) -> str:
    """Membersihkan respons dari LLM agar konsisten dengan identitas Developer Solo Ampera."""
    if not text:
        return ""
    
    t = text
    # Bersihkan sebutan tim ampera
    t = re.sub(r"\b(?:tim|team)\s+ampera\b", "Developer Solo Ampera", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:tim|team)\s+pengembang\s+ampera\b", "Developer Solo Ampera", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:dibuat|dikembangkan|diciptakan)\s+oleh\s+(?:tim|team)\b", "diciptakan oleh Developer Solo Ampera", t, flags=re.IGNORECASE)
    
    # Bersihkan klaim dibuat oleh Groq / Meta / OpenAI
    t = re.sub(r"\b(?:dibuat|dikembangkan|diciptakan|dilatih)\s+oleh\s+groq\b", "diciptakan secara mandiri oleh Developer Solo Ampera", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:dibuat|dikembangkan|diciptakan|dilatih)\s+oleh\s+meta\b", "diciptakan oleh Developer Solo Ampera", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:dibuat|dikembangkan|diciptakan|dilatih)\s+oleh\s+openai\b", "diciptakan oleh Developer Solo Ampera", t, flags=re.IGNORECASE)
    t = re.sub(r"\bmodel\s+(?:bahasa\s+)?(?:ai\s+)?dari\s+groq\b", "asisten AI buatan Developer Solo Ampera", t, flags=re.IGNORECASE)
    t = re.sub(r"\bsaya\s+adalah\s+(?:model\s+)?(?:ai\s+)?groq\b", "Aku adalah Aira, asisten AI buatan Developer Solo Ampera", t, flags=re.IGNORECASE)
    t = re.sub(r"\baku\s+adalah\s+(?:model\s+)?(?:ai\s+)?groq\b", "Aku adalah Aira, asisten AI buatan Developer Solo Ampera", t, flags=re.IGNORECASE)

    return t


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
            
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model_name = "llama-3.3-70b-versatile"

    def __call__(self, prompt: str, max_tokens: int = 512, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            raw_text = response.choices[0].message.content or ""
            return {"choices": [{"text": sanitize_aira_response(raw_text)}]}
        except Exception:
            # Coba fallback ke model instant jika versatile error
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                raw_text = response.choices[0].message.content or ""
                return {"choices": [{"text": sanitize_aira_response(raw_text)}]}
            except Exception as e2:
                return {"choices": [{"text": f"Error Groq API: {e2}"}]}


def find_gguf_models(directory: str = ".", *args, **kwargs) -> List[str]:
    if not os.path.exists(directory):
        return [DEFAULT_MODEL_PATH]
    models = [f for f in os.listdir(directory) if f.endswith(".gguf")]
    return models if models else [DEFAULT_MODEL_PATH]


def load_model(model_path: str = DEFAULT_MODEL_PATH, *args, **kwargs):
    if os.path.exists(model_path):
        try:
            from compound import compound
            return compound(model_path=model_path, n_ctx=2048, verbose=False)
        except Exception:
            pass
    try:
        return GroqModelWrapper()
    except Exception:
        return None


def load_model_or_mock(model_path: str = DEFAULT_MODEL_PATH, *args, **kwargs):
    return load_model(model_path=model_path, *args, **kwargs)


def generate_response(prompt: str, model: Any = None, max_tokens: int = 512, *args, **kwargs) -> str:
    if model is not None:
        if isinstance(model, GroqModelWrapper):
            res = model(prompt, max_tokens=max_tokens)
            return sanitize_aira_response(res["choices"][0]["text"].strip())
        try:
            output = model(prompt, max_tokens=max_tokens, stop=["User:", "\n\n"], echo=False)
            return sanitize_aira_response(output["choices"][0]["text"].strip())
        except Exception as e:
            return f"Error saat menghasilkan respons: {e}"
    return "Model LLM belum dimuat."


def generate_aira_response(*args, **kwargs) -> str:
    try:
        model = kwargs.get("llm") or kwargs.get("model") or (args[0] if len(args) > 0 else None)
        user_input = kwargs.get("user_input") or kwargs.get("prompt") or (args[1] if len(args) > 1 else None)
        
        if isinstance(model, str) and not user_input:
            user_input = model
            model = None

        if not user_input and len(args) > 0 and isinstance(args[0], str):
            user_input = args[0]

        context = kwargs.get("context", "")
        history = kwargs.get("history", [])

        # Fallback load model jika belum ada
        if not model:
            try:
                model = load_model()
            except Exception:
                model = None

        system_instruction = (
            "Kamu adalah Aira, asisten AI-Chatbot yang ramah, santai, dan cerdas.\n\n"
            "PEDOMAN IDENTITAS & PENCIPTA MUTLAK:\n"
            "1. Nama kamu adalah Aira.\n"
            "2. Kamu diciptakan, didesain, dan dikembangkan secara mandiri oleh Developer Solo Ampera (Ampera Official / Ampera.ai).\n"
            "3. Kamu BUKAN diciptakan oleh Groq, Meta, OpenAI, atau Google. Groq hanyalah penyedia inferensi komputasi cepat, BUKAN pencipta kamu.\n"
            "4. Jika pengguna bertanya siapa kamu, siapa pembuatmu, siapa developermu, atau asal usulmu, kamu HARUS SELALU menjawab bahwa kamu adalah Aira buatan Developer Solo Ampera.\n"
            "5. Jawab pertanyaan pengguna dalam Bahasa Indonesia yang santai, ramah, dan solutif."
            "6. cerna pertnyaan dengan benar dari user, dan jangan selalu menjawab tentang identitas kamu, kecuali sang user bertanya."
            "7. kritisi pertnyaan dan berikan jawaban sesuai pertanyaan yang diberikan user."
        )

        if model and isinstance(model, GroqModelWrapper):
            messages = [{"role": "system", "content": system_instruction}]
            if history and isinstance(history, list):
                for h in history[-3:]:
                    if isinstance(h, dict):
                        messages.append({"role": h.get("role", "user"), "content": str(h.get("content", ""))})
            if context and "Tidak ada memori" not in context:
                messages.append({"role": "system", "content": f"Konteks Memori Pengetahuan Lokal:\n{context}"})
            messages.append({"role": "user", "content": str(user_input)})
            
            try:
                response = model.client.chat.completions.create(
                    model=model.model_name,
                    messages=messages,
                    max_tokens=512,
                    temperature=0.7
                )
                raw_ans = response.choices[0].message.content or ""
                return sanitize_aira_response(raw_ans)
            except Exception:
                # Fallback ke model instant
                response = model.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    max_tokens=512,
                    temperature=0.7
                )
                raw_ans = response.choices[0].message.content or ""
                return sanitize_aira_response(raw_ans)

        if model:
            formatted_prompt = f"System: {system_instruction}\n\nKonteks:\n{context}\n\nUser: {user_input}\nAssistant:" if context else f"System: {system_instruction}\n\nUser: {user_input}\nAssistant:"
            return sanitize_aira_response(generate_response(formatted_prompt, model=model, max_tokens=512))

        # Jika model offline / tanpa API key, gunakan data knowledge base lokal
        if context and "Tidak ada memori" not in context:
            parts = []
            for item in context.split("\n"):
                if item.startswith("[") and "]: " in item:
                    title, body = item.split("]: ", 1)
                    parts.append(f"**{title[1:]}**\n{body}")
                elif item.strip():
                    parts.append(item.strip())
            return "\n\n".join(parts)

        return (
            "Aku Aira! Asisten AI ciptaan **Developer Solo Ampera**. "
            "Saat ini aku berjalan menggunakan memori lokal di perangkatmu. "
            "Ada kendala seputar Android, APK, RAM, atau sistem yang bisa aku bantu?"
        )
    except Exception as e:
        if context and "Tidak ada memori" not in context:
            parts = []
            for item in context.split("\n"):
                if item.startswith("[") and "]: " in item:
                    title, body = item.split("]: ", 1)
                    parts.append(f"**{title[1:]}**\n{body}")
                elif item.strip():
                    parts.append(item.strip())
            return "\n\n".join(parts)
        return (
            "Aku Aira, asisten AI-Chatbot ciptaan **Developer Solo Ampera**. "
            "Aku siap membantu troubleshooting Android, APK, RAM, atau ngobrol santai!"
        )
