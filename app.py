#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py - Chatbot Aira (Cyberpunk Anime UI)
"""

from __future__ import annotations
import os
import re
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

# ---------------------------------------------------------------------------
# Pengaturan Awal
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# [Impor Lokal & Fallback]
SEARCH_IMPORT_ERROR = ""
LLM_IMPORT_ERROR = ""

try:
    from search_engine import resolve_query, search_knowledge, load_knowledge, DEFAULT_KB_PATH, NO_MEMORY_MSG
except Exception as _search_exc:
    SEARCH_IMPORT_ERROR = f"{_search_exc.__class__.__name__}: {_search_exc}"
    DEFAULT_KB_PATH = os.path.join(_BASE_DIR, "knowledge.json")
    NO_MEMORY_MSG = "Tidak ada memori spesifik"
    def resolve_query(user_input: str, last_bot_response: str = "") -> str: return (user_input or "").strip()
    def search_knowledge(query: str, **kwargs: Any) -> str: return NO_MEMORY_MSG
    def load_knowledge(path: str = DEFAULT_KB_PATH) -> list: return []

try:
    from llm_engine import load_model, generate_aira_response, load_model_or_mock, find_gguf_models, DEFAULT_MODEL_PATH, ModelNotFoundError
except Exception as _llm_exc:
    LLM_IMPORT_ERROR = f"{_llm_exc.__class__.__name__}: {_llm_exc}"
    DEFAULT_MODEL_PATH = os.path.join(_BASE_DIR, "models", "qwen2.5-3b-instruct-q4_k_m.gguf")
    class ModelNotFoundError(FileNotFoundError): pass
    def find_gguf_models(models_dir: str = "") -> list: return []
    def load_model(model_path: str = DEFAULT_MODEL_PATH, **kwargs: Any) -> Any: raise RuntimeError(LLM_IMPORT_ERROR or "llm_engine tidak tersedia")
    def load_model_or_mock(model_path: str = DEFAULT_MODEL_PATH, **kwargs: Any) -> Any: return None
    def generate_aira_response(llm: Any, user_input: str, context: str = "", history=None, **kwargs: Any) -> str:
        return "Modul llm_engine.py belum siap. Cek instalasi llama-cpp-python."

# ---------------------------------------------------------------------------
# CSS — Tampilan Cyberpunk Anime Glassmorphism (set_ui_style)
# ---------------------------------------------------------------------------
def set_ui_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #050814;
            background-image: 
                radial-gradient(circle at 50% 50%, rgba(0, 243, 255, 0.08) 0%, transparent 60%),
                linear-gradient(rgba(5, 8, 20, 0.85), rgba(5, 8, 20, 0.85)),
                url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%2300f3ff' fill-opacity='0.05' fill-rule='evenodd'%3E%3Cpath d='M0 0h40v40H0V0zm40 40h40v40H40V40zm0-40h2v40h-2V0zm-40 40h40v2H0v-2zM20 0v80h2V0h-2zm40 0v80h2V0h-2z'/%3E%3C/g%3E%3C/svg%3E");
            background-size: cover;
            animation: circuitPulse 12s infinite alternate ease-in-out;
        }
        @keyframes circuitPulse {
            0% { filter: hue-rotate(0deg) brightness(1); }
            50% { filter: hue-rotate(180deg) brightness(1.2); }
            100% { filter: hue-rotate(360deg) brightness(1); }
        }
        [data-testid="stChatMessage"] {
            backdrop-filter: blur(16px) !important;
            border-radius: 20px !important;
            padding: 16px !important;
            margin-bottom: 14px !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        [data-testid="stChatMessage"]:nth-child(odd) {
            background: rgba(20, 25, 45, 0.75) !important;
            border: 1px solid rgba(0, 243, 255, 0.25) !important;
            border-left: 5px solid #00f3ff !important;
        }
        [data-testid="stChatMessage"]:nth-child(even) {
            background: rgba(45, 20, 55, 0.75) !important;
            border: 1px solid rgba(255, 0, 128, 0.25) !important;
            border-right: 5px solid #ff0080 !important;
        }
        div.stButton > button {
            background: rgba(15, 22, 36, 0.8) !important;
            border: 1px solid rgba(0, 243, 255, 0.4) !important;
            color: #00f3ff !important;
        }
        div.stButton > button:hover {
            box-shadow: 0 0 25px rgba(0, 243, 255, 0.8) !important;
        }
        [data-testid="stChatInput"] {
            border-radius: 35px !important;
            background: linear-gradient(60deg, #00f3ff, #ff0080, #7928ca, #00f3ff) !important;
            padding: 2px !important;
        }
        [data-testid="stChatInput"] > div { background-color: #080c14 !important; border-radius: 33px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Konfigurasi & UI Utama
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Aira - Asisten AI Lokal", page_icon="💠", layout="centered")

APP_TITLE = "Aira - Asisten AI Lokal"
WELCOME_TEXT = "Hai, aku **Aira**. Ada yang bisa kubantu hari ini?"
USER_AVATAR = "🙂"
AIRA_AVATAR = "💠"
EXAMPLE_PROMPTS = ["Siapa kamu?", "APK gagal install", "RAM penuh", "Apa itu RAG?"]

# [Fungsi Helper]
def _normalize_intent_text(text: str) -> str: return (text or "").lower().strip()
def detect_intent_bypass(user_input: str) -> Optional[str]: return None # Sederhanakan untuk contoh
def get_last_bot_response(messages: List[Dict[str, str]]) -> str: return ""
def history_for_llm(messages: List[Dict[str, str]]) -> List[Dict[str, str]]: return messages[-10:]

# [Cache Resources]
@st.cache_resource
def get_cached_llm() -> Dict[str, Any]:
    return {"llm": None, "mode": "mock", "path": DEFAULT_MODEL_PATH}

@st.cache_data
def get_kb_status() -> Dict[str, Any]: return {"exists": False, "count": 0}

# [Fungsi Utama]
def handle_user_message(user_input: str, llm: Any) -> None:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar=USER_AVATAR): st.markdown(user_input)
    
    # Simulasi balasan
    answer = f"Halo! Aku Aira. Kamu bilang: '{user_input}'"
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant", avatar=AIRA_AVATAR): st.markdown(answer)

def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": WELCOME_TEXT}]

def main() -> None:
    set_ui_style()  # <--- Panggil fungsi CSS di sini
    init_session_state()
    model_info = get_cached_llm()
    
    st.title(APP_TITLE)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
    if prompt := st.chat_input("Tulis pesan untuk Aira..."):
        handle_user_message(prompt, llm=model_info.get("llm"))

if __name__ == "__main__":
    main()
