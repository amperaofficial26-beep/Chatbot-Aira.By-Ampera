#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py
======
Aira · Dark Obsidian Glassmorphism UI
       + Dynamic Theme Accent Switcher (Violet, Cyan, Pink, Emerald)
       + Interactive Diagnostic Cards & Quick Topic Launchers
       + Chat Exporter (.md transcript download) & Realtime Timestamps
       + Ultra-Transparent Frosted Glass Chat Input
       + Streamlit Chatbot Ciptaan Developer Solo Ampera
"""

from __future__ import annotations

import base64
import html
import os
import re
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# ---------------------------------------------------------------------------
# Impor modul lokal
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

SEARCH_IMPORT_ERROR = ""
LLM_IMPORT_ERROR = ""

try:
    from search_engine import (  # type: ignore
        resolve_query,
        search_knowledge,
        load_knowledge,
        DEFAULT_KB_PATH,
        NO_MEMORY_MSG,
    )
except Exception as _search_exc:  # pragma: no cover
    SEARCH_IMPORT_ERROR = f"{_search_exc.__class__.__name__}: {_search_exc}"
    DEFAULT_KB_PATH = os.path.join(_BASE_DIR, "knowledge.json")
    NO_MEMORY_MSG = "Tidak ada memori spesifik"

    def resolve_query(user_input: str, last_bot_response: str = "") -> str:
        return (user_input or "").strip()

    def search_knowledge(query: str, **kwargs: Any) -> str:
        return NO_MEMORY_MSG

    def load_knowledge(path: str = DEFAULT_KB_PATH) -> list:
        return []

try:
    from llm_engine import (  # type: ignore
        load_model,
        generate_aira_response,
        load_model_or_mock,
        find_gguf_models,
        DEFAULT_MODEL_PATH,
        ModelNotFoundError,
    )
except Exception as _llm_exc:  # pragma: no cover
    LLM_IMPORT_ERROR = f"{_llm_exc.__class__.__name__}: {_llm_exc}"
    DEFAULT_MODEL_PATH = os.path.join(
        _BASE_DIR, "models", "groq/compound"
    )

    class ModelNotFoundError(FileNotFoundError):
        pass

    def find_gguf_models(models_dir: str = "") -> list:
        return []

    def load_model(model_path: str = DEFAULT_MODEL_PATH, **kwargs: Any) -> Any:
        raise RuntimeError(LLM_IMPORT_ERROR or "llm_engine tidak tersedia")

    def load_model_or_mock(model_path: str = DEFAULT_MODEL_PATH, **kwargs: Any) -> Any:
        return None

    def generate_aira_response(
        llm: Any, user_input: str, context: str = "", history=None, **kwargs: Any
    ) -> str:
        if context and context != NO_MEMORY_MSG:
            return f"Berdasarkan memori lokal yang aku punya:\n\n{context}"
        return (
            "Aku Aira! Asisten AI ciptaan Developer Solo Ampera. "
            "Kamu bisa bertanya seputar error Android, APK, RAM, atau fitur sistem lainnya!"
        )


st.set_page_config(
    page_title="Aira - Asisten AI-Chatbot By Ampera",
    page_icon="💮",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Theme Palettes Configuration
# ---------------------------------------------------------------------------

THEMES: Dict[str, Dict[str, str]] = {
    "violet": {
        "name": "🔮 Obsidian Violet (Default)",
        "accent": "#6366f1",
        "accent_light": "#818cf8",
        "accent_glow": "rgba(99, 102, 241, 0.38)",
        "accent_border": "rgba(129, 140, 248, 0.45)",
        "user_gradient": "linear-gradient(135deg, rgba(79, 70, 229, 0.92) 0%, rgba(124, 58, 237, 0.92) 100%)",
        "mesh_glow": (
            "radial-gradient(at 15% 15%, rgba(99, 102, 241, 0.14) 0px, transparent 50%), "
            "radial-gradient(at 85% 20%, rgba(139, 92, 246, 0.12) 0px, transparent 50%), "
            "radial-gradient(at 50% 85%, rgba(56, 189, 248, 0.10) 0px, transparent 50%)"
        ),
        "pcb_c": "#38bdf8",
        "pcb_p": "#818cf8",
    },
    "cyan": {
        "name": "💎 Cyber Sapphire (Cyan)",
        "accent": "#06b6d4",
        "accent_light": "#38bdf8",
        "accent_glow": "rgba(56, 189, 248, 0.38)",
        "accent_border": "rgba(56, 189, 248, 0.45)",
        "user_gradient": "linear-gradient(135deg, rgba(2, 132, 199, 0.92) 0%, rgba(6, 182, 212, 0.92) 100%)",
        "mesh_glow": (
            "radial-gradient(at 15% 15%, rgba(6, 182, 212, 0.15) 0px, transparent 50%), "
            "radial-gradient(at 85% 20%, rgba(56, 189, 248, 0.12) 0px, transparent 50%), "
            "radial-gradient(at 50% 85%, rgba(99, 102, 241, 0.08) 0px, transparent 50%)"
        ),
        "pcb_c": "#06b6d4",
        "pcb_p": "#38bdf8",
    },
    "pink": {
        "name": "🌸 Neon Synthwave (Pink)",
        "accent": "#ec4899",
        "accent_light": "#f472b6",
        "accent_glow": "rgba(236, 72, 153, 0.38)",
        "accent_border": "rgba(244, 114, 182, 0.45)",
        "user_gradient": "linear-gradient(135deg, rgba(219, 39, 119, 0.92) 0%, rgba(192, 38, 211, 0.92) 100%)",
        "mesh_glow": (
            "radial-gradient(at 15% 15%, rgba(236, 72, 153, 0.15) 0px, transparent 50%), "
            "radial-gradient(at 85% 20%, rgba(217, 70, 239, 0.12) 0px, transparent 50%), "
            "radial-gradient(at 50% 85%, rgba(168, 85, 247, 0.10) 0px, transparent 50%)"
        ),
        "pcb_c": "#d946ef",
        "pcb_p": "#f472b6",
    },
    "emerald": {
        "name": "🌿 Emerald Matrix (Green)",
        "accent": "#10b981",
        "accent_light": "#34d399",
        "accent_glow": "rgba(16, 185, 129, 0.38)",
        "accent_border": "rgba(52, 211, 153, 0.45)",
        "user_gradient": "linear-gradient(135deg, rgba(5, 150, 105, 0.92) 0%, rgba(16, 185, 129, 0.92) 100%)",
        "mesh_glow": (
            "radial-gradient(at 15% 15%, rgba(16, 185, 129, 0.15) 0px, transparent 50%), "
            "radial-gradient(at 85% 20%, rgba(52, 211, 153, 0.12) 0px, transparent 50%), "
            "radial-gradient(at 50% 85%, rgba(6, 182, 212, 0.08) 0px, transparent 50%)"
        ),
        "pcb_c": "#10b981",
        "pcb_p": "#34d399",
    },
}


# ---------------------------------------------------------------------------
# CSS & Styling (Dark Obsidian Glassmorphism + Dynamic Themes)
# ---------------------------------------------------------------------------

def set_ui_style(theme_key: str = "violet") -> None:
    pal = THEMES.get(theme_key, THEMES["violet"])

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400;1,600&family=Orbitron:wght@500;600;700;800;900&display=swap');

        :root {{
            /* Palette Dynamic Glass */
            --bg-base: #080a10;
            --bg-darker: #05060a;
            --surface-glass: rgba(18, 22, 34, 0.72);
            --surface-glass-hover: rgba(28, 34, 52, 0.85);
            --surface-glass-active: rgba(36, 44, 68, 0.95);
            
            /* Glassmorphism Borders & Highlights */
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glass-bright: rgba(255, 255, 255, 0.15);
            
            /* Theme Dynamic Colors */
            --theme-accent: {pal["accent"]};
            --theme-accent-light: {pal["accent_light"]};
            --theme-accent-glow: {pal["accent_glow"]};
            --theme-accent-border: {pal["accent_border"]};
            --theme-user-bubble: {pal["user_gradient"]};
            
            --indigo: #6366f1;
            --indigo-light: #818cf8;
            --violet: #8b5cf6;
            --cyan: #06b6d4;
            --cyan-light: #38bdf8;
            --emerald: #10b981;
            --emerald-light: #34d399;
            
            /* Text & Typography */
            --text-main: #f8fafc;
            --text-sub: #cbd5e1;
            --text-muted: #94a3b8;
            --text-dim: #64748b;

            /* Animations */
            --spin: 0deg;
        }}

        /* Reset & Global */
        *, *::before, *::after {{
            box-sizing: border-box;
        }}

        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background-color: var(--bg-base) !important;
            background-image: {pal["mesh_glow"]} !important;
            background-attachment: fixed !important;
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        /* Hide Streamlit default decor */
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{ 
            background: transparent !important; 
        }}
        #MainMenu, footer {{ 
            visibility: hidden; 
        }}

        /* Custom Scrollbar */
        ::-webkit-scrollbar {{
            width: 7px;
            height: 7px;
        }}
        ::-webkit-scrollbar-track {{
            background: rgba(8, 10, 16, 0.6);
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--theme-accent-glow);
            border-radius: 99px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--theme-accent);
        }}

        /* Selection */
        ::selection {{
            background: var(--theme-accent-glow);
            color: #ffffff;
        }}

        /* Container Layout */
        [data-testid="stMain"], [data-testid="stMainBlockContainer"] {{
            background: transparent !important;
            position: relative;
            z-index: 1;
        }}
        [data-testid="stMainBlockContainer"] {{
            padding-top: 1rem !important;
            padding-bottom: 7.5rem !important;
            max-width: 820px;
        }}

        /* Ambient Cyber Particles & Neural Wave */
        .cyber-particles {{
            position: fixed; inset: 0; z-index: 0; pointer-events: none;
            background-image:
                radial-gradient(1.5px 1.5px at 15% 20%, rgba(255, 255, 255, 0.4) 50%, transparent 51%),
                radial-gradient(1.2px 1.2px at 80% 15%, var(--theme-accent-light) 50%, transparent 51%),
                radial-gradient(1.4px 1.4px at 25% 75%, var(--cyan-light) 50%, transparent 51%),
                radial-gradient(1.3px 1.3px at 85% 80%, var(--theme-accent-light) 50%, transparent 51%),
                radial-gradient(1.6px 1.6px at 50% 45%, rgba(255, 255, 255, 0.5) 50%, transparent 51%),
                radial-gradient(1.2px 1.2px at 70% 65%, var(--cyan-light) 50%, transparent 51%);
            animation: particleTwinkle 4s ease-in-out infinite alternate;
        }}
        @keyframes particleTwinkle {{
            0% {{ opacity: 0.35; transform: translateY(0); }}
            100% {{ opacity: 0.85; transform: translateY(-8px); }}
        }}

        /* PCB / Ambient Layer */
        .pcb-layer {{
            position: fixed; inset: 0; z-index: 0;
            pointer-events: none; overflow: hidden;
            contain: strict; opacity: 0.28;
        }}
        .pcb-layer svg {{ width: 100%; height: 100%; display: block; }}
        .pcb-tr {{
            fill: none; stroke: rgba(139, 92, 246, 0.45); stroke-width: 1.4;
            stroke-linecap: round; stroke-linejoin: round;
        }}
        .pcb-tr.alt {{ stroke: rgba(56, 189, 248, 0.4); }}
        .pcb-glow {{
            fill: none; stroke-linecap: round; stroke-linejoin: round;
            stroke-width: 2.2; stroke-dasharray: 32 240;
            animation: traceDraw 10s linear infinite;
        }}
        .pcb-glow.c {{ stroke: {pal["pcb_c"]}; filter: drop-shadow(0 0 6px {pal["pcb_c"]}); }}
        .pcb-glow.p {{ stroke: {pal["pcb_p"]}; animation-direction: reverse; animation-duration: 12s; filter: drop-shadow(0 0 6px {pal["pcb_p"]}); }}
        .pcb-pad {{ fill: #080a10; stroke: var(--theme-accent-light); stroke-width: 1.2; }}
        .pcb-hole {{ fill: var(--theme-accent); }}
        .element-container:has(.pcb-layer) {{
            position: fixed !important; inset: 0; height: 0 !important;
            margin: 0 !important; overflow: visible !important;
        }}
        @keyframes traceDraw {{ to {{ stroke-dashoffset: -272; }} }}

        /* -------------------------------------------------------------------
           Header Banner (Obsidian Glass Floating Banner)
           ------------------------------------------------------------------- */
        .app-head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 12px 18px;
            margin: 4px 0 20px;
            background: linear-gradient(135deg, rgba(22, 27, 42, 0.72) 0%, rgba(14, 18, 28, 0.85) 100%);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--border-glass-bright);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }}
        .app-head-left {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .app-logo {{
            width: 52px; height: 52px; border-radius: 16px; display: grid; place-items: center;
            background: #0d111a;
            border: 1px solid var(--theme-accent-border);
            box-shadow: 0 0 20px var(--theme-accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.15);
            font-family: 'Outfit', sans-serif; font-weight: 800; color: #c7d2fe;
            background-size: cover; background-position: center;
            position: relative;
            flex-shrink: 0;
        }}
        .app-logo span {{ color: var(--theme-accent-light); font-size: .75rem; margin-left: 1px; }}
        .app-head h1 {{
            font-family: 'Outfit', sans-serif !important; font-size: 1.45rem;
            font-weight: 700;
            margin: 0 !important;
            background: linear-gradient(135deg, #ffffff 30%, var(--theme-accent-light) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }}
        .app-head p {{ 
            margin: 2px 0 0; 
            color: var(--text-muted); 
            font-size: .84rem; 
            font-weight: 400;
        }}
        .app-head-status {{
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 5px 12px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(52, 211, 153, 0.28);
            border-radius: 99px;
            color: #6ee7b7;
            font-size: 0.76rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
        }}
        .app-head-status i {{
            width: 7px; height: 7px; border-radius: 50%;
            background: #34d399;
            box-shadow: 0 0 8px #34d399;
            animation: pulseDot 1.6s ease-in-out infinite;
        }}

        /* -------------------------------------------------------------------
           Interactive Topic & Diagnostic Cards
           ------------------------------------------------------------------- */
        .topic-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 14px 0 22px;
        }}
        .topic-card {{
            padding: 14px 16px;
            border-radius: 18px;
            background: linear-gradient(145deg, rgba(22, 27, 42, 0.65) 0%, rgba(14, 18, 28, 0.75) 100%);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-glass-bright);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            cursor: pointer;
            text-align: left;
        }}
        .topic-card:hover {{
            transform: translateY(-3px);
            border-color: var(--theme-accent-border);
            box-shadow: 0 10px 28px var(--theme-accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }}
        .topic-card-icon {{
            font-size: 1.35rem;
            margin-bottom: 6px;
            display: inline-block;
        }}
        .topic-card-title {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 0.96rem;
            color: #ffffff;
            margin-bottom: 3px;
        }}
        .topic-card-desc {{
            font-size: 0.78rem;
            color: var(--text-muted);
            line-height: 1.45;
        }}

        /* -------------------------------------------------------------------
           Chat Thread & Glassmorphism Bubbles
           ------------------------------------------------------------------- */
        .wa-thread {{ 
            display: flex; 
            flex-direction: column; 
            gap: 16px; 
            margin-bottom: 24px;
        }}
        .wa-row {{ 
            display: flex; 
            align-items: flex-end; 
            gap: 10px; 
            width: 100%; 
            animation: bubbleFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
        }}
        .wa-row.left {{ justify-content: flex-start; }}
        .wa-row.right {{ justify-content: flex-end; }}
        
        .wa-avatar {{
            width: 38px; height: 38px; border-radius: 50%; flex: 0 0 38px;
            background-size: cover; background-position: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            position: relative;
        }}
        .wa-avatar-aira {{ 
            border: 2px solid var(--theme-accent-border); 
            background-color: #121624; 
            box-shadow: 0 0 14px var(--theme-accent-glow);
        }}
        .wa-avatar-user {{
            display: grid; place-items: center; 
            background: linear-gradient(135deg, #1e1b4b, #312e81);
            border: 2px solid rgba(167, 139, 250, 0.5);
            box-shadow: 0 0 14px rgba(139, 92, 246, 0.3);
            font-size: 1.1rem;
        }}
        .wa-fallback {{
            display: grid; place-items: center; color: #c7d2fe;
            font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.05rem;
        }}
        
        .wa-bubble-wrap {{
            max-width: min(80%, 580px);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .wa-row.right .wa-bubble-wrap {{
            align-items: flex-end;
        }}
        
        .wa-meta {{
            font-size: 0.72rem;
            color: var(--text-dim);
            font-family: 'JetBrains Mono', monospace;
            padding: 0 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .wa-meta.user {{
            color: rgba(203, 213, 225, 0.7);
        }}
        
        .wa-bubble {{
            padding: 13px 17px 14px;
            line-height: 1.62; 
            font-size: .94rem; 
            word-wrap: break-word;
            position: relative;
        }}
        
        /* Assistant Bubble (Obsidian Glass) */
        .wa-aira {{
            background: linear-gradient(150deg, rgba(22, 27, 42, 0.88) 0%, rgba(14, 18, 28, 0.94) 100%);
            color: #f1f5f9;
            border-radius: 4px 18px 18px 18px;
            border: 1px solid var(--border-glass-bright);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }}
        
        /* User Bubble (Dynamic Gradient Glass) */
        .wa-user {{
            background: var(--theme-user-bubble);
            color: #ffffff;
            border-radius: 18px 4px 18px 18px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 8px 25px var(--theme-accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.22);
        }}

        /* Bubble inner formatting */
        .wa-bubble strong {{ color: #ffffff; font-weight: 600; }}
        .wa-bubble code {{
            background: rgba(99, 102, 241, 0.16); 
            padding: 2px 6px; 
            border-radius: 6px; 
            color: #a5b4fc;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.88em;
            border: 1px solid rgba(99, 102, 241, 0.28);
        }}
        .wa-user code {{
            background: rgba(0, 0, 0, 0.25);
            border-color: rgba(255, 255, 255, 0.2);
            color: #f3e8ff;
        }}
        .wa-list {{
            margin: 6px 0 6px 18px;
            padding: 0;
        }}
        .wa-list li {{
            margin-bottom: 4px;
            color: #e2e8f0;
        }}
        .wa-quote {{
            margin: 8px 0;
            padding: 6px 12px;
            border-left: 3px solid var(--theme-accent-light);
            background: var(--theme-accent-glow);
            border-radius: 0 8px 8px 0;
            color: var(--text-sub);
            font-style: italic;
        }}
        .wa-h3 {{
            margin: 10px 0 4px;
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            color: #ffffff;
            font-weight: 700;
        }}
        .wa-h4 {{
            margin: 8px 0 4px;
            font-family: 'Outfit', sans-serif;
            font-size: 1.02rem;
            color: #c7d2fe;
            font-weight: 600;
        }}
        .wa-gap {{
            height: 6px;
        }}
        .wa-code-wrap {{
            margin: 10px 0;
            background: rgba(7, 9, 15, 0.88);
            border: 1px solid var(--theme-accent-border);
            border-radius: 10px;
            overflow: hidden;
        }}
        .code-lang {{
            display: block;
            padding: 4px 10px;
            background: rgba(99, 102, 241, 0.14);
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            color: #93c5fd;
            font-size: 0.72rem;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }}
        .wa-code-block {{
            display: block;
            padding: 10px 12px;
            margin: 0;
            overflow-x: auto;
            color: #e2e8f0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.84rem;
            line-height: 1.5;
            background: transparent !important;
            border: none !important;
        }}

        /* -------------------------------------------------------------------
           Proses Berpikir (AI Thinking State Component)
           ------------------------------------------------------------------- */
        .think {{
            min-width: 250px;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        .think-head {{
            display: flex; align-items: center; gap: 8px;
            color: #c7d2fe; font-size: .74rem; font-weight: 700;
            letter-spacing: .12em;
            margin-bottom: 8px;
            font-family: 'JetBrains Mono', monospace;
        }}
        .think-orb {{
            width: 9px; height: 9px; border-radius: 50%;
            background: var(--theme-accent-light);
            box-shadow: 0 0 10px var(--theme-accent-light);
            animation: pulseDot 1.1s ease-in-out infinite;
        }}
        .think-now {{
            color: #ffffff; font-size: .94rem;
            min-height: 1.4em;
        }}
        .think-now b {{ 
            color: var(--theme-accent-light); 
            font-weight: 600; 
            background: var(--theme-accent-glow);
            padding: 1px 6px;
            border-radius: 6px;
        }}
        .think-dots::after {{
            content: "";
            animation: dots 1.2s steps(4, end) infinite;
        }}
        .think-bar {{
            margin-top: 10px; height: 3px; border-radius: 99px;
            background: rgba(255, 255, 255, 0.08); overflow: hidden;
        }}
        .think-bar i {{
            display: block; height: 100%; width: 42%;
            background: linear-gradient(90deg, var(--theme-accent), var(--cyan-light), var(--theme-accent-light));
            border-radius: 99px;
            box-shadow: 0 0 8px var(--theme-accent-glow);
            animation: barRun 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
        }}
        .think-log {{
            margin-top: 10px; color: var(--text-muted); 
            font-size: .76rem; line-height: 1.6;
            font-family: 'JetBrains Mono', monospace;
        }}
        .think-log .done {{ color: #6ee7b7; display: flex; align-items: center; gap: 4px; }}
        .think-log .wait {{ color: #93c5fd; display: flex; align-items: center; gap: 4px; }}

        .type-caret {{
            display: inline-block; width: 6px; height: 1em;
            margin-left: 2px; background: var(--theme-accent-light); vertical-align: -2px;
            border-radius: 2px;
            box-shadow: 0 0 6px var(--theme-accent-light);
            animation: blink .7s step-end infinite;
        }}

        /* -------------------------------------------------------------------
           Chat Input Styling (Ultra-Transparent Frosted Glass)
           ------------------------------------------------------------------- */
        [data-testid="stBottom"],
        [data-testid="stBottom"] > *,
        [data-testid="stBottom"] > * > *,
        [data-testid="stBottomBlockContainer"],
        [data-testid="stChatInputContainer"],
        .stChatFloatingInputContainer,
        div[data-testid="stBottom"],
        div[data-testid="stBottomBlockContainer"],
        footer {{
            background: transparent !important;
            background-color: transparent !important;
            background-image: none !important;
            box-shadow: none !important;
            border: none !important;
            overflow: visible !important;
        }}
        
        [data-testid="stChatInput"],
        .stChatInput,
        div:has(> [data-testid="stChatInput"]) {{
            background: transparent !important;
            background-color: transparent !important;
            box-shadow: none !important;
        }}

        [data-testid="stChatInput"] {{
            background: rgba(255, 255, 255, 0.04) !important;
            background-color: rgba(255, 255, 255, 0.04) !important;
            backdrop-filter: blur(28px) saturate(200%) !important;
            -webkit-backdrop-filter: blur(28px) saturate(200%) !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 24px !important;
            box-shadow: 0 10px 35px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.22) !important;
            padding: 3px 6px !important;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }}
        [data-testid="stChatInput"]:hover {{
            border-color: var(--theme-accent-border) !important;
            background: rgba(255, 255, 255, 0.06) !important;
            background-color: rgba(255, 255, 255, 0.06) !important;
        }}
        [data-testid="stChatInput"]:focus-within {{
            background: rgba(255, 255, 255, 0.08) !important;
            background-color: rgba(255, 255, 255, 0.08) !important;
            border-color: var(--theme-accent-light) !important;
            box-shadow: 0 0 30px var(--theme-accent-glow), 0 12px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        }}
        [data-testid="stChatInput"] div,
        [data-testid="stChatInput"] [data-baseweb="base-input"],
        [data-testid="stChatInput"] [data-baseweb="textarea"] {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        [data-testid="stChatInput"] textarea {{
            background: transparent !important;
            background-color: transparent !important;
            color: #ffffff !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 0.95rem !important;
            line-height: 1.55 !important;
            padding: 8px 12px !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }}
        [data-testid="stChatInput"] textarea::placeholder {{ 
            color: rgba(203, 213, 225, 0.6) !important; 
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }}
        [data-testid="stChatInput"] button {{
            background: var(--theme-accent-glow) !important;
            border: 1px solid var(--theme-accent-border) !important;
            border-radius: 50% !important;
            color: #c7d2fe !important;
            margin: auto 4px !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }}
        [data-testid="stChatInput"] button:hover {{
            background: var(--theme-user-bubble) !important;
            border-color: rgba(255, 255, 255, 0.5) !important;
            color: #ffffff !important;
            transform: scale(1.1) !important;
            box-shadow: 0 0 18px var(--theme-accent-glow) !important;
        }}

        /* -------------------------------------------------------------------
           Sidebar (Glassmorphism Control Center)
           ------------------------------------------------------------------- */
        [data-testid="stSidebar"] {{
            background: rgba(10, 13, 22, 0.88) !important;
            backdrop-filter: blur(24px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
            border-right: 1px solid var(--border-glass) !important;
            box-shadow: 4px 0 30px rgba(0, 0, 0, 0.4) !important;
        }}
        [data-testid="stSidebar"] * {{ 
            color: var(--text-main); 
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ 
            margin-bottom: .35rem; 
        }}
        section[data-testid="stSidebar"] > div {{ 
            padding-top: .8rem; 
        }}

        .side-hero {{
            position: relative;
            padding: 18px 16px 16px;
            margin: 0 0 14px;
            border-radius: 22px;
            background: linear-gradient(165deg, rgba(30, 36, 56, 0.7) 0%, rgba(16, 20, 32, 0.85) 100%);
            border: 1px solid var(--border-glass-bright);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12);
            overflow: hidden;
        }}
        .side-hero::after {{
            content: "";
            position: absolute; inset: auto 0 0 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--theme-accent), var(--cyan-light), transparent);
        }}
        .side-ava-wrap {{
            width: 86px; height: 86px; margin: 0 auto 10px; position: relative;
        }}
        .side-ava, .ph {{
            width: 86px; height: 86px; border-radius: 50%;
            background-color: #0f1320; background-size: cover; background-position: center;
            box-shadow: 0 0 0 2px var(--theme-accent-border), 0 0 22px var(--theme-accent-glow);
        }}
        .side-ring {{
            position: absolute; inset: -6px; border-radius: 50%;
            background: conic-gradient(from var(--spin), var(--theme-accent), var(--cyan-light), transparent 40%, var(--theme-accent-light), transparent 75%, var(--theme-accent));
            -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            animation: spinBorder 4.5s linear infinite;
            pointer-events: none;
        }}
        .ph {{
            display: grid; place-items: center;
            font-family: 'Outfit', sans-serif; color: #c7d2fe; font-weight: 800; font-size: 1.5rem;
        }}
        .side-name {{
            text-align: center; font-family: 'Outfit', sans-serif;
            font-size: 1.35rem; font-weight: 700; letter-spacing: -0.01em; color: #ffffff;
        }}
        .side-tag {{
            text-align: center; color: var(--text-muted); font-size: .8rem; margin-top: 2px;
            font-weight: 500;
        }}
        .side-online {{
            margin: 8px auto 0; width: fit-content;
            display: flex; align-items: center; gap: 7px;
            padding: 4px 12px; border-radius: 999px;
            background: rgba(16, 185, 129, .12);
            border: 1px solid rgba(52, 211, 153, .35);
            color: #6ee7b7; font-size: .76rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
        }}
        .side-online i {{
            width: 7px; height: 7px; border-radius: 50%; background: #34d399;
            box-shadow: 0 0 8px #34d399; animation: pulseDot 1.6s ease-in-out infinite;
        }}
        .side-grid {{
            display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;
        }}
        .tile {{
            padding: 10px 12px 11px; border-radius: 16px;
            background: rgba(22, 27, 42, 0.65);
            border: 1px solid var(--border-glass);
            backdrop-filter: blur(12px);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .tile:hover {{
            transform: translateY(-2px);
            border-color: var(--theme-accent-border);
        }}
        .tile em {{
            display: block; font-style: normal; font-size: .68rem;
            letter-spacing: .12em; color: var(--text-muted); margin-bottom: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
        }}
        .tile b {{ font-size: .88rem; color: #ffffff; font-weight: 700; font-family: 'Outfit', sans-serif; }}
        .tile.ok b {{ color: #6ee7b7; }}
        .tile.warn b {{ color: #fcd34d; }}
        .tile.err b {{ color: #fca5a5; }}
        .tile.ok {{ border-color: rgba(52, 211, 153, 0.25); }}
        .tile.warn {{ border-color: rgba(251,191,36,.3); }}
        .tile.err {{ border-color: rgba(251,113,133,.35); }}
        
        .side-panel {{
            padding: 14px; border-radius: 18px; margin-bottom: 12px;
            background: rgba(14, 18, 28, 0.65);
            border: 1px solid var(--border-glass);
            backdrop-filter: blur(12px);
        }}
        .side-panel-h {{
            font-family: 'JetBrains Mono', monospace; font-size: .72rem;
            letter-spacing: .14em; color: #c7d2fe; margin-bottom: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .kv {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 6px 0; border-bottom: 1px dashed rgba(255, 255, 255, 0.07);
            font-size: .84rem;
        }}
        .kv:last-child {{ border-bottom: 0; padding-bottom: 0; }}
        .kv span {{ color: var(--text-muted); }}
        .kv b {{
            color: #ffffff; background: var(--theme-accent-glow);
            border: 1px solid var(--theme-accent-border);
            border-radius: 999px; padding: 2px 9px; font-size: .74rem;
            font-family: 'JetBrains Mono', monospace;
        }}
        .side-quote {{
            margin: 0 0 12px; padding: 11px 13px; border-radius: 14px;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(56, 189, 248, 0.08) 100%);
            border: 1px solid var(--theme-accent-border);
            border-left: 3px solid var(--theme-accent-light);
            color: #e2e8f0; font-size: .8rem; line-height: 1.48;
        }}

        /* Sidebar Buttons */
        [data-testid="stSidebar"] .stButton > button {{
            background: rgba(22, 27, 42, 0.6) !important;
            color: var(--text-sub) !important;
            border: 1px solid var(--border-glass) !important;
            border-radius: 12px !important;
            text-align: left !important;
            font-size: 0.84rem !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            padding: 8px 12px !important;
            transition: all .2s cubic-bezier(0.16, 1, 0.3, 1) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            transform: translateY(-2px) !important; 
            color: #ffffff !important;
            border-color: var(--theme-accent-border) !important;
            background: rgba(30, 38, 58, 0.8) !important;
            box-shadow: 0 6px 20px var(--theme-accent-glow) !important;
        }}
# Di dalam fungsi set_ui_style()
def set_ui_style(theme_key: str = "violet") -> None:
    pal = THEMES.get(theme_key, THEMES["violet"])

    st.markdown(
        f"""
        <style>
        /* CSS diletakkan di dalam tanda <style> ini */
        .diag-box {{
            background: rgba(14, 18, 28, 0.75);
            border: 1px solid var(--border-glass-bright);
            border-radius: 16px;
            padding: 12px 14px;
            margin: 10px 0 8px;
            backdrop-filter: blur(14px);
        }}
        .diag-score-wrap {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
        }}
        .diag-score-num {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 800;
        }}
        .diag-score-num.ok {{ color: #6ee7b7; }}
        .diag-score-num.warn {{ color: #fcd34d; }}
        .diag-score-num.err {{ color: #fca5a5; }}

        .diag-bar-bg {{
            height: 5px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 99px;
            overflow: hidden;
            margin-bottom: 10px;
        }}
        .diag-bar-fill {{
            height: 100%;
            border-radius: 99px;
            transition: width 0.4s ease;
        }}
        .diag-bar-fill.ok {{ background: linear-gradient(90deg, #10b981, #34d399); }}
        .diag-bar-fill.warn {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
        .diag-bar-fill.err {{ background: linear-gradient(90deg, #ef4444, #f87171); }}

        .diag-item {{
            font-size: 0.76rem;
            color: var(--text-sub);
            line-height: 1.4;
            margin-bottom: 4px;
            padding-left: 12px;
            position: relative;
        }}
        .diag-item::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: var(--theme-accent-light);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
        /* Generic Buttons & Action Button */
        .stButton > button {{
            background: rgba(18, 22, 34, 0.8) !important; 
            color: var(--text-main) !important;
            border: 1px solid var(--border-glass-bright) !important; 
            border-radius: 12px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px) !important; 
            color: #ffffff !important;
            border-color: var(--theme-accent-border) !important;
            box-shadow: 0 6px 20px var(--theme-accent-glow) !important;
        }}
        button[data-testid="baseButton-primary"] {{
            min-height: 54px; 
            font-family: 'Outfit', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: .25em !important; 
            font-size: 1.05rem !important;
            border-radius: 999px !important;
            background: var(--theme-user-bubble) !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            box-shadow: 0 8px 30px var(--theme-accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }}
        button[data-testid="baseButton-primary"]:hover {{
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 12px 35px var(--theme-accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.4) !important;
        }}

        .aira-foot {{ 
            text-align: center; 
            color: var(--text-dim) !important; 
            font-size: .8rem; 
            margin-top: 24px;
            font-family: 'JetBrains Mono', monospace;
        }}

        /* -------------------------------------------------------------------
           Splash Screen (Modern AI Gate)
           ------------------------------------------------------------------- */
        .splash {{
            position: relative; z-index: 2;
            min-height: 88vh; display: flex; flex-direction: column;
            align-items: center; justify-content: center; text-align: center;
            overflow: hidden;
            padding: 20px 0;
        }}
        .splash-orb {{
            position: absolute; border-radius: 50%; filter: blur(30px);
            pointer-events: none; z-index: 0;
        }}
        .splash-orb.a {{
            width: 320px; height: 320px; top: 10%; left: 10%;
            background: radial-gradient(circle, var(--theme-accent-glow), transparent 68%);
            animation: orbFloat 8s ease-in-out infinite;
        }}
        .splash-orb.b {{
            width: 360px; height: 360px; right: 8%; bottom: 12%;
            background: radial-gradient(circle, rgba(56, 189, 248, 0.22), transparent 68%);
            animation: orbFloat 9.5s ease-in-out infinite reverse;
        }}
        .splash-card {{
            position: relative; z-index: 3; 
            width: min(580px, 94vw);
            padding: 36px 28px 32px;
            border-radius: 28px;
            background: linear-gradient(165deg, rgba(22, 27, 42, 0.75) 0%, rgba(12, 16, 26, 0.88) 100%);
            backdrop-filter: blur(28px) saturate(180%);
            -webkit-backdrop-filter: blur(28px) saturate(180%);
            border: 1px solid var(--border-glass-bright);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.14);
            animation: haloIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
        }}
        .splash-halo {{
            width: 170px; height: 170px; margin: 0 auto 12px; position: relative;
        }}
        .splash-halo::before {{
            content: ""; position: absolute; inset: 0; border-radius: 50%;
            background: conic-gradient(from var(--spin), var(--theme-accent), var(--cyan-light), transparent 40%, var(--theme-accent-light), transparent 80%, var(--theme-accent));
            -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            animation: spinBorder 4s linear infinite;
        }}
        .splash-halo::after {{
            content: ""; position: absolute; inset: 10px; border-radius: 50%;
            border: 1px dashed var(--theme-accent-border);
            animation: spinBorder 20s linear infinite reverse;
        }}
        .splash-logo {{
            position: absolute; inset: 0; display: grid; place-items: center;
            font-family: 'Outfit', sans-serif; font-weight: 800; line-height: .85;
            font-size: 2.8rem; color: #ffffff; letter-spacing: -.03em;
            text-shadow: 0 0 20px var(--theme-accent-glow);
            animation: logoPop 1.15s cubic-bezier(.16,1,.3,1) both;
        }}
        .splash-logo span {{ color: var(--theme-accent-light); font-size: .45em; margin-left: 2px; }}
        .splash-logo-img {{
            position: absolute; inset: 20px; border-radius: 50%;
            background: #080a10 center/contain no-repeat;
            box-shadow: 0 0 28px var(--theme-accent-glow);
            animation: logoPop 1.15s cubic-bezier(.16,1,.3,1) both;
            z-index: 2;
        }}
        .splash-brand {{
            margin-top: 10px; 
            letter-spacing: .35em; 
            font-size: .8rem; 
            color: #c7d2fe;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
        }}
        .splash-hello {{
            margin: 14px auto 0; max-width: 460px; color: var(--text-main);
            font-size: 1.12rem; line-height: 1.6;
            font-weight: 400;
        }}
        .splash-hello strong {{
            color: #ffffff;
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff, var(--theme-accent-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .boot {{
            width: min(440px, 90vw); margin: 18px auto 0; text-align: left;
            font-size: .78rem; color: var(--text-muted); line-height: 1.7;
            font-family: 'JetBrains Mono', monospace;
            background: rgba(8, 10, 16, 0.6);
            padding: 12px 16px;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }}
        .boot div {{
            opacity: 0; transform: translateY(6px);
            animation: bootLine .45s ease forwards;
        }}
        .boot div:nth-child(1) {{ animation-delay: .2s; }}
        .boot div:nth-child(2) {{ animation-delay: .45s; }}
        .boot div:nth-child(3) {{ animation-delay: .7s; }}
        .boot div:nth-child(4) {{ animation-delay: .95s; }}
        .boot b {{ color: #6ee7b7; }}
        .splash-hint {{
            margin-top: 12px; color: var(--text-dim); font-size: .76rem;
            letter-spacing: .18em; font-family: 'JetBrains Mono', monospace;
        }}
        .splash-miss {{
            margin-top: 8px; color: #fca5a5; font-size: .72rem; opacity: .85;
        }}

        /* -------------------------------------------------------------------
           Responsive Adjustments (Mobile & Tablet)
           ------------------------------------------------------------------- */
        @media (max-width: 640px) {{
            [data-testid="stMainBlockContainer"] {{
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-bottom: 6.5rem !important;
            }}
            .app-head {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
                padding: 12px 14px;
            }}
            .app-head-status {{
                align-self: flex-start;
            }}
            .wa-bubble-wrap {{
                max-width: 90%;
            }}
            .wa-bubble {{
                font-size: 0.91rem;
                padding: 11px 14px;
            }}
            .splash-card {{
                padding: 26px 18px 24px;
            }}
            .splash-halo {{
                width: 140px;
                height: 140px;
            }}
            .splash-logo {{
                font-size: 2.3rem;
            }}
            .boot {{
                font-size: 0.72rem;
                padding: 10px 12px;
            }}
            .topic-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        /* -------------------------------------------------------------------
           Keyframe Animations
           ------------------------------------------------------------------- */
        @keyframes spinBorder {{ to {{ --spin: 360deg; }} }}
        @keyframes blink {{ 50% {{ opacity: 0; }} }}
        @keyframes pulseDot {{ 50% {{ opacity: .35; transform: scale(.8); }} }}
        @keyframes dots {{
            0%   {{ content: ""; }}
            25%  {{ content: "."; }}
            50%  {{ content: ".."; }}
            75%  {{ content: "..."; }}
        }}
        @keyframes barRun {{
            0%   {{ transform: translateX(-120%); }}
            100% {{ transform: translateX(260%); }}
        }}
        @keyframes orbFloat {{
            0%,100% {{ transform: translate(0,0); }}
            50% {{ transform: translate(16px,-14px); }}
        }}
        @keyframes haloIn {{
            from {{ opacity: 0; transform: scale(.92) translateY(12px); }}
            to {{ opacity: 1; transform: none; }}
        }}
        @keyframes logoPop {{
            from {{ opacity: 0; transform: scale(.5); filter: blur(6px); }}
            to {{ opacity: 1; transform: none; filter: none; }}
        }}
        @keyframes bootLine {{ to {{ opacity: 1; transform: none; }} }}
        @keyframes bubbleFadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: none; }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            .pcb-glow, [data-testid="stChatInput"]::before,
            .splash-halo::before, .side-ring, .think-bar i, .think-dots::after,
            .cyber-particles {{
                animation: none !important;
            }}
        }}
        </style>
        <div class="cyber-particles" aria-hidden="true"></div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# PCB
# ---------------------------------------------------------------------------

def _pcb_pts(x: float, y: float, spec: str) -> List[Tuple[float, float]]:
    pts = [(x, y)]
    tok = spec.split()
    i = 0
    while i < len(tok):
        op, val = tok[i], float(tok[i + 1])
        i += 2
        if op == "H":
            x += val
        elif op == "V":
            y += val
        elif op == "SE":
            x += val
            y += val
        elif op == "NE":
            x += val
            y -= val
        elif op == "SW":
            x -= val
            y += val
        elif op == "NW":
            x -= val
            y -= val
        pts.append((x, y))
    return pts


def _d(x: float, y: float, spec: str) -> str:
    pts = _pcb_pts(x, y, spec)
    return "M " + " L ".join(f"{px:.0f} {py:.0f}" for px, py in pts)


_PCB_SPECS = [
    (-20, 28, "H 680"), (-20, 42, "H 540"), (-20, 56, "H 760"),
    (-20, 70, "H 420 SE 26 H 160"), (-20, 84, "H 820"), (-20, 98, "H 380"),
    (-20, 112, "H 600 V 32 H 140"), (-20, 126, "H 490"), (-20, 140, "H 700"),
    (-20, 154, "H 330 SE 34 H 200"), (-20, 168, "H 640"), (-20, 182, "H 450"),
    (-20, 196, "H 790"), (-20, 210, "H 290 V 46 H 240"), (-20, 224, "H 570"),
    (-20, 238, "H 440 SE 22 H 80"), (-20, 252, "H 680"), (-20, 266, "H 360"),
    (-20, 280, "H 620 V -36 H 110"), (-20, 294, "H 500"),
    (420, 70, "V 86 SE 36 H 70"), (600, 144, "V 66 SW 28 V 36"),
    (700, 196, "SE 46 H 130 V 32"), (290, 256, "V 76 SE 42 H 90"),
    (110, 336, "H 250 SE 54 H 170 NE 36 H 200"),
    (70, 366, "H 190 SE 74 V 46 H 150"),
    (190, 406, "H 320 NE 32 H 80 SE 46 H 120"),
    (30, 446, "H 170 V 66 H 220 SE 28 H 70"),
    (510, 356, "H 190 V 84 H 150 NE 40 H 60"),
    (690, 326, "SE 64 H 170 V 36 H 80"),
    (850, 296, "H 150 SE 32 H 190"),
    (930, 376, "H 210 V 56 SE 36 H 70"),
    (390, 496, "H 270 SE 50 H 180 V 28"),
    (150, 536, "H 200 NE 36 H 140 SE 64 H 90"),
    (610, 476, "V 76 H 130 SE 32 H 190"),
    (1610, 856, "H -210 NW 44 H -130 SW 32 H -170"),
    (1610, 834, "H -150 NW 64 H -80 SW 26 H -120"),
    (1610, 812, "H -290 NE 36 H -110 NW 46 H -70"),
    (1610, 790, "H -100 SW 56 H -190 NW 30 H -80"),
    (1610, 768, "H -240 NW 28 H -150"),
    (1610, 746, "H -70 NW 84 H -130 SE 36 H -90"),
    (1610, 724, "H -180 SW 40 H -60 NW 54 H -140"),
    (1610, 702, "H -320"),
    (1570, 680, "H -110 NW 50 H -190 V -36 H -70"),
    (1570, 658, "H -250 SE 28 H -80"),
    (1530, 636, "H -80 SW 64 H -170 NE 32 H -60"),
    (1490, 596, "H -150 NW 36 V -46 H -110"),
    (1470, 556, "H -210 SE 44 H -70 NW 26"),
    (1450, 516, "H -90 NE 54 H -160 SW 36 H -50"),
    (1510, 476, "H -230 V 32 H -80"),
    (1550, 436, "H -170 SE 46 H -130"),
    (1590, 396, "H -290 NW 26 H -70"),
    (1590, 356, "H -130 SW 54 H -190"),
    (1570, 316, "H -80 NE 40 H -220 SE 32"),
    (1170, 776, "NW 64 H -150 NE 36 H -80"),
    (1090, 696, "H -120 SW 46 H -70 V 36"),
    (1010, 616, "NE 32 H -140 SE 54 H -60"),
    (970, 816, "H -190 NW 44 V -26 H -80"),
    (870, 756, "SW 36 H -110 NE 64 H -50"),
    (810, 676, "H -80 V 76 H -130 SE 26"),
    (-10, 776, "H 230 SE 36 H 170 V 28 H 80"),
    (-10, 806, "H 310 NE 26 H 130"),
    (-10, 836, "H 170 SE 46 H 250 NW 18 H 70"),
    (-10, 866, "H 400"),
    (70, 716, "H 150 V 46 SE 32 H 110"),
    (190, 676, "SE 54 H 140 V 36 H 60"),
    (350, 736, "H 190 NE 36 H 80 SE 26"),
    (890, 36, "H 210 SE 32 H 150"),
    (970, 66, "H 170 V 40 H 130"),
    (1030, 106, "H 250 NE 22 H 70"),
    (1110, 146, "H 130 SE 46 H 180"),
    (1190, 196, "H 170 V -32 H 110"),
    (1270, 246, "SE 36 H 150 V 26"),
    (890, 176, "H 150 V 64 SE 26 H 70"),
    (750, 86, "H 120 SE 42 H 60"),
]

_PCB_GLOW = [
    ("c", -20, 56, "H 760"),
    ("p", 1610, 856, "H -210 NW 44 H -130 SW 32 H -170"),
    ("c", 110, 336, "H 250 SE 54 H 170 NE 36 H 200"),
    ("p", 390, 496, "H 270 SE 50 H 180 V 28"),
]


def _build_pcb() -> str:
    parts = ['<svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">']
    vias: List[Tuple[int, int]] = []
    for i, (x, y, spec) in enumerate(_PCB_SPECS):
        cls = "pcb-tr alt" if i % 3 == 0 else "pcb-tr"
        parts.append(f'<path class="{cls}" d="{_d(x, y, spec)}"/>')
        pts = _pcb_pts(x, y, spec)
        vias.append((int(pts[-1][0]), int(pts[-1][1])))
    for kind, x, y, spec in _PCB_GLOW:
        parts.append(f'<path class="pcb-glow {kind}" d="{_d(x, y, spec)}"/>')
    for vx, vy in vias[::3]:
        if -20 < vx < 1620 and -20 < vy < 920:
            parts.append(f'<circle class="pcb-pad" cx="{vx}" cy="{vy}" r="4.2"/>')
            parts.append(f'<circle class="pcb-hole" cx="{vx}" cy="{vy}" r="1.4"/>')
    parts.append("</svg>")
    return "".join(parts)


_PCB_SVG = _build_pcb()


def render_pcb_layer() -> None:
    st.markdown(f'<div class="pcb-layer" aria-hidden="true">{_PCB_SVG}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Konstanta & Teks
# ---------------------------------------------------------------------------

APP_TITLE = "Aira - Asisten AI-Chatbot By Ampera"
APP_TAGLINE = "Asisten AI-Chatbot Ciptaan Developer Solo Ampera · Siap bantu di perangkatmu"
WELCOME_TEXT = (
    "Hai, aku **Aira**! Asisten AI-Chatbot yang diciptakan dan dikembangkan secara mandiri oleh **Developer Solo Ampera** (Ampera Official / Ampera.ai).\n\n"
    "Aku siap bantu kamu seputar error Android, APK bandel, RAM mepet, optimasi sistem OS, maupun ngobrol santai. "
    "Percakapan kita berjalan privat di perangkatmu.\n\nTulis keluhanmu di bawah atau pilih kartu topik bantuan cepat!"
)
IDENTITY_REPLY = (
    "Aku **Aira**, asisten AI-Chatbot yang diciptakan dan dikembangkan secara mandiri oleh **Developer Solo Ampera** (Ampera Official / Ampera.ai).\n\n"
    "Aku dirancang agar ramah, cerdas, dan santai untuk membantu troubleshooting Android, manajemen sistem & RAM, serta pertanyaan sehari-hari secara privat di perangkatmu. "
    "Panggil aja Aira kapan pun kamu butuh!"
)
CREATOR_REPLY = (
    "Aku diciptakan dan dikembangkan secara mandiri oleh **Developer Solo Ampera** (Ampera Official / Ampera.ai)! ✨\n\n"
    "Beliau membangun aku sebagai asisten AI chatbot yang cerdas, ramah, dan privat untuk membantu berbagai hal, terutama troubleshooting Android, APK, optimasi RAM, dan teman diskusi sehari-hari."
)
PROVIDER_DISCLAIMER_REPLY = (
    "Bukan! Aku adalah **Aira**, asisten AI-Chatbot yang diciptakan dan dikembangkan secara mandiri oleh **Developer Solo Ampera** (Ampera Official / Ampera.ai)! ✨\n\n"
    "Jika sistem menggunakan Groq, itu hanyalah infrastruktur inferensi komputasi berkecepatan tinggi di balik layar, bukan penciptaku. Otak, kepribadian, desain, dan pengetahuan Aira dibangun sepenuhnya oleh Developer Solo Ampera."
)

TOPIC_LAUNCHERS = [
    {
        "icon": "📦",
        "title": "Troubleshoot APK",
        "desc": "Solusi Parse Error & gagal pasang paket instalasi APK / XAPK.",
        "prompt": "Kenapa APK gagal diinstall dan muncul pesan Parse Error?",
    },
    {
        "icon": "⚡",
        "title": "Optimasi RAM & Lag",
        "desc": "Cara mengatasi game keluar sendiri / multitasking reload.",
        "prompt": "Bagaimana cara mengatasi RAM penuh dan game yang sering keluar sendiri?",
    },
    {
        "icon": "🧹",
        "title": "Clear Cache vs Data",
        "desc": "Panduan aman membersihkan storage tanpa kehilangan file akun.",
        "prompt": "Apa bedanya Clear Cache sama Clear Data di Android?",
    },
    {
        "icon": "🛡️",
        "title": "Root & Keamanan",
        "desc": "Kupas tuntas konsep Root, Custom ROM, dan risikonya.",
        "prompt": "Apa itu Root dan Custom ROM di Android serta risikonya?",
    },
]

EXAMPLE_PROMPTS = [
    "Siapa kamu?",
    "Siapa yang menciptakan kamu?",
    "APK gagal install, Package Installer error",
    "RAM penuh, game keluar sendiri",
    "Bedanya RAM sama storage apa?",
]

_GREETING_EXACT = {
    "halo", "hai", "hay", "hi", "hello", "hey", "yo", "helo",
    "halo aira", "hai aira", "hay aira", "hi aira", "hello aira", "hey aira",
    "halo kak", "hai kak", "halo dong", "hai dong",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
    "pagi", "siang", "sore", "malam",
    "pagi aira", "siang aira", "sore aira", "malam aira",
    "selamat pagi aira", "selamat siang aira", "selamat sore aira",
    "selamat malam aira",
    "apa kabar", "apa kabar aira", "apakabar", "gimana kabar",
    "gimana kabarnya", "how are you", "halo halo", "hai hai",
}

_IDENTITY_RE = re.compile(
    r"^(?:"
    r"siapa\s+(?:kamu|kau|anda|namamu|nama\s+kamu|nama\s+anda|nama\s+mu)"
    r"|kamu\s+siapa|kau\s+siapa|namamu\s+siapa|nama\s+kamu\s+siapa|nama\s+anda\s+siapa"
    r"|kamu\s+ini\s+siapa|kamu\s+siapa\s+(?:sih|ya|dong)"
    r"|kenalan(?:\s+(?:dong|yuk|yu[k]|dulu))?"
    r"|perkenalkan(?:\s+diri(?:mu)?)?|perkenalan(?:\s+dong)?"
    r"|aira\s+itu\s+siapa|kamu\s+(?:robot|ai|asisten)(?:\s+ya)?|kamu\s+aira"
    r")$",
    re.IGNORECASE,
)

_PUNCT_RE = re.compile(r"[\"'`~!@#$%^&*()_+\-={}\[\]|\\:;<>?,./]+")
_SPACE_RE = re.compile(r"\s+")
MAX_HISTORY_FOR_LLM = 12
_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

THINK_STAGES_RAG = [
    ("Mencerna pertanyaan", "membaca input"),
    ("Mengurai konteks", "memetakan makna"),
    ("Menelusuri memori", "scan knowledge"),
    ("Berpikir", "menyusun nalar"),
    ("Menyusun jawaban", "menulis balasan"),
]
THINK_STAGES_FAST = [
    ("Mencerna sapaan", "mengenali pola"),
    ("Berpikir", "memilih nada"),
    ("Menyusun jawaban", "menulis balasan"),
]


def _normalize_intent_text(text: str) -> str:
    cleaned = (text or "").lower().strip()
    cleaned = _PUNCT_RE.sub(" ", cleaned)
    return _SPACE_RE.sub(" ", cleaned).strip()


def _daypart_label(now: Optional[datetime] = None) -> str:
    hour = (now or datetime.now()).hour
    if 4 <= hour < 11:
        return "pagi"
    if 11 <= hour < 15:
        return "siang"
    if 15 <= hour < 18:
        return "sore"
    return "malam"


def _greeting_reply(normalized: str) -> str:
    waktu = _daypart_label()
    if "pagi" in normalized:
        return "Selamat pagi! Aku Aira, asisten AI ciptaan Developer Solo Ampera. Semoga harinya lancar! Ada yang bisa aku bantu pagi ini?"
    if "siang" in normalized:
        return "Selamat siang! Aku Aira, asisten AI ciptaan Developer Solo Ampera. Mau dibantu apa hari ini?"
    if "sore" in normalized:
        return "Selamat sore! Aku Aira, asisten AI ciptaan Developer Solo Ampera. Ada yang mau ditanyakan?"
    if "malam" in normalized:
        return "Selamat malam! Aku Aira, asisten AI ciptaan Developer Solo Ampera. Masih semangat—mau dibantu apa?"
    if "kabar" in normalized:
        return "Kabar baik! Aira sehat dan selalu siap sedia bantu kamu. Ada kendala sistem atau mau ngobrol santai?"
    return f"Halo, selamat {waktu}! Aku Aira, asisten AI-Chatbot ciptaan Developer Solo Ampera. Mau tanya sesuatu atau ngobrol santai?"


def is_creator_query(text: str) -> bool:
    t = _normalize_intent_text(text)
    if not t:
        return False
    direct_words = [
        "nyiptain", "menciptakan", "ciptain", "pencipta", "pembuat", "developer",
        "creator", "programmer", "founder", "pendiri", "developer solo", "solo ampera",
        "menciptakanmu", "pembuatmu", "developermu", "creatormu", "penciptamu", "bikin kamu",
        "buat kamu", "ciptaanmu", "siapa ampera"
    ]
    for dw in direct_words:
        if dw in t:
            return True
    actions = ["dibuat", "diciptakan", "dibikin", "dikembangkan", "diprogram", "buatan", "ciptaan", "yang buat", "yang bikin", "yang ciptain", "coding", "desain", "mendesain"]
    questions = ["siapa", "siapakah", "mana", "orang", "asal", "ampera", "oleh", "sama", "dari"]
    if any(a in t for a in actions) and any(q in t for q in questions):
        return True
    if "ampera" in t and any(q in t for q in ["siapa", "apa itu", "maksudnya", "itu apa", "siapakah"]):
        return True
    return False


def is_identity_query(text: str) -> bool:
    t = _normalize_intent_text(text)
    if not t:
        return False
    identity_triggers = [
        "siapa kamu", "kamu siapa", "siapa anda", "anda siapa", "siapa namamu",
        "namamu siapa", "nama kamu siapa", "kamu ini siapa", "kamu sebenarnya siapa",
        "kamu ini apa", "kamu itu apa", "perkenalkan diri", "perkenalan", "kenalan",
        "siapa aira", "aira siapa", "aira itu siapa", "kamu ai apa", "kamu robot apa"
    ]
    for it in identity_triggers:
        if it in t:
            return True
    return bool(_IDENTITY_RE.match(t))


def is_provider_query(text: str) -> bool:
    t = _normalize_intent_text(text)
    if not t:
        return False
    return any(p in t for p in ["groq", "chatgpt", "openai", "meta ai", "gemini", "claude"])


def detect_intent_bypass(user_input: str) -> Optional[str]:
    text = _normalize_intent_text(user_input)
    if not text:
        return None
    if text in _GREETING_EXACT:
        return _greeting_reply(text)
    if is_provider_query(text) and ("siapa" in text or "kamu" in text or "apakah" in text or "dibuat" in text):
        return PROVIDER_DISCLAIMER_REPLY
    if is_creator_query(text):
        return CREATOR_REPLY
    if is_identity_query(text):
        return IDENTITY_REPLY
    return None


def get_last_bot_response(messages: List[Dict[str, str]]) -> str:
    for item in reversed(messages):
        if item.get("role") == "assistant":
            return str(item.get("content") or "")
    return ""


def history_for_llm(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    trimmed = [m for m in messages if m.get("role") in {"user", "assistant"}]
    if trimmed and trimmed[-1].get("role") == "user":
        trimmed = trimmed[:-1]
    if len(trimmed) > MAX_HISTORY_FOR_LLM:
        trimmed = trimmed[-MAX_HISTORY_FOR_LLM:]
    return trimmed


# ---------------------------------------------------------------------------
# Gambar & Media
# ---------------------------------------------------------------------------

def _asset_roots() -> List[str]:
    return [_BASE_DIR, os.path.join(_BASE_DIR, "assets"), os.getcwd()]


def _read_image(path: str) -> Dict[str, str]:
    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")
    with open(path, "rb") as fh:
        raw = fh.read()
    return {"mime": mime, "b64": base64.b64encode(raw).decode("ascii"), "path": path}


def _scan_image(exact_names: Tuple[str, ...], *needles: str) -> str:
    needles_l = [n.lower() for n in needles]
    for root in _asset_roots():
        if not root or not os.path.isdir(root):
            continue
        for name in exact_names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                return os.path.abspath(path)
        try:
            for fn in os.listdir(root):
                low = fn.lower()
                if not low.endswith(_IMG_EXT):
                    continue
                if all(n in low for n in needles_l):
                    return os.path.abspath(os.path.join(root, fn))
        except OSError:
            pass
    return ""


def find_profile_file() -> str:
    names = ("aira.jpg", "aira.jpeg", "aira.png", "aira.webp", "Aira.jpg", "Aira.JPG")
    return _scan_image(names, "aira")


def find_logo_file() -> str:
    names = (
        "logo ampera.jpg",
        "logo ampera.jpeg",
        "logo ampera.png",
        "logo ampera.webp",
        "logo_ampera.jpg",
        "logo_ampera.png",
        "logo-ampera.jpg",
        "Logo Ampera.jpg",
        "logoampera.jpg",
        "ampera.jpg",
        "ampera.png",
    )
    path = _scan_image(names, "logo", "ampera")
    return path or _scan_image(names, "ampera")


@st.cache_data(show_spinner=False)
def get_profile_image() -> Dict[str, str]:
    path = find_profile_file()
    return _read_image(path) if path else {"mime": "", "b64": "", "path": ""}


@st.cache_data(show_spinner=False)
def get_logo_image() -> Dict[str, str]:
    path = find_logo_file()
    return _read_image(path) if path else {"mime": "", "b64": "", "path": ""}


def inject_media_css(photo: Dict[str, str], logo: Dict[str, str]) -> None:
    rules = []
    if photo.get("b64"):
        url = f'data:{photo["mime"]};base64,{photo["b64"]}'
        rules.append(f".wa-avatar-aira,.side-ava{{background-image:url('{url}')!important;}}")
    if logo.get("b64"):
        url = f'data:{logo["mime"]};base64,{logo["b64"]}'
        rules.append(f".splash-logo-img,.app-logo.has-img{{background-image:url('{url}')!important;}}")
    if rules:
        st.markdown(f"<style>{''.join(rules)}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Markdown to HTML Formatter
# ---------------------------------------------------------------------------

def md_lite(text: str) -> str:
    if not text:
        return ""
    
    code_blocks = []
    def code_block_sub(match):
        lang = match.group(1) or ""
        code = match.group(2)
        code_blocks.append((lang, code))
        return f"@@@CODEBLOCK_{len(code_blocks)-1}@@@"
    
    processed = re.sub(r"```([a-zA-Z0-9_-]+)?\n?(.*?)```", code_block_sub, text, flags=re.DOTALL)
    lines = processed.split("\n")
    out_lines = []
    in_ul = False
    in_ol = False
    
    for line in lines:
        stripped = line.strip()
        
        if "@@@CODEBLOCK_" in stripped:
            if in_ul:
                out_lines.append("</ul>")
                in_ul = False
            if in_ol:
                out_lines.append("</ol>")
                in_ol = False
            out_lines.append(stripped)
            continue
            
        ul_match = re.match(r"^[*-]\s+(.+)$", stripped)
        if ul_match:
            if in_ol:
                out_lines.append("</ol>")
                in_ol = False
            if not in_ul:
                out_lines.append("<ul class=\"wa-list\">")
                in_ul = True
            content = html.escape(ul_match.group(1))
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"`([^`]+)`", r"<code>\1</code>", content)
            out_lines.append(f"<li>{content}</li>")
            continue
            
        ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ol_match:
            if in_ul:
                out_lines.append("</ul>")
                in_ul = False
            if not in_ol:
                out_lines.append("<ol class=\"wa-list\">")
                in_ol = True
            content = html.escape(ol_match.group(1))
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"`([^`]+)`", r"<code>\1</code>", content)
            out_lines.append(f"<li>{content}</li>")
            continue
            
        if in_ul:
            out_lines.append("</ul>")
            in_ul = False
        if in_ol:
            out_lines.append("</ol>")
            in_ol = False
            
        if not stripped:
            out_lines.append("<div class=\"wa-gap\"></div>")
            continue
            
        if stripped.startswith("> "):
            quote_text = html.escape(stripped[2:])
            quote_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", quote_text)
            quote_text = re.sub(r"`([^`]+)`", r"<code>\1</code>", quote_text)
            out_lines.append(f"<blockquote class=\"wa-quote\">{quote_text}</blockquote>")
            continue
            
        if stripped.startswith("### "):
            h_text = html.escape(stripped[4:])
            h_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", h_text)
            out_lines.append(f"<h4 class=\"wa-h4\">{h_text}</h4>")
            continue
        elif stripped.startswith("## "):
            h_text = html.escape(stripped[3:])
            h_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", h_text)
            out_lines.append(f"<h3 class=\"wa-h3\">{h_text}</h3>")
            continue
            
        esc = html.escape(line)
        esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
        esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
        out_lines.append(esc + "<br>")
    
    if in_ul:
        out_lines.append("</ul>")
    if in_ol:
        out_lines.append("</ol>")
        
    result = "\n".join(out_lines)
    result = re.sub(r"<br>\s*\n?(<ul|<ol|<blockquote|<div class=\"wa-gap\")", r"\n\1", result)
    result = re.sub(r"(</ul>|</ol>|</blockquote>|</div>)\s*<br>", r"\1", result)
    result = re.sub(r"<br>$", "", result.strip())
    
    for idx, (lang, code) in enumerate(code_blocks):
        lang_label = f"<span class=\"code-lang\">{html.escape(lang)}</span>" if lang else ""
        escaped_code = html.escape(code.strip())
        block_html = f'<div class="wa-code-wrap">{lang_label}<pre class="wa-code-block"><code>{escaped_code}</code></pre></div>'
        result = result.replace(f"@@@CODEBLOCK_{idx}@@@", block_html)
        
    return result


def aira_avatar_html(photo: Dict[str, str]) -> str:
    if photo.get("b64"):
        return '<div class="wa-avatar wa-avatar-aira" title="Aira"></div>'
    return '<div class="wa-avatar wa-avatar-aira wa-fallback">A</div>'


def build_wa_row(role: str, inner_html: str, photo: Dict[str, str], timestamp: str = "") -> str:
    t_str = timestamp or datetime.now().strftime("%H:%M")
    if role == "user":
        return (
            f'<div class="wa-row right">'
            f'<div class="wa-bubble-wrap">'
            f'<div class="wa-meta user">Kamu • {t_str}</div>'
            f'<div class="wa-bubble wa-user">{inner_html}</div>'
            f'</div>'
            f'<div class="wa-avatar wa-avatar-user">😎</div></div>'
        )
    return (
        f'<div class="wa-row left">{aira_avatar_html(photo)}'
        f'<div class="wa-bubble-wrap">'
        f'<div class="wa-meta">Aira • {t_str}</div>'
        f'<div class="wa-bubble wa-aira">{inner_html}</div>'
        f'</div></div>'
    )


def show_wa(role: str, text: str, photo: Dict[str, str], timestamp: str = "") -> None:
    st.markdown(build_wa_row(role, md_lite(text), photo, timestamp), unsafe_allow_html=True)


def render_think_html(stage: str, done: List[str], detail: str = "") -> str:
    logs = "".join(f'<div class="done">✓ {html.escape(item)}</div>' for item in done)
    logs += f'<div class="wait">› {html.escape(stage)}<span class="think-dots"></span></div>'
    return (
        '<div class="think">'
        '<div class="think-head"><span class="think-orb"></span>AIRA · NEURAL PROCESSING</div>'
        f'<div class="think-now">sedang <b>{html.escape(stage.lower())}</b></div>'
        f'<div class="think-log">{logs}</div>'
        '<div class="think-bar"><i></i></div>'
        "</div>"
    )


def show_think(
    box: Any,
    photo: Dict[str, str],
    stage: str,
    done: List[str],
    hold: float = 0.32,
) -> None:
    box.markdown(
        build_wa_row("assistant", render_think_html(stage, done), photo),
        unsafe_allow_html=True,
    )
    if hold > 0:
        time.sleep(hold)


def stream_reply(box: Any, photo: Dict[str, str], answer: str) -> None:
    """Tampilkan balasan perlahan dengan efek typewriter yang halus."""
    text = answer or ""
    tokens = re.findall(r"\S+\s*", text)
    if len(tokens) <= 4:
        box.markdown(build_wa_row("assistant", md_lite(text), photo), unsafe_allow_html=True)
        return

    step = 2 if len(tokens) < 70 else 4
    acc = ""
    for i, tok in enumerate(tokens, 1):
        acc += tok
        if i % step == 0 or i == len(tokens):
            caret = "" if i == len(tokens) else '<span class="type-caret"></span>'
            box.markdown(
                build_wa_row("assistant", md_lite(acc) + caret, photo),
                unsafe_allow_html=True,
            )
            if i != len(tokens):
                time.sleep(0.022 if step == 2 else 0.014)

    box.markdown(build_wa_row("assistant", md_lite(text), photo), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Resource & State
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Menyiapkan Neural Engine Aira...")
def get_cached_llm() -> Dict[str, Any]:
    payload: Dict[str, Any] = {"llm": None, "mode": "error", "error": "", "path": DEFAULT_MODEL_PATH}
    try:
        llm = load_model(model_path=DEFAULT_MODEL_PATH)
        payload["llm"] = llm
        payload["mode"] = "gguf" if getattr(llm, "model_name", "") != "llama-3.3-70b-versatile" else "Groq Engine"
        payload["path"] = getattr(llm, "aira_model_path", DEFAULT_MODEL_PATH)
        return payload
    except (ModelNotFoundError, FileNotFoundError, ImportError, RuntimeError) as exc:
        payload["error"] = str(exc).split("\n")[0]
        try:
            mock = load_model_or_mock(model_path=DEFAULT_MODEL_PATH)
            payload["llm"] = mock
            payload["mode"] = "mock" if mock is not None else "error"
            return payload
        except Exception as exc2:
            payload["error"] = f"{payload['error']} | fallback gagal: {exc2}"
            return payload
    except Exception as exc:
        payload["error"] = f"{exc.__class__.__name__}: {exc}"
        return payload


@st.cache_data(show_spinner=False)
def get_kb_status() -> Dict[str, Any]:
    path = DEFAULT_KB_PATH
    info: Dict[str, Any] = {"path": path, "exists": os.path.isfile(path), "count": 0, "error": SEARCH_IMPORT_ERROR}
    if not info["exists"]:
        return info
    try:
        info["count"] = len(load_knowledge(path))
    except Exception as exc:
        info["error"] = str(exc)
    return info


def warmup_retriever() -> Tuple[bool, str]:
    try:
        from search_engine import get_engine  # type: ignore
        get_engine()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def init_session_state() -> None:
    if "entered_app" not in st.session_state:
        st.session_state.entered_app = False
    if "theme_accent" not in st.session_state:
        st.session_state.theme_accent = "violet"
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": WELCOME_TEXT,
            "time": datetime.now().strftime("%H:%M")
        }]
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = ""
    if "last_debug" not in st.session_state:
        st.session_state.last_debug = {"bypass": False, "resolved_query": "", "context": ""}


def ensure_runtime_ready() -> None:
    if "retriever_ready" not in st.session_state:
        ok, err = warmup_retriever()
        st.session_state.retriever_ready = ok
        st.session_state.retriever_error = err


def reset_conversation() -> None:
    st.session_state.messages = [{
        "role": "assistant",
        "content": WELCOME_TEXT,
        "time": datetime.now().strftime("%H:%M")
    }]
    st.session_state.last_debug = {"bypass": False, "resolved_query": "", "context": ""}
    st.session_state.pending_prompt = ""


def queue_example(prompt: str) -> None:
    st.session_state.pending_prompt = prompt


def get_chat_export_text() -> str:
    lines = [
        "# Riwayat Obrolan Aira - Asisten AI-Chatbot",
        f"# Tanggal Ekspor: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "# Developer: Developer Solo Ampera (Ampera Official)",
        "# Sistem: Neural Engine & Private Local Memory\n",
        "---\n"
    ]
    for m in st.session_state.get("messages", []):
        role_label = "👤 Pengguna" if m.get("role") == "user" else "💮 Aira"
        time_tag = f" [{m.get('time', '')}]" if m.get("time") else ""
        lines.append(f"### {role_label}{time_tag}\n")
        lines.append(m.get("content", "").strip())
        lines.append("\n\n---\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# RAG Pipeline
# ---------------------------------------------------------------------------

def run_rag_pipeline(user_input: str, last_bot_response: str, llm: Any) -> Tuple[str, str, str]:
    resolved, context = user_input, ""
    try:
        resolved = resolve_query(user_input, last_bot_response=last_bot_response) or user_input
    except Exception:
        resolved = user_input
    try:
        context = search_knowledge(resolved) or ""
    except Exception:
        context = ""
    reply = generate_aira_response(
        llm=llm,
        user_input=user_input,
        context=context,
        history=history_for_llm(st.session_state.messages),
    )
    return (reply or "").strip(), resolved, context


def handle_user_message(user_input: str, llm: Any, photo: Dict[str, str]) -> None:
    text = (user_input or "").strip()
    if not text:
        return

    curr_time = datetime.now().strftime("%H:%M")
    last_bot = get_last_bot_response(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": text, "time": curr_time})
    show_wa("user", text, photo, curr_time)

    box = st.empty()
    bypass_reply = detect_intent_bypass(text)
    stages = THINK_STAGES_FAST if bypass_reply else THINK_STAGES_RAG
    done: List[str] = []

        /* RAM Diagnostic Widget Styling */
        .diag-box {{
            background: rgba(14, 18, 28, 0.75);
            border: 1px solid var(--border-glass-bright);
            border-radius: 16px;
            padding: 12px 14px;
            margin: 10px 0 8px;
            backdrop-filter: blur(14px);
        }}
        .diag-score-wrap {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
        }}
        .diag-score-num {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 800;
        }}
        .diag-score-num.ok {{ color: #6ee7b7; }}
        .diag-score-num.warn {{ color: #fcd34d; }}
        .diag-score-num.err {{ color: #fca5a5; }}

        .diag-bar-bg {{
            height: 5px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 99px;
            overflow: hidden;
            margin-bottom: 10px;
        }}
        .diag-bar-fill {{
            height: 100%;
            border-radius: 99px;
            transition: width 0.4s ease;
        }}
        .diag-bar-fill.ok {{ background: linear-gradient(90deg, #10b981, #34d399); }}
        .diag-bar-fill.warn {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
        .diag-bar-fill.err {{ background: linear-gradient(90deg, #ef4444, #f87171); }}

        .diag-item {{
            font-size: 0.76rem;
            color: var(--text-sub);
            line-height: 1.4;
            margin-bottom: 4px;
            padding-left: 12px;
            position: relative;
        }}
        .diag-item::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: var(--theme-accent-light);
        }}     
    # Animasi jeda berpikir neural
    show_think(box, photo, stages[0][0], done, 0.35)
    done.append(stages[0][0])
    show_think(box, photo, stages[1][0], done, 0.35)
    done.append(stages[1][0])

    if bypass_reply:
        answer = bypass_reply
        if len(stages) > 2:
            show_think(box, photo, stages[2][0], done, 0.20)
        st.session_state.last_debug = {
            "bypass": True, "resolved_query": text, "context": "(dilewati — intent sapaan/identitas)"
        }
    else:
        show_think(box, photo, stages[2][0], done, 0.35)
        done.append(stages[2][0])
        show_think(box, photo, stages[3][0], done, 0.35)
        try:
            answer, resolved, context = run_rag_pipeline(text, last_bot, llm)
        except Exception as exc:
            traceback.print_exc()
            answer = f"Ada kendala teknis saat memproses jawaban: `{exc.__class__.__name__}`"
            resolved, context = text, ""
        if not answer:
            answer = "Hmm, Aira belum tau jawabannya. Bisa coba tanyakan dengan kalimat lain?"
        done.append(stages[3][0])
        show_think(box, photo, stages[4][0], done, 0.35)
        st.session_state.last_debug = {"bypass": False, "resolved_query": resolved, "context": context}

    stream_reply(box, photo, answer)
    ans_time = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "assistant", "content": answer, "time": ans_time})


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def render_topic_cards() -> None:
    """Menampilkan kartu topik diagnosa cepat jika percakapan masih baru."""
    if len(st.session_state.messages) > 1:
        return

    st.markdown(
        """
        <div style="margin-top: 8px; margin-bottom: 6px;">
          <div style="font-family:'JetBrains Mono',monospace; font-size:0.74rem; letter-spacing:0.12em; color:var(--text-dim); text-transform:uppercase; font-weight:700;">
            ⚡ DIAGNOSA & BANTUAN CEPAT
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for idx, card in enumerate(TOPIC_LAUNCHERS):
        with cols[idx % 2]:
            st.markdown(
                f"""
                <div class="topic-card">
                  <div class="topic-card-icon">{card['icon']}</div>
                  <div class="topic-card-title">{html.escape(card['title'])}</div>
                  <div class="topic-card-desc">{html.escape(card['desc'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Pilih {card['title']}", key=f"topic_btn_{idx}", use_container_width=True):
                queue_example(card["prompt"])
                st.rerun()


def render_sidebar(model_info: Dict[str, Any], photo: Dict[str, str]) -> None:
    kb = get_kb_status()
    mode = model_info.get("mode", "error")

    if mode in ["gguf", "Groq Engine"]:
        model_tile, model_label = "ok", "Aktif"
    elif mode == "mock":
        model_tile, model_label = "warn", "KB Active"
    else:
        model_tile, model_label = "err", "Offline"

    mem_ok = bool(kb["exists"] and kb["count"] > 0)
    mem_tile = "ok" if mem_ok else "warn"
    mem_label = f"{kb.get('count', 0)} Entri" if mem_ok else "Kosong"
    ava = '<div class="side-ava"></div>' if photo.get("b64") else '<div class="ph">A</div>'

    with st.sidebar:
        st.markdown(
            f"""
            <div class="side-hero">
              <div class="side-ava-wrap">
                {ava}
                <div class="side-ring"></div>
              </div>
              <div class="side-name">Aira AI</div>
              <div class="side-tag">Ciptaan Developer Solo Ampera</div>
              <div class="side-online"><i></i> online · Neural Bus</div>
            </div>
            <div class="side-grid">
              <div class="tile {model_tile}"><em>MODEL</em><b>{html.escape(model_label)}</b></div>
              <div class="tile {mem_tile}"><em>MEMORI</em><b>{html.escape(mem_label)}</b></div>
            </div>
            <div class="side-quote">Diciptakan secara mandiri oleh Developer Solo Ampera untuk membantu masalah Android, APK, RAM, atau ngobrol santai secara privat di perangkatmu.</div>
            <div class="side-panel">
              <div class="side-panel-h">STATUS SISTEM</div>
              <div class="kv"><span>Developer</span><b>Solo Ampera</b></div>
              <div class="kv"><span>Mode Engine</span><b>{html.escape(str(mode))}</b></div>
              <div class="kv"><span>Knowledge Base</span><b>{kb.get('count', 0)} item</b></div>
              <div class="kv"><span>Privasi</span><b>Lokal / Privat</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="side-panel-h" style="margin:14px 0 6px;">🎨 TEMA AKSEN</div>', unsafe_allow_html=True)
        theme_keys = list(THEMES.keys())
        theme_labels = [THEMES[k]["name"] for k in theme_keys]
        current_idx = theme_keys.index(st.session_state.get("theme_accent", "violet"))
        
        selected_label = st.selectbox(
            "Pilih Tema Visual",
            options=theme_labels,
            index=current_idx,
            label_visibility="collapsed",
            key="theme_selector"
        )
        for k, v in THEMES.items():
            if v["name"] == selected_label and st.session_state.theme_accent != k:
                st.session_state.theme_accent = k
                st.rerun()

        st.markdown('<div class="side-panel-h" style="margin:14px 0 6px;">🛠️ ALAT & KONTROL</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✦ Obrolan Baru", use_container_width=True, key="btn_reset"):
                reset_conversation()
                st.rerun()
        with c2:
            st.download_button(
                label="📥 Unduh Chat",
                data=get_chat_export_text(),
                file_name=f"aira-chat-{datetime.now().strftime('%Y%m%d-%H%M')}.md",
                mime="text/markdown",
                use_container_width=True,
                key="btn_dl_chat",
            )

        st.markdown(
            '<div class="side-panel-h" style="margin:16px 0 8px;">PROMPT CEPAT</div>',
            unsafe_allow_html=True,
        )
        for sample in EXAMPLE_PROMPTS:
            if st.button(f"› {sample}", use_container_width=True, key=f"ex_{sample}"):
                queue_example(sample)
                st.rerun()


def render_header(logo: Dict[str, str]) -> None:
    mark = (
        '<div class="app-logo has-img" title="Developer Solo Ampera"></div>'
        if logo.get("b64")
        else '<div class="app-logo">A<span>.ai</span></div>'
    )
    st.markdown(
        f"""
        <div class="app-head">
          <div class="app-head-left">
            {mark}
            <div>
              <h1>Aira AI</h1>
              <p>Asisten AI-Chatbot Ciptaan Developer Solo Ampera</p>
            </div>
          </div>
          <div class="app-head-status">
            <i></i> Siap Bantu
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_history(photo: Dict[str, str]) -> None:
    chunks = [
        build_wa_row(
            item.get("role", "assistant"),
            md_lite(item.get("content") or ""),
            photo,
            item.get("time", "")
        )
        for item in st.session_state.messages
    ]
    st.markdown(f'<div class="wa-thread">{"".join(chunks)}</div>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown('<p class="aira-foot">Aira · Asisten AI-Chatbot Ciptaan Developer Solo Ampera · Edition 2026</p>', unsafe_allow_html=True)


def render_splash(logo: Dict[str, str]) -> None:
    if logo.get("b64"):
        mark = '<div class="splash-logo-img" title="Developer Solo Ampera"></div>'
        miss = ""
    else:
        mark = '<div class="splash-logo">A<span>.ai</span></div>'
        miss = '<div class="splash-miss">Logo belum ketemu. Taruh file <b>logo ampera.jpg</b> di folder app.</div>'

    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stHeader"] {{ display: none !important; }}
        [data-testid="stMainBlockContainer"] {{ max-width: 740px; padding-top: 0 !important; }}
        </style>
        <div class="splash">
          <div class="splash-orb a"></div>
          <div class="splash-orb b"></div>
          <div class="splash-card">
            <div class="splash-halo">{mark}</div>
            <div class="splash-brand">DEVELOPER SOLO AMPERA</div>
            <div class="boot">
              <div>&gt; initialize neural bus ......... <b>READY</b></div>
              <div>&gt; load knowledge base .......... <b>OK</b></div>
              <div>&gt; connect aira persona ......... <b>GRANTED</b></div>
              <div>&gt; secure session status ........ <b>ONLINE</b></div>
            </div>
            <p class="splash-hello">
              Selamat datang di asisten AI chatbot ciptaan<br><strong>Developer Solo Ampera</strong>
            </p>
            <div class="splash-hint">TEKAN TOMBOL DI BAWAH UNTUK MASUK</div>
            {miss}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _l, mid, _r = st.columns([1, 1.2, 1])
    with mid:
        if st.button("MASUK", type="primary", use_container_width=True, key="btn_masuk"):
            st.session_state.entered_app = True
            st.rerun()


# ---------------------------------------------------------------------------
# Main Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    init_session_state()
    theme_key = st.session_state.get("theme_accent", "violet")
    set_ui_style(theme_key)
    render_pcb_layer()

    logo = get_logo_image()
    inject_media_css({"mime": "", "b64": "", "path": ""}, logo)

    if not st.session_state.entered_app:
        render_splash(logo)
        return

    ensure_runtime_ready()
    photo = get_profile_image()
    inject_media_css(photo, logo)
    model_info = get_cached_llm()

    render_sidebar(model_info, photo)
    render_header(logo)
    render_history(photo)
    render_topic_cards()

    typed = st.chat_input("Tulis pesan untuk Aira…")
    pending = (st.session_state.get("pending_prompt") or "").strip()
    if pending:
        st.session_state.pending_prompt = ""

    user_text = (typed or pending or "").strip()
    if user_text:
        handle_user_message(user_text, llm=model_info.get("llm"), photo=photo)

    render_footer()


if __name__ == "__main__":
    main()
